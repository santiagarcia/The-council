"""Letting a local model propose code without letting it change anything.

A patch from an unreviewed model is a suggestion, and the machinery here keeps
it one. Work happens in a throwaway git worktree on its own branch, writes are
confined to paths named in advance, the repository's own tests decide whether
the patch stands, and what comes back is a diff -- never a merge, never a
push, never a commit on a branch anyone else uses.

Two checks exist because passing tests is not the same as being right:

* a patch that only deletes, skips or weakens tests is rejected outright,
  whatever the suite then says;
* the agent that writes and the agent that judges do not share a context, so
  a model cannot talk itself into its own patch.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

#: Edits that make a suite pass by making it ask less. Matched on the diff's
#: added and removed lines, not on the final file, so an assertion that
#: quietly disappeared is caught as well as one that was commented out.
WEAKENING = (
    (re.compile(r"^-\s*(assert|self\.assert)", re.M), "an assertion was removed"),
    (re.compile(r"^\+.*@pytest\.mark\.(skip|xfail)", re.M), "a test was skipped or xfailed"),
    (re.compile(r"^-.*\bdef test_", re.M), "a test function was removed"),
    (
        re.compile(r"^\+\s*(pass|return)\s*$.*?^\+\s*#\s*TODO", re.M | re.S),
        "a body was replaced with a stub",
    ),
    (
        re.compile(r"^\+.*except\s+Exception\s*:\s*$\n\+\s*pass", re.M),
        "a bare except-pass was added",
    ),
    (re.compile(r"^-.*\braise\b", re.M), "a raise was removed"),
)

#: Tolerance edits are not forbidden, but they are never silent.
TOLERANCE = re.compile(
    r"^[+-].*\b(tol|tolerance|atol|rtol|eps|epsilon|threshold)\b\s*=", re.M | re.I
)


class ProposalRefused(RuntimeError):
    """A proposed patch was refused before it could be reviewed."""


@dataclass
class Proposal:
    """One patch, with everything a reviewer needs and nothing merged."""

    branch: str
    repository: Path
    worktree: Path
    writable: list[str]
    diff: str = ""
    files_changed: list[str] = field(default_factory=list)
    tests_before: dict = field(default_factory=dict)
    tests_after: dict = field(default_factory=dict)
    weakening_findings: list[str] = field(default_factory=list)
    tolerance_changes: bool = False
    out_of_scope_writes: list[str] = field(default_factory=list)
    accepted_for_review: bool = False
    refusal: str = ""
    seconds: float = 0.0

    @property
    def needs_claude(self) -> bool:
        """Always. A proposal is a request for review by construction."""
        return True

    def summary(self) -> str:
        lines = [f"proposal on {self.branch}: {len(self.files_changed)} file(s)"]
        for name in self.files_changed[:10]:
            lines.append(f"  ~ {name}")
        if self.out_of_scope_writes:
            lines.append(f"  OUT OF SCOPE: {', '.join(self.out_of_scope_writes[:5])}")
        if self.weakening_findings:
            lines.append(f"  REFUSED: {'; '.join(self.weakening_findings)}")
        if self.tolerance_changes:
            lines.append("  changes a tolerance -- needs a stated justification")
        before = self.tests_before.get("summary", "not run")
        after = self.tests_after.get("summary", "not run")
        lines.append(f"  tests before: {before}")
        lines.append(f"  tests after:  {after}")
        lines.append(
            f"  accepted for review: {self.accepted_for_review}"
            + (f" ({self.refusal})" if self.refusal else "")
        )
        return "\n".join(lines)


def open_worktree(repository: Path | str, *, branch: str, base: str = "HEAD") -> tuple[Path, str]:
    """A throwaway worktree on a new branch. Never an existing one."""
    repository = Path(repository).resolve()
    name = f"{branch}-{int(time.time())}"
    path = Path(tempfile.mkdtemp(prefix="council-proposal-"))
    subprocess.run(
        ["git", "-C", str(repository), "worktree", "add", "-b", name, str(path), base],
        check=True,
        capture_output=True,
        text=True,
    )
    return path, name


def close_worktree(repository: Path | str, worktree: Path, *, keep_branch: bool = True) -> None:
    """Remove the worktree. The branch is kept: it holds the work."""
    repository = Path(repository).resolve()
    subprocess.run(
        ["git", "-C", str(repository), "worktree", "remove", "--force", str(worktree)],
        capture_output=True,
        text=True,
    )
    if not keep_branch:
        pass  # deleting branches is not something this package does
    shutil.rmtree(worktree, ignore_errors=True)


def run_tests(worktree: Path, *, selector: str = "", timeout: int = 1800) -> dict:
    """Run the repository's own suite and report what it said."""
    argv = [
        "python",
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "-m",
        "not abaqus and not arc and not network",
    ]
    if selector:
        argv += [selector]
    try:
        done = subprocess.run(
            argv, cwd=str(worktree), capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "summary": f"timed out after {timeout}s", "tail": ""}
    tail = (done.stdout or "")[-3000:]
    last = next(
        (
            line
            for line in reversed(tail.splitlines())
            if "passed" in line or "failed" in line or "error" in line
        ),
        "",
    )
    return {
        "ok": done.returncode == 0,
        "returncode": done.returncode,
        "summary": last.strip() or f"exit {done.returncode}",
        "tail": tail,
    }


