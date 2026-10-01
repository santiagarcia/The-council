"""A benchmark built from this project's own verified results, not a public set.

Generic coding benchmarks say nothing about whether a model can read a 1987
fixed-form UMAT and report its PROPS count. This suite scores against the
corpus registry, which carries a pipeline-established label for 391 acquired
sources: `is_umat` on 346, `entry_line` on 386, `source_form` on all 391,
`ntens` on 321, and a refusal class on 151.

That makes the score objective and the ceiling honest: a model is measured
against what the project already knows to be true, so a model that scores well
is a model that can be trusted with the cases nobody has checked yet.
"""

from .cases import Case, build_cases, load_registry
from .run import BenchResult, run_benchmark
from .score import ScoredCase, score_case

__all__ = [
    "Case",
    "build_cases",
    "load_registry",
    "ScoredCase",
    "score_case",
    "BenchResult",
    "run_benchmark",
]
