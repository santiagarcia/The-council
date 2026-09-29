"""Repository loading, safe paths, structured records, and isolated local commits."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import yaml


class CouncilError(ValueError):
    """A user-actionable repository or governance error."""


class UniqueLoader(yaml.SafeLoader):
    """Reject duplicate mapping keys rather than hiding conflicting metadata."""


def unique_mapping(loader: UniqueLoader, node: yaml.MappingNode) -> dict:
    """Construct a mapping only when every key is a unique string."""
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if not isinstance(key, str) or key in result:
            raise CouncilError(f"Duplicate or non-string YAML key: {key!r}")
        result[key] = loader.construct_object(value_node)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def slug(value: str) -> str:
    """Reject unsafe identifiers rather than silently changing them."""
    if not re.fullmatch(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*", value):
        raise CouncilError(f"Invalid identifier: {value!r}; use lowercase words and hyphens")
    return value


def root_at(start: Path) -> Path:
    """Find the nearest Council root, including from a project subdirectory."""
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / "council.yaml").is_file():
            return candidate
    raise CouncilError("No council.yaml found; use --root /path/to/The-council")


def safe_path(root: Path, relative: str | Path) -> Path:
    """Resolve a repository-relative path and reject traversal and symlink escapes."""
    relative = Path(relative)
    if relative.is_absolute() or relative.drive or ":" in str(relative) or ".." in relative.parts:
        raise CouncilError(f"Expected a repository-relative path: {relative}")
    result = (root / relative).resolve()
    if not result.is_relative_to(root.resolve()):
        raise CouncilError(f"Path escapes repository: {relative}")
    return result


def yaml_load(path: Path) -> dict[str, Any]:
    """Read a YAML mapping without constructing arbitrary objects."""
    value = yaml.load(path.read_text(encoding="utf-8"), Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise CouncilError(f"Expected mapping in {path}")
    return value


def read_record(path: Path) -> tuple[dict[str, Any], str]:
    """Read Markdown with mandatory YAML front matter."""
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)(.*)\Z", text, re.DOTALL)
    if not match:
        raise CouncilError(f"Missing YAML front matter: {path}")
    value = yaml.load(match[1], Loader=UniqueLoader)
    if not isinstance(value, dict):
        raise CouncilError(f"Expected front matter mapping: {path}")
    return value, match[2].lstrip("\r\n")


def render_record(metadata: dict[str, Any], body: str) -> str:
    """Serialize stable human-readable metadata and a Markdown narrative."""
    return (
        "---\n"
        + yaml.safe_dump(metadata, sort_keys=False, allow_unicode=True)
        + "---\n\n"
        + body.rstrip()
        + "\n"
    )


def write_new(path: Path, text: str) -> None:
    """Create a file exclusively; never overwrite a user's existing artifact."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def today() -> str:
    """Return the local ISO creation date."""
    return date.today().isoformat()


def git(root: Path, *args: str) -> str:
    """Run local Git without shell expansion or global configuration changes."""
    executable = os.environ.get("COUNCIL_GIT") or shutil.which("git")
    if not executable:
        raise CouncilError("Git not found; add it to PATH or set COUNCIL_GIT to git.exe")
    result = subprocess.run(
        [executable, "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8"
    )
    if result.returncode:
        raise CouncilError(result.stderr.strip() or "Git command failed")
    return result.stdout


def commit_preflight(root: Path) -> None:
    """Refuse any pre-existing staged changes before a command creates records."""
    if (
        git(root, "rev-parse", "--show-toplevel").strip().replace("\\", "/").casefold()
        != root.as_posix().casefold()
    ):
        raise CouncilError("Council root must be the Git repository root for --commit")
    if git(root, "diff", "--cached", "--name-only").strip():
        raise CouncilError("Unrelated staged changes exist; unstage them before --commit")


def commit_files(root: Path, paths: list[Path], agent: str, message: str) -> str:
    """Commit only this command's files; reject a concurrently changed index."""
    commit_preflight(root)
    names = [p.relative_to(root).as_posix() for p in paths]
    git(root, "add", "--", *names)
    staged = set(git(root, "diff", "--cached", "--name-only").splitlines())
    if staged != set(names):
        raise CouncilError("Index changed unexpectedly; inspect staged files before committing")
    return git(
        root,
        "-c",
        f"user.name={agent.title()} (The Council)",
        "-c",
        f"user.email={agent}@council.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "--only",
        "-m",
        message,
        "--",
        *names,
    ).strip()
