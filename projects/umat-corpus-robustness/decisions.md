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
Constants that are guessed, typical or taken from the literature for "a similar material" do NOT count. Sources that use such constants are
counted in their own stage ("author-published, outside deck"), so the deck-only figures stay reportable. Where a source has no author deck,
the experiment is a council-designed deck inside the author's documented domain (design by Curie, reviewed by Vera).

## 2026-10-02 — D-20 commit and push verified progress (Santiago)
Every batch that adds verified results (Abaqus or routine-level), after Vera's review, is committed and pushed: final-umat and final-ra branch
`corpus/robustness-2026-10-01` to the GitHub repositories (public), and the council repo. Pushing does not bypass D-2: nothing whose licence
does not permit redistribution may be in a pushed tree; Vera checks this before every push.
