"""Isolated reader packets, bounded text diagnostics, and evidence-linked review gates."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from council.store import CouncilError, safe_path
from council.validation import check_schema, records, reference_ok, validate

READER_RULES = (
    "Cold-read is a fresh low-context review, not a specialist exam. "
    "Not understanding is information. No ridicule, infantilization, or humiliation. "
    "Investigate the explanation before judging the learner. "
    "Simple wording must preserve technical truth. Respect Santiago's autonomy. "
    "Affection and trust never change evidentiary standards or grant permissions."
)
QUESTIONS = (
    "What are we trying to accomplish? Why does it matter?",
    "What information and prerequisites do I need before starting?",
    "What does each term, acronym, symbol, and figure mean?",
    "Where did the equation come from, and why is each step allowed?",
    "What should I see, and how do I know it worked?",
    "What can go wrong, and what should I do when it fails?",
    "Can I restate the central idea accurately in my own words?",
    "What is the single main message?",
)
MAX_ARTIFACT_BYTES = 262_144


def read_artifact(root: Path, artifact: str) -> tuple[str, str]:
    """Read one bounded public text artifact, rejecting memory and private-source input."""
    path = safe_path(root, artifact)
    relative = path.relative_to(root.resolve())
    if not relative.parts:
        raise CouncilError("Artifact must be a file")
    if (
        "private" in relative.parts
        or relative.parts[0] in {"memory", ".git", ".council"}
        or path.name.startswith(".env")
        or path.suffix.lower() not in {".md", ".txt", ".rst", ".json", ".yaml", ".yml"}
    ):
        raise CouncilError("Review requires a public text artifact, not memory or private data")
    if not path.is_file() or path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise CouncilError("Artifact must be an existing text file of at most 256 KiB")
    return relative.as_posix(), path.read_text(encoding="utf-8")


def continuity(root: Path) -> list[dict]:
    """Return reviewed nontechnical habits without exposing event or domain-memory text."""
    path = safe_path(root, "relationships/pairs/nico-continuity.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    errors = check_schema(root, "reader-continuity", data)
    if errors:
        raise CouncilError("Invalid reader continuity:\n" + "\n".join(errors))
    result = []
    for item in data["records"]:
        if item["status"] != "adopted" or item["review_status"] != "accepted":
            continue
        if item["reviewer"] in {None, "nico"}:
            raise CouncilError("Reader continuity requires independent review")
        if not item["evidence_refs"] or not all(
            reference_ok(root, ref) for ref in item["evidence_refs"]
        ):
            raise CouncilError("Adopted reader continuity requires existing event evidence")
        result.append(
            {
                "participants": item["participants"],
                "qualities": item["qualities"],
                "practices": item["practices"],
            }
        )
    return result


def reader_context(root: Path, mode: str) -> str:
    """Load Nico's role and methods, never project context or domain memories."""
    if mode not in {"cold-read", "developing-reader"}:
        raise CouncilError("Unknown reader mode")
    chunks = [f"# Nico: {mode}\n\n{READER_RULES}\n"]
    for name in ("identity.md", "system-prompt.md", "operating-beliefs.yaml",
                 "affective-profile.yaml"):
        path = safe_path(root, f"members/nico/{name}")
        chunks.append(f"## Source: members/nico/{name}\n\n{path.read_text(encoding='utf-8')}")
    chunks.append("## Reviewed nontechnical continuity\n" + json.dumps(continuity(root), indent=2))
    chunks.append("## Evaluation questions\n" + "\n".join(f"- {q}" for q in QUESTIONS))
    return "\n\n".join(chunks)


def review_packet(
    root: Path,
    agent: str,
    mode: str,
    artifact: str,
    audience: str = "",
    project: str | None = None,
) -> dict:
    """Build an isolated artifact handoff; developing readers may load scoped Nico lessons."""
    from council.context import require_agent, require_project

    require_agent(root, agent)
    if agent != "nico":
        raise CouncilError("Reader review currently supports --agent nico")
    if mode == "cold-read" and project is not None:
        raise CouncilError("Cold-read forbids --project and domain-memory loading")
    errors = validate(root)
    if errors:
        raise CouncilError("Repository validation failed:\n" + "\n".join(errors))
    path, text = read_artifact(root, artifact)
    context = reader_context(root, mode)
    lessons = []
    if project is not None:
        require_project(root, project)
        for _path, memory, _body in records(root, "memory/agents/nico/*.md"):
            if (
                memory["owner"] == "nico"
                and memory["project"] == project
                and memory["status"] == "adopted"
            ):
                lessons.append(
                    {"id": memory["id"], "observation": memory["observation"],
                     "limitations": memory["limitations"]}
                )
    return {
        "format_version": 1,
        "agent": "nico",
        "mode": mode,
        "audience": audience or "No audience supplied; report this evaluation limitation.",
        "artifact": {
            "path": path, "content": text,
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        },
        "reader_context": context,
        "learning_context": lessons,
        "instructions": (
            "Attempt the artifact's task and an accurate restatement. Record locations of "
            "missing information, expected/actual outcomes, and recovery gaps. "
            "In developing-reader mode record the explanation behind each breakthrough. "
            "Do not pretend a packet is a completed review or import hidden domain context."
        ),
    }


