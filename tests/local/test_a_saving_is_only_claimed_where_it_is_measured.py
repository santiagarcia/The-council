"""The ledger never invents the reviewer's side of the saving."""

from __future__ import annotations

from council_local.metrics import Delegation, record, summarise


def test_an_unreviewed_run_is_not_counted_as_accepted(tmp_path):
    ledger = tmp_path / "d.jsonl"
    record(Delegation(task="classify_umat", model="m", seconds=20.0), ledger=ledger)
    out = summarise(ledger)
    assert out["delegations"] == 1
    assert out["awaiting_review"] == 1
    assert out["accepted_without_correction"] is None


def test_acceptance_is_measured_only_over_reviewed_runs(tmp_path):
    ledger = tmp_path / "d.jsonl"
    for outcome in ("accepted", "accepted", "corrected", "pending"):
        record(Delegation(task="t", model="m", outcome=outcome), ledger=ledger)
    out = summarise(ledger)
    assert out["reviewed"] == 3
    assert out["accepted_without_correction"] == round(2 / 3, 3)


def test_claude_tokens_are_never_estimated(tmp_path):
    ledger = tmp_path / "d.jsonl"
    record(Delegation(task="t", model="m"), ledger=ledger)
    assert "not measured" in summarise(ledger)["claude_tokens_avoided"]


def test_compression_is_reported_as_what_it_is(tmp_path):
    item = Delegation(task="t", model="m", summary_chars=300, detail_chars=6000)
    assert round(item.compression, 2) == 0.95
    assert Delegation(task="t", model="m").compression == 0.0
