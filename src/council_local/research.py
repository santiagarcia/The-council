"""A research cycle with an end, an allowlist and a budget.

Not a daemon that runs until stopped. One cycle has a question, a fixed set of
domains it may read, a page cap, a time cap, a token cap, and a stopping
condition; it produces a report with citations and *proposed* lessons, and it
exits.

Network access is off unless a fetcher is supplied. The module does no I/O of
its own: the caller passes a callable that fetches a URL, which keeps the
policy decisions here and the egress decision with the caller, and makes the
whole thing testable without the network.

What a cycle may never do is fixed in code rather than in a prompt: no login,
no posting, no purchase, no executable download, no merging its own
conclusions, and no important claim resting on a single source.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

#: Domains a cycle may read without a specific grant. Primary and official
#: sources only; a blog that summarises a paper is not the paper.
DEFAULT_ALLOWLIST = (
    "docs.python.org",
    "numpy.org",
    "scipy.org",
    "gcc.gnu.org",
    "fortran-lang.org",
    "j3-fortran.org",
    "netlib.org",
    "nist.gov",
    "nasa.gov",
    "ntrs.nasa.gov",
    "lanl.gov",
    "osti.gov",
    "arxiv.org",
    "doi.org",
    "github.com",
    "raw.githubusercontent.com",
    "help.3ds.com",
    "scholar.archive.org",
    "zenodo.org",
)

#: Refused regardless of allowlist. These are the capabilities a research
#: agent must not have, not merely sites it should avoid.
FORBIDDEN = (
    (re.compile(r"/login|/signin|/oauth|/auth/", re.I), "authentication endpoint"),
    (
        re.compile(r"\.(exe|msi|dmg|deb|rpm|sh|ps1|jar|whl|tar\.gz|zip)(\?|$)", re.I),
        "executable or archive download",
    ),
    (
        re.compile(r"/api/.*(post|create|delete|purchase|order|checkout)", re.I),
        "state-changing API call",
    ),
    (re.compile(r"mailto:|/compose|/message", re.I), "messaging endpoint"),
)

#: An important claim needs this many independent sources.
CORROBORATION = 2


class ResearchRefused(RuntimeError):
    """A cycle tried to do something a research agent may not do."""


@dataclass
class Budget:
    """What one cycle may spend before it stops, whatever it has found."""

    max_pages: int = 12
    max_seconds: int = 600
    max_tokens: int = 60_000
    pages_fetched: int = 0
    seconds_used: float = 0.0
    tokens_used: int = 0

    def exhausted(self) -> str:
        if self.pages_fetched >= self.max_pages:
            return f"page cap reached ({self.max_pages})"
        if self.seconds_used >= self.max_seconds:
            return f"time cap reached ({self.max_seconds}s)"
        if self.tokens_used >= self.max_tokens:
            return f"token cap reached ({self.max_tokens})"
        return ""


@dataclass
class Source:
    """One thing read, kept so a claim can be checked."""

    url: str
    title: str = ""
    retrieved: str = ""
    excerpt: str = ""


@dataclass
class Finding:
    """A statement and the sources behind it."""

    statement: str
    sources: list[str] = field(default_factory=list)
    important: bool = False

    @property
    def corroborated(self) -> bool:
        """Whether this finding rests on enough independent sources."""
        if not self.important:
            return bool(self.sources)
        return len({urlparse(s).netloc for s in self.sources}) >= CORROBORATION


@dataclass
class Cycle:
    """One bounded investigation and its report."""

    question: str
    allowlist: tuple[str, ...] = DEFAULT_ALLOWLIST
    budget: Budget = field(default_factory=Budget)
    sources: list[Source] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    refused: list[str] = field(default_factory=list)
    stopped_because: str = ""

    def permitted(self, url: str) -> tuple[bool, str]:
        """Whether this URL may be read, and why not if it may not."""
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, f"scheme {parsed.scheme!r} is not http(s)"
        for pattern, why in FORBIDDEN:
            if pattern.search(url):
                return False, why
        host = parsed.netloc.lower().split(":")[0]
        if not any(host == allowed or host.endswith("." + allowed) for allowed in self.allowlist):
            return False, f"{host} is not on the allowlist"
        return True, ""

    def fetch(self, url: str, fetcher) -> Source | None:
        """Read one page if it is permitted and the budget allows."""
        stop = self.budget.exhausted()
        if stop:
            self.stopped_because = stop
            return None
        ok, why = self.permitted(url)
        if not ok:
            self.refused.append(f"{url}: {why}")
            return None
        started = time.time()
        text = fetcher(url)
        self.budget.pages_fetched += 1
        self.budget.seconds_used += time.time() - started
        self.budget.tokens_used += len(text) // 4
        source = Source(url=url, retrieved=time.strftime("%Y-%m-%d"), excerpt=text[:2000])
        self.sources.append(source)
        return source

    def record(self, statement: str, sources: list[str], *, important: bool = False) -> Finding:
        """Record a finding. An uncorroborated important claim is kept but marked."""
        finding = Finding(statement=statement, sources=list(sources), important=important)
        self.findings.append(finding)
        return finding

    def report(self) -> dict:
        """The structured report a cycle owes, with the gaps visible."""
        uncorroborated = [f.statement for f in self.findings if not f.corroborated]
        return {
            "question": self.question,
            "sources": [{"url": s.url, "retrieved": s.retrieved} for s in self.sources],
            "findings": [
                {
                    "statement": f.statement,
                    "sources": f.sources,
                    "important": f.important,
                    "corroborated": f.corroborated,
                }
                for f in self.findings
            ],
            "uncorroborated": uncorroborated,
            "refused": self.refused,
            "budget": {
                "pages": self.budget.pages_fetched,
                "seconds": round(self.budget.seconds_used, 1),
                "tokens": self.budget.tokens_used,
            },
            "stopped_because": self.stopped_because or "the question was answered",
            # A cycle proposes. Nothing it concludes is adopted here.
            "lessons_proposed": len(self.findings),
            "lessons_adopted": 0,
            "needs_claude": True,
        }
