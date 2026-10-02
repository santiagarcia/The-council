# B1 / m5_diag (Gauss, diagnostician) — parameter-sensitivity regression (saved by lead)
Since 57eaeff the PS driver uses the combined in-place entry UMAT_WITH_SENSITIVITIES (services/transformation.py
_generate_parameter_sensitivity_artifact(combined_interface=…)); it severs parameter derivatives two ways:
A. source_transform.transform_umat_to_oti_from_config taint loop grows only through _names_declared_real; implicitly typed
   copies (TAU0=PROPS(3) under ABA_PARAM.INC) have detected_type "unknown" → `TAU0=REAL(PROPS_OTI(3))` → all DSIGMA_DP/DSTATEV_DP = 0.
   Fix: _names_typed_real = declared reals + untyped names outside implicit_integer_letters (nothing guessed under IMPLICIT NONE).
B. DDSDDE used as stiffness store (STRESS += DDSDDE*DSTRAN) kept real → `DDSDDE(K2,K1)=REAL(ELAM_OTI)` loses dC/dp·Δε
   (10/20 curated models); same pattern caused 5 J2/Perzyna transform_failed (old_ddsdde_assignments_disabled not routine-scoped).
   Fix: in parameter mode, _ddsdde_scratch_use(carried_names=…) redirects live DDSDDE writes into DDSDDE_OTI shadow.
Full 20-model sweep: ce4255a 19/20 (14539/14540 rows); f0f0731 0/20 (5692/10600, 5 transform failures); fix A 4/20;
A+B on current tree incl. Ada 19/20, 14539/14540, per-model worst identical to ce4255a; m6_fcc 1 unresolved row (same at ce4255a).
claim1 m5 patched: succeeded 840/840, slide worst 9.8e-9 (= ce4255a).
Patch: fix_parameter_derivative_carriers.patch (source_transform.py + tests/test_an_implicitly_typed_parameter_copy_carries_its_derivative.py,
4 cases {ABA_PARAM.INC, IMPLICIT DOUBLE} × {param copy, DDSDDE store}; 3-increment total derivative vs central FD of original;
unpatched 4 fail, A-only 2 fail, A+B pass). Note: FD reference calls original umat linked from transform output (real arithmetic).
Regression: 5dacb13 tests etc. 122 passed; full offline suite patched 16 failed/3835 passed = base set (+2 flaky: test_packaging, test_reproduce_profiles).
Blast radius: combined entry (CLI transform with DSIGMA_DP/DSTATEV_DP, Table-6 sweep, consumers of OTI_DSIGMA_DP). NOT the corpus
funnel (lifted path) nor RA provider. Corpus text scan: A in 98, B in 46, A∨B in 128 of 346 records (corpus_carrier_scan.json).
Proposed failure class: "parameter derivative severed by a real cast in the combined entry".
Open: _old_ddsdde_assignments_disabled not routine-scoped; COMMON/PARAMETER-routed values stay real (derivatives dropped by design
since 5dacb13); parameter flow through CALL outputs unverified; Fix B gated to parameter mode.
