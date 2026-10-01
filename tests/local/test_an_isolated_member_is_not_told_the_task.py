"""Nico must not be handed the shared context, and the code has to refuse it.

A cold read establishes whether an artifact can be followed by someone who has
not been told what it is for. Naming the task defeats it: the reader then knows
the answer the document was supposed to give them. The charter states this, and
a note in a document is not a safeguard -- so the isolated role refuses to
build an ordinary prompt at all, and the only prompt it will build carries the
member's disposition and the intended audience and nothing else.
"""

from __future__ import annotations

import pytest

from council_local.roster import (
    ROLES,
    IsolationRequired,
    isolated_roles,
    role,
    role_for_task,
    roster,
)


def test_nico_refuses_a_task_description():
    with pytest.raises(IsolationRequired) as caught:
        role("nico").system_prompt("classify a UMAT source")
    message = str(caught.value)
    assert "must not be given a task description" in message
    # The refusal names the supported path rather than just saying no.
    assert "council review --agent nico --mode cold-read" in message


def test_the_cold_read_prompt_carries_no_task_and_no_objective():
    prompt = role("nico").cold_read_prompt(audience="a new graduate student")
    assert "a new graduate student" in prompt
    assert "Current task" not in prompt
    for leaked in ("objective", "UMAT", "corpus", "OTI", "transform", "Abaqus"):
        assert leaked.lower() not in prompt.lower(), leaked


def test_a_non_isolated_member_cannot_borrow_the_cold_read_path():
    """Otherwise 'cold read' becomes a label anyone can apply to themselves."""
    with pytest.raises(IsolationRequired, match="not an isolated member"):
        role("gauss").cold_read_prompt()


def test_only_nico_is_isolated_today():
    assert isolated_roles() == ["nico"]


def test_the_cold_read_task_routes_to_the_isolated_member():
    chosen = role_for_task("cold_read")
    assert chosen.name == "nico"
    assert chosen.isolated


def test_all_ten_members_load_a_versioned_identity():
    """The ten-member roster is merged, so none of them is local-only now."""
    members = roster()
    assert len(members) == 10
    assert {m.name for m in members} == {
        "atlas",
        "curie",
        "gauss",
        "ada",
        "vera",
        "iris",
        "scout",
        "noether",
        "maya",
        "nico",
    }
    for member in members:
        assert member.identity_text, f"{member.name} has no identity text"
        assert not member.local_only, f"{member.name} is still local-only"


def test_every_role_names_an_identity_directory():
    assert all(spec.get("identity") for spec in ROLES.values())
