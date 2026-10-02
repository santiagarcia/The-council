# B2 / vera — combined review: harness, primal gate, contract 4.0.0 (saved by lead, 2026-10-02)
0 Abaqus jobs. Evidence in this dir. Verdict: do NOT report param-sens numbers or D-12 "fully defined" counts yet.
1 CONFIRMED: all 13 B1 injections, c_floor 12/12, hidden-state toys trip; clean toy verified.
2 DEFECT High: zero vs snan init misses uninitialised values used via NaN guard (IF(X.NE.X)), comparison (IF(X.GT.0.5)), integers
  (both ≤0) — cells verified/fully_def True or blamed on transform. Same pair on Abaqus side (replay.py:1214, verify_store:3090).
  Third init build (+inf real, +77777 int, flipped logicals) separates all; clean toy unchanged. OTI bug only where original undefined
  is hidden by design (only fully_def=False shows it). Nothing counts stress_and_ddsdde_fully_defined yet.
3 CONFIRMED nonzero params (1e-5 errors caught); DEFECT High zero-valued params: step floor 1e-6 → 3rd step 1e-10 → atol≈3.5e-3 →
  true derivative passes as "structural zero" (local and total). Total-derivative n·max|o| term opens same window (D=500 dropped passes at atol 888).
  Medium: mixed-unit STATEV block (slot 1e12 smaller) dropped/×15 passes with double reference.
4 DEFECT Medium: PureGravity bound 2.2e-4·max|σ| (K/max|σ|=1.6e10) — 1e-4 relative stress errors pass routine + Jacobian-matched;
  source mutation 2.0D0→2.0004D0 (6.9e-4) passes. Stiffness taken from TRANSFORMED side (verify_store:3206/3267/4323) — inflating
  transformed DDSDDE ×1e6 at one call lets 1e-6 error pass. 64 ulpK calibrated on same 77 rows (circular) but classification insensitive
  (held-out 25 rows: agree ≤3.8, disagree ≥3.3e3).
5 CONFIRMED: independent FD spot check 6 states (Sina, abaci, Jeff97 PureGrowth): 0 entries outside tolerance (double and quad).
6 CONFIRMED contract 4.0.0 complete; Low: app/plain_language.PLAIN lacks undefined_in_original (falls back to harness_error text).
Required: third init build (harness + Abaqus side); counting reads stress_and_ddsdde_fully_defined; zero-valued PROPS step from physical
scale + structural-zero only if FD differences exactly zero across ladder or atol < 1e-3 of derivative scale, count affected fv44 cells;
restrict column-max Euler term to STRESS block; primal gate stiffness from ORIGINAL (or min of builds), publish bound/max|σ| per row,
prefer per-row noise floor; PLAIN entry.
