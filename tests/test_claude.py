"""Native adapter generation preserves canonical identities and local user edits."""

from pathlib import Path

import pytest

from council.claude import sync
from council.cli import main
from council.store import CouncilError, read_record, render_record, yaml_load


def test_sync_preview_and_check_do_not_write(repo):
    assert sync(repo, dry_run=True)[0] == 0
    assert sync(repo, check=True)[0] == 1
    assert not (repo / ".claude").exists()


def test_generates_native_members_and_is_idempotent(repo):
    assert sync(repo)[0] == 0
    files = sorted((repo / ".claude/agents").glob("*.md"))
    assert len(files) == 10
    for path in files:
        metadata, body = read_record(path)
        assert metadata["name"] == path.stem
        assert metadata["model"] == "inherit"
        assert metadata["permissionMode"] == "default"
        assert "description" in metadata
        assert "memory" not in metadata
        assert f"members/{path.stem}/identity.md" in body
        if path.stem == "nico":
            assert metadata["tools"] == []
            assert "review --agent nico" in body
        else:
            assert f"assemble --agent {path.stem}" in body
    assert "Write" in read_record(repo / ".claude/agents/ada.md")[0]["tools"]
    assert "Write" not in read_record(repo / ".claude/agents/vera.md")[0]["tools"]
    assert "WebSearch" in read_record(repo / ".claude/agents/scout.md")[0]["tools"]
    times = {path: path.stat().st_mtime_ns for path in files}
    assert sync(repo, check=True)[0] == 0
    assert sync(repo)[0] == 0
    assert all(path.stat().st_mtime_ns == stamp for path, stamp in times.items())


def test_identity_text_stays_canonical_and_role_updates_regenerate(repo):
    sync(repo)
    identity = repo / "members/ada/identity.md"
    meta, body = read_record(identity)
    meta["role"] = "Scientific software and reproducibility engineer"
    identity.write_text(
        render_record(meta, body + "\nUnique canonical refinement.\n"), encoding="utf-8"
    )
    assert sync(repo, check=True)[0] == 1
    assert sync(repo)[0] == 0
    adapter = (repo / ".claude/agents/ada.md").read_text(encoding="utf-8")
    assert meta["role"] in adapter
    assert "Unique canonical refinement." not in adapter
    assert "Unique canonical refinement." in identity.read_text(encoding="utf-8")


@pytest.mark.parametrize("managed", [False, True])
def test_conflict_preflight_preserves_all_files(repo, managed):
    if managed:
        sync(repo)
    path = repo / ".claude/agents/vera.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("My existing reviewer", encoding="utf-8")
    before = {p: p.read_bytes() for p in (repo / ".claude").rglob("*") if p.is_file()}
    with pytest.raises(CouncilError, match="Preserving"):
        sync(repo)
    after = {p: p.read_bytes() for p in (repo / ".claude").rglob("*") if p.is_file()}
    assert before == after


def test_unrelated_custom_agent_is_untouched(repo):
    custom = repo / ".claude/agents/personal.md"
    custom.parent.mkdir(parents=True)
    custom.write_text("Personal custom agent", encoding="utf-8")
    sync(repo)
    assert custom.read_text() == "Personal custom agent"


def test_sync_cli_and_checked_in_adapters(repo):
    assert main(["--root", str(repo), "claude", "sync", "--dry-run"]) == 0
    assert main(["--root", str(repo), "claude", "sync"]) == 0
    assert main(["--root", str(repo), "claude", "sync", "--check"]) == 0
    assert sync(Path(__file__).resolve().parents[1], check=True)[0] == 0


def test_removed_member_does_not_delete_adapter(repo):
    import yaml

    sync(repo)
    config = yaml_load(repo / "council.yaml")
    config["agents"].remove("scout")
    (repo / "council.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    with pytest.raises(CouncilError, match="removal review"):
        sync(repo)
    assert (repo / ".claude/agents/scout.md").exists()


def test_new_registered_member_generates_without_hardcoded_mapping(repo):
    import shutil

    import yaml

    folder = repo / "members/maxwell"
    shutil.copytree(repo / "members/curie", folder)
    path = folder / "identity.md"
    meta, body = read_record(path)
    meta.update(agent="maxwell", role="Electromagnetics scientist")
    path.write_text(render_record(meta, body), encoding="utf-8")
    beliefs = yaml_load(folder / "operating-beliefs.yaml")
    beliefs["agent"] = "maxwell"
    (folder / "operating-beliefs.yaml").write_text(yaml.safe_dump(beliefs), encoding="utf-8")
    profile = yaml_load(folder / "affective-profile.yaml")
    profile["agent"] = "maxwell"
    (folder / "affective-profile.yaml").write_text(yaml.safe_dump(profile), encoding="utf-8")
    config = yaml_load(repo / "council.yaml")
    config["agents"].append("maxwell")
    (repo / "council.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    sync(repo)
    metadata, text = read_record(repo / ".claude/agents/maxwell.md")
    assert "Electromagnetics scientist" in metadata["description"]
    assert metadata["tools"] == "Read, Grep, Glob, Bash"
    assert "members/maxwell/identity.md" in text
