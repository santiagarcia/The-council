# Pilot: six corpus sources, one per situation

`qwen2.5-coder:7b`, 2026-09-30. Run with `scripts/local/pilot.py`. Raw result
in `pilot.json`.

The batch is chosen, not sampled: one source already verified, one whose
transform is refused, one with an unresolved dependency, one multi-file, one
with unclear metadata, and one that is not a UMAT at all.

| situation | source | registry state |
| --- | --- | --- |
| already verified | `NeoHookean_umat.for` | `fully_verified` |
| transform refused | `hyplast_Cauchy3D-DP.for` | `transform_refused` |
| unresolved dependency | `Diffusion_3D.for` | `external_dependency_unavailable` |
| multi-file | `umat_DP_primal_CPPM_def.f90` | `not_a_umat` |
| unclear metadata | `UMAT_ABAQUS_ELASTIC.f` | `missing_material_data` |
| not a UMAT | `plasticity_xx15.F90` | `not_a_umat` |

## Result

**Agreement with the registry: 63.9 % over 36 scoreable fields. Claude was
still needed on 22 of them.** Eighteen task calls took 10 min 40 s in all,
about 36 s each.

Two calls failed the schema outright and returned an envelope saying so. Seven
of eighteen escalated themselves as under-evidenced. Nothing was returned
silently empty.

## What the pilot found that the benchmark did not

**A false compile failure in the harness.** Four of the six sources failed the
sandboxed syntax check at **column 72** — gfortran truncates fixed-form source
there by default, and real UMATs run past it constantly. The compile line
lifted the free-form limit and not the fixed-form one. With
`-ffixed-line-length-none` the same six go from **2 of 6 compiling to 4 of 6**,
and the two that still fail do so for a real reason: `USE precision` naming a
module that is genuinely not in the cache, which is exactly what the registry
records for them.

This is the failure mode worth naming. The check was reporting a syntax error,
at a specific line and column, for valid code — a result that reads like a
finding and is an artefact of the tool. It would have been invisible in an
aggregate pass rate.

**A cost that was being reported as zero.** A call that fails the schema still
spends the time it spent failing, and a retry spends it twice. Those were
recorded as `0.0s`, understating the price of the answers that never arrive.
Both are fixed, with regression tests.

## Where Claude was still needed

Twenty-two items, in three kinds:

- **the model disagreed with the registry** on a field the registry records —
  most often `entry_line`, the weakest field in the benchmark at 30.4 %;
- **the answer escalated itself** as under-evidenced, which is the system
  working;
- **two schema failures**, which are unusable by construction.

None of the twenty-two was a case where the model was confidently wrong and
the envelope looked fine. That is the failure this design exists to prevent,
and it did not occur in this batch — six sources is not enough to call it
absent.
