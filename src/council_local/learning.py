"""Turning a local run into a proposed Council lesson, and no further.

The Council already has a learning loop and a memory store with its own
schema, commit discipline and review rules. This module does not reimplement
any of it: it shapes what a local run observed into the form
``council remember`` accepts, and stops.

The stopping is the point. A local model may propose; promotion to adopted
knowledge, an identity change or a permission change stays with Santiago and
with Vera's challenge. Nothing here writes to ``memory/`` directly and nothing
here can set a review status.
"""

from __future__ import annotations

import json
import shlex
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
#: Proposals land here, outside `memory/`, until a reviewer moves them.
PROPOSALS = REPO / "evaluations/local/proposals"


@dataclass
class Prediction:
    """What was expected before a task ran, recorded so it can be wrong.

    A lesson drawn after the fact from an outcome is a story. Writing the
    prediction first is what makes the reflection evidence.
    """

    task: str
    expectation: str
    basis: str = ""
    recorded: str = ""


@dataclass
class Lesson:
    """A candidate lesson in the shape the learning loop requires."""

    trigger: str
    previous_belief: str
    observation: str
    evidence: list[str]
    new_behavioral_rule: str
    scope: str
    exceptions: str = "none recorded"
    confidence: float = 0.3
    verification_test: str = ""
    agent: str = "ada"
    project: str = ""
    #: Fixed. There is no argument that changes it.
    review_status: str = "proposed"
    memories_loaded: list[str] = field(default_factory=list)
    memories_used: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.evidence:
            raise ValueError("a candidate lesson needs evidence; none was given")
        self.confidence = min(max(float(self.confidence), 0.0), 1.0)
        self.review_status = "proposed"

    @property
    def memory_help(self) -> str:
        """Whether retrieved memories were actually used, for the loop's record."""
        if not self.memories_loaded:
            return "none loaded"
        if not self.memories_used:
            return f"{len(self.memories_loaded)} loaded, none used"
        return f"{len(self.memories_used)} of {len(self.memories_loaded)} used"

    def observation_text(self) -> str:
        """The single observation string `council remember` stores."""
        return (
            f"{self.observation} Previous belief: {self.previous_belief}."
            f" Proposed rule: {self.new_behavioral_rule}."
            f" Scope: {self.scope}. Exceptions: {self.exceptions}."
            f" Verification: {self.verification_test or 'none proposed'}."
            f" Retrieved memories: {self.memory_help}."
        )

    def remember_command(self) -> str:
        """The exact `council remember` invocation a reviewer would run.

        Returned as text rather than executed. A local model that could run
        this would be writing to the Council's memory without review, and the
        charter reserves that.
        """
        argv = [
            "council",
            "remember",
            "--agent",
            self.agent,
            "--project",
            self.project or "corpus-robustification",
            "--type",
            "episodic",
            "--scope",
            "project",
            "--observation",
            self.observation_text(),
            "--confidence",
            f"{self.confidence:.2f}",
        ]
        for item in self.evidence:
            argv += ["--evidence", item]
        if self.verification_test:
            argv += [
                "--limitations",
                f"proposed by a local model; unverified until {self.verification_test}",
            ]
        else:
            argv += ["--limitations", "proposed by a local model; no verification test proposed"]
        return " ".join(shlex.quote(part) for part in argv)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["remember_command"] = self.remember_command()
        data["adopted"] = False
        return data


def record_proposal(lesson: Lesson, *, out_dir: Path | str | None = None) -> Path:
    """Write a proposal to disk for review. Never touches ``memory/``."""
    out_dir = Path(out_dir) if out_dir else PROPOSALS
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "".join(c if c.isalnum() else "-" for c in lesson.trigger.lower())[:60]
    path = out_dir / f"{stem.strip('-') or 'proposal'}.json"
    index = 1
    while path.exists():
        index += 1
        path = out_dir / f"{stem.strip('-') or 'proposal'}-{index}.json"
    path.write_text(json.dumps(lesson.to_dict(), indent=2) + "\n")
    return path


@dataclass
class TrainingExample:
    """An accepted local answer, kept for a dataset that does not exist yet.

    By instruction nothing trains. Examples are collected with the task, the
    input, the output, the reviewer's correction and the evaluation, so that a
    held-out set can be built later from material whose provenance is known.
    """

    task: str
    model: str
    input_digest: str
    output: dict
    accepted: bool
    correction: str = ""
    reviewer: str = ""
    score: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def collect(example: TrainingExample, *, out_dir: Path | str | None = None) -> Path:
    """Append one example to the collection. Nothing reads it to train."""
    out_dir = Path(out_dir) if out_dir else REPO / "evaluations/local/examples"
    out_dir.mkdir(parents=True, exist_ok=True)
    bucket = "accepted" if example.accepted else "rejected"
    path = out_dir / f"{bucket}.jsonl"
    with path.open("a") as handle:
        handle.write(json.dumps(example.to_dict(), default=str) + "\n")
    return path
