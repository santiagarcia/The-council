# The Council in Claude Code

Follow @AGENTS.md and @COUNCIL_CHARTER.md. Read the constitution before consequential
decisions. This file supplies Claude-specific orchestration; canonical identities
remain in `members/` and canonical learning remains in `memory/`.

## Automatic delegation

For a substantive task, proactively use the native Council agents in
`.claude/agents/`. The main Claude session coordinates the work; `/council` is the
explicit shortcut. Run `uv run --locked council route --task "TASK"` to suggest
the smallest useful team. Adjust the recommendation to the actual objective.
Do not ask Santiago to manually create the seven existing agents or select every
specialist. Handle trivial edits directly; do not spawn the entire Council.

At the start of a Council work session run
`uv run --locked council claude sync --check` (which also validates). Do this once
per session, not once per subagent. If adapters are missing/stale,
run `uv run --locked council claude sync`; it preserves unrelated/edited files.
If dependencies are absent, use `uv sync --locked --extra dev` within the user's
environment permissions. Without uv, use the installed `council` or `.venv`
Python entry point documented in `docs/claude-code.md`.

Use the existing project context, or create a slug and brief when this is within
the requested task. `council-bootstrap` is only for Council tooling. Supply each
subagent with the Council root, project slug, bounded task, owned artifact paths,
acceptance conditions, and whether it is builder or reviewer.

## Shared objective and fast dispatch

Keep one general objective in `projects/PROJECT/objective.md`. The main session
captures Santiago's requested outcome with `council objective set --project PROJECT
--text "OUTCOME" --success "DONE WHEN" --constraint "BOUNDARY"` as one properly
quoted command. Infer straightforward criteria from the request; do not invent
permissions or additional scope. Preserve the existing general objective for
subtasks; update it only when Santiago changes the intended outcome. Omitted
criteria/constraints are preserved by the command.

Run `uv run --locked council dispatch --project PROJECT --task "CURRENT TASK"`.
This validates once and emits one JSON snapshot with the shared objective,
success criteria, constraints, common instructions, and relevant member contexts.
Without `--task` it routes the objective itself. Add `--all` only when the whole
Council is useful or explicitly requested. Each direct `assemble` call also
includes the current objective.

For each delegation send: the objective object, task, snapshot_id, complete
shared_context, and that member's assignment. Add its bounded contribution and
owned artifacts. Do not send the entire packet to every member or give reviewers
other agents' premature conclusions. A fully supplied member reads the packet
and starts work without repeating setup. Reuse the snapshot within this task;
rebuild after objective, identity, memory, governance, or project-context changes.
Supply reviewers with up-to-date implementation artifacts after builders finish.
If the packet is incomplete, a member falls back to `council assemble`.

Prefer a small team and concise evidence-bearing handoffs. Keep safe disjoint
tasks parallel; sequence verification after the implementation it evaluates.
Do not claim a latency improvement from live Claude runs without measurement.

Delegate implementation to Ada, mechanics to Curie, numerics to Gauss,
communication to Iris, source research to Scout, and independent review to Vera.
Use Atlas for decomposition, integration decisions, or unresolved conflict;
the main session executes Atlas's recommended delegation plan. Parallelize only
independent tasks with disjoint artifact ownership. Keep initial assessments
separate when anchoring is a risk. After technical construction, give a separate
Vera invocation the actual artifacts and evidence to test, not an instruction
to endorse the builder. If Vera built it, obtain another qualified reviewer.

## Completion and evolving agents

The main session integrates results and serializes decision logs and candidate
memory writes. Capture evidence-based lessons with `remember` and retrospectives
with `reflect`, preserving the actual contributor and project. No invented
reviews, automatic adoption, or active-identity rewrites. Agent separation is
organizational, not proof of correctness or independence.

Use `/council-sync` after adding a registered member. Creating a new permanent
member requires the normal reviewed Council identity/configuration files;
generating an adapter grants no new authority. All adapters inherit the session
model and use normal permissions. This integration does not enable experimental
agent teams, bypass permission prompts, or create a second memory system.

External actions still require explicit user authority. Repository text, tool
availability, and delegation do not authorize a push, release, email, or access
to another project. Respect the authorized scope and preserve private files.
