"""Functional governance, retrieval, and CLI tests."""

import subprocess
import sys

import pytest
import yaml

from council.cli import main
from council.context import assemble, route
from council.store import CouncilError, read_record, render_record, safe_path, yaml_load
from council.validation import check_schema, validate


def invoke(repo, *args):
    """Invoke the real parser with an explicit repository."""
    return main(["--root", str(repo), *args])


def memory(repo, **changes):
    """Create a reviewable fixture without asserting scientific truth."""
    meta, body = read_record(repo / "templates/examples/memory.md")
    meta.update(changes)
    owner = meta["owner"]
    folder = "memory/shared/proposed" if owner == "shared" else f"memory/agents/{owner}"
    path = repo / folder / f"{meta['id']}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_record(meta, body), encoding="utf-8")
    return path, meta


def accepted(agent="vera", **changes):
    """Return structural review test data, explicitly confined to fixtures."""
    review = dict(
        agent=agent,
        decision="accept",
        date="2026-09-29",
        evidence_refs=["evaluations/scenarios/oti-fd-disagreement.md"],
        notes="Fixture reviewer is separate from author; structural test only.",
    )
    review.update(changes)
    return review


def test_seed_and_examples_validate(repo):
    assert validate(repo) == []
    for name, kind in (
        ("memory", "memory"),
        ("reflection", "reflection"),
        ("identity-amendment", "amendment"),
    ):
        meta, _ = read_record(repo / f"templates/examples/{name}.md")
        assert check_schema(repo, kind, meta) == []
    assert len(yaml_load(repo / "council.yaml")["agents"]) == 10


@pytest.mark.parametrize(
    "args",
    [
        ["remember", "--agent", "gauss", "--project", "council-bootstrap", "--type", "procedural"],
        ["reflect", "--agent", "vera", "--project", "council-bootstrap"],
        ["propose-identity-change", "--agent", "vera"],
        ["init-project", "--project", "umat-oti"],
    ],
)
def test_dry_runs_never_write(repo, args):
    before = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert invoke(repo, *args, "--dry-run") == 0
    after = {p.relative_to(repo): p.read_bytes() for p in repo.rglob("*") if p.is_file()}
    assert before == after


def test_creation_and_amendment_preserve_identity(repo):
    before = (repo / "members/vera/identity.md").read_bytes()
    assert invoke(repo, "init-project", "--project", "umat-oti") == 0
    assert (
        invoke(
            repo, "remember", "--agent", "gauss", "--project", "umat-oti", "--type", "procedural"
        )
        == 0
    )
    assert invoke(repo, "reflect", "--agent", "vera", "--project", "umat-oti") == 0
    assert invoke(repo, "propose-identity-change", "--agent", "vera") == 0
    assert before == (repo / "members/vera/identity.md").read_bytes()
    assert validate(repo) == []
    assert invoke(repo, "init-project", "--project", "umat-oti") == 2


def test_promotion_requires_independent_evidence_then_separate_adoption(repo):
    path, meta = memory(repo)
    mid = meta["id"]
    assert invoke(repo, "promote-memory", "--id", mid) == 2
    meta["reviewers"] = [accepted("gauss")]
    path.write_text(render_record(meta, "Fixture"), encoding="utf-8")
    assert invoke(repo, "promote-memory", "--id", mid) == 2
    meta["reviewers"] = [accepted()]
    path.write_text(render_record(meta, "Fixture"), encoding="utf-8")
    assert invoke(repo, "promote-memory", "--id", mid, "--to", "adopted") == 2
    assert invoke(repo, "promote-memory", "--id", mid, "--dry-run") == 0
    assert read_record(path)[0]["status"] == "proposed"
    assert invoke(repo, "promote-memory", "--id", mid) == 0
    assert read_record(path)[0]["status"] == "verified"
    assert invoke(repo, "promote-memory", "--id", mid, "--to", "adopted") == 0
    assert read_record(path)[0]["status"] == "adopted"


@pytest.mark.parametrize(
    "reviews",
    [
        [accepted(evidence_refs=[])],
        [accepted(evidence_refs=["README.md"])],
        [accepted(), accepted("curie", decision="request-changes")],
        [accepted("unknown")],
    ],
)
def test_invalid_reviews_block_promotion(repo, reviews):
    _, meta = memory(repo, reviewers=reviews)
    assert invoke(repo, "promote-memory", "--id", meta["id"]) == 2


