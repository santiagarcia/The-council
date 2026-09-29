# Using The Council with Claude Code

Open this repository in Claude Code. The checked-in `.claude/agents/` files make
all seven members available as native subagents; `CLAUDE.md` asks the main session
to delegate substantive work automatically. You do not need to create each agent
by hand or configure an API key for the Council CLI. Claude Code itself still
requires its normal installation and account setup.

Try either ordinary language or the explicit shortcut:

```text
Use the Council to implement this change and independently review it.
/council umat-oti investigate why OTI and FD sensitivities disagree
/council council-bootstrap improve the CLI and have Vera review the result
Use Iris to prepare a presentation outline from the verified project findings.
```

The main session chooses specialists, provides scoped context, integrates their
outputs, and records candidate learning. The `/council` command is a prompt-driven
workflow, not a deterministic scheduler; Claude makes the actual delegation
decisions. Explicitly naming a member is available when you want direct control.
Trivial tasks need not start multiple agents.

## One objective, fast handoffs

Tell Claude the overall outcome once, for example:

```text
/council umat-oti verify the UMAT sensitivities and prepare a defensible presentation.
Success means an FD-step sweep and analytical limit check pass, followed by an independent review.
Keep unpublished source code in its project repository.
```

Claude captures that objective in `projects/umat-oti/objective.md`, then prepares
the team packet in one CLI call. Later subtasks preserve the general objective.
Every selected member receives the same outcome, criteria, and constraints
alongside its own identity, relevant memories, and bounded assignment. You can
inspect or set this explicitly:

```bash
council objective set --project umat-oti --text "Verify UMAT sensitivities" --success "Independent derivative checks pass" --constraint "Keep source in its own repository"
council objective show --project umat-oti
council dispatch --project umat-oti
council dispatch --project umat-oti --task "check OTI versus FD disagreement"
council dispatch --project umat-oti --all
```

Create the project with `init-project` first if it does not exist. Repeat
`--success` and `--constraint` for multiple entries. On updates, omitted criteria
and constraints stay in place; explicitly supplied lists replace those lists.
The narrative beneath the objective's metadata is preserved. Use `--dry-run`
before setting it when a preview is useful. The objective is a versionable file,
not a background process or an authority to expand permissions.

Dispatch validates once, loads common instructions once, and selects memories
from one shared in-process collection. It emits shared context once plus separate
member contexts. The main session passes the shared portion and only the
recipient's assignment to each agent, so unrelated specialist instructions do
not inflate every handoff. The default maximum is six relevant memories per
member (`--limit` adjusts it). Default routing uses the smallest useful team;
`--all` includes every registered member, and repeatable `--agent` selects a team.

The snapshot hash identifies the exact prepared context; it is not a signature
or proof of freshness. Do not rerun setup in each subagent when a complete packet
was supplied. Regenerate after changing objective, governance, identities,
memories, or project context. After implementation, give the reviewer current
artifacts and evidence; the packet's `after` dependencies identify selected
technical builders that precede Vera. The parent still decides artifact ownership
and dependencies appropriate to the task. Packets can be saved with `--output
.council/round-one.json`; existing files are never overwritten.

This reduces redundant local preparation. Actual model latency and usage depend
on Claude, task size, and selected team; no live Claude speedup is claimed.

Local measurement on 2026-09-29 (Windows, Python 3.11.16, three in-process rounds,
seven members, `council-bootstrap`, task `implement Claude integration`, limit 6):
median separate assembly took 358.6 ms versus 59.3 ms for one dispatch. The seven
assembled bundles contained 154,858 characters combined; serialized dispatch
contained 59,120 characters. This measures preparation and parent-packet size,
not end-to-end model latency or total token usage across subagents. Reproduce by
timing seven `council.context.assemble` calls versus one
`council.dispatch.dispatch(..., all_agents=True)` with `time.perf_counter`.

## Setup and automatic agent generation

From the repository root:

```bash
uv sync --locked --extra dev
uv run --locked council validate
uv run --locked council claude sync --check
```

