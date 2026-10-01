"""Provenance for scraped corpus sources, read from the record that exists.

The UMAT repository's `corpus_registry.json` already carries acquisition URL,
commit, licence, SHA-256 and byte count for all 391 acquired sources. Writing
a second manifest beside it would create two answers to the same question, so
this module defines the schema the Council needs and *derives* it from that
registry, reporting what is missing rather than inventing it.

The one judgement added here is redistribution. A source whose licence is
unstated is not "probably fine": it is `research_only_do_not_redistribute`
until someone establishes otherwise, and that is what the field says.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: SPDX identifiers whose terms permit redistribution with attribution.
REDISTRIBUTABLE = {
    "MIT",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "Apache-2.0",
    "ISC",
    "Zlib",
    "CC0-1.0",
    "Unlicense",
    "MPL-2.0",
    "LGPL-2.1-only",
    "LGPL-3.0-only",
    "GPL-2.0-only",
    "GPL-3.0-only",
    "EPL-2.0",
}

#: Redistribution statuses, from most to least permissive.
STATUSES = (
    "redistributable_with_attribution",
    "share_alike_obligations",
    "research_only_do_not_redistribute",
    "unknown",
)


@dataclass
class Provenance:
    """Where one corpus source came from and what may be done with it."""

    source_id: str
    source_url: str = ""
    retrieval_date: str = ""
    license_spdx: str = ""
    author_or_organisation: str = ""
    original_filename: str = ""
    sha256: str = ""
    bytes: int = 0
    redistribution: str = "unknown"
    completeness: str = "unknown"
    validation: str = "unknown"
    gaps: list[str] = field(default_factory=list)

    @property
    def may_redistribute(self) -> bool:
        return self.redistribution == "redistributable_with_attribution"

    @property
    def complete_record(self) -> bool:
        """Whether every field a citation needs is actually present."""
        return not self.gaps


def redistribution_for(license_spdx: str) -> str:
    """The redistribution status a licence implies.

    Unstated means research-only. A licence nobody recorded is not a licence
    that permits anything; treating silence as permission is how third-party
    code ends up in a release.
    """
    identifier = (license_spdx or "").strip()
    if not identifier or identifier.lower() in ("", "none", "unknown", "unstated"):
        return "research_only_do_not_redistribute"
    if identifier in REDISTRIBUTABLE:
        if identifier.startswith(("GPL", "LGPL", "MPL", "EPL")):
            return "share_alike_obligations"
        return "redistributable_with_attribution"
    return "research_only_do_not_redistribute"


def from_registry_record(record: dict) -> Provenance:
    """One provenance row derived from a registry record."""
    source_id = record.get("source_id", "")
    repository = record.get("repository") or ""
    author = repository.split("__")[0] if "__" in repository else repository
    entry = Provenance(
        source_id=source_id,
        source_url=record.get("acquisition_url") or "",
        retrieval_date=record.get("retrieved") or record.get("acquired") or "",
        license_spdx=record.get("license_spdx") or "",
        author_or_organisation=author,
        original_filename=Path(source_id).name if source_id else "",
        sha256=record.get("sha256") or "",
        bytes=int(record.get("bytes") or 0),
        completeness=(
            "complete" if record.get("adequately_specified") else "incomplete_or_unspecified"
        ),
        validation=record.get("terminal_state") or "unknown",
    )
    entry.redistribution = redistribution_for(entry.license_spdx)
    for name, value in (
        ("source_url", entry.source_url),
        ("retrieval_date", entry.retrieval_date),
        ("license_spdx", entry.license_spdx),
        ("sha256", entry.sha256),
    ):
        if not value:
            entry.gaps.append(name)
    return entry


def manifest(registry: Path | str) -> dict:
    """A provenance manifest for a whole registry, with its gaps counted."""
    records = json.loads(Path(registry).read_text())["records"]
    rows = [from_registry_record(record) for record in records]
    by_status: dict[str, int] = {}
    missing: dict[str, int] = {}
    for row in rows:
        by_status[row.redistribution] = by_status.get(row.redistribution, 0) + 1
        for gap in row.gaps:
            missing[gap] = missing.get(gap, 0) + 1
    return {
        "schema": "council-local/provenance/1",
        "source_registry": str(registry),
        "count": len(rows),
        "by_redistribution": dict(sorted(by_status.items())),
        "records_missing_a_field": dict(sorted(missing.items())),
        "complete_records": sum(1 for r in rows if r.complete_record),
        "rows": [asdict(r) for r in rows],
    }
