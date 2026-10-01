#!/usr/bin/env python
"""A controlled pilot over a deliberately diverse handful of corpus sources.

Not a corpus sweep. The batch is chosen to include the cases that break
things: a straightforward model, a multi-file one, one with an unresolved
dependency, one whose transformation currently fails, one whose metadata is
unclear, and one already verified so there is a known-good answer in the set.

Every conclusion is compared with what the registry already established, and
the report says where Claude was still needed.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from council_local.bench.cases import CACHE, Case, _truth_for, load_registry  # noqa: E402
from council_local.bench.score import score_case  # noqa: E402
from council_local.client import LocalClient  # noqa: E402
from council_local.learning import Lesson, record_proposal  # noqa: E402
from council_local.policy import Policy  # noqa: E402
from council_local.runtime import Server  # noqa: E402
from council_local.sandbox import syntax_check  # noqa: E402
from council_local.tasks import TASKS  # noqa: E402

#: One source per situation we want represented, picked by registry state.
WANTED = [
    ("already verified", lambda r: r.get("terminal_state") == "fully_verified"),
    ("transform refused", lambda r: r.get("terminal_state") == "transform_refused"),
    (
        "unresolved dependency",
        lambda r: r.get("terminal_state") == "external_dependency_unavailable",
    ),
    ("multi-file", lambda r: bool(r.get("companion_files"))),
    ("unclear metadata", lambda r: r.get("is_umat") is None or not r.get("props_count")),
    ("not a UMAT", lambda r: r.get("terminal_state") == "not_a_umat"),
]


def _resolve(record):
    raw = record.get("cache_path") or ""
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = CACHE / raw
    return path if path.is_file() else None


def choose(records):
    """One record per wanted situation, never the same file twice."""
    chosen, seen = [], set()
    for label, predicate in WANTED:
        for record in records:
            if record["source_id"] in seen:
                continue
            path = _resolve(record)
            if path is None or not predicate(record):
                continue
            chosen.append((label, record, path))
            seen.add(record["source_id"])
            break
    return chosen


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parents[2] / "evaluations/local"
    )
    args = parser.parse_args(argv)

    server = Server().start()
    client = LocalClient(server=server, model=args.model)
    batch = choose(load_registry())
    print(f"pilot batch: {len(batch)} sources\n")

    report = {
        "model": args.model,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sources": [],
        "claude_still_needed": [],
        "totals": {},
    }
    agreed = disagreed = escalated = 0
    started = time.time()

    for label, record, path in batch:
        print(f"--- {label}: {path.name}")
        entry = {
            "situation": label,
            "source_id": record["source_id"],
            "registry_state": record.get("terminal_state"),
            "tasks": {},
        }
        policy = Policy.load(path.parent)
        for task in ("classify_umat", "extract_umat_contract", "detect_dependencies"):
            try:
                envelope = TASKS[task](path, policy=policy, client=client)
            except Exception as error:
                entry["tasks"][task] = {"error": f"{type(error).__name__}: {error}"}
                report["claude_still_needed"].append(
                    {"source": record["source_id"], "task": task, "why": "task raised"}
                )
                continue
            truth, scoreable = _truth_for(task, record)
            row = {
                "answers": envelope.answers,
                "grounded": round(envelope.grounded_fraction, 2),
                "seconds": envelope.usage.seconds,
                "escalation": envelope.escalation,
            }
            if scoreable:
                scored = score_case(
                    Case(
                        case_id=f"{task}:{record['source_id']}",
                        task=task,
                        path=path,
                        truth=truth,
                        scoreable=scoreable,
                    ),
                    envelope,
                )
                row["scored"] = {
                    "correct": scored.correct,
                    "wrong": scored.wrong,
                    "missing": scored.missing,
                    "details": scored.details,
                }
                agreed += scored.correct
                disagreed += scored.wrong + scored.missing
                for field, detail in scored.details.items():
                    if detail["verdict"] != "correct":
                        report["claude_still_needed"].append(
                            {
                                "source": record["source_id"],
                                "task": task,
                                "why": f"{field}: said {detail['got']!r},"
                                f" registry says {detail['expected']!r}",
                            }
                        )
            if envelope.needs_claude:
                escalated += 1
                report["claude_still_needed"].append(
                    {
                        "source": record["source_id"],
                        "task": task,
                        "why": f"escalated: {envelope.escalation}",
                    }
                )
            entry["tasks"][task] = row
            print(
                f"    {task:24} {envelope.usage.seconds:5.1f}s "
                f"grounded={envelope.grounded_fraction:.0%} {envelope.escalation}"
            )

        sand = syntax_check(path)
        entry["sandboxed_compile"] = {
            "ok": sand.ok,
            "isolated": sand.isolated,
            "isolation": sand.isolation,
            "seconds": sand.seconds,
        }
        print(
            f"    sandboxed compile        {sand.seconds:5.1f}s "
            f"ok={sand.ok} isolated={sand.isolated}"
        )
        report["sources"].append(entry)

    report["totals"] = {
        "sources": len(batch),
        "fields_agreeing_with_registry": agreed,
        "fields_disagreeing": disagreed,
        "agreement": round(agreed / (agreed + disagreed), 3) if agreed + disagreed else 0,
        "escalated_answers": escalated,
        "seconds": round(time.time() - started, 1),
    }

    lesson = Lesson(
        trigger="first local pilot over a diverse corpus batch",
        previous_belief="a 7B local model can replace first-pass corpus triage",
        observation=f"agreement with the registry was "
        f"{report['totals']['agreement']:.0%} over "
        f"{agreed + disagreed} scoreable fields; "
        f"{escalated} answers escalated themselves",
        evidence=["evaluations/local/pilot.json"],
        new_behavioral_rule="delegate only the tasks whose measured agreement clears "
        "the threshold recorded in evaluations/local/benchmark.md",
        scope="corpus triage on this machine",
        verification_test="rerun scripts/local/pilot.py after any prompt change",
        confidence=0.4,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pilot.json").write_text(json.dumps(report, indent=2, default=str))
    proposal = record_proposal(lesson)

    print(
        f"\nagreement with the registry: {report['totals']['agreement']:.1%}"
        f" over {agreed + disagreed} fields"
    )
    print(f"Claude still needed on {len(report['claude_still_needed'])} items")
    print(f"wrote {args.out / 'pilot.json'} and {proposal}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
