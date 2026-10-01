"""Which Council member answers a local task, and what it is told.

A member is a system prompt plus a scope, not a separate model. All of them
share one loaded set of weights; switching member costs nothing.

Seven members have versioned identities under ``members/``, and those are
loaded from disk so the local prompt and the Claude-side prompt cannot drift
apart. Three more -- Noether, Maya and Nico -- are named in the local plan but
have no identity in ``council.yaml`` yet. They are defined here as local roles
only. Promoting them to full members changes the Council's roster, which the
charter reserves for Santiago's review, so this package does not do it.
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
        "identity": None,
        "brief": "Check mathematical assumptions, tensor and Voigt "
        "conventions, index ranges and derivations. Produce a "
        "counterexample rather than an opinion.",
        "local_only": True,
    },
    "maya": {
        "identity": None,
        "brief": "Judge the CLI and GUI as a user meets them: the error "
        "message, the default, the next step.",
        "local_only": True,
    },
    "nico": {
        "identity": None,
        "brief": "Cold-read. You have not seen this project. Say exactly "
        "where the instructions stop being followable.",
        "local_only": True,
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


@dataclass(frozen=True)
class Role:
    """One member as the local runtime sees it."""

    name: str
    brief: str
    identity_text: str = ""
    local_only: bool = False

    def system_prompt(self, task: str) -> str:
        """The system prompt for this member on this task.

        The versioned identity is trimmed hard. A 7B model at an 8k context
        gives better answers from four lines of scope than from a page of
        charter text, and the page costs tokens that the evidence needs.
        """
        parts = [f"You are {self.name.title()} of the Council.", self.brief]
        if self.identity_text:
            parts.append(self.identity_text)
        parts.append(f"Current task: {task}.")
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
    )


def role_for_task(task: str) -> Role:
    """The member a task goes to by default."""
    return role(TASK_ROLES.get(task, "ada"))


def roster() -> list[Role]:
    """Every local role, versioned members first."""
    return sorted((role(n) for n in ROLES), key=lambda r: (r.local_only, r.name))
