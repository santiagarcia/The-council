# B1 / ada — pass17 regression, job-layout compile census, diagnostics (2026-10-01; saved by lead from Ada's hand-back)

Builder output; needs independent review. Uncommitted. Full diff: final-umat-ada.patch; tests: final-umat-ada-tests.tgz; raw data beside.
"Transformed/compiled/analysis completed" ≠ verified.

## Root causes
- pass17: 140/234 verification rows → transformed_job_failed (`#5102 Cannot open include file 'dependencies/ABA_PARAM.INC'`);
  by pass16 rung: verified 43, primal_disagreed 55, primal_mismatch_explained 19, tangent_not_verified 13, other 10.
  Cause (57eaeff): dependency bundler resolved the include against the gfortran stub, copied it into dependencies/, rewrote the include.
  Fix: dependency_bundle.py never stages/rewrites the solver header (any case). Under the old uncommitted patch alone, the stub
  (lacking nprecd) would have been compiled into Abaqus jobs instead of the real header.
- Uncommitted patch: kept (COMMON I–N integer typing, reasons for silent build losses, stage_dependencies, job-layout instrument).
  Bug fixed: job_layout_compile ran build script by relative path with cwd=stage → relative --work-dir made everything "compile_failed"
  (0/238 → 209/238 on transform_store). OSError now `harness_error`; also `compile_timed_out`.
- Mis-attributed console lines: verify_store_in_abaqus.run_batch prints result lines under another thread's header; jsonl correct.
  Patch + regression test (fails before, passes after) in proposed/vs/ (lead-owned file).

## pass16→pass17 regression classes (pass16_vs_pass17_changes.{json,csv}, 153 rows)
A header rewrite 140 (fixed) · B COMMON typing 4 theysy (fixed; Abaqus-confirmed) · C renamed header 2 Worlthen (fixed) ·
D staged include 2 jpsferreira (fixed → back to pass16 refusal) · E reason text 2 · F new refusal 1 CLD-Rostock SPRINC (correct) ·
H not reached 2 (pass17 stopped at 234/238).

## Job-layout compile census (gfortran; all 391 re-transformed into B1/ada/store, fingerprint 1669bf6e5f59a15d;
transform_store/ stale at 650a66ab55825346)
Compiles: pass17 no-deps 11/238 · pass17 209 · patch 214 · **final 219/238**. Remaining 19 = 14 inherited (published source fails
gfortran -c) + interface-block array-valued function 2, REAL(PRESENT()) in lifted helper 1, type-bound procedure on promoted object 1,
no UMAT interface 1. Transformed-and-compiled pass16/pass17/patch/final: 214/209/214/219.
Newly compiling: AnargyrosKarakalas, MCM-QMUL, keisuke58 2ch, shayansss hml; SUM-enabled ahartloper UVCuniaxial, compas hooke-iso,
matmodlab neohooke. Newly refused: bessagroup ×2 (det), lucassalmon czmHealing ×2 (previously compiled with truncated derivative).

## 11 general transformer changes (each with behavioural test)
dependency_bundle: runtime header never bundled; case-insensitive include files.
helper_lifting: COMMON I–N integer; renamed header; staged include resolution; SUM(array) over OTI (DIM/MASK refused w/ remedy);
import renames for declared names (TINY); wrap mixed real/OTI array constructors in OTI_VALUE; free-form wrap never splits `**`/exponent sign;
case-insensitive helper INCLUDEs; undefined-callee refusals with call line + Abaqus-utility/LAPACK/missing-file remedy.
parameter_sensitivity_transform (oti_intrinsics only): SUM r1/r2, NORM2 r1/r2, OTI_VALUE, OTI×INTEGER MATMUL r2.
source_transform: DSINH/DCOSH/DTANH/DASIN/DACOS/DATAN/DLOG10 normalised; new refusal for OTI values into unlifted REAL functions;
READ-sync continuation no longer duplicated, only in selected routine; no SAVE on automatic shadows; scalar STRESS/DSTRAN refused w/ line;
diagnostics with line + "What to do" (+ Meaning for semantic-check failures).
abaqus/support.py: compile_one(subject=...). tools/transform_all.py: absolute stage paths; stage_source_includes; strip_build_byproducts
(gfortran .o/.mod caused ifort #7013); reason cap 700; anchor-not-located reasons name the contract field.
Tests: 3 of 5 untracked tests adapted to header rule; new test_transform_runtime_header_is_never_bundled.py (10),
test_transform_corpus_compile_classes.py (13; SUM/NORM2/OTI_VALUE values & derivatives vs analytical to 1e-14). Mutation-checked.

## Diagnostics audit (153 refused rows, current code)
"What to do" 0 → 117; line number 15 → 74. Still no line: COMPLEX (9), undeclared-from-module (7), deferred shape (4).
Registry refusal classes: undefined callee 22, undeclared from unread module 12, unsupported intrinsic 12, semantic check 11,
unlifted callee given shadow 9, COMPLEX on stress path 9, DDSDDE outside region 7, REAL into OTI dummy 7, deferred shape 4,
delegating wrapper 4, anchors 4, DATA shadow 2, promoted w/o shape 2, generic-name collision 1.

## Abaqus (3 jobs): cc_ada_mml_u2, cc_ada_mml_u3, cc_ada_irfancn_elastic completed; MML_U2SA/U3SA compile with ifort line (not UMATs).

## Tests
Acceptance subset 204 passed (runs/tests_acceptance_subset.log). Broad set (87 files) 1158 passed, 5 failed, 1 skipped:
4 fail on pristine HEAD too (supplied_abaqus_utilities, 2× gfortran-not-f77, unary plus); 1 by design (SUM now supported) —
proposed/test_sign_sum_assertion.patch.

## Open
1. Apply proposed/vs/verify_store_log_attribution.patch (+test) and proposed/test_sign_sum_assertion.patch (lead-owned files).
2. Re-verify whole store in Abaqus at new fingerprint (only irfancn of 140 class-A confirmed).
3. Open classes: interface-block array function (2), REAL(PRESENT()) (1), type-bound on promoted object (1, should be named refusal),
   undefined callees SPRINC/SPRIND/GETNFNH/LAPACK (38 — biggest lever), COMPLEX on stress path (9).
4. New OTI forms checked only at module level; not yet vs FD on a corpus UMAT.
5. Gauss F1–F4/F6 untouched.

## Reproduce (B = batches/B1/ada)
PYTHONPATH=src python tools/transform_all.py --all --jobs 10 --store-root $B/store --work-dir $B/work --json $B/runs/transform_all_final.json
python $B/tools/job_layout_census.py $B/store $B/census/census_final.json [--no-deps]
python $B/tools/{original_compiles,class_table,diff_pass16_17,classify_regressions,refusal_audit,abaqus_confirm}.py ...
