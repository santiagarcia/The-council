"""The same objective and current instructions reach every selected member efficiently."""

from unittest.mock import patch

import pytest

from council.cli import main
from council.context import assemble
from council.dispatch import dispatch, get_objective, set_objective
from council.store import CouncilError, read_record, render_record
from council.validation import validate


def test_objective_dry_run_and_preserved_constraints(repo):
    set_objective(repo, "council-bootstrap", "Improve the CLI", ["Tests pass"], ["No push"], True)
    path = repo / "projects/council-bootstrap/objective.md"
    assert not path.exists()
    set_objective(repo, "council-bootstrap", "Improve the CLI", ["Tests pass"], ["No push"])
    meta, body = read_record(path)
    path.write_text(render_record(meta, body + "\nPreserve manual discussion.\n"), encoding="utf-8")
    set_objective(repo, "council-bootstrap", "Implement fast Council software")
    objective = get_objective(repo, "council-bootstrap")
    assert objective["success_criteria"] == ["Tests pass"]
    assert objective["constraints"] == ["No push"]
    assert "Preserve manual discussion." in path.read_text(encoding="utf-8")
    assert validate(repo) == []


def test_dispatch_validates_once_and_factors_shared_instructions(repo):
    set_objective(repo, "council-bootstrap", "Implement the CLI", ["Tests pass"], ["No push"])
    with patch("council.dispatch.validate", wraps=validate) as checker:
        packet = dispatch(repo, "council-bootstrap", all_agents=True)
    assert checker.call_count == 1
    assert len(packet["assignments"]) == 10
    assert packet["objective"]["constraints"] == ["No push"]
    assert "constitution/permissions.md" in packet["shared_context"]
    assert "AGENTS.md" in packet["shared_context"]
    for assignment in packet["assignments"]:
        agent = assignment["agent"]
        assert f"members/{agent}/identity.md" in assignment["member_context"]
        assert "constitution/permissions.md" not in assignment["member_context"]
    vera = next(a for a in packet["assignments"] if a["agent"] == "vera")
    assert set(vera["after"]) == {"ada", "curie", "gauss", "noether", "maya", "iris"}
    assert dispatch(repo, "council-bootstrap", all_agents=True) == packet


def test_dispatch_routes_subtask_and_refreshes_after_objective_change(repo):
    set_objective(repo, "council-bootstrap", "Implement research software")
    packet = dispatch(repo, "council-bootstrap", "write presentation slides")
    assert [a["agent"] for a in packet["assignments"]] == ["iris", "maya", "nico"]
    set_objective(repo, "council-bootstrap", "Document verified sensitivity results")
    new_packet = dispatch(repo, "council-bootstrap", "write presentation slides")
    assert new_packet["snapshot_id"] != packet["snapshot_id"]
    assert "Document verified sensitivity results" in assemble(
        repo, "vera", "council-bootstrap", "review results"
    )


def test_dispatch_fails_on_missing_objective_and_bad_agent(repo):
    with pytest.raises(CouncilError, match="No shared objective"):
        dispatch(repo, "council-bootstrap")
    set_objective(repo, "council-bootstrap", "Implement software")
    with pytest.raises(CouncilError, match="Unknown agent"):
        dispatch(repo, "council-bootstrap", agents=["unknown"])
    with pytest.raises(CouncilError, match="limit"):
        dispatch(repo, "council-bootstrap", limit=0)


def test_objective_validation_and_packet_output_preservation(repo):
    assert (
        main(
            [
                "--root",
                str(repo),
                "objective",
                "set",
                "--project",
                "council-bootstrap",
                "--text",
                "Implement software",
                "--success",
                "Tests pass",
            ]
        )
        == 0
    )
    assert main(["--root", str(repo), "objective", "show", "--project", "council-bootstrap"]) == 0
    args = [
        "--root",
        str(repo),
        "dispatch",
        "--project",
        "council-bootstrap",
        "--all",
        "--output",
        ".council/packet.json",
    ]
    assert main(args) == 0
    assert main(args) == 2
    path = repo / "projects/council-bootstrap/objective.md"
    metadata, body = read_record(path)
    metadata["project"] = "wrong-project"
    path.write_text(render_record(metadata, body), encoding="utf-8")
    assert any("Objective project mismatch" in e for e in validate(repo))