def inspect_diff(worktree: Path, writable: list[str]) -> tuple[str, list[str], list[str]]:
    """The diff, the files it touches, and anything outside the allowed paths."""
    done = subprocess.run(
        ["git", "-C", str(worktree), "diff", "HEAD"], capture_output=True, text=True, check=True
    )
    diff = done.stdout
    names = subprocess.run(
        ["git", "-C", str(worktree), "diff", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    untracked = subprocess.run(
        ["git", "-C", str(worktree), "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    changed = sorted(set(names) | set(untracked))
    out_of_scope = [
        name
        for name in changed
        if not any(
            name == allowed or name.startswith(allowed.rstrip("/") + "/") for allowed in writable
        )
    ]
    return diff, changed, out_of_scope


def check_not_weakened(diff: str) -> tuple[list[str], bool]:
    """Findings that the patch made the suite ask less, and tolerance edits."""
    findings = [why for pattern, why in WEAKENING if pattern.search(diff)]
    return findings, bool(TOLERANCE.search(diff))


def evaluate(
    repository: Path | str,
    worktree: Path,
    branch: str,
    writable: list[str],
    *,
    before: dict | None = None,
    selector: str = "",
) -> Proposal:
    """Judge a patch that has already been written into ``worktree``."""
    started = time.time()
    diff, changed, out_of_scope = inspect_diff(worktree, writable)
    findings, tolerance = check_not_weakened(diff)
    proposal = Proposal(
        branch=branch,
        repository=Path(repository),
        worktree=worktree,
        writable=list(writable),
        diff=diff[:200_000],
        files_changed=changed,
        tests_before=before or {},
        weakening_findings=findings,
        tolerance_changes=tolerance,
        out_of_scope_writes=out_of_scope,
    )

    if not changed:
        proposal.refusal = "the patch is empty"
    elif out_of_scope:
        proposal.refusal = f"wrote outside the allowed paths: {', '.join(out_of_scope[:5])}"
    elif findings:
        # Refused before the suite is consulted: a suite that passes because
        # it was made to ask less is not evidence, so running it would only
        # produce a number that looks like one.
        proposal.refusal = "; ".join(findings)
    else:
        proposal.tests_after = run_tests(worktree, selector=selector)
        if not proposal.tests_after.get("ok"):
            proposal.refusal = f"tests fail: {proposal.tests_after.get('summary')}"
        else:
            proposal.accepted_for_review = True

    proposal.seconds = round(time.time() - started, 1)
    return proposal
