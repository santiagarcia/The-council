# The Council

A persistent team of evolving AI collaborators for Santiago's research. Git preserves identities, decisions, evidence, and lessons; the CLI brings relevant context into each new session and captures candidate learning afterward.

**Recording is not verification, and verification is not adoption.** A commit records an experience. Independent review evaluates its evidence. Adoption makes a scoped lesson available as future guidance. The system never claims that role names alone create independent reviewers or that a repository can reason on its own.

Atlas integrates, Curie checks mechanics, Gauss checks numerics and sensitivities, Ada builds scientific software, Vera independently challenges claims, Iris communicates, and Scout finds primary sources. Santiago remains Principal Investigator and final authority. Members begin at identity version 1.0 and can evolve through visible, evidence-linked amendments and trials.

## Quick start

Requires Python 3.11+; Git is needed only for commits. Run from this repository:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e '.[dev]'
council validate
council list-agents
council init-project --project umat-oti
council route --task "verify OTI residual sensitivities in a UMAT"
council assemble --agent gauss --project umat-oti --task "verify sensitivities"
council assemble --agent vera --project umat-oti --task "review derivative verification"
```

Pass `--root /path/to/The-council` **before** the subcommand when working elsewhere. From a fresh Codex session, follow [AGENTS.md](AGENTS.md): assemble context, read the resulting bundle, then work. The CLI prints Markdown, or writes a new file with `--output .council/gauss-context.md`. Existing files are preserved. `route` recommends roles; it does not call a model or spawn agents.

If Python is not on PATH, the equivalent uv setup is `uv sync --extra dev --python 3.11`, then `uv run council validate`. In the environment used for initial setup, commands are also available directly as `.venv\Scripts\council.exe` and `.venv\Scripts\python.exe`. The checked-in `uv.lock` records the initial dependency resolution; use `uv sync --locked --extra dev` to reproduce it.

## Capture and review learning

```bash
council remember --agent gauss --project umat-oti --type procedural --tag fd --tag sensitivities --observation "Describe the bounded observation" --evidence projects/umat-oti/findings.md --dry-run
council remember --agent gauss --project umat-oti --type procedural
council reflect --agent vera --project umat-oti
council propose-identity-change --agent vera --previous "Current trait" --proposed "Testable refinement"
```

Fill draft evidence, limitations, and reproduction details before requesting review. Evidence locators are existing repository files or HTTPS references, with a description of what they support. Quote dates in manually authored YAML. See [memory-authoring.md](docs/memory-authoring.md) and [examples](templates/examples/).

An independent reviewer records an accepting review citing the memory's declared evidence. Any unresolved `request-changes` review blocks promotion. Then perform the two explicit transitions:

```bash
council promote-memory --id MEMORY-ID --to verified --dry-run
council promote-memory --id MEMORY-ID --to verified
council promote-memory --id MEMORY-ID --to adopted
```

Assembly includes only relevant adopted guidance and separately labeled verified observations. It filters by owner, project scope, task words, and tags; contradictory references remain visible. A general lesson can cross projects only when explicitly scoped `general`. Proposed, deprecated, and superseded records are excluded from guidance. Record status lives in front matter; promotion preserves the original file path.

Memory, reflection, and amendment creation accept `--commit`. This refuses a nonempty staging area before writing, stages only the new record, uses command-scoped member attribution, and never pushes or changes global Git configuration. Unstaged unrelated work is left alone. Add Git to PATH, or set `COUNCIL_GIT` to its executable path. Review the staging area after any Git failure. Do not run simultaneous index-writing commands.

Identity proposals do not change active identities. Applying a reviewed amendment is a deliberate Git change to the identity, matching beliefs version, and proposal outcome. Foundational changes and permission expansion always require Santiago; see [identity evolution](constitution/identity-evolution.md).

## Presentation learning

Place selected `.pptx` decks in **`style_sources/presentations/private/`**, then run:

```bash
council style ingest style_sources/presentations/private --dry-run
council style ingest style_sources/presentations/private
```

Sources remain unchanged. The command generates `deck-inventory.json`, `presentation-style-profile.yaml`, and `style-observations.md` under `style/derived/`, and refreshes only a marked region of the style guide. Empty source folders work. Raw presentations, ZIP archives, and derived reports are ignored by default. The existing OneDrive archive is preserved; ingestion does not automatically extract it. See [source handling and intentional LFS tracking](style_sources/presentations/README.md).

Direct observations cover dimensions, themes, direct fonts and sizes, title positions, backgrounds, layouts, density, explicit bullets, pictures, tables, charts, equation XML, and structural cues. Inherited formatting and raster plot labels require manual review. Caption/logo candidates and lexical status cues are explicitly heuristic. No slide text, notes, filenames, or images are exported into reports.

## Repository map

```text
constitution/          Shared governance and evidence rules
members/<agent>/       Active identity, beliefs, prompt, reflections, amendments
memory/                Agent/shared records; index.yaml describes scan-based retrieval
projects/              Project context and reusable template
protocols/             Routing, collaboration, review, learning, conflict resolution
schemas/               JSON Schemas for structured records
templates/             Authoring forms and clearly illustrative examples
evaluations/           Eight scenarios and an evidence-based scorecard
src/council/            CLI, validation, retrieval, safe Git, presentation ingestion
tests/                 Deterministic CLI, governance, Git, and PPTX tests
style_sources/         Instructions and ignored private presentation directory
style/                 Known preferences and ignored derived reports
docs/                  Contribution, memory, and security guidance
.github/               CI and pull-request template
```

Commands: `validate`, `list-agents`, `route`, `assemble`, `init-project`, `remember`, `reflect`, `propose-identity-change`, `promote-memory`, and `style ingest`. Use `council COMMAND --help` for options. Mutating commands offer `--dry-run`.

## Development and verification

```bash
python -m pytest
ruff check src tests
ruff format --check src tests
council validate
```

CI runs these checks with read-only repository permissions on Python 3.11 and 3.12. Tests create isolated temporary repositories, generated decks, and subprocess CLI sessions outside the working repository. Evaluation scenarios are specifications for future agent trials, not claimed successful independent reviews.

## Current limits

Review identities and evidence quality require human governance: metadata is not authentication, and local users can edit files. Remote evidence links are syntax-checked, not fetched. Retrieval and routing are deterministic lexical heuristics, without embeddings or a model backend. Context size is limited by memory count, not total tokens. There is no automatic identity application, cross-owner edit workflow, or concurrent-writer coordination. Presentation extraction does not perform OCR or fully resolve inherited formatting. No live research conclusions or successful independent Council trials are invented by setup.

The safest next step is a small real project: fill its brief, run an independent implementation/review cycle, and adopt one narrow lesson supported by reproducible evidence. Separately select a few approved presentation decks and review their derived style observations before generalizing.