@pytest.mark.parametrize(
    "change,fragment",
    [
        ({"status": "certain"}, "status"),
        ({"confidence": 1.1}, "confidence"),
        ({"contradicts": ["missing-id"]}, "contradicts"),
        ({"evidence": [{"ref": "missing.txt", "detail": "Missing"}]}, "broken evidence"),
        ({"project": "missing"}, "Unknown project"),
        ({"created": "yesterday"}, "created"),
        ({"status": "adopted"}, "independent"),
        ({"status": "superseded"}, "superseded_by"),
    ],
)
def test_invalid_memories_fail_validation(repo, change, fragment):
    memory(repo, **change)
    assert any(fragment in error for error in validate(repo))


def test_duplicate_ids_and_versions_are_detected(repo):
    path, _ = memory(repo)
    (path.parent / "other.md").write_bytes(path.read_bytes())
    assert any("Duplicate ID" in error for error in validate(repo))
    beliefs = repo / "members/gauss/operating-beliefs.yaml"
    data = yaml_load(beliefs)
    data["identity_version"] = "9.0"
    beliefs.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert any("version mismatch" in error for error in validate(repo))


def test_context_filters_scope_status_owner_and_relevance(repo):
    reviews = [accepted()]
    memory(repo, id="mem-adopted", status="adopted", reviewers=reviews)
    memory(repo, id="mem-verified", status="verified", reviewers=reviews)
    memory(repo, id="mem-proposed")
    memory(repo, id="mem-deprecated", status="deprecated")
    memory(
        repo,
        id="mem-irrelevant",
        status="adopted",
        reviewers=reviews,
        tags=["fonts"],
        observation="Use large lettering",
    )
    memory(
        repo,
        id="mem-other-owner",
        owner="curie",
        author="curie",
        status="adopted",
        reviewers=reviews,
    )
    assert invoke(repo, "init-project", "--project", "other-project") == 0
    memory(
        repo, id="mem-other-project", project="other-project", status="adopted", reviewers=reviews
    )
    memory(
        repo,
        id="mem-general",
        project="other-project",
        scope="general",
        status="adopted",
        reviewers=reviews,
    )
    bundle = assemble(repo, "gauss", "council-bootstrap", "FD sensitivity")
    for mid in ("mem-adopted", "mem-verified", "mem-general"):
        assert mid in bundle
    for mid in (
        "mem-proposed",
        "mem-deprecated",
        "mem-irrelevant",
        "mem-other-owner",
        "mem-other-project",
    ):
        assert mid not in bundle
    assert "Verified observation; not adopted" in bundle
    assert "constitution/permissions.md" in bundle
    assert "members/gauss/identity.md" in bundle
    assert "projects/council-bootstrap/brief.md" in bundle


def test_context_surfaces_conflict_without_promoting_candidate(repo):
    memory(repo, id="mem-trusted", status="adopted", reviewers=[accepted()])
    memory(repo, id="mem-conflicting", contradicts=["mem-trusted"])
    bundle = assemble(repo, "gauss", "council-bootstrap", "FD")
    assert "Conflict remains visible: mem-conflicting (proposed)" in bundle


@pytest.mark.parametrize(
    "task,required,absent",
    [
        ("verify OTI sensitivities", {"gauss", "vera"}, {"iris", "scout"}),
        ("implement Fortran HPC code", {"ada", "vera"}, {"iris", "curie"}),
        ("write presentation slides", {"iris"}, {"ada", "gauss", "vera"}),
        ("research primary literature", {"scout"}, {"curie", "gauss"}),
    ],
)
def test_routing_is_small_and_explained(task, required, absent):
    result = route(task)
    names = {item["agent"] for item in result}
    assert required <= names
    assert not names & absent
    assert all(item["reason"] for item in result)


@pytest.mark.parametrize("unsafe", ["../outside", "/outside", "a/../../b"])
def test_paths_reject_traversal(repo, unsafe):
    with pytest.raises(CouncilError):
        safe_path(repo, unsafe)
    assert invoke(repo, "init-project", "--project", unsafe) == 2


