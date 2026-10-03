# Scout B6 — triage of 10 pre-existing failures

Commits: 3c26b56 (refusal census + MohrCoulomb expectations after the pass19 registry), 1fa8e99 (utilities test is behavioural; intrinsic export rule asserted directly), aee3baf (audit entries).

| # | test | class | action |
|---|---|---|---|
| 1-4 | refusal census ×3, whole-array stress update | stale after an intended registry rebuild (f14f3f1) | 3c26b56; hand-edited measured totals, every moved record read |
| 5-6 | supplied utilities, intrinsic unary plus | stale (5dacb13, 57eaeff, faeec2b) | 1fa8e99 |
| 7 | contract_fixtures generation dbe9f928… vs ab32cce7… | stale record since c71d5af; cross-repo re-record | → Ada + Noether |
| 8 | batch command real contracts | REAL regression 57eaeff: summary "source" = bundled copy (transformation.py:121-124,177) | → Ada |
| 9-10 | gfortran-not-f77 ×2 | REAL regression 57eaeff: Makefile hard-codes FC, no clean target (transformation.py:398-403) | → Ada |

Rerun: 49 passed, 4 failed. Audit: 6 passed. case-ci: 4/4.

## Follow-up on Vera's notes 1, 3, 4
- 499722b: adequacy assertion restated; T-12 reasons state the flip.
- bd1a71b: contract-level ROTSIG test; fails with the supply call removed.
- bf8e169: registry builder.
  - refused ⇒ compiled False (11 records);
  - not_a_umat reasons keep the entry-point verdict;
  - bytes/sha256 was not a defect (file size vs the decoded length, 1ffc540).
  Counts unchanged (238/67/109).
- 3947752: audit map.

Tests: audit 6 passed; registry/manifest tests 215 passed.