def diagnostics(text: str, kind: str) -> list[dict]:
    """Flag explainable text patterns; findings are candidates, not semantic proof."""
    findings = []
    for number, line in enumerate(text.splitlines(), 1):
        if re.search(r"\b(idiot|stupid|childish|dumb)\b", line, re.IGNORECASE):
            findings.append(
                {"rule": "possible-humiliation", "line": number,
                 "detail": "Check for ridicule or infantilization; inspect context."}
            )
        if re.search(r"\b(obviously|trivial|simply understand)\b", line, re.IGNORECASE):
            findings.append(
                {"rule": "assumed-understanding", "line": number,
                 "detail": "Check whether required steps are explained without dismissal."}
            )
        for acronym in sorted(set(re.findall(r"\b[A-Z][A-Z0-9]{1,7}\b", line))):
            if acronym in {"TODO", "NOTE", "WARNING", "PATH"}:
                continue
            if not re.search(r"\(" + re.escape(acronym) + r"\)", text):
                findings.append(
                    {"rule": "possibly-undefined-acronym", "line": number,
                     "detail": f"Check whether {acronym} is defined for this audience."}
                )
    if kind == "usability":
        lower = text.lower()
        if re.search(r"\b(install|pip|uv sync|npm)\b", lower):
            if not re.search(r"\b(prerequisite|requires|required|python [0-9])", lower):
                findings.append(
                    {"rule": "missing-prerequisites", "line": 1,
                     "detail": "Installation text may omit prerequisites."}
                )
            if not re.search(r"\b(expect|success|verify|check|output)\b", lower):
                findings.append(
                    {"rule": "missing-success-feedback", "line": 1,
                     "detail": "The workflow may omit expected output or a success check."}
                )
        if not re.search(r"\b(error|fail|recover|undo|rollback|revert)\b", lower):
            findings.append(
                {"rule": "missing-recovery", "line": 1,
                 "detail": "Check whether failure handling and reversal are discoverable."}
            )
    return findings


def reviewed_gate(root: Path, report: dict, artifact: str) -> bool:
    """Require evidenced correctness and comprehension, with no unresolved blocking findings."""
    errors = check_schema(root, "deliverable-review", report)
    if errors:
        raise CouncilError("Invalid review report:\n" + "\n".join(errors))
    if report["artifact"] != artifact:
        raise CouncilError("Review report refers to another artifact")
    _, text = read_artifact(root, artifact)
    if report["artifact_sha256"] != hashlib.sha256(text.encode("utf-8")).hexdigest():
        raise CouncilError("Review report is stale: artifact content changed")
    for part in ("correctness", "comprehension", "usability"):
        assessment = report[part]
        for ref in assessment["evidence_refs"]:
            if not reference_ok(root, ref):
                raise CouncilError(f"Broken review evidence: {ref}")
        if assessment["decision"] == "pass" and not assessment["evidence_refs"]:
            raise CouncilError("A passing review must cite evidence")
    if report["correctness"]["reviewer"] == "nico":
        raise CouncilError("Nico reviews comprehension, not technical correctness")
    if report["correctness"]["reviewer"] == report["builder"]:
        raise CouncilError("Builder cannot certify correctness")
    return (
        report["builder"] != "nico"
        and all(report[part]["decision"] == "pass" for part in ("correctness", "comprehension"))
        and bool(report["comprehension"]["restatement"].strip())
        and report["comprehension"]["technically_faithful"]
        and report["comprehension"]["mode"] == "cold-read"
        and (
            report["correctness"]["mathematical_status"] != "supported"
            or bool(report["correctness"]["assumptions"])
        )
        and all(
            report["correctness"][field] != "unsupported"
            for field in ("mathematical_status", "physical_status", "numerical_status")
        )
        and (
            report["usability"]["decision"] != "pass"
            or report["usability"]["implementation_constraints_considered"]
        )
        and report["usability"]["decision"] in {"pass", "not-applicable"}
        and not report["blocking_findings"]
    )


def evaluate_artifact(
    root: Path, kind: str, artifact: str, report_path: str | None = None
) -> tuple[int, dict]:
    """Run bounded diagnostics and optionally evaluate an explicitly supplied review report."""
    if kind not in {"comprehension", "usability"}:
        raise CouncilError("Unknown evaluation kind")
    path, text = read_artifact(root, artifact)
    findings = diagnostics(text, kind)
    result = {
        "kind": kind,
        "artifact": path,
        "artifact_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "status": "needs-human-review",
        "findings": findings,
        "final_review_passed": None,
        "limitations": (
            "Pattern checks cannot prove understanding, mathematical/physical validity, "
            "accessibility, or truthful simplification. Review labels are not authentication."
        ),
        "review_questions": list(QUESTIONS) if kind == "comprehension" else [
            "Is system status visible and uncertainty calibrated?",
            "Can the user predict consequences and retain meaningful control?",
            "Are inputs, outputs, units, errors, and prerequisites understandable?",
            "Are safe defaults, accessibility, and recovery tested?",
            "Were implementation constraints considered with Ada?",
        ],
    }
    if report_path is not None:
        report = json.loads(safe_path(root, report_path).read_text(encoding="utf-8"))
        passed = reviewed_gate(root, report, path)
        result["final_review_passed"] = passed
        result["status"] = "reviewed-pass" if passed else "reviewed-fail"
        return (0 if passed else 1), result
    return (1 if findings else 0), result
