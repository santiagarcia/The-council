"""The operations Claude may delegate, as plain functions over the envelope.

This is the whole delegation surface. ``mcp_server`` exposes it over stdio and
``scripts/local/delegate.py`` exposes the same functions on the command line,
so the two cannot drift: an operation added here appears in both.

Every operation returns a dict with a ``summary`` -- a few lines -- and a
``detail`` the caller may ignore. That split is the token saving: if a
reviewer has to read the full envelope to decide whether to care, delegating
cost tokens instead of saving them.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

from .bench.cases import build_cases
from .bench.run import run_benchmark
from .client import LocalClient
from .envelope import Envelope
from .hardware import inventory
from .policy import Policy, PolicyRefusal
from .roster import role, roster
from .runtime import Server
from .sandbox import available as sandbox_available
from .sandbox import syntax_check
from .tasks import TASKS

_SERVER: Server | None = None


def _server() -> Server:
    """One server for the process, started on first use."""
    global _SERVER
    if _SERVER is None:
        _SERVER = Server().start()
    return _SERVER


def _client(model: str | None = None) -> LocalClient:
    return LocalClient(server=_server(), model=model or "qwen2.5-coder:7b")


def _result(envelope: Envelope) -> dict:
    """The two-level result every operation returns."""
    return {
        "summary": envelope.summary(),
        "needs_claude": envelope.needs_claude,
        "escalation": envelope.escalation,
        "answers": envelope.answers,
        "detail": envelope.to_dict(),
    }


def get_local_agent_status() -> dict:
    """Hardware, runtime, models, tiers and sandbox, measured now."""
    inv = inventory()
    server = Server()
    return {
        "hardware": json.loads(inv.to_json()),
        "server": server.health(),
        "tiers": [asdict(t) for t in LocalClient(server=server).tiers()],
        "roster": [{"name": r.name, "local_only": r.local_only} for r in roster()],
        "sandbox": sandbox_available(),
        "tasks": sorted(TASKS),
    }


def delegate_task(
    task: str,
    path: str,
    *,
    model: str | None = None,
    agent: str | None = None,
    root: str | None = None,
) -> dict:
    """Run one named task over one file."""
    if task not in TASKS:
        return {"error": f"unknown task {task!r}; known: {', '.join(sorted(TASKS))}"}
    target = Path(path)
    policy = Policy.load(root or target.parent)
    try:
        envelope = TASKS[task](target, policy=policy, client=_client(model))
    except PolicyRefusal as refusal:
        return {"error": str(refusal), "refused": True, "needs_claude": True}
    if agent:
        envelope.agent = agent
    return _result(envelope)


def classify_umat(path: str, model: str | None = None) -> dict:
    """Decide what a scraped Fortran file is."""
    return delegate_task("classify_umat", path, model=model)


def extract_umat_contract(path: str, model: str | None = None) -> dict:
    """Extract PROPS, STATEV, components and kinematics from a source."""
    return delegate_task("extract_umat_contract", path, model=model)


def triage_failure(log_text: str, source: str | None = None, model: str | None = None) -> dict:
    """Name the first cause of a build or job failure."""
    envelope = TASKS["triage_failure"](log_text, source=source, client=_client(model))
    return _result(envelope)


def review_transformation(original: str, transformed: str, model: str | None = None) -> dict:
    """Check a transformed source for dropped seeding or write-back."""
    policy = Policy.load(Path(original).parent)
    try:
        envelope = TASKS["review_transformation"](
            original, transformed, policy=policy, client=_client(model)
        )
    except PolicyRefusal as refusal:
        return {"error": str(refusal), "refused": True, "needs_claude": True}
    return _result(envelope)


def batch_analyze_umats(
    paths: list[str], task: str = "classify_umat", model: str | None = None, max_files: int = 200
) -> dict:
    """Run one task over many files and return only what needs attention.

    This is the operation that saves the most: the caller gets counts, the
    escalations and the disagreements, not 200 envelopes.
    """
    if task not in TASKS:
        return {"error": f"unknown task {task!r}"}
    if len(paths) > max_files:
        return {
            "error": f"{len(paths)} files exceeds max_files={max_files};"
            " split the batch so a failure does not cost the whole run"
        }
    client = _client(model)
    started = time.time()
    done, escalated, refused, failed = [], [], [], []
    for raw in paths:
        target = Path(raw)
        policy = Policy.load(target.parent)
        try:
            envelope = TASKS[task](target, policy=policy, client=client)
        except PolicyRefusal as refusal:
            refused.append({"path": raw, "reason": str(refusal)})
            continue
        except Exception as error:
            failed.append({"path": raw, "error": f"{type(error).__name__}: {error}"})
            continue
        row = {
            "path": raw,
            "answers": envelope.answers,
            "grounded": round(envelope.grounded_fraction, 2),
            "seconds": envelope.usage.seconds,
        }
        done.append(row)
        if envelope.needs_claude:
            escalated.append(
                {
                    **row,
                    "escalation": envelope.escalation,
                    "reason": envelope.escalation_reason,
                    "summary": envelope.summary(),
                }
            )
    tokens = sum(1 for _ in done)
    return {
        "task": task,
        "model": client.model,
        "counts": {
            "requested": len(paths),
            "analysed": len(done),
            "escalated": len(escalated),
            "refused": len(refused),
            "failed": len(failed),
        },
        "seconds": round(time.time() - started, 1),
        "seconds_per_file": round((time.time() - started) / max(tokens, 1), 1),
        "escalations": escalated,
        "refusals": refused,
        "failures": failed,
        "results": done,
        "needs_claude": bool(escalated or failed),
    }


def sandboxed_syntax_check(path: str, include_dir: str | None = None) -> dict:
    """Compile one untrusted source for syntax only, with no network or home."""
    result = syntax_check(path, include_dir=include_dir)
    return {
        "ok": result.ok,
        "returncode": result.returncode,
        "isolated": result.isolated,
        "isolation": result.isolation,
        "stderr": result.stderr[:4000],
        "seconds": result.seconds,
        "note": result.note,
    }


def propose_memory(
    trigger: str,
    previous_belief: str,
    observation: str,
    evidence: list[str],
    new_rule: str,
    scope: str,
    confidence: float = 0.3,
    exceptions: str = "",
    verification_test: str = "",
) -> dict:
    """Shape a candidate lesson. It is proposed, never adopted.

    ``review_status`` is fixed at ``proposed`` and there is no argument to
    change it: a model that could mark its own lesson adopted would be the
    Council's learning loop with the review step removed.
    """
    if not evidence:
        return {"error": "a candidate lesson needs evidence; none was given"}
    return {
        "trigger": trigger,
        "previous_belief": previous_belief,
        "observation": observation,
        "evidence": list(evidence),
        "new_behavioral_rule": new_rule,
        "scope": scope,
        "exceptions": exceptions or "none recorded",
        "confidence": min(max(float(confidence), 0.0), 1.0),
        "verification_test": verification_test or "none proposed",
        "review_status": "proposed",
        "adopted": False,
        "needs_claude": True,
    }


def run_local_benchmark(models: list[str] | None = None, limit: int = 12) -> dict:
    """Score models against the corpus registry's established labels."""
    cases = build_cases(limit=limit)
    out = {}
    for model in models or ["qwen2.5-coder:7b"]:
        result = run_benchmark(model=model, cases=cases, server=_server())
        out[model] = result.summary
    return {"cases": len(cases), "summaries": out, "needs_claude": True}


def get_role(name: str) -> dict:
    """The system prompt a local member would be given."""
    member = role(name)
    return {
        "name": member.name,
        "local_only": member.local_only,
        "brief": member.brief,
        "system_prompt": member.system_prompt("<task>"),
    }


#: Operation name -> callable. The MCP server and the CLI both read this.
OPERATIONS = {
    "get_local_agent_status": get_local_agent_status,
    "delegate_task": delegate_task,
    "classify_umat": classify_umat,
    "extract_umat_contract": extract_umat_contract,
    "triage_failure": triage_failure,
    "review_transformation": review_transformation,
    "batch_analyze_umats": batch_analyze_umats,
    "sandboxed_syntax_check": sandboxed_syntax_check,
    "propose_memory": propose_memory,
    "run_local_benchmark": run_local_benchmark,
    "get_role": get_role,
}
