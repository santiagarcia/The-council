"""The shape every local-agent answer has to arrive in.

A local model's output is a *claim*, and the difference between a claim and a
finding is the evidence attached to it. The three benchmark probes run while
this package was written make the point: asked to recall the 37 arguments of
the UMAT interface, the 1.5B model invented an interface that does not exist,
the 7B dropped STRESS and invented two arguments, and the 32B produced sixteen
correct names and then drifted into UEL arguments. None of them said it was
unsure.

So the envelope forbids a bare assertion. Every claim carries file and line
references a reviewer can open, uncertainties are a required field rather than
an optional flourish, and ``verified`` is not a value a model is allowed to
set about its own work -- only a test, a benchmark comparison or a reviewer
can move a claim there.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: A claim's standing. A model may only ever produce ``asserted``.
STANDINGS = ("asserted", "evidenced", "tested", "verified")

#: Why a result is being sent to Claude rather than accepted locally.
ESCALATIONS = (
    "none",
    "low_confidence",
    "contradiction",
    "high_impact",
    "schema_invalid",
    "policy_refusal",
    "tool_failure",
    "no_evidence",
)


class EnvelopeError(ValueError):
    """A local answer did not meet the envelope's requirements."""


@dataclass
class Evidence:
    """A pointer a reviewer can open: a path, a line, and the text found there."""

    path: str
    line: int = 0
    quote: str = ""

    def __post_init__(self) -> None:
        if not self.path:
            raise EnvelopeError("evidence needs a path")
        self.quote = self.quote[:400]

    @property
    def locator(self) -> str:
        """``path:line``, the form that is clickable in an editor."""
        return f"{self.path}:{self.line}" if self.line else self.path


@dataclass
class Claim:
    """One statement, its evidence, and how far it has actually been taken."""

    statement: str
    evidence: list[Evidence] = field(default_factory=list)
    standing: str = "asserted"
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.standing not in STANDINGS:
            raise EnvelopeError(
                f"unknown standing {self.standing!r}; expected one of {', '.join(STANDINGS)}"
            )
        if self.standing != "asserted" and not self.evidence:
            raise EnvelopeError(
                f"a claim at standing {self.standing!r} must carry evidence:"
                f" {self.statement[:80]!r}"
            )
        self.confidence = min(max(float(self.confidence), 0.0), 1.0)

    @property
    def grounded(self) -> bool:
        """Whether anything in this claim can be checked without rerunning the model."""
        return bool(self.evidence)


