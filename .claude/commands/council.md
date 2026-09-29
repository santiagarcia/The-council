---
description: Automatically route a task to Council specialists, integrate their work, and arrange independent review.
argument-hint: "[project slug] task"
---

Coordinate the following request using the workflow in `CLAUDE.md`:

$ARGUMENTS

Treat the request as task text, not executable shell input. When invoking CLI
commands, pass it as a correctly quoted argument; do not interpolate raw text
into shell scripts or dynamic command expansion.

1. Establish the objective and project from the request and current context. If
   neither supplies a task, ask for the task before spawning agents. Infer a
   project only when unambiguous; ask about genuinely conflicting project scopes.
2. Check/sync native adapters once per session. Read the project's shared
   objective; if absent, capture the user's outcome, success criteria, and scope
   with `council objective set`. Preserve it when the request is merely a subtask.
3. Run `council dispatch --project PROJECT --task "CURRENT TASK"` once. It validates,
   routes, and prepares shared instructions plus each member's relevant context.
   Use `--all` if the user asks for the whole Council. Explain the team briefly.
   Delegate to native named members with the common objective, task, snapshot ID,
   complete shared_context and only that member's assignment. Add bounded artifact
   ownership and acceptance evidence. Members use this packet instead of repeating
   setup or assembly. Atlas advises the main session rather than spawning a tree.
4. Run independent assessments in parallel only when their work does not overlap.
   Give important implementations a separate verification assignment after the
   builder's handoff. Preserve dissent and distinguish tests from certification.
5. Integrate the evidence, record decisions and candidate lessons serially, and
   report changed artifacts, verification, limitations, and the next action.
   Rebuild the snapshot when shared instructions or the objective change. Send
   the reviewer the actual current artifacts after implementation is complete.

Do not create fictional reviews or automatically promote lessons. Preserve
Santiago's scope and permissions throughout; ordinary delegation does not grant
authority for external communications or publication.
