"""When the local model fails, the answer is an escalation, not an empty one.

The dangerous failure is not a crash; it is a task that returns something
falsy and gets counted as "nothing to report". A sweep over 391 files that
quietly produced no findings for the thirty where the server had died would
look like a clean sweep.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from council_local.client import LocalClient, LocalModelError, _parse
from council_local.runtime import RuntimeUnavailable, Server
from council_local.tasks import classify_umat


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "umat.for"
    path.write_text("      SUBROUTINE UMAT(STRESS)\n      STRESS(1)=0.D0\n      END\n")
    return path


def test_an_unreachable_server_is_reported_not_swallowed(tmp_path):
    """A dead port must not look like a file with nothing interesting in it."""
    dead = LocalClient(server=Server(port=1), model="whatever")
    with pytest.raises(OSError):
        classify_umat(_source(tmp_path), client=dead)


def test_unparsable_output_becomes_an_escalated_envelope(tmp_path):
    """The task still returns an envelope -- one that says it cannot be used."""

    class Babbling(LocalClient):
        def generate(self, **kwargs):
            raise LocalModelError("did not return valid JSON after 2 attempts")

    envelope = classify_umat(_source(tmp_path), client=Babbling())
    assert envelope.needs_claude
    assert envelope.escalation == "schema_invalid"
    assert not envelope.claims
    assert "valid JSON" in envelope.escalation_reason


def test_a_batch_records_a_failure_instead_of_shrinking(tmp_path):
    """A file that failed is reported as failed, never dropped from the count."""
    from council_local.bench.cases import Case
    from council_local.bench.run import run_benchmark

    class Exploding(LocalClient):
        def generate(self, **kwargs):
            raise OSError("connection refused")

    case = Case(
        case_id="classify_umat:x",
        task="classify_umat",
        path=_source(tmp_path),
        truth={"verdict": "genuine_umat"},
        scoreable=["verdict"],
    )
    result = run_benchmark(model="m", cases=[case], server=Server(port=1))
    assert result.summary.get("cases", 0) == 0
    assert len(result.failures) == 1
    assert "x" in result.failures[0]["case"]


def test_a_missing_runtime_says_how_to_install_one(monkeypatch):
    """The failure a new machine hits first should name its own remedy."""
    from council_local import runtime

    # `runtime` binds the finder at import, so patch it where it is used.
    monkeypatch.setattr(runtime, "_ollama_binary", lambda: None)
    with pytest.raises(RuntimeUnavailable) as caught:
        Server(port=1).start(wait=0.1)
    message = str(caught.value)
    assert "no ollama binary found" in message
    assert "install_runtime.sh" in message
    assert "~/.local/ollama/bin" in message


def test_garbage_is_a_parse_error_and_not_a_default():
    for text in ("", "not json at all", "[1, 2, 3]", "```json\nnope\n```"):
        with pytest.raises(ValueError):
            _parse(text)


def test_a_fenced_object_is_still_accepted():
    """Small models add a fence even when told not to; prose around it is not."""
    assert _parse('```json\n{"claims": []}\n```') == {"claims": []}
    with pytest.raises(ValueError):
        _parse('Here you go: {"claims": []} hope that helps')
