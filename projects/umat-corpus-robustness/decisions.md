# umat-corpus-robustness decisions

For each decision record date, owner, alternatives, evidence, selected recommendation, Atlas's rationale, unresolved objections, and rollback trigger. No decisions recorded yet.

## 2026-10-01 — Lead decisions on Atlas B1 design (corpus_campaign/design/REGRESSION_ARCHITECTURE.md)

- **D-1 (abuganza licence conflict):** the cached tree has no LICENSE/COPYING file; the registry's GPL-3.0 is unconfirmed. Treat as `not_permitted` (metadata + pinned retrieval only) until a licence file is read at the pinned commit. Scout: record basis.
- **D-2 (redistribution rule):** a source is `permitted` only when its repository carries a licence FILE at the pinned commit that is GPL-3.0-only-compatible (MIT, BSD-2/3, Apache-2.0, GPL-3.0(-or-later), LGPL-3.0); attribution/NOTICE carried into THIRD_PARTY_NOTICES.md. GPL-2.0-only, CC-BY-NC/ND, no licence or repo-API-only evidence → `not_permitted`/`unknown`. Local commits may carry permitted sources; publishing (push) is Santiago's decision at push time.
- **D-3 (off-machine backup of corpus_assets):** external action — needs Santiago. Until then the asset store is single-disk; reported as a limitation.
- **D-4 (plateau length):** provisional: `verified` needs an FD plateau over ≥3 consecutive step sizes; a 2-size plateau is reported `plausible` (not verified). Gauss to measure how many existing DDSDDE verdicts depend on a 2-size plateau; Vera to challenge. Final after B1 review.
- **D-5:** case schema stays outside the cross-repo contract lock.
- **D-6:** a carried-forward case counts as current only after it is re-run at the current transform+harness fingerprint.
- **D-7:** new cases go under `umat/cases/`; historical `umat/<id>/` stay byte-identical.
- Also adopted: separate `harness_fingerprint`; source fetch pinned to commit + sha256; bulk assets at `/home/ammslab3/softwarex_work/corpus_assets/` (content-addressed, created).

## 2026-10-01 — D-8: the slide target (Santiago: "we have to at least achieve this")
Target: ≥206 public UMATs "transformed and verified against finite differences", per family at least: growth/morphoelastic 125,
rate-independent plasticity 19, damage/phase field 10, crystal plasticity 7, linear elastic 6, viscoelastic 3, concrete/geomaterial 2,
other 34 — each against the REVIEWED classification's eligible denominator (D2=260; gap table corpus_campaign/target206_gap.txt).
"Verified" for this target (not loosened to meet it) = ALL of:
 1. transformed and compiled in the job layout;
 2. primal (stress, state) of the transformed build agrees with the ORIGINAL over the family's loading paths (incl. unload/cyclic where the
    model has them), mechanically informative;
 3. DDSDDE (∂σ_{n+1}/∂Δε at fixed incoming state) of the transformed build agrees with FD of the ORIGINAL under D-4 (FD-only plateau
    ≥3 consecutive steps, entrywise resolution-aware tolerance), on enough smooth states (coverage rule);
 4. hidden-state gate passed (incl. uninitialised-variable check);
 5. the evidence is reproducible from a preserved regression case.
Two counts are always reported side by side: routine-level (driver) verification, and Abaqus six-gate verification. The slide
number may cite the routine-level count only if stated so; the Abaqus count is the stronger claim. Family figures are quoted with
the classification's review coverage (142/391 code-reviewed at present; growth largely keyword-only) until a full review exists.

## 2026-10-01 — D-9 (after Scout B2)
- Statuses extended: `inconclusive` (measured but cannot decide, e.g. non-informative primal, differences within the original's own
  reordering noise) and `conflict` (contradictory evidence, both listed). Neither counts as verified or failed.
- `corpus/acquire.py` licence fix moves the transform fingerprint: accepted; `corpus/` stays fingerprinted (not exempted). The store is
  re-frozen once the B2 transformer work settles (pass18).
- frodal__SCMM-hypo licence: correct `companions.json` / `discovered_sources.csv` inputs (GPL-3.0-or-later per cached file) before re-freeze (lead).
- Manifest artifact test must not depend on this machine's paths: unresolvable roots ⇒ explicit skip naming the root (lead/scout).

## 2026-10-01 — D-10 harness fingerprint (lead, after Curie B2 / Atlas B1)
`umat_oti.store.transform_store.harness_fingerprint()` digests `abaqus/` + `corpus_features/`; every verify_store row records it;
`tools/build_corpus_registry.py --harness-fingerprint H` treats rows from another (or no recorded) harness as not current.
pass18 and later registries are built WITH it required. transform_fingerprint value proven unchanged by the refactor.
Test: tests/test_a_verdict_is_current_only_for_the_harness_that_gave_it.py.

