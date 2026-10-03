# Vera B6 — review of Ada (b44ed12, 8c8bd99, 20e1510, 2ab6f4a) and Scout (bf8e169, 499722b, bd1a71b, 3947752)

ACCEPT WITH NOTES. **No pass21 needed.**

A/B 4123acc (ab32cce7bec15c93) vs HEAD (a4f0ea8c9d124f18), from git archive copies, PYTHONHASHSEED=0:
- 16 corpus sources: 7 verified, 6 multi-file bundles, 3 others. All generated Fortran, compile_hint, dependencies and reports are byte-identical. Only derivative_manifest.json differs (generated_at, and source.path/sha now name the author's file); nothing in src/ or tools/ reads it.
- 6 parameter-sensitivity contracts: only the Makefile and objects differ; all output CSVs are byte-identical.
- The 7 sampled frozen cases match their recorded transform sha256, 49/49.
- The 4123acc copy reproduces the pass20 store (220 files) after path normalisation.

Commits:
- b44ed12: the bundle copy is what is transformed; the author path is used only in reporting.
- 8c8bd99: FC is honoured from the environment and the command line, gfortran is the default, and clean works. Notes: duplicate -I..; funnel.py:403 and internal_jacobian_validation.py:344 now see an exported FC; stale comment at tools/run_parameter_sensitivity_sweep.py:352.
- 20e1510: write_lock reproduces the lock byte for byte. Note: evidence_status names only pass16 and should record pass20 at ab32cce7 and this equivalence.
- bf8e169: only reason (17), not_verified_reason (17) and compiled (11) changed; 238/67 unchanged; the rebuild reproduces exactly. Minor: [:500] truncation.

The 6 deselected tests: 5 gui (all pass with -m gui) and the corpus_pass whole-store Abaqus re-run (answered by the A/B above).

Evidence: evidence/ (scripts, sample, diff summary; the full out_A/out_B trees were in /tmp).
