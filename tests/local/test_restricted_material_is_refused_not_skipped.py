"""A file a model may not read must raise, not quietly drop out of a sweep.

A silent skip in a 391-file corpus pass is indistinguishable from a file that
was read and found uninteresting. These tests fix the opposite behaviour: the
refusal is raised at the point the bytes would enter a prompt, and a batch
reports what it was not allowed to look at.
"""

from __future__ import annotations

import pytest

from council_local.policy import CLASSIFICATIONS, Policy, PolicyRefusal


def _policy(tmp_path, text):
    (tmp_path / ".councilignore").write_text(text)
    return Policy.load(tmp_path)


def test_restricted_material_raises_at_the_point_of_use(tmp_path):
    policy = _policy(tmp_path, "secret/ restricted owner=jhu reason=no AI-use grant\n")
    (tmp_path / "secret").mkdir()
    target = tmp_path / "secret" / "model.f"
    target.write_text("      SUBROUTINE UMAT\n")
    with pytest.raises(PolicyRefusal) as caught:
        policy.check(target)
    message = str(caught.value)
    assert "jhu" in message and "no AI-use grant" in message
    assert ".councilignore:1" in message


def test_an_unclassified_path_is_internal_not_open(tmp_path):
    """Material nobody classified is material nobody cleared for release."""
    policy = Policy.load(tmp_path)
    assert policy.classification(tmp_path / "whatever.f") == "internal"
    assert policy.decide(tmp_path / "whatever.f").allowed


def test_a_later_rule_narrows_an_earlier_one(tmp_path):
    policy = _policy(
        tmp_path,
        "corpus/ restricted reason=unscreened\ncorpus/cleared/ internal reason=licence checked\n",
    )
    assert not policy.decide("corpus/raw.f").allowed
    assert policy.decide("corpus/cleared/ok.f").allowed


def test_a_filtered_sweep_reports_what_it_could_not_read(tmp_path):
    policy = _policy(tmp_path, "private/ restricted reason=no grant\n")
    allowed, refused = policy.filter(["open.f", "private/a.f", "private/b.f"])
    assert [p.name for p in allowed] == ["open.f"]
    assert len(refused) == 2
    assert all("restricted" in d.reason for d in refused)


def test_the_refusal_count_survives_on_the_policy(tmp_path):
    policy = _policy(tmp_path, "private/ restricted reason=no grant\n")
    policy.filter(["private/a.f", "private/b.f"])
    assert len(policy.refusals) == 2


def test_an_unknown_classification_is_a_configuration_error(tmp_path):
    with pytest.raises(ValueError, match="unknown classification"):
        _policy(tmp_path, "x/ sort-of-secret\n")


def test_every_classification_is_spelled_the_same_everywhere():
    assert CLASSIFICATIONS == ("open", "internal", "restricted")
