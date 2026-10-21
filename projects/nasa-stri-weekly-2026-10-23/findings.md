# nasa-stri-weekly-2026-10-23 findings

Findings about the review process, not about the research. Technical findings stay with the deck, outside this repository.

| Status | Finding | Evidence locator | Limitations |
|---|---|---|---|
| Observed | A verification log marked every parameter "validated" while one output column was zero for every parameter, including the active ones. That column was never compared | Gauss review, round 3 (private records) | One package |
| Observed | Zero-versus-zero cases were counted as passes in "N of N within tolerance" | Vera review, round 3 | One package |
| Observed | A mean error taken over all components was diluted by components whose reference is identically zero | Gauss review, round 3 | One figure set |
| Observed | Per-call cost times pass count did not reconcile with the measured ratio because a wrapper made extra library calls inside each counted call | Iris and Vera reviews, round 3 | One benchmark |
| Observed | The text-only cold read caught a headline that named the wrong cause (solver instead of ordering) and two dangling cross-references that the domain reviewers missed | Nico cold read, round 3 | Instruction-level isolation only |
| Observed | The deck was rebuilt while the final review was running, so the reviewer had to diff two builds | Vera review, round 3 | One round |
| Observed | A parameter read from the input was never used by the implemented update, contrary to its textbook role | Curie review, earlier round | One UMAT |
| Unknown | Whether native Council agents would behave differently from the emulated ones | Not tested, native agents were not loadable in this host | |