@dataclass
class Usage:
    """What the answer cost, so delegation can be shown to be worth it."""

    model: str = ""
    quantization: str = ""
    backend: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    tokens_per_second: float = 0.0
    peak_vram_mib: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class Envelope:
    """A complete local-agent answer.

    Construct it through :meth:`build` rather than directly where possible:
    that path applies the rule a model cannot be trusted to apply to itself,
    which is that an answer with no evidence is escalated, not returned.
    """

    agent: str
    task: str
    claims: list[Claim] = field(default_factory=list)
    files_examined: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    recommended_next_action: str = ""
    tool_calls: list[dict] = field(default_factory=list)
    tests_executed: list[dict] = field(default_factory=list)
    candidate_memories: list[dict] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)
    policy_refusals: list[str] = field(default_factory=list)
    #: The task's typed answers, when it declared any. Scored directly by the
    #: benchmark; a prose claim cannot be compared with a registry field.
    answers: dict = field(default_factory=dict)
    escalation: str = "none"
    escalation_reason: str = ""
    raw: str = ""
    created: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        if not self.agent:
            raise EnvelopeError("an answer must name the agent that produced it")
        if self.escalation not in ESCALATIONS:
            raise EnvelopeError(f"unknown escalation {self.escalation!r}")

    @property
    def needs_claude(self) -> bool:
        """Whether a human-reviewed model should look at this before it is used."""
        return self.escalation != "none"

    @property
    def grounded_fraction(self) -> float:
        """Share of claims carrying at least one openable reference."""
        if not self.claims:
            return 0.0
        return sum(1 for c in self.claims if c.grounded) / len(self.claims)

    def escalate(self, reason: str, detail: str = "") -> Envelope:
        """Mark this answer as needing review, keeping the first reason given."""
        if reason not in ESCALATIONS:
            raise EnvelopeError(f"unknown escalation {reason!r}")
        if self.escalation == "none":
            self.escalation, self.escalation_reason = reason, detail
        return self

    def to_dict(self) -> dict:
        data = asdict(self)
        data["needs_claude"] = self.needs_claude
        data["grounded_fraction"] = round(self.grounded_fraction, 3)
        return data

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)

    def summary(self) -> str:
        """The few lines Claude reads instead of the whole answer.

        This is the token-saving surface: if a reviewer has to open the full
        envelope to know whether to care, delegation has saved nothing.
        """
        head = (
            f"[{self.agent}/{self.usage.model}] {self.task} — "
            f"{len(self.claims)} claims, {self.grounded_fraction:.0%} grounded, "
            f"{self.usage.total_tokens} tok in {self.usage.seconds:.1f}s"
        )
        lines = [head]
        for key, value in list(self.answers.items())[:12]:
            lines.append(f"  = {key}: {str(value)[:100]}")
        for claim in self.claims[:8]:
            mark = "+" if claim.grounded else "!"
            where = claim.evidence[0].locator if claim.evidence else "no evidence"
            lines.append(f"  {mark} {claim.statement[:110]}  [{where}]")
        if len(self.claims) > 8:
            lines.append(f"  … {len(self.claims) - 8} more")
        if self.uncertainties:
            lines.append(f"  unsure: {'; '.join(self.uncertainties[:3])[:200]}")
        if self.needs_claude:
            lines.append(f"  ESCALATED ({self.escalation}): {self.escalation_reason[:160]}")
        if self.recommended_next_action:
            lines.append(f"  next: {self.recommended_next_action[:160]}")
        return "\n".join(lines)

    @classmethod
    def build(
        cls,
        *,
        agent: str,
        task: str,
        payload: dict,
        usage: Usage,
        files_examined=(),
        policy_refusals=(),
        raw: str = "",
        root: Path | str | None = None,
    ) -> Envelope:
        """Assemble an envelope from a model's parsed JSON, applying the rules.

        ``payload`` is whatever the model returned. Anything missing becomes an
        escalation rather than a default, because a field a model omitted is a
        field nobody checked.
        """
        claims = []
        for item in payload.get("claims", []) or []:
            if isinstance(item, str):
                claims.append(Claim(statement=item))
                continue
            evidence = []
            for ref in item.get("evidence", []) or []:
                if isinstance(ref, str):
                    evidence.append(Evidence(path=ref))
                else:
                    evidence.append(
                        Evidence(
                            path=str(ref.get("path", "")),
                            line=int(ref.get("line", 0) or 0),
                            quote=str(ref.get("quote", "")),
                        )
                    )
            claims.append(
                Claim(
                    statement=str(item.get("statement", "")).strip(),
                    evidence=evidence,
                    standing="evidenced" if evidence else "asserted",
                    confidence=float(item.get("confidence", 0) or 0),
                )
            )

        envelope = cls(
            agent=agent,
            task=task,
            claims=claims,
            answers=dict(payload.get("answers") or {}),
            files_examined=[str(p) for p in files_examined],
            uncertainties=[str(u) for u in (payload.get("uncertainties") or [])],
            recommended_next_action=str(payload.get("recommended_next_action", "")),
            candidate_memories=list(payload.get("candidate_memories") or []),
            usage=usage,
            policy_refusals=[str(r) for r in policy_refusals],
            raw=raw,
        )

        if policy_refusals:
            envelope.escalate(
                "policy_refusal", f"{len(policy_refusals)} path(s) excluded by classification"
            )
        if not claims:
            envelope.escalate("no_evidence", "the model returned no claims")
        elif envelope.grounded_fraction < 0.5:
            envelope.escalate(
                "no_evidence", f"only {envelope.grounded_fraction:.0%} of claims cite a file"
            )
        if root is not None:
            missing = envelope._unopenable(Path(root))
            if missing:
                envelope.escalate(
                    "no_evidence",
                    f"{len(missing)} citation(s) name a path that does not exist:"
                    f" {', '.join(missing[:3])}",
                )
        return envelope

    def _unopenable(self, root: Path) -> list[str]:
        """Citations naming a file that is not there.

        A fabricated line number is hard to catch; a fabricated *path* is not,
        and in practice a model that invents one has invented the rest.
        """
        missing = []
        for claim in self.claims:
            for ref in claim.evidence:
                candidate = Path(ref.path)
                if not candidate.is_absolute():
                    candidate = root / ref.path
                if not candidate.exists():
                    missing.append(ref.path)
        return missing
