# B2 / curie_g — growth primal/tangent diagnosis (saved by lead)
77 eligible growth rows (50 primal_disagreed, 14 explained, 13 tangent_not_verified). 19 Abaqus jobs cc_cug_01..19. Evidence 1.8 GB here
(final_groups.json, classify.json, quad_tangent_results.json, quad_primal_rows.jsonl, abaqus/, scripts/). Repos untouched.
Method: material-point replay of every converged pass16 call (original replay bit-exact to Abaqus on 83/83 rows); init variants (ifort
zero/huge/snan, gfortran zero/snan, -real-size 64); construct patcher applying the transform's precision changes to the ORIGINAL; ulpK =
max|Δσ|/(eps·max|DDSDDE|); quad-precision FD of the original (REAL*16, constants bit-identical); Jacobian-matched Abaqus control.
MAIN: Abaqus primal comparison is not a test of the routine — the transformed DDSDDE differs by design and changes the converged FE answer
(C3D8: Newton path; C3D8H: deviatoric–volumetric structure). Original DDSDDE given the transformed's structure reproduces the transformed
run to 1.6e-12. Jacobian-matched control: MinSur1 3.2e-12; CASE4 5.7e-14; Wrinkle-101 4.4e-8; SweetMelon 5.7e-12; SeaShell 2.7e-13.
Clusters:
A harness/Jacobian-steered FE comparison — 9 rows (MinSur ×5, Catenoid, Sphere, 2Stages ×2). Fix (lead, verify_store): primal = routine-level
  replay at recorded inputs + Abaqus Jacobian-matched control, tol |Δσ| ≤ 1e-10·max|σ| + 64·eps·max|DDSDDE|; precision control the same way; FE comparison informational.
B transform precision — 24 proven (+4 B*): W declared REAL(4) lifted to double OTI (Growth-EX, conformal ×6, CASE ×9, Wrinkle ×6, shell ×4);
  L literal kind promotion in lifted statements (-5.0/3.0→-5.0D0/3.0D0, Sqrt(3.0), 1.0/200, 9.0/40, ...). Patch applied to original ⇒ ≤10 ulpK on 25/30.
  Fix (ada): never append D0 to default-REAL literals; REAL(4) variables' real part computed in original kind. HAZARD: global promotion breaks
  `(TIME(2)+DTIME) .LE. 2.2` (works only because 2.2 is binary32).
C undefined behaviour in ORIGINAL confined to write-only STATEV — 17+1+1 primal rows + 6 tangent rows: C1 Lambda1z2 → STATEV(7) (e59bd12e :212);
  C2 G13/G23/G31/G32 unassigned → STATEV(9) (From-2D). zero/huge/snan change only that slot (also in Abaqus jobs 18–19). Policy = D-12.
C3 undefined behaviour affecting STRESS — Growth-Alex, Growth-Robot: ThickCoord defined only for NPT ≤2 (:116-119); C3D8H has 8 points.
D zero-stress free growth — 3 mholla rows (area/fiber/iso_morph): relative metric divides rounding by rounding; use stiffness scale + constrained growth loading.
E transform non-finite at call 0 — GOH: fginv(i)= assignments commented with no lifted replacement (transformed :926-931; original :604-609),
  `lnJe = REAL(LOG(DETFE_OTI))` truncates derivative (:970); Curing ×2: (cure/max_cure)**m at cure=0 (OTI real part non-finite); deck ignores author SDVINI (1e-15).
F tangent_not_verified 13: 12 Jeff97 plane strain ν=0.4999 — double FD cannot resolve (2400 ulp pressure noise); quad FD 7-decade plateau, OTI agrees
  ≤1.2e-7 entrywise (→5.6e-16 with exponent matched); fix: quad-precision FD reference. mholla fiber_stretch: coverage only.
Projection (D2 growth 132): today 35 → +19 (A+F+D) = 54 → +31 (B+E+SDVINI) = 85 → +25 (policy C) = 110 → +0–2 (C3).
125 needs policy C AND 13–15 of 20 out-of-scope blockers (transformed_job_failed 5, transform_refused 5, original_job_failed 4,
experiment_not_informative 3, arguments_diverged 2, support_build_failed 1). Without policy C ceiling ≈87.
Side: authors' DDSDDE O(1) wrong on small entries in most conformal/shell sources; OTI matches quad FD.

---
# B2c / curie_g (builder) — primal gate, stiffness metric, SDVINI, 77-row re-evaluation (saved by lead)
Uncommitted. Changed: tools/verify_store_in_abaqus.py, abaqus/compare.py, abaqus/replay.py (additive). New: 8 tests/test_primal_gate_*.py (29 pass,
incl. end-to-end verify_one on MinSur1 with recorded Abaqus outputs), tests/fixtures/primal_gate/*.json.gz (~860 KB).
Gate: D-12 undefined-output check first (gfortran zero vs snan, same flags as corpus_features.harness — test enforces); STRESS/DDSDDE undefined ⇒
new stage `undefined_in_original`. (a) routine-level replay of every converged call (original replay must reproduce solver record ≤1e-12,
else refused as hidden state); bound |Δσ| ≤ 1e-10·max|σ| + 64·eps·max|DDSDDE| (64 measured: agreeing ≤10 ulpK, first real difference ≥7e5);
STATEV each slot ≤1e-10 of own max. (b) Jacobian-matched Abaqus control. Record: primal_gate.decided_by, routine_primal, jacobian_matched_primal,
undefined_in_original, undefined_outputs, evidence.primal_decided_by; FE comparison in record["primal"] informational_only. Precision control
redone same way (can only route to primal_mismatch_explained). Association control no longer run.
(D) compare_primal(stiffness=) floor 64·eps·max|DDSDDE|. SDVINI: honour_author_sdvini → *INITIAL CONDITIONS, TYPE=SOLUTION, USER when deck states none.
Re-evaluation (pass16 store dbe9f928; pass17 store entries don't compile; working tree a8cc18d7 has no entries) — projected, 17 confirming jobs cc_cug_20..36:
 verified 18 (Abaqus control run on 7, all agree; 12 exclude STATEV(7) undefined) — growth 35 → 53 projected
 tangent_not_verified 24 (FD resolution near-incompressible + 1 coverage) — needs quad FD (gauss)
 primal_mismatch_explained 21 — wait on Ada REAL(4) widening fix
 primal_disagreed 11 — wait on Ada literal-kind fix (9) + 2 curing (single-precision constants in lifted helper, STATEV(2) 5e-8/7e-7)
 undefined_in_original 3 — Alex, Robot (STRESS undefined at points 3–8); GOH (DDSDDE rows 2–3 depend on uninitialised var in ORIGINAL — new).
Curing rows finite in Abaqus with SDVINI (cc_cug_28/30).
Lead items: register undefined_in_original in terminal_states.py + registry; verify_one job names lack agent prefix; Abaqus control
differences ~113/92 ulpK pass via 1e-10·max|σ| term; registry columns reading record["primal"] must move to primal_gate/routine_primal;
7 failing legacy tests grep pre-B2c text (test_a_gate_that_reads_false_beside_a_verdict_says_why.py, test_an_unmeasured_zero_is_not_a_measurement.py);
8 failures in test_abaqus_trial.py (not touched by curie_g).
