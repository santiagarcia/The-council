"""Real Git integration tests for constrained local authoring."""

import subprocess

import pytest

from council.cli import main
from council.store import git


@pytest.fixture
def git_repo(repo, git_executable):
    """Initialize a disposable repository with a baseline commit."""
    subprocess.run([git_executable, "init", str(repo)], check=True, capture_output=True)
    git(repo, "add", ".")
    git(
        repo,
        "-c",
        "user.name=Fixture",
        "-c",
        "user.email=fixture@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-m",
        "fixture",
    )
    return repo


@pytest.mark.parametrize(
    "command,agent,extra",
    [
        ("remember", "gauss", ["--project", "council-bootstrap", "--type", "procedural"]),
        ("reflect", "vera", ["--project", "council-bootstrap"]),
        ("propose-identity-change", "iris", []),
    ],
)
def test_commit_only_owns_its_artifact(git_repo, command, agent, extra):
    root = git_repo
    unrelated = root / "council.yaml"
    unrelated.write_text(unrelated.read_text() + "# unrelated user change\n", encoding="utf-8")
    assert main(["--root", str(root), command, "--agent", agent, *extra, "--commit"]) == 0
    paths = git(root, "show", "--format=", "--name-only", "HEAD").strip().splitlines()
    assert len(paths) == 1
    assert paths[0].endswith(".md")
    assert "council.yaml" not in paths
    assert agent in git(root, "show", "-s", "--format=%ae", "HEAD")
    assert " M council.yaml" in git(root, "status", "--short")
    assert not git(root, "diff", "--cached", "--name-only").strip()
    assert "user" not in git(root, "config", "--local", "--list")


def test_unrelated_staging_refuses_before_write(git_repo):
    root = git_repo
    (root / "unrelated.txt").write_text("user work", encoding="utf-8")
    git(root, "add", "unrelated.txt")
    count = len(list((root / "memory").rglob("*.md")))
    assert (
        main(
            [
                "--root",
                str(root),
                "remember",
                "--agent",
                "gauss",
                "--project",
                "council-bootstrap",
                "--type",
                "procedural",
                "--commit",
            ]
        )
        == 2
    )
    assert len(list((root / "memory").rglob("*.md"))) == count
    assert git(root, "diff", "--cached", "--name-only").strip() == "unrelated.txt"


def test_private_sources_are_ignored(git_repo):
    root = git_repo
    for name in (
        "style_sources/presentations/private/secret.pptx",
        "secret.pptx",
        "OneDrive_1_9-29-2026.zip",
        "style/derived/deck-inventory.json",
    ):
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
        assert git(root, "check-ignore", name).strip() == name
    assert git(root, "status", "--porcelain").strip() == ""