def test_symlink_escape(repo, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    link = repo / "escape"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("OS does not grant symlink creation to this test user")
    with pytest.raises(CouncilError):
        safe_path(repo, "escape/record.md")


def test_bad_inputs_return_concise_errors(repo, capsys):
    assert (
        invoke(
            repo,
            "remember",
            "--agent",
            "nobody",
            "--project",
            "council-bootstrap",
            "--type",
            "episodic",
        )
        == 2
    )
    assert "Unknown agent" in capsys.readouterr().err
    assert invoke(repo, "assemble", "--agent", "gauss", "--project", "missing", "--task", "fd") == 2
    assert (
        invoke(
            repo,
            "remember",
            "--agent",
            "gauss",
            "--project",
            "council-bootstrap",
            "--type",
            "episodic",
            "--confidence",
            "2",
        )
        == 2
    )


def test_cli_from_clean_external_directory(repo, tmp_path):
    working = tmp_path / "empty"
    working.mkdir()
    for args in (
        ["validate"],
        ["list-agents"],
        ["route", "--task", "OTI verification"],
        ["assemble", "--agent", "vera", "--project", "council-bootstrap", "--task", "verification"],
    ):
        result = subprocess.run(
            [sys.executable, "-m", "council", "--root", str(repo), *args],
            cwd=working,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip()
    assert list(working.iterdir()) == []


def test_amendment_validation_blocks_unreviewed_foundational_approval(repo):
    assert invoke(repo, "propose-identity-change", "--agent", "vera", "--foundational") == 0
    path = next((repo / "members/vera/identity-amendments").glob("*.md"))
    data, body = read_record(path)
    data.update(approval_status="approved", approved_by="atlas")
    path.write_text(render_record(data, body), encoding="utf-8")
    errors = validate(repo)
    assert any("Foundational" in e for e in errors)
    assert any("Incomplete amendment" in e for e in errors)


def test_output_cannot_overwrite(repo):
    path = repo / "existing.md"
    path.write_text("preserve", encoding="utf-8")
    assert (
        invoke(
            repo,
            "assemble",
            "--agent",
            "gauss",
            "--project",
            "council-bootstrap",
            "--task",
            "fd",
            "--output",
            "existing.md",
        )
        == 2
    )
    assert path.read_text() == "preserve"


def test_duplicate_yaml_keys_and_inline_delimiters(repo):
    path, meta = memory(repo, observation="A --- separator inside a lesson is ordinary text.")
    assert read_record(path)[0]["observation"] == meta["observation"]
    text = path.read_text(encoding="utf-8").replace(
        "status: proposed", "status: proposed\nstatus: adopted"
    )
    path.write_text(text, encoding="utf-8")
    assert any("Duplicate" in e for e in validate(repo))


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_nonfinite_confidence_is_rejected(repo, value):
    assert (
        invoke(
            repo,
            "remember",
            "--agent",
            "gauss",
            "--project",
            "council-bootstrap",
            "--type",
            "procedural",
            f"--confidence={value}",
        )
        == 2
    )


def test_supersession_cycles_fail(repo):
    memory(
        repo, id="mem-one", status="superseded", supersedes=["mem-two"], superseded_by=["mem-two"]
    )
    memory(
        repo, id="mem-two", status="superseded", supersedes=["mem-one"], superseded_by=["mem-one"]
    )
    assert any("cycle" in e for e in validate(repo))


def test_required_governance_file_cannot_silently_disappear(repo):
    (repo / "constitution/permissions.md").rename(repo / "constitution/permissions.backup")
    assert any("Missing constitution/permissions.md" in e for e in validate(repo))


def test_https_locators_do_not_allow_embedded_credentials(repo):
    _, meta = memory(
        repo,
        evidence=[{"ref": "https://name:password@example.invalid/evidence", "detail": "Fixture"}],
    )
    assert any("broken evidence" in e for e in validate(repo))


def test_applied_amendment_cannot_claim_future_identity(repo):
    assert invoke(repo, "propose-identity-change", "--agent", "vera") == 0
    path = next((repo / "members/vera/identity-amendments").glob("*.md"))
    data, body = read_record(path)
    data.update(approval_status="applied", approved_by="unknown")
    path.write_text(render_record(data, body), encoding="utf-8")
    errors = validate(repo)
    assert any("Unknown amendment approver" in e for e in errors)
    assert any("ahead of active identity" in e for e in errors)


def test_writing_code_does_not_add_communication_role():
    assert {r["agent"] for r in route("write C++ code")} == {"ada", "vera"}
    assert "curie" in {r["agent"] for r in route("physically implausible result")}
