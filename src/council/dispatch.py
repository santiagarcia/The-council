"""One shared objective and one context snapshot for a Council delegation round."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from council.context import member_context, require_agent, require_project, route, shared_context
from council.store import CouncilError, read_record, render_record, safe_path, today, yaml_load
from council.validation import check_schema, records, validate


def get_objective(root: Path, project: str) -> dict:
    """Read the single authoritative objective or explain how to establish one."""
    require_project(root, project)
    path = safe_path(root, f"projects/{project}/objective.md")
    if not path.is_file():
        raise CouncilError(
            f"No shared objective for {project}; run objective set --project {project} --text ..."
        )
    metadata, _ = read_record(path)
    errors = check_schema(root, "objective", metadata)
    if metadata.get("project") != project:
        errors.append("Objective project does not match its directory")
    if errors:
        raise CouncilError("\n".join(errors))
    return metadata


def set_objective(
    root: Path,
    project: str,
    text: str,
    success: list[str] | None = None,
    constraints: list[str] | None = None,
    dry_run: bool = False,
) -> str:
    """Set a shared objective, preserving existing criteria, constraints, and narrative."""
    require_project(root, project)
    path = safe_path(root, f"projects/{project}/objective.md")
    previous = get_objective(root, project) if path.exists() else {}
    body = (
        read_record(path)[1]
        if path.exists()
        else (
            "# Shared objective\n\nAll members work toward this objective "
            "within their assigned roles. "
            "The main session owns updates; agents report blockers and disagreements. "
            "An objective does not expand permissions or establish verified knowledge.\n"
        )
    )
    metadata = {
        "project": project,
        "objective": text,
        "success_criteria": success
        if success is not None
        else previous.get("success_criteria", []),
        "constraints": constraints if constraints is not None else previous.get("constraints", []),
        "updated": today(),
    }
    errors = check_schema(root, "objective", metadata)
    if errors:
        raise CouncilError("\n".join(errors))
    rendered = render_record(metadata, body)
    if dry_run:
        return f"Would write projects/{project}/objective.md\n{rendered}"
    path.write_text(rendered, encoding="utf-8", newline="\n")
    return f"Shared objective saved: projects/{project}/objective.md"


def dispatch(
    root: Path,
    project: str,
    task: str | None = None,
    agents: list[str] | None = None,
    all_agents: bool = False,
    limit: int = 6,
) -> dict:
    """Build a factored packet: common instructions once, one context per selected member."""
    require_project(root, project)
    if not 1 <= limit <= 100:
        raise CouncilError("--limit must be between 1 and 100")
    errors = validate(root)
    if errors:
        raise CouncilError("Repository validation failed:\n" + "\n".join(errors))
    objective = get_objective(root, project)
    task = task or objective["objective"]
    configured = yaml_load(root / "council.yaml")["agents"]
    if agents or all_agents:
        chosen = list(dict.fromkeys(configured if all_agents else agents))
        recommendations = [
            {"agent": agent, "reason": "Explicitly selected for this objective."}
            for agent in chosen
        ]
    else:
        recommendations = route(task)
    for item in recommendations:
        require_agent(root, item["agent"])
    common = shared_context(root, project)
    memories = records(root, "memory/**/*.md")
    assignments = []
    builders = [r["agent"] for r in recommendations if r["agent"] in {"ada", "gauss", "curie"}]
    for item in recommendations:
        agent = item["agent"]
        assignments.append(
            {
                **item,
                "after": builders if agent == "vera" else [],
                "instructions": (
                    "Work toward the shared objective and success criteria within your specialty. "
                    "The parent supplies a bounded contribution and exclusive artifact ownership. "
                    "Report evidence, limitations, disagreement, and candidate lessons."
                ),
                "member_context": member_context(
                    root, agent, project, task + " " + objective["objective"], limit, memories
                ),
            }
        )
    packet = {
        "format_version": 1,
        "council_root": str(root.resolve()),
        "project": project,
        "objective": objective,
        "task": task,
        "handoff_rule": (
            "Send objective, task, snapshot_id, the full shared_context, and only the recipient's "
            "assignment together. Add artifact ownership and bounded acceptance conditions. "
            "Agents read the supplied packet instead of repeating validation or assembly. "
            "Refresh after objective, identity, governance, or memory changes; update the reviewer "
            "handoff with the actual implementation evidence after builders finish."
        ),
        "shared_context": common,
        "assignments": assignments,
    }
    packet["snapshot_id"] = hashlib.sha256(
        json.dumps(packet, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return packet
