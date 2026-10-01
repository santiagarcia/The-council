"""Whether delegating actually saved anything, measured rather than assumed.

Delegation pays only if the reviewer reads less than they would have. A local
answer that has to be checked line by line cost tokens on both sides. So every
run records what it spent locally, what it returned, and -- the number that
decides it -- how often the answer was accepted without correction.

Nothing here estimates Claude's tokens. The reviewer's side is recorded when a
reviewer records it; an invented saving is worse than no figure.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LEDGER = REPO / "evaluations/local/delegation.jsonl"


@dataclass
class Delegation:
    """One delegated task and what became of it."""

    task: str
    model: str
    local_prompt_tokens: int = 0
    local_completion_tokens: int = 0
    seconds: float = 0.0
    summary_chars: int = 0
    detail_chars: int = 0
    escalated: bool = False
    escalation: str = "none"
    #: Set by the reviewer afterwards, not by the model.
    outcome: str = "pending"
    correction: str = ""
    recorded: float = field(default_factory=time.time)

    @property
    def compression(self) -> float:
        """How much smaller the summary is than the full answer.

        This is the honest proxy for what a reviewer avoids reading. It is not
        a token saving on the reviewer's side, and is not reported as one.
        """
        if not self.detail_chars:
            return 0.0
        return 1 - (self.summary_chars / self.detail_chars)


def record(delegation: Delegation, *, ledger: Path | str | None = None) -> Path:
    """Append one delegation to the ledger."""
    path = Path(ledger) if ledger else LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as handle:
        handle.write(json.dumps(asdict(delegation)) + "\n")
    return path


def summarise(ledger: Path | str | None = None) -> dict:
    """What the ledger says so far, with unreviewed work counted as unreviewed."""
    path = Path(ledger) if ledger else LEDGER
    if not path.is_file():
        return {"delegations": 0, "note": "no delegations recorded yet"}
    rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    if not rows:
        return {"delegations": 0}
    reviewed = [r for r in rows if r.get("outcome") in ("accepted", "corrected", "rejected")]
    accepted = [r for r in reviewed if r["outcome"] == "accepted"]
    by_task: dict[str, dict] = {}
    for row in rows:
        bucket = by_task.setdefault(row["task"], {"runs": 0, "seconds": 0.0, "escalated": 0})
        bucket["runs"] += 1
        bucket["seconds"] += row.get("seconds", 0.0)
        bucket["escalated"] += int(bool(row.get("escalated")))
    for bucket in by_task.values():
        bucket["seconds"] = round(bucket["seconds"], 1)
    return {
        "delegations": len(rows),
        "local_tokens": sum(
            r.get("local_prompt_tokens", 0) + r.get("local_completion_tokens", 0) for r in rows
        ),
        "local_seconds": round(sum(r.get("seconds", 0.0) for r in rows), 1),
        "escalated": sum(1 for r in rows if r.get("escalated")),
        "reviewed": len(reviewed),
        "awaiting_review": len(rows) - len(reviewed),
        "accepted_without_correction": (
            round(len(accepted) / len(reviewed), 3) if reviewed else None
        ),
        "mean_compression": round(
            sum(
                1 - (r.get("summary_chars", 0) / r["detail_chars"])
                for r in rows
                if r.get("detail_chars")
            )
            / max(sum(1 for r in rows if r.get("detail_chars")), 1),
            3,
        ),
        "by_task": by_task,
        # Stated rather than estimated: the reviewer's own cost is only known
        # when a reviewer records it.
        "claude_tokens_avoided": "not measured; requires the reviewer to record it",
    }
