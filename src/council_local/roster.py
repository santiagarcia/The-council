"""Which Council member answers a local task, and what it is told.

A member is a system prompt plus a scope, not a separate model. All of them
share one loaded set of weights; switching member costs nothing.

All ten members have versioned identities under ``members/``, loaded from disk
so the local prompt and the Claude-side prompt cannot drift apart. Noether,
Maya and Nico were local-only roles here until the ten-member roster was
merged; they are ordinary members now.

Nico is the exception that needs code, not a note. The charter forbids sending
him the shared objective, the project context, other members' conclusions or
previous technical answers: a cold read is worthless once the reader has been
told the answer. So an isolated role refuses to build an ordinary task prompt
at all, and the only prompt it will build contains the artifact and the
intended audience. ``council review --agent nico --mode cold-read --artifact
PATH`` is what prepares the packet; this module will not invent one.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MEMBERS = REPO / "members"

#: Local roles. ``identity`` names a directory under ``members/`` when the
#: member has a versioned identity; otherwise the brief here is all there is.
ROLES: dict[str, dict] = {
    "atlas": {
        "identity": "atlas",
        "brief": "Decompose the task, route it, and record the decision. Do not implement.",
    },
    "curie": {
        "identity": "curie",
        "brief": "Interpret the constitutive model and judge physical "
        "plausibility. Name the kinematics and the state.",
    },
    "gauss": {
        "identity": "gauss",
        "brief": "Judge derivatives, conditioning and numerical error. "
        "Separate a tolerance question from a reference question.",
    },
    "ada": {
        "identity": "ada",
        "brief": "Read the Fortran and the build. Name constructs, dialect, "
        "dependencies and what would stop a compile.",
    },
    "vera": {
        "identity": "vera",
        "brief": "Review adversarially. Try to falsify the claim you are "
        "given before you agree with it.",
    },
    "iris": {
        "identity": "iris",
        "brief": "Explain for a reader who was not here. Keep every "
        "statement traceable to the evidence.",
    },
    "scout": {
        "identity": "scout",
        "brief": "Establish provenance: where the source came from, its "
        "licence, and whether it is complete.",
    },
    "noether": {
        "identity": "noether",
        "brief": "Check mathematical assumptions, tensor and Voigt "
        "conventions, index ranges and derivations. Produce a "
        "counterexample rather than an opinion.",
    },
    "maya": {
        "identity": "maya",
        "brief": "Judge the CLI and GUI as a user meets them: the error "
        "message, the default, the next step.",
    },
    "nico": {
        "identity": "nico",
        "brief": "You are reading this for the first time. Say exactly where "
        "it stops being followable, which words are undefined, and what "
        "you cannot restate.",
        # Never given the task, the objective, or anyone else's findings.
        "isolated": True,
    },
}

#: Which role a task goes to by default. Routing is advice; a caller may override.
TASK_ROLES = {
    "classify_umat": "ada",
    "extract_umat_contract": "ada",
    "detect_dependencies": "ada",
    "triage_failure": "ada",
    "review_transformation": "vera",
    "analyze_residual_sensitivity": "gauss",
    "explain_constitutive_update": "curie",
    "audit_conventions": "noether",
    "research_question": "scout",
    "cold_read": "nico",
    "usability_review": "maya",
    "document": "iris",
    "decompose": "atlas",
}


class IsolationRequired(RuntimeError):
    """An isolated member was about to be given the shared context."""


@dataclass(frozen=True)
class Role:
    """One member as the local runtime sees it."""

    name: str
    brief: str
    identity_text: str = ""
    local_only: bool = False
    #: True for a member who must never receive the task, the objective or
    #: another member's conclusions. Nico is the only one today.
    isolated: bool = False

    def system_prompt(self, task: str) -> str:
        """The system prompt for this member on this task.

        The versioned identity is trimmed hard. A 7B model at an 8k context
        gives better answers from four lines of scope than from a page of
        charter text, and the page costs tokens that the evidence needs.

        Raises for an isolated member. Naming the task is already telling the
        reader what the artifact is supposed to achieve, which is the one thing
        a cold read has to establish for itself.
        """
        if self.isolated:
            raise IsolationRequired(
                f"{self.name} must not be given a task description. Prepare the"
                " packet with `council review --agent"
                f" {self.name} --mode cold-read --artifact PATH` and use"
                " Role.cold_read_prompt(). See docs/reader-review.md."
            )
        parts = [f"You are {self.name.title()} of the Council.", self.brief]
        if self.identity_text:
            parts.append(self.identity_text)
        parts.append(f"Current task: {task}.")
        return "\n\n".join(parts)

    def cold_read_prompt(self, *, audience: str = "") -> str:
        """The only prompt an isolated member gets: no task, no objective.

        It carries the member's own disposition and the intended audience, and
        nothing about what the artifact is for. The artifact itself is supplied
        separately as the user message.
        """
        if not self.isolated:
            raise IsolationRequired(f"{self.name} is not an isolated member; use system_prompt()")
        parts = [f"You are {self.name.title()} of the Council.", self.brief]
        if self.identity_text:
            parts.append(self.identity_text)
        if audience:
            parts.append(f"You are the kind of reader described as: {audience}.")
        parts.append(
            "You have not been told what this document is for, and you must not"
            " guess from outside knowledge. Report only what the text in front of"
            " you does and does not let you do."
        )
        return "\n\n".join(parts)


@cache
def _identity(name: str) -> str:
    """The 'Working practice' paragraph of a member's identity, if present."""
    path = MEMBERS / name / "identity.md"
    if not path.is_file():
        return ""
    lines = path.read_text().splitlines()
    try:
        start = lines.index("## Working practice") + 1
    except ValueError:
        return ""
    collected = []
    for line in lines[start:]:
        if line.startswith("## "):
            break
        if line.strip():
            collected.append(line.strip())
    return " ".join(collected)[:700]


def role(name: str) -> Role:
    """Look up one role by name."""
    key = name.lower()
    if key not in ROLES:
        raise KeyError(f"unknown role {name!r}; known: {', '.join(sorted(ROLES))}")
    spec = ROLES[key]
    identity = _identity(spec["identity"]) if spec.get("identity") else ""
    return Role(
        name=key,
        brief=spec["brief"],
        identity_text=identity,
        local_only=bool(spec.get("local_only")),
        isolated=bool(spec.get("isolated")),
    )


def role_for_task(task: str) -> Role:
    """The member a task goes to by default."""
    return role(TASK_ROLES.get(task, "ada"))


def roster() -> list[Role]:
    """Every local role, versioned members first."""
    return sorted((role(n) for n in ROLES), key=lambda r: (r.local_only, r.name))


def isolated_roles() -> list[str]:
    """Members a caller must not hand the shared context to."""
    return sorted(name for name, spec in ROLES.items() if spec.get("isolated"))
