# Vera B6 — review of Atlas pass20 (6bd2a89, ea44cd1)

ACCEPT WITH NOTES.
1. Identity: fingerprints recomputed from git archive of 4123acc = ab32cce7bec15c93 / d6f92d4704bee702. The registry, manifest, 113 cases and 484 run_id.json files agree.
2. No counted change: the per-source registry diff shows 0 terminal_state changes; the manifest has 0 of 9537 status cells changed. Counts are 238 / 67 / 109, and 71/114, 34/114, 6/43.
3. The re-freeze changed provenance only: 1210 asset files are byte-identical to the pass19 archive. case-ci 4/4.
4. "111" is reproducible: it is the pre-rerun3c denominator (the 3 RitioL rows, unsupported: a named lifted compile failure, were missing). Use 114. Dropping unsupported rows would flatter the rate.
5. pass19 harness-fingerprint mismatch: no count or verdict was wrong. The equivalent judging code differs by non-judging diffs only. REGRESSION_CASES.md@4123acc:107-108 was imprecise (the pass19 primal run was at d105cef = 815264878209659f); the pass20 text is correct.

Notes:
- record harness_fingerprint_live in run_id.json;
- contract_transform_generation dbe9f928191e1d43 in case.json is stale (same issue as the test_contract_fixtures failure).
