"""Command line entry points for the Council's explicit learning loop."""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path

import yaml

from council.context import assemble, require_agent, require_project, route
from council.store import (
    CouncilError,
    commit_files,
    commit_preflight,
    read_record,
    render_record,
    root_at,
    safe_path,
    slug,
    today,
    write_new,
    yaml_load,
)
from council.validation import check_schema, records, review_errors, validate


def record_id(prefix: str, agent: str) -> str:
    """Make collision-resistant IDs without global counters."""
    return f"{prefix}-{agent}-{today()}-{uuid.uuid4().hex[:10]}"


def mutation_flags(parser: argparse.ArgumentParser, commit: bool = False) -> None:
    """Add consistent preview and controlled-commit options."""
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned content without writing"
    )
    if commit:
        parser.add_argument(
            "--commit", action="store_true", help="Commit only this command's new file; never push"
        )


def parser() -> argparse.ArgumentParser:
    """Build the CLI with self-contained subcommand help."""
    cli = argparse.ArgumentParser(
        description="The Council: versioned research context and evidence"
    )
    cli.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Council repository or a directory inside it"
    )
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "validate", help="Check schemas, references, reviews, and identity versions"
    )
    commands.add_parser("list-agents", help="List current member roles and identity versions")
    routing = commands.add_parser(
        "route", help="Recommend a minimal useful team without spawning agents"
    )
    routing.add_argument("--task", required=True)
    context = commands.add_parser("assemble", help="Print a reusable task context bundle")
    context.add_argument("--agent", required=True)
    context.add_argument("--project", required=True)
    context.add_argument("--task", required=True)
    context.add_argument("--limit", type=int, default=12)
    context.add_argument(
        "--output", help="New repository-relative output file; existing files are preserved"
    )
    mutation_flags(context)
    project = commands.add_parser("init-project", help="Create a project from the tracked template")
    project.add_argument("--project", required=True)
    mutation_flags(project)
    memory = commands.add_parser(
        "remember", help="Capture a proposed memory; no truth is established"
    )
    memory.add_argument("--agent", required=True)
    memory.add_argument("--project", required=True)
    memory.add_argument(
        "--type", choices=["episodic", "semantic", "procedural", "self_model"], required=True
    )
    memory.add_argument("--shared", action="store_true")
    memory.add_argument("--scope", choices=["project", "general"], default="project")
    memory.add_argument(
        "--observation", default="Draft: record the observation before requesting review."
    )
    memory.add_argument(
        "--evidence",
        action="append",
        default=[],
        help="Existing repository file or HTTPS locator; repeatable",
    )
    memory.add_argument(
        "--limitations",
        default="Unreviewed draft; applicability and evidence remain to be established.",
    )
    memory.add_argument("--tag", action="append", default=[])
    memory.add_argument("--confidence", type=float, default=0.0)
    mutation_flags(memory, commit=True)
    reflection = commands.add_parser(
        "reflect", help="Create a retrospective with explicit evidence gaps"
    )
    reflection.add_argument("--agent", required=True)
    reflection.add_argument("--project", required=True)
    mutation_flags(reflection, commit=True)
    amendment = commands.add_parser(
        "propose-identity-change", help="Propose an amendment without changing active identity"
    )
    amendment.add_argument("--agent", required=True)
    amendment.add_argument(
        "--previous", default="Describe the current belief or trait with an identity citation."
    )
    amendment.add_argument(
        "--proposed", default="Describe a testable refinement; no active identity change is made."
    )
    amendment.add_argument(
        "--foundational", action="store_true", help="Require explicit Santiago review"
    )
    mutation_flags(amendment, commit=True)
    promotion = commands.add_parser(
        "promote-memory", help="Review-gated proposed -> verified -> adopted transition"
    )
    promotion.add_argument("--id", required=True)
    promotion.add_argument("--to", choices=["verified", "adopted"], default="verified")
    mutation_flags(promotion)
    style = commands.add_parser("style", help="Learn observable presentation conventions")
    styles = style.add_subparsers(dest="style_command", required=True)
    ingest = styles.add_parser(
        "ingest", help="Read PPTX files without modifying them; emit aggregate statistics"
    )
    ingest.add_argument("source", type=Path)
    mutation_flags(ingest)
    claude = commands.add_parser("claude", help="Maintain Claude Code native Council agents")
    claude_commands = claude.add_subparsers(dest="claude_command", required=True)
    sync = claude_commands.add_parser("sync", help="Generate native agents from council.yaml")
    mode = sync.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Fail if generated agents are stale")
    mode.add_argument("--dry-run", action="store_true", help="Preview without writing")
    objective = commands.add_parser("objective", help="Maintain one shared project objective")
    objectives = objective.add_subparsers(dest="objective_command", required=True)
    show = objectives.add_parser("show", help="Read the objective, criteria, and constraints")
    show.add_argument("--project", required=True)
    set_goal = objectives.add_parser("set", help="Set the objective for every Council member")
    set_goal.add_argument("--project", required=True)
    set_goal.add_argument("--text", required=True)
    set_goal.add_argument("--success", action="append", help="Success criterion; repeatable")
    set_goal.add_argument("--constraint", action="append", help="Constraint; repeatable")
    mutation_flags(set_goal)
    dispatch = commands.add_parser("dispatch", help="Prepare one fast shared delegation packet")
    dispatch.add_argument("--project", required=True)
    dispatch.add_argument("--task", help="Current subtask; defaults to the shared objective")
    selection = dispatch.add_mutually_exclusive_group()
    selection.add_argument("--agent", action="append", help="Select specific members; repeatable")
    selection.add_argument(
        "--all", action="store_true", help="Include the entire registered Council"
    )
    dispatch.add_argument(
        "--limit", type=int, default=6, help="Maximum relevant memories per member"
    )
    dispatch.add_argument("--output", help="New repository-relative JSON output file")
    return cli


