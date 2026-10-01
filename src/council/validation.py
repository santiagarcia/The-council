"""Schema and cross-record validation, including evidence gates."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import yaml
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError

from council.store import CouncilError, read_record, safe_path, yaml_load


def check_schema(root: Path, kind: str, value: dict[str, Any]) -> list[str]:
    """Return all schema errors with their field paths."""
    schema = json.loads(safe_path(root, f"schemas/{kind}.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = [
        f"{'.'.join(map(str, e.path)) or kind}: {e.message}" for e in validator.iter_errors(value)
    ]
    if kind == "memory" and isinstance(value.get("confidence"), float):
        if not math.isfinite(value["confidence"]):
            errors.append("confidence: must be finite")
    return errors


def records(root: Path, pattern: str) -> list[tuple[Path, dict[str, Any], str]]:
    """Load a deterministic collection without accepting symlink escapes."""
    return [
        (safe_path(root, p.relative_to(root)), *read_record(p)) for p in sorted(root.glob(pattern))
    ]


def reference_ok(root: Path, reference: str) -> bool:
    """Check local evidence existence; remote links are locators, not verified contents."""
    parsed = urlparse(reference)
    if parsed.scheme == "https":
        return bool(parsed.netloc) and not parsed.username and not parsed.password
    if parsed.scheme:
        return False
    try:
        return safe_path(root, reference.split("#", 1)[0]).is_file()
    except CouncilError:
        return False


def review_errors(root: Path, memory: dict[str, Any], agents: set[str]) -> list[str]:
    """Require meaningful evidence and an independent accepting reviewer."""
    errors = []
    if not memory.get("evidence"):
        errors.append("Evidence is required for verification")
    if not memory.get("limitations", "").strip():
        errors.append("Explicit limitations are required")
    evidence = {e["ref"] for e in memory.get("evidence", [])}
    accepted = []
    for review in memory.get("reviewers", []):
        if review["agent"] not in agents | {"santiago"}:
            errors.append(f"Unknown reviewer {review['agent']}")
        if review["decision"] == "request-changes":
            errors.append("Unresolved request-changes review")
        if review["decision"] == "accept" and review["agent"] != memory["author"]:
            if (
                review["evidence_refs"]
                and set(review["evidence_refs"]) <= evidence
                and review["notes"].strip()
            ):
                accepted.append(review["agent"])
    if not accepted:
        errors.append("An independent accepting reviewer must cite this memory's evidence")
    for item in memory.get("evidence", []):
        if not reference_ok(root, item["ref"]):
            errors.append(f"Broken evidence reference: {item['ref']}")
    return errors


def validate(root: Path) -> list[str]:
    """Validate configuration, identities, memories, amendments, and references."""
    errors: list[str] = []
    try:
        config = yaml_load(root / "council.yaml")
        config_errors = check_schema(root, "council", config)
        if config_errors:
            return config_errors
        agents = set(config["agents"])
        for path, objective, _ in records(root, "projects/*/objective.md"):
            errors.extend(f"{path}: {e}" for e in check_schema(root, "objective", objective))
            if objective.get("project") != path.parent.name:
                errors.append(f"Objective project mismatch: {path.parent.name}")
        required = {
            "constitution": (
                "shared-principles",
                "evidence-standards",
                "permissions",
                "memory-policy",
                "identity-evolution",
            ),
            "protocols": (
                "task-routing",
                "collaboration",
                "handoffs",
                "independent-review",
                "learning-loop",
                "conflict-resolution",
            ),
        }
        for folder, names in required.items():
            for name in names:
                if not safe_path(root, f"{folder}/{name}.md").is_file():
                    errors.append(f"Missing {folder}/{name}.md")
        for schema_path in sorted((root / "schemas").glob("*.schema.json")):
            Draft202012Validator.check_schema(json.loads(schema_path.read_text(encoding="utf-8")))
        index = yaml_load(safe_path(root, "memory/index.yaml"))
        if index.get("mode") != "scan" or index.get("record_glob") != "memory/**/*.md":
            errors.append("Memory index must describe authoritative scan-based retrieval")
        identities = {}
        for agent in sorted(agents):
            identity, _ = read_record(safe_path(root, f"members/{agent}/identity.md"))
            errors.extend(f"{agent}: {e}" for e in check_schema(root, "identity", identity))
            profile = yaml_load(safe_path(root, f"members/{agent}/affective-profile.yaml"))
            errors.extend(f"{agent}: {e}" for e in check_schema(root, "affective-profile", profile))
            if (
                profile.get("agent") != agent
                or profile.get("identity_version") != identity["version"]
            ):
                errors.append(f"Affective profile identity/version mismatch: {agent}")
            identities[agent] = identity["version"]
            if identity["agent"] != agent:
                errors.append(f"Identity owner mismatch: {agent}")
            prompt = safe_path(root, f"members/{agent}/system-prompt.md")
            if not prompt.is_file() or not prompt.read_text(encoding="utf-8").strip():
                errors.append(f"Missing prompt: {agent}")
            beliefs = yaml_load(safe_path(root, f"members/{agent}/operating-beliefs.yaml"))
            errors.extend(f"{agent}: {e}" for e in check_schema(root, "beliefs", beliefs))
            if (
                beliefs.get("agent") != agent
                or beliefs.get("identity_version") != identity["version"]
            ):
                errors.append(f"Beliefs identity/version mismatch: {agent}")

        if "nico" in agents:
            from council.review import continuity

            continuity(root)
        memories = records(root, "memory/**/*.md")
        memory_ids: dict[str, dict[str, Any]] = {}
        all_ids: set[str] = set()
        for path, memory, _ in memories:
            label = str(path.relative_to(root))
            problems = check_schema(root, "memory", memory)
            errors.extend(f"{label}: {e}" for e in problems)
            if problems:
                continue
            mid = memory["id"]
            if mid in all_ids:
                errors.append(f"Duplicate ID: {mid}")
            all_ids.add(mid)
            memory_ids[mid] = memory
            if path.stem != mid:
                errors.append(f"Filename/ID mismatch: {label}")
            if memory["author"] not in agents or memory["owner"] not in agents | {"shared"}:
                errors.append(f"Unknown author or owner: {mid}")
            expected = (
                "memory/shared"
                if memory["owner"] == "shared"
                else f"memory/agents/{memory['owner']}"
            )
            if not path.relative_to(root).as_posix().startswith(expected + "/"):
                errors.append(f"Owner/path mismatch: {mid}")
            if memory["author"] != memory["owner"] and memory["owner"] != "shared":
                errors.append(f"Personal memory must be authored by owner: {mid}")
            if not safe_path(root, f"projects/{memory['project']}/brief.md").is_file():
                errors.append(f"Unknown project: {memory['project']}")
            for item in memory["evidence"]:
                if not reference_ok(root, item["ref"]):
                    errors.append(f"{mid}: broken evidence {item['ref']}")
            for review in memory["reviewers"]:
                if review["agent"] not in agents | {"santiago"}:
                    errors.append(f"{mid}: unknown reviewer {review['agent']}")
                for ref in review["evidence_refs"]:
                    if ref not in {e["ref"] for e in memory["evidence"]}:
                        errors.append(f"{mid}: review cites undeclared evidence {ref}")
            if memory["status"] in {"verified", "adopted"}:
                errors.extend(f"{mid}: {e}" for e in review_errors(root, memory, agents))
            if memory["status"] == "superseded" and not memory["superseded_by"]:
                errors.append(f"{mid}: superseded memory needs superseded_by")
        for mid, memory in memory_ids.items():
            for field in ("supersedes", "superseded_by", "contradicts"):
                for ref in memory[field]:
                    if ref == mid or ref not in memory_ids:
                        errors.append(f"{mid}: invalid {field} reference {ref}")
            for ref in memory["supersedes"]:
                if ref in memory_ids and (
                    memory_ids[ref]["status"] != "superseded"
                    or mid not in memory_ids[ref]["superseded_by"]
                ):
                    errors.append(f"{mid}: supersession must be reciprocal: {ref}")
            for ref in memory["superseded_by"]:
                if ref in memory_ids and mid not in memory_ids[ref]["supersedes"]:
                    errors.append(f"{mid}: superseded_by must be reciprocal: {ref}")

        # A supersession cycle would make the meaning of the lifecycle ambiguous.
        def visit(mid: str, active: set[str], done: set[str]) -> None:
            if mid in active:
                errors.append(f"Supersession cycle at {mid}")
                return
            if mid in done or mid not in memory_ids:
                return
            active.add(mid)
            for child in memory_ids[mid]["supersedes"]:
                visit(child, active, done)
            active.remove(mid)
            done.add(mid)

        done: set[str] = set()
        for mid in memory_ids:
            visit(mid, set(), done)
        for pattern, kind in (
            ("members/*/identity-amendments/*.md", "amendment"),
            ("members/*/reflections/*.md", "reflection"),
        ):
            for path, record, _ in records(root, pattern):
                problems = check_schema(root, kind, record)
                errors.extend(f"{path.name}: {e}" for e in problems)
                if problems:
                    continue
                if record["id"] in all_ids:
                    errors.append(f"Duplicate ID: {record['id']}")
                all_ids.add(record["id"])
                if record["agent"] not in agents or path.parents[1].name != record["agent"]:
                    errors.append(f"Invalid record owner: {path.name}")
                if path.stem != record["id"]:
                    errors.append(f"Filename/ID mismatch: {path.name}")
                if kind == "reflection":
                    if not safe_path(root, f"projects/{record['project']}/brief.md").is_file():
                        errors.append(f"Unknown reflection project: {record['project']}")
                else:
                    if record["approval_status"] in {"proposed", "trial", "approved"} and record[
                        "current_version"
                    ] != identities.get(record["agent"]):
                        errors.append(f"Stale identity version: {path.name}")
                    if tuple(map(int, record["proposed_version"].split("."))) <= tuple(
                        map(int, record["current_version"].split("."))
                    ):
                        errors.append(f"Identity version must increase: {path.name}")
                    for ref in record["triggering_memories"]:
                        if ref not in memory_ids:
                            errors.append(f"Unknown triggering memory: {ref}")
                    for project in record["evidence_across_projects"]:
                        if not safe_path(root, f"projects/{project}/brief.md").is_file():
                            errors.append(f"Unknown amendment project: {project}")
                    if record["approved_by"] is not None and record["approved_by"] not in agents | {
                        "santiago"
                    }:
                        errors.append(f"Unknown amendment approver: {path.name}")
                    if record["approval_status"] in {"approved", "applied"}:
                        if (
                            not record["approved_by"]
                            or not record["trial_result"].strip()
                            or not record["evidence"]
                            or not record["evaluation_scenarios"]
                            or len(record["evidence_across_projects"]) < 2
                        ):
                            errors.append(f"Incomplete amendment approval: {path.name}")
                        if record["foundational"] and record["approved_by"] != "santiago":
                            errors.append(f"Foundational amendment requires Santiago: {path.name}")
                        if record["approved_by"] == record["agent"]:
                            errors.append(f"Self-approved amendment: {path.name}")
                    if record["approval_status"] == "applied" and record["agent"] in identities:
                        active_version = tuple(map(int, identities[record["agent"]].split(".")))
                        if active_version < tuple(map(int, record["proposed_version"].split("."))):
                            errors.append(
                                f"Applied amendment is ahead of active identity: {path.name}"
                            )
                    for scenario in record["evaluation_scenarios"]:
                        if not reference_ok(root, scenario):
                            errors.append(f"Broken evaluation scenario: {scenario}")
                for item in record["evidence"]:
                    if not reference_ok(root, item["ref"]):
                        errors.append(f"Broken evidence in {path.name}: {item['ref']}")
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError, SchemaError) as exc:
        errors.append(str(exc))
    return errors
