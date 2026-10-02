# B3 / nico — novice reproduction from docs (fresh clone + venv) (saved by lead, 2026-10-02)
1 install/smoke/GUI subset worked; full pytest duration/subset not documented; install described 3 ways (START_HERE says Python ≥3.10, INSTALL tested 3.11.7).
2 make case-ci 4/4 in 8 s (doc says "minutes", no expected output); 2 offline cases PASS (replay ~3 s, R+P 7 s); fetch resolved from
  discovery_cache (outside clone) — doc says $UMAT_CASE_ASSETS default; no case list / index.json not mentioned; ids very long.
3 manifest build FAILED as documented outside workspace layout (../discovery_cache); worked with all root flags absolute; rebuild not
  byte-identical (absolute roots in header + generated); doc says built by merging B1 but committed merges list B2; test
  test_noethers_b1_records_fold_without_rejection_and_stay_out_of_the_pipeline fails (absolute B1 evidence path). Answers: D0 415, D1 391,
  D2 260, DDSDDE verified 0 (legacy gate 62 not counted), primal 58/57.
4 harness: no documented command; RELATIVE --out silently gives "original routine did not build" (all not_attempted) — absolute works
  (13 primal + 13 ddsdde verified, 10.7 s); evidence locators don't resolve outside campaign root.
Top doc fixes: (1) workspace layout requirement or clone-elsewhere recipe with all root flags; (2) runnable harness command + expected
output, absolute --out or fix; (3) B1/B2 mismatch + expected path-layout test failure; (4) how to list cases, expected case-ci output,
worked offline example, fetch needs discovery_cache; (5) state DDSDDE verified = 0 at this commit and where verified results come from.