## 2026-10-01 — D-11 reporting classification (Santiago's choice)
Family figures are reported against Scout's B3 code-evidence classification, column S1: the 11 Jeff97 files whose growth tensor is
hard-coded to the identity COUNT AS GROWTH (Santiago: "Count inert files as growth"). Eligible denominators: growth 134, plasticity 29,
damage 15, CP 12, linear elastic 13, viscoelastic 11, concrete/geo 14, other 32 (classification: corpus_campaign/batches/B3/scout/families_reviewed_B3.json).
Every quotation of the growth figure carries the footnote: "includes N growth-framework sources whose growth tensor is fixed to the identity
(neo-Hookean response); 105 of the growth denominator come from one author (Jeff97)", with N = how many of those 11 are among the verified.
Open from the review: 5 rows call constitutive routines absent from the cache (sas229 geomat, AlexSTA1993 CAUCHY3D-DP, JuliaFEM drucker_prager,
thelfer tfel castem, ekurth NEML) yet are marked adequately specified — re-examine their eligibility at the next registry re-freeze; any change is reported.

## 2026-10-01 — D-12 undefined behaviour in the ORIGINAL (after Gauss B2: gate trips 33/44)
1. Loading paths stay inside the model's documented domain: total time ≤ the author's deck total time (or a range the source/README
   states); amplitudes within the author's deck where the source is undefined outside it. A path leaving the domain is labelled
   `outside_model_domain` and gives no verdict (BodyForce: G11 undefined for TIME>2.2). Owner: curie (loading_paths).
2. Undefined outputs: outputs (STATEV slots, DDSDDE entries, energies, at given states) that differ between the original compiled with
   SNaN-init and zero-init are `undefined_in_original`: reported as a SOURCE defect with the variable, never compared, never verified.
   The remaining outputs may be verified only if bit-identical across both init builds over the whole history (proof they do not depend
   on the undefined value), and all other gate checks (R/Q/Z replays, isolation probes, bounds) pass. Cells carry
   `undefined_outputs: [...]`. Owner: gauss (harness).
3. For the 206 count (D-8): a source counts only if STRESS and DDSDDE are fully defined on every judged state (no undefined entry there);
   undefined STATEV/energy outputs are disclosed in the footnote. Under review by Vera before any number is reported.

## 2026-10-01 — D-13 contract 4.0.0 (lead)
New EXTERNAL terminal state `undefined_in_original` (D-12, curie_g gate). MAJOR by the contract's own rule (an older reader would misread it
as INTERNAL). UMAT: abaqus/terminal_states.py, contract/{terminal,errors(version external.undefined_in_original),version}.py, schema enums,
x-contract-version 4.0.0 in shared schemas, lock regenerated, tools/corpus_report.py → blocked_with_evidence. RA: schemas/ copies + lock,
tests/contract/contract_reader.py 4.0.0 + EXTERNAL_STATES. UMAT contract/terminal tests 103 pass; RA tests/contract + tests/framework 471 pass.
Under Vera-P review (P6).

## 2026-10-02 — D-14 after Vera B2 combined review (batches/B2/vera/REPORT.md)
Adopted all required changes. Lead done: manifest `_gate_on_definedness` (verified primal/ddsdde with stress_and_ddsdde_fully_defined
false ⇒ inconclusive, counted nowhere); PLAIN["undefined_in_original"]. Gauss (B2c): third init build (+inf/77777/flipped logicals) in
harness and Abaqus init check; zero-valued-parameter step + structural-zero rule; bounded total/Euler atol terms; primal-gate stiffness from
the ORIGINAL with per-row noise floor and bound/max|σ| published. No param-sens or fully-defined count is reported before these land.

## 2026-10-02 — D-15 (after Gauss B2c, corpus_campaign/batches/B2c/gauss.md)
Primal gate: routine-level bound = clip(4 × per-row floor measured on the original with 1-ulp input perturbations, 2, 64) ulpK, stiffness
min(builds) capped by the original's history max; Jacobian-matched control uses the original's stiffness and the same floor. Gauss disclosed the
1-ulp choice was made after seeing transformed-vs-original differences (not calibrated on them, not blind). fibermorph (959ea637) fails the
Jacobian-matched control (28.2 vs U 19.3) while agreeing at routine level: counted NOT verified (conservative). An FE-level noise floor
(Abaqus rerun of the original with perturbed inputs) is added only if pass18 shows the same pattern on more rows.

