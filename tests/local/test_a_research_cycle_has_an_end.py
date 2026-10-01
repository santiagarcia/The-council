"""A research cycle stops, stays on its allowlist, and adopts nothing.

The capabilities a research agent must not have are fixed in code rather than
asked for in a prompt: no login, no download of an executable, no
state-changing call, no messaging.
"""

from __future__ import annotations

from council_local.research import Budget, Cycle


def _cycle(**over):
    return Cycle(
        question="how do other systems transform Fortran sources?",
        budget=Budget(**over) if over else Budget(),
    )


def test_an_off_allowlist_host_is_refused():
    cycle = _cycle()
    ok, why = cycle.permitted("https://random-blog.example/post")
    assert not ok
    assert "allowlist" in why


def test_a_primary_source_is_permitted():
    assert _cycle().permitted("https://arxiv.org/abs/1234.5678")[0]
    assert _cycle().permitted("https://gcc.gnu.org/onlinedocs/gfortran/")[0]


def test_the_capabilities_a_research_agent_must_not_have():
    cycle = _cycle()
    for url, expected in [
        ("https://github.com/login", "authentication endpoint"),
        ("https://github.com/x/releases/tool.exe", "executable or archive download"),
        ("https://github.com/api/v2/create", "state-changing API call"),
        ("https://arxiv.org/compose", "messaging endpoint"),
    ]:
        ok, why = cycle.permitted(url)
        assert not ok and why == expected, url


def test_a_cycle_stops_at_its_page_cap():
    cycle = _cycle(max_pages=2)
    for index in range(5):
        cycle.fetch(f"https://arxiv.org/abs/{index}", lambda _: "text")
    assert cycle.budget.pages_fetched == 2
    assert "page cap" in cycle.stopped_because


def test_an_important_claim_needs_two_independent_sources():
    cycle = _cycle()
    one = cycle.record(
        "OTI is equivalent to forward-mode AD", ["https://arxiv.org/abs/1"], important=True
    )
    assert not one.corroborated

    two = cycle.record(
        "OTI is equivalent to forward-mode AD",
        ["https://arxiv.org/abs/1", "https://nist.gov/x"],
        important=True,
    )
    assert two.corroborated

    same_host = cycle.record(
        "claim", ["https://arxiv.org/a", "https://arxiv.org/b"], important=True
    )
    assert not same_host.corroborated


def test_the_report_shows_what_was_refused_and_adopts_nothing():
    cycle = _cycle()
    cycle.fetch("https://random-blog.example/post", lambda _: "text")
    cycle.record("something", ["https://arxiv.org/abs/1"])
    report = cycle.report()
    assert report["refused"]
    assert report["lessons_adopted"] == 0
    assert report["needs_claude"]
