"""Bounded tasks a local Council member may be given.

Each task is a function that reads named files under a policy, builds a
grounded prompt, and returns an :class:`~council_local.envelope.Envelope`.
Tasks never write to a repository; proposing a change is a separate step that
produces a patch for review.
"""

from .residual import audit_conventions, explain_interface_contract
from .umat import (
    classify_umat,
    detect_dependencies,
    extract_umat_contract,
    review_transformation,
    triage_failure,
)

__all__ = [
    "classify_umat",
    "extract_umat_contract",
    "detect_dependencies",
    "triage_failure",
    "review_transformation",
    "audit_conventions",
    "explain_interface_contract",
    "TASKS",
]

#: Task name -> callable, for the MCP bridge and the benchmark.
TASKS = {
    "classify_umat": classify_umat,
    "extract_umat_contract": extract_umat_contract,
    "detect_dependencies": detect_dependencies,
    "triage_failure": triage_failure,
    "review_transformation": review_transformation,
    "audit_conventions": audit_conventions,
    "explain_interface_contract": explain_interface_contract,
}