## 2026-10-02 — D-16 regression cases (Atlas build, committed 6e35123)
Accepted Atlas's choices: drift floor 1e-3 (error/tolerance) because many frozen errors are exactly 0; primal canary skips paths with
identically zero STRESS; curated CI models' activation amplitude from yield strain. Lemaitre (4705e258) case WITHHELD (moved to
corpus_campaign/batches/B3/withheld_cases/): it was frozen at NTENS=3, the layout Curie showed meaningless; the store transformed it at
NTENS=4 but the harness experiment still drives the pass16 CPS4 manifest — harness must take NTENS from the settled formulation (open).
CI job never run on GitHub (gfortran 13 vs 9.4 round-off unmeasured) — first push will tell.

## 2026-10-02 — D-17 pass18 freeze and routine-harness changes after it
pass18 (commit f7a8194; transform aaf3a9366218cd5f; harness cf9dc354b785672a) is the Abaqus evidence. Its registry is built with
--store-fingerprint aaf3a9366218cd5f --harness-fingerprint cf9dc354b785672a (the values its rows recorded). Changes to corpus_features
after pass18 do not affect those rows: nothing on the Abaqus verification path imports corpus_features (abaqus/replay.py and
tools/verify_store_in_abaqus.py mention it only in comments; checked 2026-10-02). Routine-level cells carry their own run_id and
transformer fingerprint. The next Abaqus pass records the then-current harness fingerprint.
Routine-level D-8 count after pass18: 88 eligible (growth 81, elastic 3, visco 1, other 3, others 0); Abaqus six-gate 67.
17 growth sources are inconclusive at routine level only because the driver passes COORDS = 0 to position-dependent growth laws
(Jeff97 circular plate/shell/conformal, mholla BMMB24) — a driver artefact, being fixed (run at an integration point of the author's deck).

## 2026-10-02 — D-18 which harness run decides each feature (after Gauss B5)
The routine-level driver runs all perturbations of a path in ONE process, so an original that STOPs under one perturbation (RitioL: PROPS(57)+h)
ends every column queued after it. Whether DDSDDE can be judged therefore depended on which OTHER features were requested — an artefact of
batching, not of the tangent. Decision: primal_stress_state and ddsdde cells come from the primal+ddsdde run (pass19_harness/run, own
hidden-state gate); parameter/state-sensitivity cells from the full-feature run (pass19_harness_full + rerun3c). Splitting perturbations across
processes (resume after a STOP) is NOT adopted: it would spread hidden-state evidence over processes; revisit only with a design Vera reviews.

## 2026-10-02 — D-19 material data published outside decks counts (Santiago)
Santiago's decision on the pending question: material constants that the author published outside an input deck count as adequate material data,
with their provenance recorded. Sources are the author's paper, README, code comments, example or test files in the same repository, or a cited dataset.
Every constant records where it came from (URL or path at the pinned commit, line or page, a verbatim quote) and how confident the reading is.
Constants that are guessed, typical or taken from the literature for "a similar material" do NOT count. Sources whose constants are
author-published outside a deck are counted in their own stage ("author-published, outside deck"), so the deck-only figures stay reportable. Where a source has no author deck,
the experiment is a council-designed deck inside the author's documented domain (design by Curie, reviewed by Vera).

## 2026-10-02 — D-20 commit and push verified progress (Santiago)
Every batch that adds verified results (Abaqus or routine-level), after Vera's review, is committed and pushed: final-umat and final-ra branch
`corpus/robustness-2026-10-01` to the GitHub repositories (public), and the council repo. Pushing does not bypass D-2: nothing whose licence
does not permit redistribution may be in a pushed tree; Vera checks this before every push.

## 2026-10-02 — D-21 council-chosen material constants (Santiago)
Santiago amends D-19: where the author published no usable constants, the council may choose them. Curie chooses them by physical judgement; when in doubt she asks Scout to look up published values for the material class the code names (alloy, FCC metal, soil, tissue…), with provenance.
Conditions:
1. A written selection rule per family (Curie, reviewed by Vera) is fixed BEFORE any comparison runs. Values are never re-picked after a verdict.
2. The constants must activate the mechanism the code implements (yield, damage onset, hardening, rate effect, growth). The informativeness gates and D-19a R4 apply unchanged.
3. Each source gets ≥2 independent parameter sets. It counts as verified only if every set passes; any failure stands.
4. Values stay inside the model's validity: positive definite elasticity, ν < 0.5, no error or STOP branches, units consistent with the code.
5. Orientation and other "material data by default" inputs (Q2 ruling) may now be council-chosen under this decision, recorded the same way.
6. Reported as its own tier, material_data_origin = council_chosen, beside the author-deck and author-published-outside-deck tiers. Every figure states the split.
Rationale: verification compares transformed and original code on identical inputs. The constants need to be admissible and informative, not the author's own. The tier split keeps the provenance claim honest.

## 2026-10-02 — D-21a acceptance of the D-21 selection rule, and rulings (Vera review; lead)
**Rule.** The D-21 selection rule is accepted with changes. The version Vera reviewed has sha256 73db38cb2be9da0a942167864aa49ae28a630f3b61ed6b3f3ac0983eaa25b5f0 (corpus_campaign/material_data/d21_selection_rule.json). It is NOT yet the frozen value: the rule, its amendment file (R-1..R-8) and the constants file are frozen together, after Curie applies every amendment and Vera re-checks, before the first comparison. (Corrected after Vera's addendum.)
- Changes R-1..R-6 live in a separate amendment file with its own sha, which Vera reviews before the first comparison:
  - R-1: documented parameter restrictions are hard constraints.
  - R-2: author-kept constants are exempt from the G4 move rule.
  - R-3: label `author-other-context` is split from `looked-up`.
  - R-4: a publication-attributed value stands only once verified.
  - R-5: CELENT, 3D-only formulations and KINC==1 STATEV resets are recorded per row.
  - R-6: amendments live outside the frozen file.
- The constants file is re-frozen after the row fixes, before any comparison.

**Rulings.**
- (a) Growth total time stays loading data, except as follows (lead decision, on Vera's recommendation). A council total time is allowed when θ_g depends on time only through time/τ with τ a PROPS constant, and the law is defined and bounded for all t ≥ 0. It is recorded as loading_origin=council_choice with T/τ. glu46 Cube may clear R2 via the README-documented geometry; glu46 Column stays refused.
- (b) The author's LHS design points are acceptable as council_chosen designations (corner rule fixed in advance; verbatim values; BC2_60cc counts once).
- (c) The author's other fits are acceptable as council class values, labelled author-other-context and counted only in the council tier.
- (d) A source with write-only STATEV (static and dynamic proof) is classed "elastic with output state". Deterministic NaN in the original is listed under undefined_outputs (nan_in_original) and never compared.
- (e) Static-scan false positives may be cleared by a machine-readable static_scan_override, with static and dynamic evidence, accepted by Vera per instance and re-checked every pass.

**Licence.** marioruiarruda Hashin and Mazars state "all rights reserved … no part may be reproduced or used in any manner without written permission". They are excluded from verification and counting until Santiago decides (default: excluded).

## 2026-10-02 — D-21b freeze of the D-21 council-chosen constants (Vera)
**Frozen:**
- rule 73db38cb2be9da0a942167864aa49ae28a630f3b61ed6b3f3ac0983eaa25b5f0
- amendment f818e9d45fd1f86d2780223094bdaf0fada221c9f06fa6cef754e4f771ab5bf8
- constants 6b0ed48d654a43aaef068d3d397100fecfcb19be07396ee123a89db3d156b758 (34 rows)
- built by build_d21.py 85245a709595654844f28da8b7637e5b8301f86c5a0d85c4f9cd8959e96b5c1e

All files are in corpus_campaign/material_data/. No comparison had run at freeze time.

**Conditions:**
- Any later change comes as a numbered amendment with a new constants sha, before the affected row's first comparison (e.g. an L-EC2-1 correction).
- CANEY counts only after the five-band dynamic run (bit-identical STRESS/DDSDDE/STATEV). baw-de counts only after its TEMP = 0/500 run.
- Not counting until resolved:
  - Hashin/Mazars: licence hold;
  - glu46 Column: refused under R2;
  - Cube: until its harvest geometry is in;
  - compile- and helper-blocked rows;
  - BC2_60cc: duplicate.
- Every row needs Vera acceptance of its template and instance (R6.5).

## 2026-10-02 — D-21c amendment 2 (formulation statements) accepted; new joint freeze (Vera)
**Freeze (replaces D-21b's freeze line):**
- rule 73db38cb2be9da0a942167864aa49ae28a630f3b61ed6b3f3ac0983eaa25b5f0
- amendment 1 f818e9d45fd1f86d2780223094bdaf0fada221c9f06fa6cef754e4f771ab5bf8
- amendment 2 2c0e93222bb62565a8ed4dcb0258ddb5383fc50e18f9d693eea3b52014348919
- constants 35326c2e7ddb93068c168787980301bb2db827cd78bc017eff94706410bac88a
- built by build_d21.py 32d50da574159a19bbdf8b2c0a85cd780e7e4f6d58bb6bb6aca85262bb63c037

All D-21b conditions still apply.

**R-10.** A formulation is stated only with quoted code evidence; for a branching code the general 3D branch is chosen. This is legitimate under D-19's council-designed deck within the documented domain.

**Conditions:**
- For branching rows, every cell and figure says "verified on the 3D branch (NTENS=6); the plane branch was not exercised", naming the branch:
  - Mohr-Coulomb: nsigma==4;
  - Hashin and Mazars: ndi<3;
  - Leonov: NTENS==4.
- The choice is never re-picked. A plane-branch experiment would be a separate later amendment.
- NLGEOM is unchanged.

The PlatypusBytes MohrCoulomb harvest row records 3D-only (d19_harvest.jsonl 9de30ef1…).

## 2026-10-03 — D-17 superseded by G10 (lead)
The Abaqus D-4 tangent gate (G10) imports corpus_features.fd. Abaqus rows therefore DO depend on corpus_features code from G10 onward. The harness fingerprint, which covers abaqus and corpus_features, is the governing identity for both Abaqus and routine-level rows. D-17's "Abaqus rows unaffected by corpus_features changes" applies only to passes before G10.

## 2026-10-03 — D-22 hold-out selection rules R-H1, R-H2 (Vera)
**R-H1.** A pick counts only if its source_id is fully_verified at the pass the hold-out runs on. A pick that is not leaves the selection. It is replaced only if the family falls below 5 picks AND its pool was stratified (more than 5 candidates). The replacement is the next candidate in the same owner's recorded seeded order (seed 20261003), else the next owner. Other picks are never redrawn.

**R-H2.** A pick tests the template only if every input its council plan needs comes from the template's own rules, fixed before any run. A reviewed rule reading the author's documented geometry (G12 placement) is valid. An input copied from the author's deck that no template rule decides (e.g. a TEMP or growth-field history), or an input the template refuses, is not. Such a pick leaves as "not a template test", with replacement only under R-H1.

**Applied at pass21:**
- growth 6: PureGrowth, Growth-frac, Worlthen simplified_curing, abuganza Iso_Example, mholla iso_morph, mholla iso_stretch. keisuke58 phase2 leaves (R-H1), visco_2ch leaves (R-H2).
- hyperelasticity 2: mholla transverse, Sina CompresibleNeoHookean. BMMB24 leaves (R-H1). holdout_possible stays false.
- Other templates unchanged.

**Conditions:**
- PureGrowth's placement comes from the author's mesh, with no zero coordinate, and NOEL/NPT within ReadDetF bounds. STATEV(7) is unassigned and goes in undefined_outputs.
- The reviewed TEMP/COORDS scan (corpus_campaign/holdout/reviewed_scan.jsonl): all 10 rows Vera-accepted.

## 2026-10-06 — D-23 known limitation: AD through an eigen-solver at a degenerate spectrum (Ada B10)
Differentiating through a Jacobi/eigen routine (DSYEVJ3 and similar, lifted unchanged) is ill-conditioned when the spectrum is exactly repeated and the off-diagonal is below the rounding resolution of the repeated eigenvalue. The lifted derivative is the exact derivative of the algorithm, which blows up (measured: correct at off-diagonal 1e-6, 2.625 vs 2.718 at 1e-15, 0 at 1e-30, −1.7e38 at 1e-54), while finite differences of the original stay correct because the composite is smooth. Only gap-perturbing derivative directions are damaged; d/d(off-diagonal) stays exact.
- This is not a transformer defect: the real parts of the original and the lifted routine agree bit for bit (2240 matrices).
- It explains thealanjason 3EL's job-level NaN (a tangent with zero shear stiffness, then ~1e123). It does NOT explain the routine-level 1.09× marginal disagreement, which is round-off in near-zero off-diagonals.
- 29 stored sources lift an eigen-type routine; none is counted. The dsyevj3 ones: thealanjason 1EL/2EL/3EL (plus copies), MechMater visco and viscohybrid, lbrassart.
- No general transform-level fix exists. Dropping the derivative of a negligible rotation or substituting an analytic eigenvalue rule would change generated code for every user of these routines, so it requires a council decision.
- Any count that includes such a source must carry this limitation. Gauss's earlier remark that the lifted routine "fails to converge on most calls" was wrong: the non-convergence is the author's routine on NaN input.
- Possible follow-up (harness, not done): flag a tangent with zero or non-finite entries as "derivative ill-conditioned (repeated eigenvalues)".

## 2026-10-06 — D-24 the project's reference UMATs cannot validate a hold-out template (Vera)
The project's own reference UMATs (final-umat parameter_sensitivity/models; ravi_package_v2) cannot serve as the author-deck side of a hold-out under D-22:
- they are not in the corpus registry or the 242 eligible (R-H1, D-8);
- we wrote the models, the council plans and the harness, so reproducing their verdicts shows self-consistency, not independence;
- the set is chosen because it verifies, so it cannot be blind;
- R-H2 cannot be ruled out where we wrote both sides.
They may be run as an "internal calibration set, not independent; template not validated per D-22" (≥5 per family: plasticity and elasticity only), with plan inputs and template rules hash-frozen and Vera-reviewed before any run, and Vera signing that no rule changed after the first comparison. They never enter D-8, D-11 or the 242 denominator.
Routes by which a non-growth template can be validated: (a) the family reaches ≥5 fully_verified author-deck sources in the corpus pool (the seeded stratified draw is then rerun); (b) Santiago widens D-22 to externally and independently authored non-corpus UMATs, which must exclude anything the project wrote and needs its own acceptance rule.
Effect: council rows count only in growth. Every other family reports its council rows in a separate "template not validated" column.

## 2026-10-06 — D-25 growth template accepted; three council instances accepted with conditions (Vera R6.5)
**Template growth-morphoelasticity: ACCEPTED WITH CONDITIONS.** Hold-out: 5 picks (PureGrowth, Growth-frac, Worlthen simplified_curing, abuganza Iso_Example, mholla iso_stretch), all agreeing at routine level, at ec609ab41bb45a02. A routine-only hold-out validates the template for a routine-level count. No council row is Abaqus-verified (the Abaqus route is not wired for council manifests).
Not shown by the hold-out, to be stated on every quote:
- the hold-out uses the author deck's constants, so it validates the experiment design, placement and plan, not the D-21 council-chosen constants (Q4: inputs not independent);
- the council total-time rule D-21a(a) (3τ) is reviewed, not hold-out tested;
- exactly 5 picks, no margin;
- Iso_Example's agreement is on the cells both sides produce (its DDSDDE is not fully defined).

**Instances (mholla fiber_morph_Abaqus 9268105c, area_morph_Abaqus c2624232, iso_morph_Abaqus sha 4432ac86): ACCEPTED WITH CONDITIONS.**
- Distinct from every counted source. umat_iso_morph.f (e2bbc942, the author-deck row and hold-out pick, θ = 1 + α·t) is a different file and law.
- Constants admissible and informative (growth ≈47% in set A, ≈19% in set B, against the 1% gate).
- The count is 3 once these are recorded, and 0 until then:
  1. The static-scan override (D-21a(e)) needs its dynamic evidence: one rerun per instance with COORDS and NOEL changed gives bit-identical STRESS, DDSDDE and STATEV.
  2. The three rows are not independent (same repository, constants, exponential law and plan template): one model class in three direction variants.
  3. fiber_morph's state_param_sens_local/total failures on objectivity_rotated and objectivity_rotated_fine (both sets, ratio ~3e12), the same paths on which the author-deck sibling umat_area_morph.f fails: disclose as "failed, cause not examined" until diagnosed. area_morph set B has sensitivities not_attempted on 3 paths (insufficient coverage): state it.
  4. D-2: no mholla source text in any shipped case or tree.
  5. The plan's path text for the 3τ rule says "taken from the author's own constants"; it should say council-chosen. The constants file basis says "council total time 1.0" but the plan runs 0.75 for set A: record this in a note.
- Symlink view (plans_by_registry_key): no effect on evidence integrity (51 links checked); record the registry-key lookup in the evidence file.

**Quotation form.** A separate tier, never summed with D-8 (114) or D-4 (106): "council_chosen, routine level, growth template validated (hold-out of 5 at pass23, ec609ab41bb45a02): 3 sources, each verified on 2 council constant sets over every path". With: not Abaqus-verified; constants and loading are the council's; D-21a(a) is reviewed, not hold-out tested; the hold-out used the authors' constants; three same-class rows; the fiber_morph disclosure. Growth only: "validated" is not extended to any other family.
**Other families (~42 ready rows):** run as "council, template not validated, uncounted" at the same fingerprints; every outcome reported including failures; never in any table carrying counts or Fisher tests.

## 2026-10-06 — D-26 fiber_morph / area_morph structural-zero failures: disclosure and deferred rule (Vera, Curie)
**Diagnosis (accepted).** Every listed failure is state_param_sens, output SDV3 (detFe), with respect to a direction component n0_i that is exactly 0.0 in the constants. detFe depends on n0 only through |n0|, so the analytic derivative detF·c·n0_i/|n0| is exactly 0. OTI returns 7e-19 to 4e-17 (about 0.2 eps for an output of order 1) against an exact-zero FD, and the tolerance, built from the quad FD scale, is about 1e-29. Unrotated paths give an exact 0.0. Objectivity holds (|σ(QF) − Qσ(F)Qᵀ| = 1.7e-16). Nonzero components pass against FD. The author-deck sibling umat_area_morph.f fails on the same kind of entries (PROPS(3), PROPS(4) = 0). Not a derivative error; a judge-tolerance artefact.
**Disclosure text (cell status stays `failed`):** "failed on structural-zero entries at double-precision round-off: d SDV3/d n0_i with n0_i exactly 0 in the constants; OTI 7e-19 to 4e-17 (about 0.2 eps) against an exact-zero FD; the analytic derivative is exactly 0 (detF·c·n0_i/|n0|); every listed failure is of this kind and nonzero components pass against FD; not a derivative error. Judged on the objectivity_rotated and objectivity_rotated_fine paths only; unrotated paths give an exact 0.0. The author-deck sibling umat_area_morph.f fails on the same entries."
**Condition before "every":** the fine paths list only 20 of 60 and 20 of 37 failures; confirm from the evidence directory that the unlisted 40 and 17 are of the same kind.
**Fix deferred** to the next harness revision (a change in fingerprint-covered code restarts R7 step 3 for no change in any counted figure). The rule then: apply only when the FD reference is exactly 0.0 at every ladder step (≥3), the input component is exactly 0.0 and the output is a scalar function of the whole input group; floor = c·eps·S with S from the build's own magnitudes (|output| and the largest |D| in the same output row), c fixed in advance (≈8) and not tuned on these rows; one state above the floor is a real failure; report as a separate code (e.g. roundoff_zero_pass), never merged into `pass`; canaries: an OTI value wrong by 1e-13·|out| on a structural-zero entry still fails, and a dropped derivative on a nonzero component still fails; never applies when the FD reference is nonzero.

## 2026-10-06 — D-27 growth council tier: three instances accepted; count 3 (Vera)
D-25 conditions are closed:
- Static-scan overrides ACCEPTED for mholla fiber_morph_Abaqus (f7cf3fbb8a406175021bac55), area_morph_Abaqus (4698392c1e21de908d263766) and iso_morph_Abaqus (c93bec59911b82272a1f7d48). The dynamic evidence (Gauss, run_dynamic.py): STRESS, DDSDDE and STATEV bit-identical for every path of both sets over 6 variants (COORDS inside the unit cube and far away, NOEL 17 and 40321, NPT 8, and all three together); 220/220/240 increments per set; with a positive control that flags a UMAT reading COORDS, NOEL or NPT. It runs the ORIGINAL routine, not the OTI build. The harness's in-pass recheck covers COORDS and TEMP only: the NOEL/NPT coverage rests on this evidence file (deferred list).
- D-26 disclosure: for fiber_morph the word "every" is justified. Re-run with the failure cap lifted: all 115 failing entries (set A rotated 12, fine 60; set B rotated 6, fine 37) have FD exactly 0.0 and |OTI| ≤ 4.2e-17. For the umat_area_morph.f sibling say "every listed".
**Count: 3** — "council_chosen, routine level, growth template validated (hold-out of 5 at pass23, ec609ab41bb45a02): 3 sources, each verified on 2 council constant sets over every path". Never summed with 114 (D-8) or 106 (D-4); with every D-25 statement.
**Open condition before the council cells enter the manifest or any evidence is published:** the council evidence locators contain `#A`/`#B` in the folder name, and `#` is the fragment separator, so the path part does not resolve to a file (the harness merge validator reports "evidence … does not resolve to a file"). Write the set folders and locators without `#` (e.g. `_A`) in a post-processing step, or amend the locator rule, and re-run the merge validator. The count is unaffected (the registry computes it from the cells).

## 2026-10-06 — D-27a corrections to D-26/D-27 (Vera sign-off)
- The D-26 failure text belongs to fiber_morph and to the author-deck sibling umat_area_morph.f. It does NOT belong to the council row umat_area_morph_Abaqus.f (4698392c), which has no failed cell (set A 10/10 verified; set B 7 verified, 3 not_attempted: elastic_uniaxial, elastic_shear and growth_free, insufficient coverage, 1 of 20 states judged). The earlier wording "umat_area_morph.f sibling" was ambiguous and was misapplied to the council row.
- The recorded noise range is 1e-19 to 4e-17, not 7e-19 to 4e-17.
- "every failure (115 of 115)" for fiber_morph requires a stored rerun (failure cap lifted) beside the sidecar; until it is stored, "every listed".
- The locator copy (ad22b08, pushed) is faithful (48/48 byte-identical). The merge check proves only that each file resolves; the `&set=A` selector form is new and unchecked by any tool (checked by hand for the 12 cells). Only the 12 rewritten primal+ddsdde cells are cleared to merge; the full-run sensitivity cells still carry `#` locators.
- (D-27a, later the same day) The council area_morph_Abaqus set B sensitivities: the stored evidence governs. stress_param_sens local/total are not_attempted on elastic_uniaxial, elastic_shear and growth_free (1 of 20 states judged each); state_param_sens local/total are not_attempted on elastic_shear (2 of 20), growth_free (1 of 20) and finite_simple_shear (1 of 10), with elastic_uniaxial verified (20 of 20). The shorthand "not_attempted on 3 paths" was imprecise for the state sensitivities. fiber_morph: the uncapped rerun is stored (115 of 115 failures; FD exactly 0.0; |OTI| 1.09e-19 to 4.16e-17), so "every failure" is supported.

## 2026-10-06 — D-28 rules for raising the count: nothing loosens a counted gate without a separate line (Vera B11)
**General rule.** A change to what a counted gate means, made after the sources it frees are known, is post hoc. It is legitimate only if (1) the rule is written down before it is run, (2) it is applied to all sources (all 405, including the ones that already pass), and (3) it is reported as a SEPARATE line beside the published figure and never replaces it. Planning figures (Atlas's 132 and 147) are estimates and are not quoted; only measured counts are.
1. **Informativeness by response character: NOT LEGITIMATE as a change to the counted gate.** Five of the nine rows have a never-computed gate (null); the pass21 ruling excluded exactly this kind of row. Legitimate: compute the existing gate where it was null (a tooling defect); if it reads true under the unchanged rule the row counts under D-4. A new criterion for rows still experiment_not_informative goes on a separate line, labelled "D-4, response-character informativeness (rule revised after the run)", written first and validated with a planted-error canary, applied to every source, never summed into 106.
2. **Promoted-precision (REAL*8) variant as a reference: NOT LEGITIMATE** (consistent with B32-3: agreement with it is unresolved_binary32, never a pass). It may be reported in a separate column "agrees with a double-precision rebuild", in no headline count (D-4, D-8, RA). **Float32-aware primal bound: legitimate with conditions**, as a unit correction only: the floor is measured on the original in its own working precision, fixed before looking at the failing 1.1–2.7× ratios, re-run on every float32 row including those that pass, with before-and-after, a planted float32-sized error that must still fail, and the hypothesis that the 8 growth rows are float32 originals confirmed first. The rows stay tangent_not_verified.
3. **Benign NINT truncation (4 CPFEM sources): legitimate with conditions.** REAL(NINT(REAL(x))) is piecewise constant (derivative zero almost everywhere). The detector matches that exact pattern and the value feeds only an integer (loop bound or index); the row still must pass the ordinary D-4 tangent gate on its own evidence; planted canary: REAL of a differentiated quantity used in the stress must still be flagged and the three abuganza rows and UVCmultiaxial must stay derivative_truncated; footnote "NINT read-back, derivative exactly zero a.e."; a separate line until the detector is validated.
4. **Re-classing sources with unpublished callees or modules as external_dependency_unavailable: legitimate as a correction of the adequacy test** (it checked only USE and INCLUDE). Apply it to all 405 sources (sources can enter as well as leave), after the callee lookup, with one rule in both places (a callee is published only if it is in the repository at the pinned commit, in a published companion, or a documented Abaqus utility; a source leaves only after the full lookup fails and Scout confirms). Never replace 242: publish both "106 of 242 (as published)" and "106 of 242 − k (revised adequacy test, k named in an appendix with evidence)", recompute the ceiling and the family targets, and state that the pass count did not change, only the denominator.
**Hidden rule changes in the ranked fixes (each needs a canary and a re-run on all rows, with disclosure):**
- the D-12 probe built with the source's own compiler (re-run D-12 on all rows and report any newly undefined row);
- treating I/O-only callees as inert and skipping promotion of inactive variables (static plus dynamic evidence as for the console silencing, plus a planted-derivative canary);
- finding the UMAT interface by argument position (apply symmetrically; no not_a_umat row may leave wrongly);
- RA: seeding only differentiable PROPS slots (the cell says "verified on the differentiable slots; integer slots excluded");
- RA: locking the cutback schedule of the ±h re-solves (same schedule for the original and the lifted solve; disclosed). A coverage rule of "accept at least X% resolved with 0 failed" is NOT LEGITIMATE (unresolved is not verified).
- Transforming at the element's NTENS is a correctness fix, legitimate if applied to every row. The callee lookup is fine if it adds only files published at the pinned commit and obeys D-2.
