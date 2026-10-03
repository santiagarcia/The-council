# Noether B6: RA re-freeze at a4f0ea8c9d124f18 (blocked, nothing committed)

- schemas/transform_generation.json and contract_lock.json copied byte for byte from final-umat (cmp OK). Combined digest is cff11c2c22032a0068faf17da2c470a72c462febaa4b8c710ea9b3e8cde94980, which matches.
- scripts/regenerate_recovery_fixture.py was run for both fixtures, with work dirs under refreeze_a4f0ea8c/{elasticity,j2}/ here. That was 6 Abaqus jobs, run one after another (original, transformed and jacobian_matched per material; the script names them imqrf_*). Both verified: 1.069e-14 and 8.250e-11.
- Diff against the dbe9f928 fixtures: every number is identical. `generated` and `transform_fingerprint` changed, and one new key appears in finite_history.evidence: "primal_decided_by": "routine_level+jacobian_matched" (from the UMAT verifier, 4d91f0c).
- fixture_residual_check: elasticity 1 held / 2 not established, J2 32 held / 3 not established, unchanged.
- BLOCKER: the shared contract schema residual_fixture_v1.schema.json (identical in both repositories and locked) has additionalProperties:false on finite_history.evidence and does not list primal_decided_by. The UMAT producer now freezes fixtures that its own contract rejects. RA's test_current_operational_fixtures_carry_independent_verification fails. The fix belongs in final-umat: add the key to the schema (or stop emitting it), regenerate the lock, then copy again. That changes the lock digest.
- RA suite (`-m "not abaqus and not arc and not network"`): 719 passed, 5 failed, 19 skipped. One failure is the blocker above. Three in tests/corpus/test_corpus_residual.py fail with "no registry record with key ..." against the pass20 registry in final-umat, not caused by this change. tests/integration/test_connected_j2.py::test_reproducer_fresh_build_and_nonzero_failure fails because `python -I` ignores PYTHONPATH and the installed umat_oti is the old checkout (no umat_oti.provider): environment.
- test_audit_integrity.py: 6 passed.
- Working tree in final-ra holds the uncommitted re-freeze (schemas, fixtures, check JSONs, and current-fingerprint docs: COMPATIBILITY, which_layer, USAGE_REPORT §10, HANDBOOK md/html, CHANGELOG, final_refreeze.md addendum).

## Follow-up (coordinator's message)
- 7a490d3 makes the three live corpus tests name their materials by (source_id, source sha256) through the new residual_core.corpus.sources.key_for_source. load_case now reads the manifest from the registry record's verification_source (pass20) instead of a hard-coded pass16 file. tests/corpus: 19 passed.
- c0dde13 adds the T-11 map entry for 7a490d3 (its message contains "fixed"). test_audit_integrity.py: 6 passed.
- test_connected_j2::test_reproducer_fresh_build_and_nonzero_failure fails identically at 681f71c (git archive copy, re-inited as a standalone repo because the reproducer calls git rev-parse): "No module named umat_oti.provider" under `python -I`. Environmental: the venv's installed umat_oti is the old checkout.
- The re-freeze stays uncommitted, waiting for Ada's schema fix and the new lock digest.

## 4.1.0 sync (closed)
- Copied byte for byte from final-umat 8a9a0ea: contract_lock.json, plus the residual_fixture_v1, umat_contract_v1 and contract_error_v1 schemas and transform_generation.json. Combined digest ece44657d1350d504a5b24d3dfbee2bb20084a992fcfbdecdcd2ba7427164dc4 matches.
- 82a7d3b: re-freeze plus 4.1.0 (CONTRACT_VERSION 4.1.0, a new test that 4.0 records are still read with a caveat, CHANGELOG, COMPATIBILITY row 3.0.0→4.1.0, final_refreeze.md).
- 644041e: T-12 review entries for the two fixtures (json_only_changed now includes finite_history.evidence.primal_decided_by).
- tests/contract: 90 passed, 11 skipped (pass11 store absent; these skips predate this work). Documented suite: 724 passed, 1 failed (test_connected_j2, environmental), 19 skipped, 5 deselected. Audit: 6 passed.
- RA commits since d74bce8: 9. Working tree clean.
