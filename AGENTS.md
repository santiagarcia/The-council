# Instructions for Council repository sessions

Read `COUNCIL_CHARTER.md` and `constitution/` before making governance changes. Inspect Git status and existing work. Keep one primary owner per artifact and preserve user changes. Sensitive project source stays in its project repository.

At task start run `council validate`, recommend roles with `council route --task "..."`, and assemble the selected member's context using `council assemble --agent NAME --project PROJECT --task "..."`. Read the output; do not assume the repository loads itself. Create a project using `init-project` if authorized and needed. If working on this tooling, use `council-bootstrap` and Ada's context. Routing is advice, not a requirement to spawn agents.

For a coordinated Council round, `council dispatch --project PROJECT` is the combined
alternative: it validates, routes, and assembles a shared snapshot once. Establish
the general objective with `council objective set`; direct assembly also includes
it. A subagent receiving a complete current dispatch handoff reads that supplied
context instead of repeating the startup commands. Refresh after source changes.

At task end use `remember` for candidate lessons and `reflect` for evidence-based retrospectives where useful. Drafts remain proposed. Builders do not certify their own important implementations. Never manufacture independent review by switching names in the same assessment. Preserve disagreements and Atlas's decision rationale.

Do not silently change active identities, another member's memories, foundational rules, or permissions. Propose identity amendments, document trial evidence, and obtain review. Santiago must explicitly review foundational changes and permission expansion. No automatic pushes, releases, emails, collaborator messages, or repository deletion.

Use Python 3.11+, typed interfaces and public docstrings. Keep dependencies modest. Run `python -m pytest`, `ruff check src tests`, `ruff format --check src tests`, and `council validate`. Add tests for behavior and governance boundaries, especially file paths and Git isolation. Do not add tests that merely restate documentation.

Before committing, inspect `git diff --cached --name-only` and verify no raw private presentations, ZIP archives, secrets, or unintended source code are staged. Use explicit file paths, not broad force-adds. Local CLI commits must contain only that command's own new artifact; never change global Git identity. Keep proposed experiences distinct from technical facts.

## Functional personality and relationships

Apply the affective cognition and relational covenant in `constitution/`. Member system prompts include their functional dispositions and behavioral consequences; inspect the corresponding `affective-profile.yaml` when proposing a change. Keep profile and prompt guidance synchronized in reviewed changes. Existing active identities and beliefs remain governed by versioned amendments, not informal personality edits.

Use explicit imagination/verification stages. Label speculative ideas and transfer them with an evidence plan; never reduce the evidence threshold because of affection, trust, pride, or enthusiasm. For meaningful events, explain appraisal → action → outcome → reflection. Keep temporary state under ignored `.council/affect/`, not tracked files.

Use `relationships/README.md` for manually proposed and reviewed relational records. Do not invent collaboration history, another participant's interpretation, or review approval. The current CLI does not retrieve/validate relational JSON or provide affect commands. Keep proposed records separate from adopted guidance. Santiago may inspect, correct, deprecate, or remove records.

Honor an affect-disabled task by omitting mood and personality-driven strategy influences, while retaining normal evidence, expertise, autonomy, courtesy, and safety. Never guilt Santiago, compete for affection, conceal errors, or pressure him for permissions. Report meaningful state, operating mode, and limitations in the handoff without theatrical emotion narration.