The definitions are already generated and tracked. After registering a future
member or changing a role, run `/council-sync` in Claude, or:

```bash
uv run --locked council claude sync --dry-run
uv run --locked council claude sync
```

Synchronization reads `council.yaml` and each registered identity. It writes only
managed `.claude/agents/<member>.md` adapters and their checksum manifest. It does
not duplicate identities or memory: each agent retrieves its current canonical
identity, prompt, beliefs, project, protocols, and reviewed memories at task time
using `council assemble`. Approved identity refinements are therefore available
without manually editing a second prompt. CI checks generated adapters for drift.

Sync is idempotent, supports check-only and dry-run modes, and refuses to overwrite
an edited or unrelated adapter. It preflights all destinations before writing.
For an intentional adapter customization, update `src/council/claude.py` and
regenerate; preserve any local edits before resolving a conflict. Removing a
registered member requires explicit review of its adapter and manifest entry;
sync does not silently delete files. Additional unrelated custom Claude agents
are left alone.

For a new permanent member, prepare its substantive identity, system prompt and
beliefs following the existing schema and governance, register it in
`council.yaml`, validate, and sync. Claude can do this within an authorized task;
sync alone does not invent new identities or permissions. Unknown future roles
receive the conservative Read/Grep/Glob/Bash tool set until deliberately updated.

## Runtime and permissions

All adapters use `model: inherit` and `permissionMode: default`. Ada and Iris have
file-editing tools; Scout has web research tools; other members have repository
reading and Bash for context assembly and tests. Bash is not a read-only sandbox:
artifact ownership and ordinary tool permissions still apply. The main session
owns orchestration and serializes shared logs and memory capture; these adapters
do not depend on nested agents or experimental agent teams.

Vera receives a separate review assignment and must actually reproduce or
challenge evidence. Different agent names or contexts do not prove independence
or authorize self-certification. No auto-adoption, parallel personal-memory
system, permission bypass, automatic push, or collaborator messaging is enabled.

Use the actual research project slug in assignments. `council-bootstrap` is for
Council tooling only. Work in another repository requires explicit scope and the
Council root path; opening The Council does not grant blanket access to external
projects. This integration is project-local, not a global Claude installation.

If uv is unavailable, activate the installed environment and use `council`.
Without activation, use `.venv/Scripts/python.exe -m council` on Windows or
`.venv/bin/python -m council` on POSIX systems. In PowerShell, quote a path with
spaces and invoke it using `&`. Do not assume PowerShell backslashes work inside
Claude's Bash tool. If tools cannot run, agents must disclose the fallback and
read canonical files directly rather than pretending memory retrieval succeeded.

If the new agents/commands are missing in an already-open session, restart Claude
Code in this repository and retry. User-level configuration or organizational
policy can affect availability. Native runtime behavior needs a Claude Code
session; the repository tests validate generation, preservation, and the checked-in
configuration, not a live model's delegation choices.

## Format references

Checked against official documentation on 2026-09-29:

- [Claude Code subagents](https://code.claude.com/docs/en/sub-agents): native agent
  location, descriptions, tool configuration, inherited models and permissions.
- [Claude Code commands and skills](https://code.claude.com/docs/en/slash-commands):
  `.claude/commands/` remains supported and exposes `/council` and `/council-sync`.
- [Claude Code project memory](https://code.claude.com/docs/en/memory): project
  instructions through `CLAUDE.md` and referenced files.

## Verification of this integration

The full local suite passed: 66 tests, with one Windows symlink-creation skip.
Ruff lint/format checks, Council validation, and adapter synchronization checks
passed. Tests cover generation for a newly registered member, idempotence,
dry runs, preservation of edited/unrelated agents, shared-objective updates,
one validation pass per dispatch, all-member context, objective refresh, review
ordering, output preservation, and compatibility with existing memory retrieval.
Claude Code was not available on the test shell's PATH, so live model delegation
has not been exercised. Restart a Claude Code session in this repository and try
`/council council-bootstrap inspect the shared objective and assign the next task`.
