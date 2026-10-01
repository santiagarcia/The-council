"""A local model's output is a claim until something else moves it.

The envelope exists because three models on this machine answered a recall
question confidently and wrongly. These tests fix the properties that make
that safe: a claim with no evidence cannot reach a standing above "asserted",
an answer whose citations do not resolve is escalated rather than returned,
and nothing a model produces can mark itself adopted or verified.
"""

from __future__ import annotations

import pytest

from council_local.bridge import propose_memory
from council_local.envelope import Claim, Envelope, EnvelopeError, Evidence, Usage


def _payload(**over):
    base = {
        "claims": [
            {"statement": "UMAT is defined here", "evidence": [{"path": "umat.for", "line": 16}]}
        ],
        "uncertainties": [],
        "recommended_next_action": "",
    }
    base.update(over)
    return base


def test_a_claim_above_asserted_must_carry_evidence():
    Claim(statement="grounded", evidence=[Evidence("a.f", 1)], standing="evidenced")
    with pytest.raises(EnvelopeError, match="must carry evidence"):
        Claim(statement="ungrounded", standing="evidenced")


def test_a_model_cannot_hand_back_a_verified_claim(tmp_path):
    """`verified` is reachable in the vocabulary but not from a model's JSON."""
    (tmp_path / "umat.for").write_text("x\n")
    payload = _payload(
        claims=[
            {
                "statement": "it agrees",
                "standing": "verified",
                "evidence": [{"path": "umat.for", "line": 1}],
            }
        ]
    )
    envelope = Envelope.build(agent="ada", task="t", payload=payload, usage=Usage(), root=tmp_path)
    assert [c.standing for c in envelope.claims] == ["evidenced"]


def test_an_answer_with_no_claims_is_escalated():
    envelope = Envelope.build(agent="ada", task="t", payload=_payload(claims=[]), usage=Usage())
    assert envelope.needs_claude
    assert envelope.escalation == "no_evidence"


def test_mostly_ungrounded_claims_are_escalated(tmp_path):
    (tmp_path / "umat.for").write_text("x\n")
    payload = _payload(
        claims=[
            {"statement": "cited", "evidence": [{"path": "umat.for", "line": 1}]},
            {"statement": "bare", "evidence": []},
            {"statement": "also bare", "evidence": []},
        ]
    )
    envelope = Envelope.build(agent="ada", task="t", payload=payload, usage=Usage(), root=tmp_path)
    assert envelope.needs_claude
    assert envelope.grounded_fraction < 0.5


def test_a_citation_to_a_file_that_is_not_there_is_escalated(tmp_path):
    """The cheapest hallucination to catch, and the one that predicts the rest."""
    payload = _payload(
        claims=[{"statement": "found it", "evidence": [{"path": "invented.for", "line": 42}]}]
    )
    envelope = Envelope.build(agent="ada", task="t", payload=payload, usage=Usage(), root=tmp_path)
    assert envelope.needs_claude
    assert "does not exist" in envelope.escalation_reason


def test_a_proposed_lesson_is_never_adopted():
    lesson = propose_memory(
        trigger="t",
        previous_belief="b",
        observation="o",
        evidence=["f.py:1"],
        new_rule="r",
        scope="s",
        confidence=1.0,
    )
    assert lesson["review_status"] == "proposed"
    assert lesson["adopted"] is False
    assert lesson["needs_claude"] is True


def test_a_lesson_without_evidence_is_refused():
    assert "error" in propose_memory(
        trigger="t", previous_belief="b", observation="o", evidence=[], new_rule="r", scope="s"
    )


def test_the_summary_names_the_model_and_the_cost():
    """What a reviewer reads instead of the envelope has to carry the price."""
    envelope = Envelope.build(
        agent="ada",
        task="classify_umat",
        payload=_payload(),
        usage=Usage(
            model="qwen2.5-coder:7b", prompt_tokens=5000, completion_tokens=200, seconds=19.3
        ),
    )
    summary = envelope.summary()
    assert "qwen2.5-coder:7b" in summary
    assert "5200 tok" in summary
    assert "19.3s" in summary
