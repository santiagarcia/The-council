"""Permanent-member registration, selective routing, reader isolation, and review gates."""

import hashlib
import json
from unittest.mock import patch

import pytest

from council.cli import main
from council.context import assemble, route
from council.dispatch import dispatch, set_objective
from council.review import evaluate_artifact, review_packet, reviewed_gate
from council.store import CouncilError, read_record, render_record, yaml_load
from council.validation import validate


def public_artifact(repo, text="A clear explanation of one idea."):
    """Create the exact artifact an intended reader receives."""
    path = repo / "public-artifact.md"
    path.write_text(text, encoding="utf-8")
    return path.name


def nico_lesson(repo):
    """Create a reviewed fixture lesson, not a real collaboration claim."""
    meta, body = read_record(repo / "templates/examples/memory.md")
    meta.update(
        id="mem-nico-domain",
        author="nico",
        owner="nico",
        status="adopted",
        observation="DOMAIN_MEMORY_SENTINEL",
        reviewers=[{
            "agent": "vera", "decision": "accept", "date": "2026-09-29",
            "evidence_refs": [meta["evidence"][0]["ref"]],
            "notes": "Separate fixture review; no claim of live verification.",
        }],
    )
    path = repo / "memory/agents/nico/mem-nico-domain.md"
    path.write_text(render_record(meta, body), encoding="utf-8")


def review_report():
    """Return explicit review metadata for testing gates, not actual agent conclusions."""
    return {
        "artifact": "public-artifact.md",
        "artifact_sha256": hashlib.sha256(
            b"A clear explanation of one idea."
        ).hexdigest(),
        "builder": "ada",
        "correctness": {
            "reviewer": "vera", "decision": "pass",
            "evidence_refs": ["public-artifact.md"],
            "mathematical_status": "supported",
            "physical_status": "not-applicable",
            "numerical_status": "not-applicable",
            "assumptions": ["The stated scalar is nonzero."],
            "limitations": "Fixture scalar argument only.",
        },
        "comprehension": {
            "reviewer": "nico", "decision": "pass",
            "evidence_refs": ["public-artifact.md"],
            "restatement": "The conclusion holds under the stated nonzero assumption.",
            "technically_faithful": True, "mode": "cold-read",
        },
        "usability": {
            "reviewer": "maya", "decision": "pass",
            "evidence_refs": ["public-artifact.md"],
            "implementation_constraints_considered": True,
            "limitations": "Fixture walkthrough only.",
        },
        "blocking_findings": [],
    }


def test_new_members_assemble_without_replacing_foundation(repo):
    for agent in ("noether", "maya"):
        bundle = assemble(repo, agent, "council-bootstrap", "Check assumptions and workflow")
        assert f"members/{agent}/identity.md" in bundle
        assert f"members/{agent}/system-prompt.md" in bundle
    assert validate(repo) == []
    assert yaml_load(repo / "members/ada/operating-beliefs.yaml")["identity_version"] == "1.0"


@pytest.mark.parametrize(
    "task,required,absent",
    [
        ("mathematical derivation of a constitutive model",
         {"noether", "curie", "gauss", "vera"}, {"maya", "nico", "scout"}),
        ("numerical solver with formal assumptions",
         {"gauss", "noether", "ada", "vera"}, {"maya", "nico"}),
        ("design a CLI interface",
         {"maya", "ada", "nico", "vera"}, {"curie", "gauss", "noether"}),
        ("write presentation slides", {"iris", "maya", "nico"}, {"ada", "vera", "scout"}),
        ("installation tutorial", {"ada", "iris", "maya", "nico"}, {"noether", "gauss"}),
        ("explain a new scientific concept",
         {"curie", "noether", "iris", "nico"}, {"scout", "maya"}),
        ("final deliverable review", {"vera", "nico"}, {"curie", "gauss", "maya"}),
    ],
)
def test_selective_complementary_routing(task, required, absent):
    chosen = {item["agent"] for item in route(task)}
    assert required <= chosen
    assert not chosen & absent
    assert len(chosen) < 10


