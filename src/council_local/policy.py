"""What a local model is allowed to read, and what it must refuse to read.

A local model feels safer than a hosted one because the bytes do not leave the
machine, and that feeling is the hazard this module exists to remove. A
collaborator's no-AI condition is a condition on *analysis*, not on egress: a
file covered by one must not be read into a prompt, summarised, embedded,
benchmarked or used as training data, whoever runs the model.

Two independent mechanisms, and a path has to clear both:

* a **classification**, declared per directory tree in ``.councilignore``, that
  says who owns the material and under what terms;
* a **refusal**, raised rather than returned, when a task reaches for a path
  whose classification forbids it.

Refusing loudly matters more than refusing often. A silent skip in a corpus
sweep is indistinguishable from a file that was read and found uninteresting,
so every exclusion is counted and named in the result.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from pathlib import Path

#: Classifications, from least to most restricted. ``open`` material may be
#: analysed and redistributed; ``internal`` may be analysed but not published;
#: ``restricted`` may not be analysed by any model, local or hosted.
CLASSIFICATIONS = ("open", "internal", "restricted")

#: Owners whose material carries a no-AI condition unless an explicit grant
#: says otherwise. Named here so that adding a directory to `.councilignore`
#: is not the only thing standing between a model and a collaborator's code.
NO_AI_OWNERS = (
    "jhu",
    "johns-hopkins",
    "nasa",
    "cmu",
    "carnegie-mellon",
    "export-controlled",
    "proprietary",
)

POLICY_FILE = ".councilignore"


class PolicyRefusal(RuntimeError):
    """A task reached for material its classification forbids a model to read.

    This is raised, never returned as a value, so that a caller cannot mistake
    a refusal for an empty analysis.
    """

    def __init__(self, path: Path, rule: Rule) -> None:
        super().__init__(
            f"{path}: classification '{rule.classification}'"
            f"{' owner ' + rule.owner if rule.owner else ''} forbids model analysis"
            f" ({rule.reason or 'no reason recorded'}; declared at {rule.source}:{rule.line})"
        )
        self.path = path
        self.rule = rule


@dataclass(frozen=True)
class Rule:
    """One line of a ``.councilignore``: a glob and what it classifies."""

    pattern: str
    classification: str
    owner: str = ""
    reason: str = ""
    source: str = POLICY_FILE
    line: int = 0

    @property
    def analysable(self) -> bool:
        """Whether a model may read material under this rule at all."""
        return self.classification != "restricted"


@dataclass
class Decision:
    """Why one path was admitted or refused, kept so a sweep can report it."""

    path: Path
    allowed: bool
    rule: Rule | None = None

    @property
    def reason(self) -> str:
        if self.rule is None:
            return "no rule matched; default classification applied"
        return (
            f"{self.rule.classification} by {self.rule.source}:{self.rule.line}"
            f" ({self.rule.pattern})"
        )


@dataclass
class Policy:
    """The rules in force for one root, newest match winning.

    ``default`` is what an unmatched path gets. It is ``internal`` rather than
    ``open`` on purpose: material nobody has classified is material nobody has
    cleared for redistribution.
    """

    root: Path
    rules: list[Rule] = field(default_factory=list)
    default: str = "internal"
    #: Paths refused during this policy's lifetime, for the run report.
    refusals: list[Decision] = field(default_factory=list)

    @classmethod
    def load(cls, root: Path | str, *, default: str = "internal") -> Policy:
        """Read ``.councilignore`` from ``root``, if it has one.

        The format is one rule per line::

            <glob> <classification> [owner=<name>] [reason=<text ...>]

        Blank lines and ``#`` comments are ignored. An unreadable or absent
        file yields a policy with no rules, which still applies ``default``.
        """
        root = Path(root).resolve()
        policy = cls(root=root, default=default)
        path = root / POLICY_FILE
        if not path.is_file():
            return policy
        for number, raw in enumerate(path.read_text().splitlines(), start=1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            policy.rules.append(_parse_rule(line, number))
        return policy

    def rule_for(self, path: Path | str) -> Rule | None:
        """The last rule matching ``path``, or None.

        Later lines win, so a broad restriction can be written first and a
        narrow, explicitly granted exception after it.
        """
        try:
            relative = Path(path).resolve().relative_to(self.root)
        except ValueError:
            relative = Path(path)
        text = relative.as_posix()
        match = None
        for rule in self.rules:
            if _matches(text, rule.pattern):
                match = rule
        return match

    def classification(self, path: Path | str) -> str:
        """The classification in force for ``path``."""
        rule = self.rule_for(path)
        return rule.classification if rule else self.default

    def decide(self, path: Path | str) -> Decision:
        """Whether a model may read ``path``, with the rule that decided it."""
        rule = self.rule_for(path)
        allowed = rule.analysable if rule else self.default != "restricted"
        decision = Decision(path=Path(path), allowed=allowed, rule=rule)
        if not allowed:
            self.refusals.append(decision)
        return decision

    def check(self, path: Path | str) -> Path:
        """Return ``path`` if a model may read it; raise ``PolicyRefusal`` if not.

        Use this at every point where repository bytes enter a prompt. It
        raises rather than returning a flag because an ignored flag is how
        restricted material ends up in a context window.
        """
        decision = self.decide(path)
        if not decision.allowed:
            rule = decision.rule or Rule("*", self.default, reason="default classification")
            raise PolicyRefusal(Path(path), rule)
        return Path(path)

    def filter(self, paths) -> tuple[list[Path], list[Decision]]:
        """Split ``paths`` into those a model may read and the refusals.

        The refusals are returned, not dropped, so a corpus sweep can say how
        many files it was not allowed to look at instead of reporting a
        smaller corpus.
        """
        allowed: list[Path] = []
        refused: list[Decision] = []
        for path in paths:
            decision = self.decide(path)
            (allowed if decision.allowed else refused).append(
                Path(path) if decision.allowed else decision
            )
        return allowed, refused


def _matches(text: str, pattern: str) -> bool:
    """Glob match that treats a bare directory name as that whole subtree."""
    if fnmatch.fnmatch(text, pattern):
        return True
    bare = pattern.rstrip("/")
    return fnmatch.fnmatch(text, f"{bare}/*") or text == bare


def _parse_rule(line: str, number: int) -> Rule:
    """Parse one `.councilignore` line into a rule."""
    parts = line.split()
    pattern = parts[0]
    classification = parts[1] if len(parts) > 1 else "restricted"
    if classification not in CLASSIFICATIONS:
        raise ValueError(
            f"{POLICY_FILE}:{number}: unknown classification {classification!r};"
            f" expected one of {', '.join(CLASSIFICATIONS)}"
        )
    owner, reason = "", ""
    tail = parts[2:]
    for index, token in enumerate(tail):
        if token.startswith("owner="):
            owner = token[len("owner=") :]
        elif token.startswith("reason="):
            reason = " ".join([token[len("reason=") :], *tail[index + 1 :]])
            break
    if not owner:
        owner = next((o for o in NO_AI_OWNERS if o in pattern.lower()), "")
    return Rule(
        pattern=pattern,
        classification=classification,
        owner=owner,
        reason=reason,
        source=POLICY_FILE,
        line=number,
    )
