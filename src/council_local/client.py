"""Calling a local model and refusing to believe it by default.

The client's job is narrow: send one grounded prompt, insist on JSON that
matches a schema, measure what it cost, and hand back an
:class:`~council_local.envelope.Envelope`. It does not decide whether an
answer is right -- that is the benchmark's job, and then Claude's.

Two design rules come from measurement rather than taste:

* **Never ask for recall.** Every one of the three models on this machine
  answered a pure recall question confidently and wrongly. Prompts here quote
  the file and ask the model to read it, so a wrong answer is contradicted by
  text that is in the same context window.
* **A model that cannot produce valid JSON twice is a failed tool call,** not
  an answer to be salvaged by a regex. Salvaging is how an unparsed field
  becomes a silent default.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from .envelope import Envelope, Usage
from .hardware import inventory
from .runtime import Server

#: Response fields every task-level prompt asks for. Mirrors Envelope.build.
RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["claims", "uncertainties", "recommended_next_action"],
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["statement", "evidence"],
                "properties": {
                    "statement": {"type": "string"},
                    "confidence": {"type": "number"},
                    "evidence": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["path", "line"],
                            "properties": {
                                "path": {"type": "string"},
                                "line": {"type": "integer"},
                                "quote": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
        "uncertainties": {"type": "array", "items": {"type": "string"}},
        "recommended_next_action": {"type": "string"},
    },
}


def response_schema(answers: dict | None = None) -> dict:
    """The envelope schema, optionally with a task's typed answer fields.

    A task that asks six questions in prose gets six restatements of the
    questions back -- measured, on the first end-to-end call of this package.
    Naming the answers as typed fields fixes that, and it is also what makes
    an answer scoreable against the corpus registry without a human reading it.
    """
    schema = json.loads(json.dumps(RESPONSE_SCHEMA))
    if answers:
        schema["properties"]["answers"] = {
            "type": "object",
            "properties": answers,
            "required": sorted(answers),
        }
        schema["required"] = [*schema["required"], "answers"]
    return schema


#: Prepended to every system prompt. Short on purpose: a long preamble costs
#: tokens on a 42 tok/s budget and the models follow the last instruction best.
GROUNDING_RULES = """\
You answer only from the text given to you in this prompt. You do not answer
from memory: if the prompt does not contain the evidence, say so in
"uncertainties" and leave the claim out.

Every claim must cite the file path and the 1-based line number where the
evidence appears, quoting the line. A claim you cannot cite is a claim you
must not make.

