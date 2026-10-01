"""Local-model Council: high-volume analysis on this machine, reviewed by Claude.

The package exists to move repetitive, evidence-grounded work off a metered
reviewer and onto hardware that is already paid for, without letting an
unreviewed model's output become a finding. Read ``docs/local/README.md``
first; the short version is that a local answer is a claim with citations and
a cost, and nothing here can mark its own work verified.
"""

from .envelope import Claim, Envelope, Evidence, Usage
from .hardware import inventory
from .policy import Policy, PolicyRefusal
from .runtime import Server

__all__ = [
    "Envelope",
    "Claim",
    "Evidence",
    "Usage",
    "Policy",
    "PolicyRefusal",
    "Server",
    "inventory",
]
