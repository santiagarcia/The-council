"""Presenting a source file to a model so that a wrong answer is checkable.

Two rules, both learned from the probes in ``docs/local/benchmark.md``:

* **Line numbers are part of the text.** A model asked to cite a line it
  cannot see will invent one. Numbering every line in the prompt turns a
  citation into something the prompt itself contradicts when it is wrong.
* **A long file is excerpted around what matters, never truncated at the
  top.** An 8k context holds roughly 800 numbered Fortran lines; corpus
  sources run to several thousand. Cutting at the head hides the subroutine
  statement, which is usually the answer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

#: Lines that decide most questions about a Fortran source.
INTERESTING = re.compile(
    r"^\s*(?:[0-9]+\s+)?(?:"
    r"SUBROUTINE|FUNCTION|MODULE|PROGRAM|USE\s|INCLUDE|IMPLICIT|"
    r"DIMENSION|PARAMETER|COMMON|DATA|CHARACTER|INTEGER|REAL|DOUBLE|COMPLEX|"
    r"CALL\s|END\s+SUBROUTINE|ENTRY\s)",
    re.IGNORECASE,
)

MAX_BYTES = 2_000_000


@dataclass
class Excerpt:
    """Numbered lines from one file, and what was left out."""

    path: Path
    text: str
    total_lines: int
    shown_lines: int
    truncated: bool

    @property
    def coverage(self) -> float:
        return self.shown_lines / self.total_lines if self.total_lines else 0.0

    def note(self) -> str:
        """One line telling the model what it is not being shown."""
        if not self.truncated:
            return f"{self.path.name}: all {self.total_lines} lines shown."
        return (
            f"{self.path.name}: {self.shown_lines} of {self.total_lines} lines shown"
            f" (declarations, calls and subroutine headers). Lines not shown are"
            f" marked with an ellipsis. Do not make claims about lines you cannot see."
        )


def read_text(path: Path | str) -> str:
    """Read a possibly non-UTF-8, possibly huge scraped source safely."""
    path = Path(path)
    size = path.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(f"{path}: {size} bytes exceeds the {MAX_BYTES} byte limit")
    return path.read_bytes().decode("utf-8", errors="replace")


def excerpt(path: Path | str, *, max_lines: int = 700, head: int = 60) -> Excerpt:
    """Numbered lines of ``path``, kept within a context budget.

    Keeps the head (where the entry point and its arguments live), then every
    structurally interesting line, then as much of the rest as fits.
    """
    path = Path(path)
    lines = read_text(path).splitlines()
    total = len(lines)
    if total <= max_lines:
        body = "\n".join(f"{n:5d}| {line}" for n, line in enumerate(lines, 1))
        return Excerpt(path, body, total, total, False)

    keep: set[int] = set(range(1, min(head, total) + 1))
    for number, line in enumerate(lines, 1):
        if INTERESTING.match(line):
            keep.update(range(max(1, number - 1), min(total, number + 1) + 1))
        if len(keep) >= max_lines:
            break
    for number in range(1, total + 1):
        if len(keep) >= max_lines:
            break
        keep.add(number)

    rendered, previous = [], 0
    for number in sorted(keep):
        if number != previous + 1 and previous:
            rendered.append(f"      |     ... {number - previous - 1} lines not shown ...")
        rendered.append(f"{number:5d}| {lines[number - 1]}")
        previous = number
    return Excerpt(path, "\n".join(rendered), total, len(keep), True)


def source_form(text: str) -> str:
    """'fixed', 'free' or 'unknown', by the evidence in the text itself.

    Reported so a reviewer can disagree with it; the transform pipeline has
    its own determination and this one does not override it.
    """
    fixed = free = 0
    for line in text.splitlines()[:400]:
        if not line.strip() or line.lstrip().startswith("!"):
            continue
        if line[:1] in "cC*" and not line[:1].isdigit():
            fixed += 1
        elif len(line) > 5 and line[5:6] not in (" ", "") and line[:5].strip() == "":
            fixed += 1
        elif line.rstrip().endswith("&"):
            free += 1
        elif line.startswith(("      ", "\t")):
            fixed += 1
    if fixed > free * 2:
        return "fixed"
    if free > fixed:
        return "free"
    return "unknown"
