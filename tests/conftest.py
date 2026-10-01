"""Isolated repositories: tests never modify real Council memories or decks."""

import os
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def repo(tmp_path):
    """Copy only the public Council seed into a clean temporary directory."""
    destination = tmp_path / "council"
    destination.mkdir()
    for name in (
        "constitution",
        "members",
        "memory",
        "relationships",
        "projects",
        "protocols",
        "schemas",
        "templates",
        "evaluations",
        "style",
        "style_sources",
    ):
        shutil.copytree(
            ROOT / name,
            destination / name,
            ignore=shutil.ignore_patterns("private", "derived")
            if name in {"style", "style_sources"}
            else shutil.ignore_patterns("objective.md")
            if name == "projects"
            else None,
        )
    for name in ("style_sources/presentations/private", "style/derived"):
        (destination / name).mkdir(parents=True, exist_ok=True)
        (destination / name / ".gitkeep").touch()
    for name in ("council.yaml", ".gitignore", "AGENTS.md", "COUNCIL_CHARTER.md"):
        shutil.copyfile(ROOT / name, destination / name)
    return destination


@pytest.fixture
def git_executable(monkeypatch):
    """Use configured Git and require tests to exercise actual Git isolation."""
    executable = os.environ.get("COUNCIL_GIT") or shutil.which("git")
    if not executable:
        pytest.fail("Git is required for isolation tests; set COUNCIL_GIT or PATH")
    monkeypatch.setenv("COUNCIL_GIT", executable)
    return executable