def test_cold_read_excludes_domain_memories_and_project_answers(repo):
    artifact = public_artifact(repo)
    nico_lesson(repo)
    (repo / "projects/council-bootstrap/findings.md").write_text(
        "PROJECT_ANSWER_SENTINEL", encoding="utf-8"
    )
    with patch("council.review.records", side_effect=AssertionError("Domain retrieval")):
        packet = review_packet(repo, "nico", "cold-read", artifact, "New researcher")
    payload = json.dumps(packet)
    assert "DOMAIN_MEMORY_SENTINEL" not in payload
    assert "PROJECT_ANSWER_SENTINEL" not in payload
    assert packet["learning_context"] == []
    bundle = assemble(repo, "nico", "council-bootstrap", "Read the public artifact")
    assert "DOMAIN_MEMORY_SENTINEL" not in bundle
    assert "PROJECT_ANSWER_SENTINEL" not in bundle
    with pytest.raises(CouncilError, match="forbids"):
        review_packet(repo, "nico", "cold-read", artifact, project="council-bootstrap")


def test_developing_reader_is_opt_in_and_does_not_contaminate_later_cold_read(repo):
    artifact = public_artifact(repo)
    nico_lesson(repo)
    fresh = review_packet(repo, "nico", "developing-reader", artifact)
    assert fresh["learning_context"] == []
    learning = review_packet(
        repo, "nico", "developing-reader", artifact, project="council-bootstrap"
    )
    assert learning["learning_context"][0]["observation"] == "DOMAIN_MEMORY_SENTINEL"
    assert "DOMAIN_MEMORY_SENTINEL" not in json.dumps(
        review_packet(repo, "nico", "cold-read", artifact)
    )


def test_nico_retains_only_reviewed_nontechnical_relational_continuity(repo):
    artifact = public_artifact(repo)
    item = {
        "id": "reader-patient-clarification",
        "participants": ["nico", "iris"],
        "status": "adopted", "review_status": "accepted", "reviewer": "vera",
        "evidence_refs": ["public-artifact.md"],
        "qualities": [{"quality": "trust", "level": "moderate"}],
        "practices": ["ask-without-apology", "request-concrete-example"],
    }
    path = repo / "relationships/pairs/nico-continuity.json"
    path.write_text(json.dumps({"records": [item]}), encoding="utf-8")
    packet = review_packet(repo, "nico", "cold-read", artifact)
    assert "ask-without-apology" in packet["reader_context"]
    item["domain_knowledge"] = "CONTAMINATING_EXPERT_FACT"
    path.write_text(json.dumps({"records": [item]}), encoding="utf-8")
    with pytest.raises(CouncilError, match="reader continuity"):
        review_packet(repo, "nico", "cold-read", artifact)


def test_dispatch_has_a_separate_nico_handoff(repo):
    set_objective(repo, "council-bootstrap", "PRIVATE_OBJECTIVE_SENTINEL")
    packet = dispatch(repo, "council-bootstrap", "CLI interface")
    nico = next(a for a in packet["assignments"] if a["agent"] == "nico")
    assert "PRIVATE_OBJECTIVE_SENTINEL" not in json.dumps(nico["handoff"])
    assert "shared_context" not in nico["handoff"]
    assert nico["handoff"]["artifact_required"]
    assert "members/nico/identity.md" in nico["member_context"]


@pytest.mark.parametrize(
    "path", ["../outside.md", "memory/shared/proposed/secret.md",
             "style_sources/presentations/private/raw.md", ".env"]
)
def test_review_rejects_private_memory_and_unsafe_inputs(repo, path):
    with pytest.raises(CouncilError):
        review_packet(repo, "nico", "cold-read", path)


def test_review_rejects_memory_symlinks_and_oversized_artifacts(repo):
    lesson = repo / "memory/agents/nico/lesson.txt"
    lesson.write_text("DOMAIN_SECRET", encoding="utf-8")
    link = repo / "public-link.txt"
    try:
        link.symlink_to(lesson)
    except OSError:
        pytest.skip("Symlinks unavailable")
    with pytest.raises(CouncilError, match="not memory"):
        review_packet(repo, "nico", "cold-read", link.name)
    artifact = public_artifact(repo, "x" * 262_145)
    with pytest.raises(CouncilError, match="256 KiB"):
        review_packet(repo, "nico", "cold-read", artifact)


