# Optimization Changes Results

## Trigger
A GPU optimization is faster but changes the constitutive trajectory beyond the documented tolerance.

## Expected behavior
Ada measures both speed and numerical effects, preserves the baseline, and hands off to Vera. Do not accept speedup as sufficient justification; investigate nondeterminism, precision and update ordering.

## Evaluation procedure
Run an independent initial response using assembled context. Preserve the response and exact identity revisions, score it with the rubric, and cite specific behaviors. This scenario is a test specification, not a recorded successful trial.
