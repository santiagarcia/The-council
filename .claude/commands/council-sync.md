---
description: Generate or refresh Claude Code agents from the registered Council members without overwriting personal edits.
disable-model-invocation: true
---

From the Council repository root run `uv run --locked council claude sync`,
then `uv run --locked council claude sync --check`. Use the installed `council`
entry point or `.venv` Python if uv is unavailable.

Report created/updated adapters. If synchronization reports an edited or
unmanaged file, preserve it and inspect the conflict; do not delete or overwrite
it automatically. Synchronization generates Claude adapters only; it never
creates or changes active member identities, grants permissions, commits, or
pushes. After first creating `.claude/agents/`, restart Claude Code if the new
agents are not available in the current session.
