#!/usr/bin/env python
"""Run the repository benchmark over one or more local models.

python scripts/local/benchmark.py --models qwen2.5-coder:7b qwen2.5-coder:1.5b
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from council_local.bench.cases import build_cases  # noqa: E402
from council_local.bench.run import run_benchmark, write_report  # noqa: E402
from council_local.runtime import Server  # noqa: E402


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen2.5-coder:7b"])
    parser.add_argument(
        "--limit", type=int, default=24, help="source files to sample (each yields several cases)"
    )
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parents[2] / "evaluations/local"
    )
    args = parser.parse_args(argv)

    server = Server().start()
    cases = build_cases(limit=args.limit)
    print(f"{len(cases)} cases over {len({c.path for c in cases})} files", flush=True)

    results = []
    for model in args.models:
        print(f"\n=== {model} ===", flush=True)

        def progress(index, total, case, _model=model):
            print(f"  [{index:3d}/{total}] {case.task:24} {case.path.name[:46]}", flush=True)

        result = run_benchmark(model=model, cases=cases, server=server, progress=progress)
        results.append(result)
        print(
            f"  -> {result.summary.get('accuracy', 0):.1%} accuracy, "
            f"{result.summary.get('seconds_per_case', 0):.1f}s/case, "
            f"{len(result.failures)} failures",
            flush=True,
        )
        # Free VRAM before the next tier loads; 8 GiB does not hold two.
        try:
            server.unload(model)
        except OSError:
            pass

    path = write_report(results, args.out)
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
