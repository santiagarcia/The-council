# nasa-stri-weekly-2026-10-23 retrospective

Three review rounds on a weekly research deck (21 Oct 2026). Members were emulated by general-purpose subagents given their `council dispatch` packets, because the native agents were not loadable in this host. Nico's cold reads used one Read of an isolated packet under instruction-level isolation. Detailed reviews are kept outside this public repository.

## Expected and actual
- Expected the domain reviews (Noether, Gauss, Curie, Iris) to catch most problems. They caught the technical ones. Nico's text-only cold read still found a wrong causal word in a headline and dangling references. Vera found overreaching conclusions and zero-versus-zero passes counted as validated.
- Expected a verified "validated" status to mean every listed output was compared. One output column was zero for every parameter, so it had not been compared.

## Reusable lessons (proposed, not adopted)
1. Freeze the PDF and its hash before the final review, and do not rebuild until the review returns (Vera).
2. Before trusting "N of N validated", count the cases where both sides are exactly zero and report them separately (Gauss, Vera).
3. A column that is identically zero for every parameter, including active ones, means the field was not compared (Gauss).
4. Take mean relative errors only over components with a nonzero reference. Show zero-reference cases as an absolute difference (Gauss).
5. When per-call cost times call count does not reproduce a measured ratio, look for calls hidden inside a wrapper before trusting either number (Iris).
6. Label any bar that is computed rather than timed as derived, and state its formula (Iris).
7. Trace pass and call counts to the benchmarked commit. If the commit is unreachable, say "measured, not traceable" (Ada).
8. Regenerate the cold-read text after every rebuild, and give Nico figure titles and axis labels, since he cannot see figures (Ada, Nico).
9. Check a parameter's role in the implementation, not its textbook role (Curie).
10. Scope a conclusion to what was demonstrated. One documented library does not establish arbitrary compiled objects (Vera).

## Limitations
Emulated members, one project, one author. Each lesson needs an independent reviewer before promotion.
