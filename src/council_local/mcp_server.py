"""An MCP server over stdio exposing the delegation operations.

Written against the protocol directly rather than an SDK: the Council's
dependencies are deliberately modest, and the surface used here is three
methods. Transport is stdio, so nothing listens on a port and nothing needs a
credential.

Register it with Claude Code as::

    claude mcp add council-local -- /path/to/.venv/bin/python \\
        /path/to/The-council/scripts/local/mcp_server.py
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any

from .bridge import OPERATIONS

PROTOCOL_VERSION = "2024-11-05"

#: Argument schemas. Kept beside the operations rather than generated, so the
#: description a caller reads says what the operation is actually for.
TOOLS: list[dict] = [
    {
        "name": "get_local_agent_status",
        "description": "Measured hardware, server health, model tiers, roster and sandbox.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "classify_umat",
        "description": "Decide whether a scraped Fortran file is a genuine Abaqus UMAT, "
        "another entry point, a fragment or a driver. Cites lines.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}, "model": {"type": "string"}},
        },
    },
    {
        "name": "extract_umat_contract",
        "description": "Extract max PROPS and STATEV indices, kinematics, inline "
        "constants and solver utilities from a UMAT source.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}, "model": {"type": "string"}},
        },
    },
    {
        "name": "delegate_task",
        "description": "Run any registered task over one file "
        "(classify_umat, extract_umat_contract, detect_dependencies, "
        "review_transformation).",
        "inputSchema": {
            "type": "object",
            "required": ["task", "path"],
            "properties": {
                "task": {"type": "string"},
                "path": {"type": "string"},
                "model": {"type": "string"},
                "agent": {"type": "string"},
            },
        },
    },
    {
        "name": "batch_analyze_umats",
        "description": "Run one task over many files; returns counts and only the "
        "cases needing review, not every envelope.",
        "inputSchema": {
            "type": "object",
            "required": ["paths"],
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}},
                "task": {"type": "string"},
                "model": {"type": "string"},
            },
        },
    },
    {
        "name": "triage_failure",
        "description": "Read a build or Abaqus log and name the earliest real error, "
        "its category, and which later errors are consequences.",
        "inputSchema": {
            "type": "object",
            "required": ["log_text"],
            "properties": {
                "log_text": {"type": "string"},
                "source": {"type": "string"},
                "model": {"type": "string"},
            },
        },
    },
    {
        "name": "review_transformation",
        "description": "Compare an original and a transformed source for shadow "
        "variables that are never seeded or never written back.",
        "inputSchema": {
            "type": "object",
            "required": ["original", "transformed"],
            "properties": {
                "original": {"type": "string"},
                "transformed": {"type": "string"},
                "model": {"type": "string"},
            },
        },
    },
    {
        "name": "sandboxed_syntax_check",
        "description": "Compile one untrusted source for syntax only, with no network, "
        "no home directory and hard resource limits.",
        "inputSchema": {
            "type": "object",
            "required": ["path"],
            "properties": {"path": {"type": "string"}, "include_dir": {"type": "string"}},
        },
    },
    {
        "name": "propose_memory",
        "description": "Shape a candidate Council lesson. Always returns "
        "review_status=proposed; it cannot adopt anything.",
        "inputSchema": {
            "type": "object",
            "required": [
                "trigger",
                "previous_belief",
                "observation",
                "evidence",
                "new_rule",
                "scope",
            ],
            "properties": {
                "trigger": {"type": "string"},
                "previous_belief": {"type": "string"},
                "observation": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "string"}},
                "new_rule": {"type": "string"},
                "scope": {"type": "string"},
                "confidence": {"type": "number"},
                "exceptions": {"type": "string"},
                "verification_test": {"type": "string"},
            },
        },
    },
    {
        "name": "run_local_benchmark",
        "description": "Score local models against the corpus registry's labels.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "models": {"type": "array", "items": {"type": "string"}},
                "limit": {"type": "integer"},
            },
        },
    },
    {
        "name": "get_role",
        "description": "The system prompt a named Council member is given locally.",
        "inputSchema": {
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}},
        },
    },
]


def _send(message: dict) -> None:
    sys.stdout.write(json.dumps(message) + "\n")
    sys.stdout.flush()


def _reply(request_id: Any, result: dict) -> None:
    _send({"jsonrpc": "2.0", "id": request_id, "result": result})


def _error(request_id: Any, code: int, message: str) -> None:
    _send({"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}})


def handle(request: dict) -> None:
    """Dispatch one JSON-RPC request."""
    method = request.get("method")
    request_id = request.get("id")
    params = request.get("params") or {}

    if method == "initialize":
        _reply(
            request_id,
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "council-local", "version": "0.1.0"},
            },
        )
    elif method == "notifications/initialized":
        return
    elif method == "tools/list":
        _reply(request_id, {"tools": TOOLS})
    elif method == "tools/call":
        name = params.get("name")
        operation = OPERATIONS.get(name)
        if operation is None:
            _error(request_id, -32601, f"unknown tool {name!r}")
            return
        try:
            payload = operation(**(params.get("arguments") or {}))
            text = json.dumps(payload, indent=2, default=str)
        except TypeError as error:
            _error(request_id, -32602, f"{name}: {error}")
            return
        except Exception:
            # A failed delegation is reported, never silently empty: an empty
            # result is indistinguishable from "nothing to report".
            _reply(
                request_id,
                {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {
                                    "error": "local delegation failed",
                                    "needs_claude": True,
                                    "traceback": traceback.format_exc()[-1500:],
                                },
                                indent=2,
                            ),
                        }
                    ],
                    "isError": True,
                },
            )
            return
        _reply(request_id, {"content": [{"type": "text", "text": text}]})
    elif request_id is not None:
        _error(request_id, -32601, f"unknown method {method!r}")


def main() -> int:
    """Read JSON-RPC from stdin until it closes."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        handle(request)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
