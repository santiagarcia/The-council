"""Benchmark cases drawn from the corpus registry's established labels."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path

WORK = Path("/home/ammslab3/softwarex_work")
REGISTRY = WORK / "final-umat/paper_results/corpus/corpus_registry.json"
CACHE = WORK / "discovery_cache"


@dataclass
class Case:
    """One scoreable task: a file, a task name, and what the truth is."""

    case_id: str
    task: str
    path: Path
    truth: dict
    #: Which truth fields are reliable for this record. A registry field that
    #: is null is unknown, not zero, and must not be scored as a miss.
    scoreable: list[str] = field(default_factory=list)
    family: str = ""
    notes: str = ""


def load_registry(path: Path | str = REGISTRY) -> list[dict]:
    """The 391 acquired records."""
    return json.loads(Path(path).read_text())["records"]


def _resolve(record: dict) -> Path | None:
    """The cached bytes for a record, if they are still on disk."""
    raw = record.get("cache_path") or ""
    if not raw:
        return None
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = CACHE / raw
    return candidate if candidate.is_file() else None


def build_cases(
    *,
    limit: int = 40,
    seed: int = 20260930,
    registry: Path | str = REGISTRY,
    tasks: tuple[str, ...] = ("classify_umat", "extract_umat_contract"),
) -> list[Case]:
    """A stratified sample of cases with known answers.

    Stratified deliberately: a random draw from 391 is 2/3 growth sources from
    three repositories, and a model that only ever sees one author's style
    would be scored on a corpus it will not meet.
    """
    records = load_registry(registry)
    rng = random.Random(seed)
    by_state: dict[str, list[dict]] = {}
    for record in records:
        if _resolve(record) is None:
            continue
        by_state.setdefault(record.get("terminal_state") or "unknown", []).append(record)

    chosen: list[dict] = []
    states = sorted(by_state)
    while len(chosen) < limit and any(by_state[s] for s in states):
        for state in states:
            bucket = by_state[state]
            if not bucket or len(chosen) >= limit:
                continue
            chosen.append(bucket.pop(rng.randrange(len(bucket))))

    cases: list[Case] = []
    for record in chosen:
        path = _resolve(record)
        for task in tasks:
            truth, scoreable = _truth_for(task, record)
            if not scoreable:
                continue
            cases.append(
                Case(
                    case_id=f"{task}:{record['source_id']}",
                    task=task,
                    path=path,
                    truth=truth,
                    scoreable=scoreable,
                    notes=record.get("terminal_state", ""),
                )
            )
    return cases


def _truth_for(task: str, record: dict) -> tuple[dict, list[str]]:
    """The registry's answer for one task, and which fields are known."""
    truth: dict = {}
    if task == "classify_umat":
        if record.get("is_umat") is not None:
            truth["verdict"] = "genuine_umat" if record["is_umat"] else "__not_umat__"
        if record.get("entry_line"):
            truth["entry_line"] = record["entry_line"]
        if record.get("entry_routine"):
            truth["entry_routine"] = record["entry_routine"]
        if record.get("writes_stress") is not None:
            truth["writes_stress"] = bool(record["writes_stress"])
        if record.get("writes_ddsdde") is not None:
            truth["writes_ddsdde"] = bool(record["writes_ddsdde"])
    elif task == "extract_umat_contract":
        if record.get("props_count"):
            truth["max_props_index"] = record["props_count"]
        if record.get("nstatv"):
            truth["max_statev_index"] = record["nstatv"]
        kinematics = (record.get("kinematics") or "").lower()
        if "finite" in kinematics:
            truth["kinematics"] = "finite_strain"
        elif "small" in kinematics or "infinitesimal" in kinematics:
            truth["kinematics"] = "small_strain"
    return truth, sorted(truth)