Reply with one JSON object and nothing else. No markdown fence, no commentary.
"""


class LocalModelError(RuntimeError):
    """The local model failed to produce a usable answer."""


@dataclass
class Tier:
    """One model tier, with the measured facts that justify choosing it."""

    name: str
    model: str
    #: Measured generation rate, filled in by the benchmark, not guessed.
    tokens_per_second: float = 0.0
    fits_in_vram: bool = False
    use_for: str = ""
    num_ctx: int = 8192


@dataclass
class LocalClient:
    """A thin, measured client over one shared inference server."""

    server: Server = field(default_factory=Server)
    model: str = "qwen2.5-coder:7b"
    temperature: float = 0.0
    num_ctx: int = 8192
    #: Retried once on invalid JSON, with the parse error fed back. Twice is
    #: already more latency than escalating to a reviewer is worth.
    retries: int = 1

    def generate(
        self,
        *,
        system: str,
        prompt: str,
        num_predict: int = 1024,
        schema: dict | None = None,
        model: str | None = None,
    ) -> tuple[dict, Usage]:
        """One structured call. Returns the parsed object and what it cost."""
        model = model or self.model
        before = _vram_used()
        started = time.time()
        payload = {
            "model": model,
            "system": GROUNDING_RULES + "\n" + system,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": num_predict,
            },
        }
        if schema is not None:
            # Ollama constrains decoding to the schema, which removes most
            # parse failures outright rather than catching them afterwards.
            payload["format"] = schema

        last_error = ""
        for attempt in range(self.retries + 1):
            if attempt:
                payload["prompt"] = (
                    f"{prompt}\n\nYour previous reply was not valid JSON"
                    f" ({last_error}). Reply with one JSON object and nothing else."
                )
            response = self.server._post("/api/generate", payload)
            text = response.get("response", "")
            usage = _usage(response, model, time.time() - started, before)
            try:
                return _parse(text), usage
            except ValueError as error:
                last_error = str(error)[:160]
        raise LocalModelError(
            f"{model} did not return valid JSON after {self.retries + 1} attempts: {last_error}"
        )

    def ask(
        self,
        *,
        agent: str,
        task: str,
        system: str,
        prompt: str,
        files_examined=(),
        policy_refusals=(),
        num_predict: int = 1024,
        root: Path | str | None = None,
        model: str | None = None,
        answers: dict | None = None,
    ) -> Envelope:
        """A full task call, returned as an envelope with the rules applied."""
        try:
            payload, usage = self.generate(
                system=system,
                prompt=prompt,
                num_predict=num_predict,
                schema=response_schema(answers),
                model=model,
            )
        except LocalModelError as error:
            usage = Usage(model=model or self.model, backend=_backend())
            envelope = Envelope(
                agent=agent, task=task, usage=usage, files_examined=[str(p) for p in files_examined]
            )
            return envelope.escalate("schema_invalid", str(error))
        return Envelope.build(
            agent=agent,
            task=task,
            payload=payload,
            usage=usage,
            files_examined=files_examined,
            policy_refusals=policy_refusals,
            raw=json.dumps(payload),
            root=root,
        )

    def tiers(self) -> list[Tier]:
        """The tiers available on this machine, screened against measured VRAM."""
        inv = inventory()
        present = {m["name"]: m["bytes"] for m in inv.models_present}
        out = []
        for name, model, use in (
            ("background", "qwen2.5-coder:1.5b", "inventory, triage, screening"),
            ("worker", "qwen2.5-coder:7b", "extraction, classification, review"),
            ("reasoner", "qwen2.5-coder:32b", "hard cases, batch only"),
        ):
            if model in present:
                out.append(
                    Tier(
                        name=name,
                        model=model,
                        fits_in_vram=inv.fits_on_gpu(present[model]),
                        use_for=use,
                    )
                )
        return out


def _parse(text: str) -> dict:
    """Parse a model's reply as one JSON object, or raise.

    Tolerates a markdown fence because small models add one even when told not
    to; does not tolerate prose around the object, because text a model added
    outside the structure is text nobody asked for.
    """
    stripped = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", stripped, re.S)
    if fence:
        stripped = fence.group(1).strip()
    if not stripped:
        raise ValueError("empty response")
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise ValueError(f"not JSON at char {error.pos}: {error.msg}") from error
    if not isinstance(parsed, dict):
        raise ValueError(f"expected a JSON object, got {type(parsed).__name__}")
    return parsed


def _usage(response: dict, model: str, wall: float, vram_before: int) -> Usage:
    """Turn Ollama's nanosecond counters into the usage block."""
    completion = int(response.get("eval_count", 0) or 0)
    eval_ns = int(response.get("eval_duration", 0) or 0)
    rate = completion / (eval_ns / 1e9) if eval_ns else 0.0
    return Usage(
        model=model,
        quantization=_quantization(model),
        backend=_backend(),
        prompt_tokens=int(response.get("prompt_eval_count", 0) or 0),
        completion_tokens=completion,
        seconds=round(wall, 2),
        tokens_per_second=round(rate, 2),
        peak_vram_mib=max(_vram_used(), vram_before),
    )


def _quantization(model: str) -> str:
    """The quantization the server reports for a model, or ''."""
    try:
        for entry in Server().tags():
            if entry.get("name") == model:
                return entry.get("details", {}).get("quantization_level", "")
    except OSError:
        pass
    return ""


def _backend() -> str:
    inv = inventory()
    return inv.gpus[0].likely_backend if inv.gpus else "cpu"


def _vram_used() -> int:
    inv = inventory()
    if not inv.gpus:
        return 0
    gpu = inv.gpus[0]
    return gpu.vram_mib - gpu.vram_free_mib
