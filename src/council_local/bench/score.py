"""Scoring a local answer against what the project already established.

The scores are deliberately unflattering in three ways.

* **A missing answer is wrong, not absent.** A model that omits a field it was
  asked for has failed the task; scoring only the fields it chose to answer
  would reward evasion.
* **Hallucination is counted separately from error.** Getting a PROPS count
  wrong by one is a different failure from citing a line that does not exist,
  and only the second makes the model unusable for unreviewed work.
* **Grounding is scored even when the answer is right.** An ungrounded correct
  answer cannot be told from a lucky guess, and the whole point of delegating
  is to get work a reviewer does not have to redo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..envelope import Envelope
from ..sources import read_text

#: How close a line citation has to be to count. A model that points at the
#: continuation line of a statement has found it; one off by 40 has not.
LINE_TOLERANCE = 3


@dataclass
class ScoredCase:
    """One case's result, with every component kept separate."""

    case_id: str
    task: str
    model: str
    correct: int = 0
    wrong: int = 0
    missing: int = 0
    details: dict = field(default_factory=dict)
    #: Citations naming a line beyond the end of the file, or a missing path.
    hallucinated_citations: int = 0
    total_citations: int = 0
    grounded_fraction: float = 0.0
    schema_valid: bool = True
    escalated: str = "none"
    seconds: float = 0.0
    tokens: int = 0

    @property
    def scored(self) -> int:
        return self.correct + self.wrong + self.missing

    @property
    def accuracy(self) -> float:
        return self.correct / self.scored if self.scored else 0.0

    @property
    def hallucination_rate(self) -> float:
        if not self.total_citations:
            return 0.0
        return self.hallucinated_citations / self.total_citations


def score_case(case, envelope: Envelope) -> ScoredCase:
    """Compare one envelope with one case's established truth."""
    result = ScoredCase(
        case_id=case.case_id,
        task=case.task,
        model=envelope.usage.model,
        grounded_fraction=round(envelope.grounded_fraction, 3),
        schema_valid=envelope.escalation != "schema_invalid",
        escalated=envelope.escalation,
        seconds=envelope.usage.seconds,
        tokens=envelope.usage.total_tokens,
    )

    answers = envelope.answers or {}
    for key in case.scoreable:
        expected = case.truth[key]
        if key not in answers or answers[key] in (None, ""):
            result.missing += 1
            result.details[key] = {"expected": expected, "got": None, "verdict": "missing"}
            continue
        got = answers[key]
        ok = _agrees(key, expected, got)
        result.correct += int(ok)
        result.wrong += int(not ok)
        result.details[key] = {
            "expected": expected,
            "got": got,
            "verdict": "correct" if ok else "wrong",
        }

    result.hallucinated_citations, result.total_citations = _citations(case.path, envelope)
    return result


def _agrees(key: str, expected, got) -> bool:
    """Whether an answer matches, by the rule appropriate to the field."""
    if key == "entry_line":
        try:
            return abs(int(got) - int(expected)) <= LINE_TOLERANCE
        except (TypeError, ValueError):
            return False
    if key == "verdict":
        # The registry stores a boolean; anything that is not a genuine UMAT
        # is scored as "did the model also decline to call it one".
        if expected == "genuine_umat":
            return str(got) == "genuine_umat"
        return str(got) != "genuine_umat"
    if key in ("max_props_index", "max_statev_index"):
        try:
            return int(got) == int(expected)
        except (TypeError, ValueError):
            return False
    if isinstance(expected, bool):
        return bool(got) is expected
    return str(got).strip().lower() == str(expected).strip().lower()


def _citations(path: Path, envelope: Envelope) -> tuple[int, int]:
    """Count citations, and how many point outside the file they name."""
    try:
        length = len(read_text(path).splitlines())
    except (OSError, ValueError):
        return 0, 0
    bad = total = 0
    for claim in envelope.claims:
        for ref in claim.evidence:
            total += 1
            if ref.line and ref.line > length:
                bad += 1
    return bad, total


def aggregate(scored: list[ScoredCase]) -> dict:
    """Roll a run up into the numbers that decide whether to delegate."""
    if not scored:
        return {}
    total_scored = sum(s.scored for s in scored)
    correct = sum(s.correct for s in scored)
    citations = sum(s.total_citations for s in scored)
    return {
        "cases": len(scored),
        "fields_scored": total_scored,
        "accuracy": round(correct / total_scored, 3) if total_scored else 0.0,
        "wrong": sum(s.wrong for s in scored),
        "missing": sum(s.missing for s in scored),
        "hallucination_rate": round(sum(s.hallucinated_citations for s in scored) / citations, 3)
        if citations
        else 0.0,
        "schema_validity": round(sum(s.schema_valid for s in scored) / len(scored), 3),
        "grounded_fraction": round(sum(s.grounded_fraction for s in scored) / len(scored), 3),
        "escalated": sum(1 for s in scored if s.escalated != "none"),
        "seconds_total": round(sum(s.seconds for s in scored), 1),
        "seconds_per_case": round(sum(s.seconds for s in scored) / len(scored), 1),
        "tokens_total": sum(s.tokens for s in scored),
        "by_task": _by_task(scored),
    }


def _by_task(scored: list[ScoredCase]) -> dict:
    """Per-task accuracy, because the tasks are not equally hard."""
    out: dict[str, dict] = {}
    for item in scored:
        bucket = out.setdefault(item.task, {"correct": 0, "scored": 0, "seconds": 0.0})
        bucket["correct"] += item.correct
        bucket["scored"] += item.scored
        bucket["seconds"] += item.seconds
    for bucket in out.values():
        bucket["accuracy"] = (
            round(bucket["correct"] / bucket["scored"], 3) if bucket["scored"] else 0.0
        )
        bucket["seconds"] = round(bucket["seconds"], 1)
    return out
