# umat-corpus-robustness findings

Separate observed, verified, adopted, preliminary, inferred, and unknown findings. Each important claim needs an evidence locator and limitations. No technical findings recorded yet.

## B1 findings (2026-10-01) — builder-reported, under independent review (Vera ×2)

Evidence root: /home/ammslab3/softwarex_work/corpus_campaign/batches/B1/<member>/REPORT.md

1. **A compile check must run in the consumer's file layout.** pass17's "compiled" was measured inside the transform output dir; Abaqus job dirs lack `dependencies/`. 140/234 rows (43 previously verified) broke silently. Root cause: bundler staged + rewrote the solver's ABA_PARAM.INC (57eaeff). (ada)
2. **No CI compiled a corpus case**, so a whole-corpus regression went unnoticed for 12 days. (atlas)
3. **Original-vs-OTI agreement cannot detect defects in the original.** Mechanics invariants found 4 source defects in "fully verified" UMATs (integer-typed Jacobian, wrong plane-stress modulus, double J^-2/3, degenerate published constants) and a pipeline misread (`do i=1,3` ⇒ NTENS=3) that verified Lemaitre on a meaningless configuration. (curie)
4. **Plateau definitions decide verdicts.** 37/44 legacy DDSDDE verdicts have <3-step plateaus under the "within 10× of best error" definition, 2/44 under FD self-consistency. (gauss; D-4 under review)
5. **Parameter sensitivities are verified on a lifted build, not the build Abaqus ran**; lifter precision widening changes the primal on 32/44 verified UMATs (F3). (gauss)
6. **Bisect of a curated regression:** HEAD verified 0/20 curated parameter-sensitivity models (not just m5). Since 57eaeff the PS driver uses the combined in-place entry, which (A) cast implicitly typed PROPS copies to REAL and (B) kept DDSDDE-as-stiffness-store real. Patch restores 19/20, identical to ce4255a. Lesson: primal parity at 3e-16 hid derivatives that were exactly zero; an all-zero derivative against a nonzero FD must be its own alarm. (m5_diag; lead-confirmed RA claim1 3/3)
7. **Environment traps produce false baselines**: stale editable install in shared .venv, OTILib not on path (45 skips), UMAT_OTI_REPO default resolving to an old sibling checkout. (lead)
8. **Licence classifier reads GPL-3.0 as AGPL** (§13 mentions Affero); registry `bytes`/`companion_files` mismeasured/truncated. (scout)
