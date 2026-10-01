"""Tasks over assembly code: conventions, contracts, and what a log means.

A convention audit is delegable for a specific reason: index ranges, Voigt
ordering, transposes and signs are *stated in the source*, so an answer can be
cited and checked in a minute. Everything downstream of a convention -- the
residual it assembles, the sensitivity it produces, the identity that checks
it -- is not delegable, because those have numerical references and the
reference is the authority.

So these tasks read and report. None of them judges whether an assembly is
correct.
"""

from __future__ import annotations

from pathlib import Path

from ..client import LocalClient
from ..envelope import Envelope
from ..policy import Policy
from ..roster import role_for_task
from ..sources import excerpt

CONVENTION_ANSWERS = {
    "voigt_order": {"type": "string"},
    "index_base": {"type": "string", "enum": ["zero", "one", "mixed", "unclear"]},
    "shear_factor": {
        "type": "string",
        "enum": ["engineering", "tensorial", "unclear", "not_applicable"],
    },
    "transposes": {"type": "array", "items": {"type": "string"}},
    "sign_conventions": {"type": "array", "items": {"type": "string"}},
    "inconsistencies": {"type": "array", "items": {"type": "string"}},
}

CONTRACT_ANSWERS = {
    "inputs_required": {"type": "array", "items": {"type": "string"}},
    "outputs_produced": {"type": "array", "items": {"type": "string"}},
    "shapes_asserted": {"type": "array", "items": {"type": "string"}},
    "shapes_assumed_without_check": {"type": "array", "items": {"type": "string"}},
    "element_types_supported": {"type": "array", "items": {"type": "string"}},
}


def audit_conventions(
    path, *, policy: Policy | None = None, client: LocalClient | None = None
) -> Envelope:
    """Report the tensor and indexing conventions a module actually uses.

    Asks for what the code does, never for what it should do. A disagreement
    between two conventions in one file is the finding worth having, and it is
    visible without knowing which is right.
    """
    path = Path(path)
    policy = policy or Policy.load(path.parent)
    policy.check(path)
    client = client or LocalClient()
    piece = excerpt(path, max_lines=700)
    system = role_for_task("audit_conventions").system_prompt(
        "report the tensor and index conventions a module uses"
    )
    prompt = f"""Below is {path.name}, with line numbers. {piece.note()}

{piece.text}

Report, each as a claim citing its line:
1. The component ordering used for symmetric second-order tensors, in the
   order the code writes them, e.g. 11,22,33,12,13,23. Quote the line where
   the order is visible -- an array literal, a loop bound, an index map.
2. Whether array indices are 0-based, 1-based, or both in different places.
   If both, say exactly where each is used; that is the finding.
3. Whether shear components carry an engineering factor of 2 anywhere, and
   where it is applied and removed.
4. Every transpose, explicit or implied by an index swap, with its line.
5. Every place a sign is negated on a residual, a stress or a derivative.
6. Any two places in this file that disagree with each other on any of the
   above.

Do not say which convention is correct. Report what the code does and where
it is inconsistent with itself.

Put the short answers in "answers". In "claims", each statement must be the
ANSWER as a complete sentence, never a restatement of the question."""
    return client.ask(
        agent="noether",
        task="audit_conventions",
        system=system,
        prompt=prompt,
        files_examined=[str(path)],
        root=path.parent,
        num_predict=1200,
        answers=CONVENTION_ANSWERS,
    )


def explain_interface_contract(
    path, *, policy: Policy | None = None, client: LocalClient | None = None
) -> Envelope:
    """What a module demands of its caller and what it promises back."""
    path = Path(path)
    policy = policy or Policy.load(path.parent)
    policy.check(path)
    client = client or LocalClient()
    piece = excerpt(path, max_lines=700)
    system = role_for_task("document").system_prompt(
        "state an interface contract from the code that implements it"
    )
    prompt = f"""Below is {path.name}, with line numbers. {piece.note()}

{piece.text}

Report, each as a claim with its line:
1. Every input the public entry points require, with its expected shape.
2. Every output they produce, with its shape.
3. Every shape that is CHECKED at runtime -- an assert, a raise, a
   comparison -- with the line of the check.
4. Every shape that is ASSUMED but never checked. This is the list that
   matters: name each one and the line where the assumption is first relied
   on.
5. Element types, component counts or kinematics the code is restricted to,
   and whether the restriction is enforced or merely assumed.

A restriction that is enforced produces a clear error; one that is assumed
produces a wrong number. Say which each is.

Put the short answers in "answers". In "claims", each statement must be the
ANSWER as a complete sentence, never a restatement of the question."""
    return client.ask(
        agent="iris",
        task="explain_interface_contract",
        system=system,
        prompt=prompt,
        files_examined=[str(path)],
        root=path.parent,
        num_predict=1200,
        answers=CONTRACT_ANSWERS,
    )
