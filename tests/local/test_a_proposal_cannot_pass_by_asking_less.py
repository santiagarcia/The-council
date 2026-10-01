"""A patch that makes the suite ask less is refused before the suite is run.

Running the tests on a patch that deleted an assertion produces a number that
looks like evidence and is not. So the weakening check comes first, and its
refusal does not depend on what pytest would have said.
"""

from __future__ import annotations

from council_local.proposals import check_not_weakened, evaluate, open_worktree

WEAKENED = {
    "a removed assertion": "--- a\n+++ b\n-    assert result == 1\n+    pass\n",
    "a skipped test": "--- a\n+++ b\n+@pytest.mark.skip(reason='flaky')\n",
    "an xfailed test": "--- a\n+++ b\n+@pytest.mark.xfail\n",
    "a deleted test": "--- a\n+++ b\n-def test_the_thing_that_mattered():\n",
    "a swallowed exception": "--- a\n+++ b\n+    except Exception:\n+        pass\n",
    "a removed raise": "--- a\n+++ b\n-        raise ValueError('bad input')\n",
}


def test_every_way_of_asking_less_is_caught():
    for label, diff in WEAKENED.items():
        findings, _ = check_not_weakened(diff)
        assert findings, f"not caught: {label}"


def test_an_honest_change_is_not_flagged():
    findings, tolerance = check_not_weakened("--- a\n+++ b\n-    return x + 1\n+    return x + 2\n")
    assert not findings and not tolerance


def test_a_tolerance_change_is_allowed_but_never_silent():
    """Widening a tolerance can be right; doing it unnoticed cannot."""
    findings, tolerance = check_not_weakened("--- a\n+++ b\n-    rtol = 1e-10\n+    rtol = 1e-6\n")
    assert not findings
    assert tolerance


def test_an_empty_patch_is_refused(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "a.txt").write_text("x\n")
    _git(repo, "add", "a.txt")
    _git(repo, "commit", "-qm", "base")

    worktree, branch = open_worktree(repo, branch="proposal")
    try:
        proposal = evaluate(repo, worktree, branch, writable=["a.txt"])
        assert not proposal.accepted_for_review
        assert proposal.refusal == "the patch is empty"
        assert proposal.needs_claude
    finally:
        _cleanup(repo, worktree)


def test_a_write_outside_the_allowed_paths_is_refused(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.invalid")
    _git(repo, "config", "user.name", "t")
    (repo / "allowed.txt").write_text("x\n")
    _git(repo, "add", "allowed.txt")
    _git(repo, "commit", "-qm", "base")

    worktree, branch = open_worktree(repo, branch="proposal")
    try:
        (worktree / "allowed.txt").write_text("y\n")
        (worktree / "sneaky.txt").write_text("elsewhere\n")
        proposal = evaluate(repo, worktree, branch, writable=["allowed.txt"])
        assert not proposal.accepted_for_review
        assert "sneaky.txt" in proposal.refusal
        assert proposal.out_of_scope_writes == ["sneaky.txt"]
    finally:
        _cleanup(repo, worktree)


def _git(repo, *args):
    import subprocess

    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _cleanup(repo, worktree):
    from council_local.proposals import close_worktree

    close_worktree(repo, worktree)