def test_diagnostics_expose_acronyms_prerequisites_and_recovery_gaps(repo):
    artifact = public_artifact(repo, "Install XYZ using pip. Obviously run the command.")
    code, result = evaluate_artifact(repo, "usability", artifact)
    assert code == 1
    rules = {f["rule"] for f in result["findings"]}
    assert {"possibly-undefined-acronym", "missing-prerequisites",
            "missing-success-feedback", "missing-recovery", "assumed-understanding"} <= rules
    assert result["final_review_passed"] is None
    assert result["status"] == "needs-human-review"


def test_clean_diagnostics_do_not_claim_successful_comprehension(repo):
    artifact = public_artifact(repo)
    code, result = evaluate_artifact(repo, "comprehension", artifact)
    assert code == 0
    assert result["final_review_passed"] is None
    assert result["status"] == "needs-human-review"


def test_formal_review_blocks_unstated_assumptions(repo):
    public_artifact(repo)
    report = review_report()
    report["correctness"]["assumptions"] = []
    assert not reviewed_gate(repo, report, report["artifact"])


def test_mathematical_validity_does_not_establish_physical_validity(repo):
    public_artifact(repo)
    report = review_report()
    report["correctness"]["physical_status"] = "unsupported"
    assert not reviewed_gate(repo, report, report["artifact"])


def test_usability_review_requires_implementation_constraints(repo):
    public_artifact(repo)
    report = review_report()
    report["usability"]["implementation_constraints_considered"] = False
    assert not reviewed_gate(repo, report, report["artifact"])


@pytest.mark.parametrize(
    "change", [{"decision": "fail"}, {"restatement": ""},
               {"technically_faithful": False}, {"mode": "developing-reader"}]
)
def test_correct_but_incomprehensible_or_false_simplification_fails(repo, change):
    public_artifact(repo)
    report = review_report()
    report["comprehension"].update(change)
    assert not reviewed_gate(repo, report, report["artifact"])


def test_review_report_requires_independence_and_real_evidence(repo):
    public_artifact(repo)
    report = review_report()
    assert reviewed_gate(repo, report, report["artifact"])
    report["correctness"]["reviewer"] = "ada"
    with pytest.raises(CouncilError, match="Builder"):
        reviewed_gate(repo, report, report["artifact"])
    report = review_report()
    report["comprehension"]["evidence_refs"] = ["missing.md"]
    with pytest.raises(CouncilError, match="Broken"):
        reviewed_gate(repo, report, report["artifact"])


def test_reader_cli_outputs_packets_and_final_gate_results_without_overwriting(repo, capsys):
    artifact = public_artifact(repo)
    base = ["--root", str(repo)]
    assert main(base + ["review", "--agent", "nico", "--artifact", artifact]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "cold-read"
    output = ".council/reader.json"
    args = base + ["review", "--agent", "nico", "--artifact", artifact, "--output", output]
    assert main(args) == 0
    assert main(args) == 2
    capsys.readouterr()
    report = review_report()
    report["comprehension"]["decision"] = "fail"
    (repo / "review.json").write_text(json.dumps(report), encoding="utf-8")
    assert main(base + [
        "evaluate", "comprehension", "--artifact", artifact, "--review-report", "review.json"
    ]) == 1
    assert json.loads(capsys.readouterr().out)["final_review_passed"] is False


def test_affective_profile_validation_rejects_missing_behavior_and_invalid_levels(repo):
    path = repo / "members/noether/affective-profile.yaml"
    data = yaml_load(path)
    data["dispositions"][0]["behavior_when_high"] = ""
    data["dispositions"][0]["baseline"] = "unbounded"
    path.write_text(json.dumps(data), encoding="utf-8")
    errors = validate(repo)
    assert any("behavior_when_high" in error for error in errors)
    assert any("baseline" in error for error in errors)


def test_stale_review_does_not_certify_a_changed_artifact(repo):
    public_artifact(repo)
    report = review_report()
    public_artifact(repo, "A different claim after review.")
    with pytest.raises(CouncilError, match="stale"):
        reviewed_gate(repo, report, report["artifact"])
