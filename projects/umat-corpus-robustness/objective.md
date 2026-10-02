---
project: umat-corpus-robustness
objective: Make UMAT Source Transformation and Residual Assembler handle as much of
  the webscraped UMAT corpus as possible, with reproducible numerical evidence that
  outputs are correct, and keep every verified UMAT as a permanent regression case.
success_criteria:
- Per-UMAT manifest + feature matrix over all 391 acquired sources with explicit denominators
  (discovered/eligible/attempted/transformed/compiled/executed/verified per feature)
- Recurring failure classes fixed by general pipeline improvements, each with a regression
  test
- Every derivative feature verified against an independent reference (original UMAT,
  analytical, or controlled multi-step FD) with stated what/wrt/held-fixed
- Verified UMATs preserved as regression assets (inputs, outputs, tolerances, hashes,
  commands); fast CI subset plus full corpus campaign command
- Independent reviewer and novice reviewer have checked each batch; final report with
  remaining blockers and next fixes
constraints:
- Never count skipped, transformed-only or compiled-only as verified; never loosen
  the definition of verified to reach a number
- Respect redistribution licences; non-redistributable source stays out of git with
  retrieval instructions
- Do not edit other assistants' paths (codex-*, imq-*-recovery, claude-*-{C,G,P,work});
  one Abaqus job prefix per agent; durable output never only under /tmp
- Commit coherent reviewed changes on corpus/robustness-2026-10-01; push only when
  Santiago asks
updated: '2026-10-01'
---

# Shared objective

All members work toward this objective within their assigned roles. The main session owns updates; agents report blockers and disagreements. An objective does not expand permissions or establish verified knowledge.