def create_record(
    root: Path, path: Path, metadata: dict, body: str, args: argparse.Namespace, kind: str
) -> None:
    """Validate and preview or persist one new record, optionally committing it."""
    problems = check_schema(root, kind, metadata)
    if problems:
        raise CouncilError("\n".join(problems))
    text = render_record(metadata, body)
    if args.dry_run:
        print(f"Would create {path.relative_to(root)}\n{text}")
        return
    if args.commit:
        commit_preflight(root)
    write_new(path, text)
    print(path.relative_to(root).as_posix())
    if args.commit:
        label = {"amendment": "identity", "memory": "memory", "reflection": "reflection"}[kind]
        summary = {
            "memory": "add " + metadata.get("observation", "candidate lesson"),
            "reflection": "review " + metadata.get("project", "project") + " cycle",
            "amendment": "propose " + metadata.get("proposed_trait", "identity refinement"),
        }[kind]
        summary = " ".join(summary.split())[:90]
        print(commit_files(root, [path], args.agent, f"{label}({args.agent}): {summary}"))


def run(args: argparse.Namespace) -> int:
    """Dispatch commands; return a process exit code."""
    root = root_at(args.root)
    if args.command == "objective":
        from council.dispatch import get_objective, set_objective

        if args.objective_command == "show":
            print(json.dumps(get_objective(root, args.project), indent=2))
        else:
            print(
                set_objective(
                    root, args.project, args.text, args.success, args.constraint, args.dry_run
                )
            )
        return 0
    if args.command == "dispatch":
        from council.dispatch import dispatch

        packet = dispatch(root, args.project, args.task, args.agent, args.all, args.limit)
        text = json.dumps(packet, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            path = safe_path(root, args.output)
            write_new(path, text)
            print(path.relative_to(root).as_posix())
        else:
            print(text)
        return 0
    if args.command == "claude":
        from council.claude import sync

        code, message = sync(root, check=args.check, dry_run=args.dry_run)
        print(message)
        return code
    if args.command == "validate":
        errors = validate(root)
        print("\n".join(errors) if errors else "Council validation passed")
        return int(bool(errors))
    if args.command == "list-agents":
        for agent in yaml_load(root / "council.yaml")["agents"]:
            identity, _ = read_record(root / f"members/{agent}/identity.md")
            print(f"{agent:8} {identity['version']:5} {identity['role']}")
    elif args.command == "route":
        print(json.dumps(route(args.task), indent=2))
    elif args.command == "assemble":
        if not 1 <= args.limit <= 100:
            raise CouncilError("--limit must be between 1 and 100")
        bundle = assemble(root, args.agent, args.project, args.task, args.limit)
        if args.output and not args.dry_run:
            path = safe_path(root, args.output)
            write_new(path, bundle)
            print(path.relative_to(root))
        else:
            print(bundle)
    elif args.command == "init-project":
        name = slug(args.project)
        destination = safe_path(root, f"projects/{name}")
        if destination.exists():
            raise CouncilError(f"Project already exists: {name}")
        for source in sorted((root / "projects/_template").glob("*.md")):
            content = source.read_text(encoding="utf-8").replace("PROJECT", name)
            if args.dry_run:
                print(f"Would create projects/{name}/{source.name}\n{content}")
            else:
                write_new(destination / source.name, content)
        print(f"Project: {name}")
    elif args.command in {"remember", "reflect", "propose-identity-change"}:
        require_agent(root, args.agent)
        if args.command != "propose-identity-change":
            require_project(root, args.project)
        if args.command == "remember":
            from council.validation import reference_ok

            for ref in args.evidence:
                if not reference_ok(root, ref):
                    raise CouncilError(f"Invalid evidence locator: {ref}")
            mid = record_id("mem", args.agent)
            owner = "shared" if args.shared else args.agent
            metadata = dict(
                id=mid,
                owner=owner,
                author=args.agent,
                memory_type=args.type,
                project=args.project,
                scope=args.scope,
                status="proposed",
                created=today(),
                tags=args.tag,
                confidence=args.confidence,
                observation=args.observation,
                evidence=[
                    {"ref": ref, "detail": "Locator supplied by author; content needs review."}
                    for ref in args.evidence
                ],
                limitations=args.limitations,
                reviewers=[],
                supersedes=[],
                superseded_by=[],
                contradicts=[],
            )
            folder = "memory/shared/proposed" if args.shared else f"memory/agents/{args.agent}"
            create_record(
                root,
                safe_path(root, f"{folder}/{mid}.md"),
                metadata,
                "# Proposed memory\n\nDescribe reproduction, alternatives, "
                "and the boundary of this lesson.\n",
                args,
                "memory",
            )
        elif args.command == "reflect":
            rid = record_id("reflection", args.agent)
            metadata = dict(
                id=rid,
                agent=args.agent,
                project=args.project,
                created=today(),
                evidence=[],
                status="draft",
            )
            body = (
                "# Retrospective\n\n## Expected outcome\nWhat was predicted, and why?\n\n"
                "## Observed outcome and evidence\n"
                "Link artifacts, commands, revisions, and failed attempts.\n\n"
                "## Surprise and alternatives\nSeparate observation from causal interpretation.\n\n"
                "## Self-model\nWhich habit helped or harmed? "
                "What counterexample would change this assessment?\n\n"
                "## Proposed learning\nList candidate memories, their scope, "
                "limitations, and independent reviewers.\n\n"
                "## Next trial\nState a measurable change and a rollback condition. "
                "No lesson is adopted by this draft.\n"
            )
            create_record(
                root,
                safe_path(root, f"members/{args.agent}/reflections/{rid}.md"),
                metadata,
                body,
                args,
                "reflection",
            )
        else:
            identity, _ = read_record(root / f"members/{args.agent}/identity.md")
            major, minor = map(int, identity["version"].split("."))
            aid = record_id("amendment", args.agent)
            metadata = dict(
                id=aid,
                agent=args.agent,
                created=today(),
                current_version=identity["version"],
                proposed_version=f"{major}.{minor + 1}",
                previous_trait=args.previous,
                proposed_trait=args.proposed,
                triggering_memories=[],
                evidence=[],
                evidence_across_projects=[],
                expected_behavior="Define observable behavior and success criteria before trial.",
                negative_consequences="Assess tradeoffs and failure modes before trial.",
                evaluation_scenarios=[],
                trial_result="",
                approval_status="proposed",
                approved_by=None,
                foundational=args.foundational,
                rollback_plan=(
                    "Revert the reviewed identity commit; "
                    "preserve the amendment and trial evidence."
                ),
            )
            create_record(
                root,
                safe_path(root, f"members/{args.agent}/identity-amendments/{aid}.md"),
                metadata,
                "# Identity amendment proposal\n\nActive identity remains unchanged. "
                "Collect evidence across projects, run a bounded trial, "
                "and request independent review. Permission expansion always requires Santiago, "
                "regardless of the foundational flag.\n",
                args,
                "amendment",
            )
    elif args.command == "promote-memory":
        errors = validate(root)
        if errors:
            raise CouncilError("Repository validation failed:\n" + "\n".join(errors))
        matching = [(p, m, b) for p, m, b in records(root, "memory/**/*.md") if m["id"] == args.id]
        if len(matching) != 1:
            raise CouncilError("Memory ID must resolve to exactly one record")
        path, memory, body = matching[0]
        expected = "proposed" if args.to == "verified" else "verified"
        if memory["status"] != expected:
            raise CouncilError(f"Transition to {args.to} requires status {expected}")
        errors = review_errors(root, memory, set(yaml_load(root / "council.yaml")["agents"]))
        if errors:
            raise CouncilError("\n".join(errors))
        memory["status"] = args.to
        if args.dry_run:
            print(render_record(memory, body))
        else:
            path.write_text(render_record(memory, body), encoding="utf-8", newline="\n")
            print(
                f"{args.id}: {args.to}; recorded review gate passed "
                "(reviewer identity is not authenticated)"
            )
    elif args.command == "style":
        from council.style import ingest

        print(ingest(root, args.source, args.dry_run))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Return concise diagnostics for expected input and repository errors."""
    try:
        return run(parser().parse_args(argv))
    except (CouncilError, OSError, yaml.YAMLError, ValueError) as exc:
        print(f"council: {exc}", file=sys.stderr)
        return 2
