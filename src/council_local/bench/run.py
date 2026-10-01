"""Running the benchmark across models and writing the result down."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..client import LocalClient
from ..hardware import inventory
from ..policy import Policy, PolicyRefusal
from ..runtime import Server
from ..tasks import TASKS
from .cases import Case, build_cases
from .score import ScoredCase, aggregate, score_case


@dataclass
class BenchResult:
    """One model's run over the suite."""

    model: str
    started: str = ""
    inventory: dict = field(default_factory=dict)
    scored: list[dict] = field(default_factory=list)
    summary: dict = field(default_factory=dict)
    failures: list[dict] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, default=str)


def run_benchmark(
    *,
    model: str,
    cases: list[Case] | None = None,
    limit: int = 24,
    server: Server | None = None,
    policy: Policy | None = None,
    progress=None,
) -> BenchResult:
    """Score one model over the suite, recording every case's outcome."""
    cases = cases if cases is not None else build_cases(limit=limit)
    server = server or Server()
    client = LocalClient(server=server, model=model)
    inv = inventory()
    result = BenchResult(
        model=model,
        started=time.strftime("%Y-%m-%dT%H:%M:%S"),
        inventory={
            "gpu": inv.gpus[0].name if inv.gpus else "none",
            "vram_mib": inv.vram_mib,
            "backend": inv.gpus[0].likely_backend if inv.gpus else "cpu",
        },
    )
    scored: list[ScoredCase] = []
    for index, case in enumerate(cases, 1):
        if progress:
            progress(index, len(cases), case)
        task = TASKS.get(case.task)
        if task is None:
            result.failures.append({"case": case.case_id, "error": "unknown task"})
            continue
        try:
            envelope = task(case.path, policy=policy, client=client)
        except PolicyRefusal as refusal:
            result.failures.append({"case": case.case_id, "error": f"refused: {refusal}"})
            continue
        except Exception as error:  # a model or IO failure is a measurement
            result.failures.append(
                {"case": case.case_id, "error": f"{type(error).__name__}: {error}"}
            )
            continue
        scored.append(score_case(case, envelope))
    result.scored = [asdict(s) for s in scored]
    result.summary = aggregate(scored)
    return result


def write_report(results: list[BenchResult], out_dir: Path | str) -> Path:
    """Write the JSON and a short Markdown comparison."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for result in results:
        (out_dir / f"bench-{result.model.replace(':', '-')}.json").write_text(result.to_json())
    lines = [
        "# Local model benchmark",
        "",
        "Scored against the corpus registry's established labels.",
        "",
    ]
    head = (
        "| model | cases | fields | accuracy | wrong | missing | hallucinated"
        " citations | schema valid | grounded | s/case |"
    )
    lines += [head, "|" + "---|" * 10]
    for result in results:
        s = result.summary
        if not s:
            continue
        lines.append(
            f"| `{result.model}` | {s['cases']} | {s['fields_scored']} |"
            f" **{s['accuracy']:.1%}** | {s['wrong']} | {s['missing']} |"
            f" {s['hallucination_rate']:.1%} | {s['schema_validity']:.0%} |"
            f" {s['grounded_fraction']:.0%} | {s['seconds_per_case']:.1f} |"
        )
    lines += ["", "## Per task", ""]
    for result in results:
        for task, bucket in (result.summary.get("by_task") or {}).items():
            lines.append(
                f"- `{result.model}` {task}: {bucket['accuracy']:.1%}"
                f" of {bucket['scored']} fields, {bucket['seconds']:.0f}s"
            )
    path = out_dir / "benchmark.md"
    path.write_text("\n".join(lines) + "\n")
    return path
