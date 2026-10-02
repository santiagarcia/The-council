# B1 / vera — independent review of harness, mechanics checks, manifest, regression design (saved by lead)

Bottom line: do NOT commit or report these numbers yet. FD-only plateau is sound; four defects change numbers/claims.
Scripts/evidence beside this file (b_c_inject.py, b_proposed_rule.py, c_floor.py, d_census.py, g_merge_probe.py, g_sample10.txt, a_hidden/).

A Independence/restored state — DEFECT High. Argument restoration complete, but hidden-state gate compares base STRESS only
  (not STATEV/DDSDDE/energies, not total-mode reruns). Toys: SAVEd PROPS-derived constants → FD dσ/dE exactly 0, gate False;
  call counter in STATEV → absorbed as "nonsmooth", ddsdde cell folded VERIFIED; file I/O → all nonsmooth, gate False.
  Real case: Jeff97 PureGrowth.for:106 Lambda1z2 never assigned, written to STATEV(7) at :208 (uninitialised, differs between
  processes) → spurious branch changes exclude ~95% DDSDDE columns on 14 Jeff97 keys (pattern in 36/64 Jeff97 sources);
  Gauss's "FD resolution" attribution wrong for these. Gradient-driven sources (40/44): FD strain direction read from the OTI
  store seed map (shared path; current verdicts checked canonical).
B Plateau D-4 — harness FD-only plateau sound; legacy compare.py plateau (from OTI-vs-FD error) DEFECT (runs backwards).
  Injection: both rules catch column errors ≥3e-6; BOTH pass a −100% error on an entry at 6e-7 of column; harness passes +0.5%
  at 1.5e-4 and ×10 at 9e-8 of column. Proposed rule: FD-only plateau ≥3 consecutive; per-entry τ = atol + rtol|D_e| + 2u_e
  (u_e = plateau spread); u_e > 1e-3|D_e| ⇒ unresolved; structural zeros from reference value. Corpus impact unmeasured.
C Tolerances — DEFECT High: allowed rel error = 1e-6·(col norm/|entry|); path floor 1e-3 of path max → 100% error passes at
  1e-9 of path max.
D Nonsmooth exclusion — DEFECT Medium: fold verifies a cell if one path verifies and others not_attempted; verified on 1/20
  states in places; branch signature uses all STATEV even for stress columns.
E Lifted vs store build — DEFECT High for reporting: no build field on cells; lifted primal ≠ store on 32/44.
F Curie's 4 claims all CONFIRMED (Sina :24/:76/:91; abaci :338; keisuke :328/333/336, predicted 1.34% matches; Lemaitre deck
  axiSymmetricNotchedBar.inp:9261 PROPS(4)=200 → Sf=0 exactly). Sina adjudication: Gauss right — OTI tangent correctly
  differentiates the stress map; state that it differs from author's DDSDDE. Check defects: elastic checks not gated on no state
  movement; NTENS=3 on non-plane-stress source should be unsupported; abaci misfiled as damage.
G Manifest — DEFECT High: 10-row sample matches raw evidence; but ddsdde verified=62 from legacy gate (18 with primal failed/
  not informative); merge accepts nonexistent evidence, tol 1e300, held_fixed "-", counts ladder not plateau, last-writer-wins
  overwrites failed, mixed tolerance semantics.
H Atlas design — DEFECT Medium: plateau_min_steps 2; per-case tolerances blessable; nonsmooth drop-out; no mutant canary;
  drift info-only.
Required (priority): 1 manifest ddsdde from D-4 evidence + primal agree; 2 entrywise resolution-aware tolerance; 3 full hidden-
state gate (bit-exact all outputs, h=0 replays, -finit-real=snan vs zero, -fcheck=bounds, trip ⇒ source not_attempted);
4 build field on param-sens cells, out of pipeline denominators; 5 harden validate_cell/merge; 6 coverage in fold, column-relevant
branch signature; 7 independent finite-strain FD direction; 8 mechanics gating fixes, abaci reclass; 9 Atlas: plateau≥3,
global tolerances, frozen judged-state set, mutant canaries. Smaller: absolute evidence paths; run_corpus_features appends
duplicates; primal failed when only mechanically_informative false → inconclusive; lifter misplaces SAVE.
