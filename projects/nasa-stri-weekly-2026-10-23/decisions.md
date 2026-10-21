# nasa-stri-weekly-2026-10-23 decisions

Generalized record. Detailed review files are kept outside this public repository with the deck.

| Date | Owner | Decision | Alternatives | Rationale | Rollback trigger |
|---|---|---|---|---|---|
| 2026-10-21 | Ada (main session) | Normalize every timing figure by the nominal analysis of the same model, machine and thread count. State the alternative denominator in the notes | Raw seconds, or an unstated denominator | Santiago's brief and stored preference. Ratios stay comparable across models | A matched nominal time is missing, in which case say so rather than invent one |
| 2026-10-21 | Ada | Show a count that cannot be traced to code as "measured, not traceable" | Guess a breakdown | The benchmarked commit was unavailable | The commit is recovered |
| 2026-10-21 | Ada | Report worst error where the mean was never stored, and say so | Recompute a mean from partial data | Only the worst value existed | Full error arrays become available |
| 2026-10-21 | Ada | Keep raw slide text, packets and reviews outside the public repository, push only generalized lessons | Push everything | `docs/security.md` and `.councilignore`: collaborator and unpublished material is not redistributable | Santiago approves publication of specific files |
