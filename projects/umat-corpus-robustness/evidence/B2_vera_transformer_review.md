# B2 / vera_t2 — review of Ada B2 transformer + Ada-C complex (saved by lead, 2026-10-02)
Store fingerprint 426d9fbc17082e93. Own driver fd/vfd.py; evidence in this dir.
1 q7 toys fixed (4/4 zero derivative); neohooke refused (FORALL :100 quoted). DEFECT High (pre-existing): name assigned BEFORE the OTI
  seed-init block gets shadow zeroed with no copy-in — czmHealing SMALL_K=1.D-8 (shear 621.7506 vs 621.75060622; damaged state DSTRAN 1e-3:
  OTI shear 2.7e-8 vs 6.2e4, DDSDDE all NaN); toy t4a E=PROPS(1)→helper ⇒ STRESS 0. Corpus scan: czmHealing ×2 (compiled), Curing C12INF,
  baw-de MohrCoulomb E/NU (not compiled). Ada's "czmHealing tested both branches" claim contradicted.
2 DEFECT High (introduced): hoisted extraction skipped by `IF(..) GOTO 200` to a label after the hoist point (t2d: primal rel err 1.0,
  DDSDDE 0 vs FD ~100). _EXIT checks RETURN/STOP/XIT only. RETURN→GO TO 99999 single exit is safe (t2a).
3 CONFIRMED binary32 (t3c derivative not rounded; t3e bitwise; INTERFACE REAL Y no leak). Low: REAL(KIND=SP) with SP=4 parameter not recognised (3.5e-8).
4 DEFECT Medium-High: DATA XI/1/ modified only by lifted helper — XI_OTI re-copied each call from never-updated XI, SAVE carry-over lost
  (t4c call 2: 0.200 vs 0.210). DATA assigned in UMAT itself correctly refused.
5 Complex CONFIRMED: CoupFE small_strain_j2 + abaqus_ufl small_strain_viscoelastic, 6 increments incl. plastic: primal ≤1.5e-17,
  DDSDDE ≤4e-11/2e-13. DEFECT Medium: imaginary-part guard bypassed by XIM=DBLE(DCMPLX(0,-1)*Z), CALL IMPART(Z,XIM), and tangent written
  as AIMAG(F)*HINV (idiom detection fails → guard off) → DDSDDE 0 vs FD 100.
6 CONFIRMED primal parity spot check (Jeff97 BodyForce bitwise inc 1–2, Sina ≤2.3e-16, AlexanderJFDR/mholla bitwise; DDSDDE ≤1.3e-10).
Required: (1) copy-in every shadow of a name assigned before seed-init (or move init first); tests SMALL_K, PROPS→E→helper, Curing; rerun
czmHealing damaged state; (2) GOTO/computed GOTO/arithmetic IF out of hoisted-over block ⇒ single exit or refuse (t2d test); (3) DATA via
helper: copy-in first call only + SAVEd shadow, or refuse (t4c test); (4) complex guard: taint reals derived from complex + CALL outputs,
detect step idiom from DCMPLX(0,h) alone, or cross-check author complex-step tangent vs OTI DDSDDE (t5b/c/d tests); (5) correct czmHealing wording.
