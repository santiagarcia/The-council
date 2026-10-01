"""A source with no stated licence is research-only, not probably fine.

Provenance is derived from the corpus registry rather than written beside it,
so there is one answer to "where did this come from". What this module adds is
the judgement the registry does not make: what may be redistributed.
"""

from __future__ import annotations

from council_local.provenance import (
    REDISTRIBUTABLE,
    STATUSES,
    from_registry_record,
    redistribution_for,
)


def test_an_unstated_licence_is_not_permission():
    for silence in ("", None, "unknown", "none", "   "):
        assert redistribution_for(silence) == "research_only_do_not_redistribute"


def test_a_permissive_licence_permits_redistribution():
    assert redistribution_for("MIT") == "redistributable_with_attribution"
    assert redistribution_for("Apache-2.0") == "redistributable_with_attribution"


def test_a_copyleft_licence_carries_its_obligations():
    for identifier in ("GPL-3.0-only", "LGPL-2.1-only", "MPL-2.0", "EPL-2.0"):
        assert redistribution_for(identifier) == "share_alike_obligations"


def test_an_unrecognised_licence_is_not_assumed_permissive():
    assert redistribution_for("SomeCompany-Proprietary-1.0") == "research_only_do_not_redistribute"


def test_a_record_reports_the_fields_it_is_missing():
    entry = from_registry_record(
        {"source_id": "repo__x/umat.f", "sha256": "abc", "license_spdx": "MIT", "bytes": 10}
    )
    assert "source_url" in entry.gaps
    assert "retrieval_date" in entry.gaps
    assert not entry.complete_record


def test_a_complete_record_has_no_gaps():
    entry = from_registry_record(
        {
            "source_id": "repo__x/umat.f",
            "acquisition_url": "https://example.invalid/x",
            "retrieved": "2026-09-01",
            "license_spdx": "MIT",
            "sha256": "abc",
            "bytes": 10,
            "adequately_specified": True,
        }
    )
    assert entry.complete_record
    assert entry.may_redistribute
    assert entry.completeness == "complete"


def test_the_statuses_and_the_licence_set_stay_in_step():
    assert "research_only_do_not_redistribute" in STATUSES
    assert "MIT" in REDISTRIBUTABLE
