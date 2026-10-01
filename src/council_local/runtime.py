"""Starting, checking and stopping the one local inference server.

One server, many identities. A Council member is a system prompt and a context
budget, not a separate copy of the weights -- loading a model per member would
exhaust 8 GiB of VRAM on the second member.

Everything here is user-space and reversible: the binary is found where it was
installed rather than installed again, the server binds to loopback, and
stopping it leaves no service behind.
"""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .hardware import _ollama_binary, inventory

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11434
#: Where the server's log and pid go. Outside any repository on purpose.
STATE_DIR = Path(os.environ.get("COUNCIL_LOCAL_STATE", Path.home() / ".cache/council-local"))


class RuntimeUnavailable(RuntimeError):
    """No local inference runtime could be found or started."""


@dataclass
class Server:
    """A handle on the local inference server."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    binary: Path | None = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def pid_file(self) -> Path:
        return STATE_DIR / f"ollama-{self.port}.pid"

    @property
    def log_file(self) -> Path:
        return STATE_DIR / f"ollama-{self.port}.log"

    def is_listening(self, timeout: float = 0.4) -> bool:
        """Whether something accepts connections on the port."""
        with socket.socket() as sock:
            sock.settimeout(timeout)
            return sock.connect_ex((self.host, self.port)) == 0

    def health(self) -> dict:
        """A health report: reachable, which models, how much VRAM is free."""
        report: dict = {"base_url": self.base_url, "listening": self.is_listening()}
        if not report["listening"]:
            report["ok"] = False
            report["detail"] = "nothing is listening on the port"
            return report
        try:
            report["models"] = [m["name"] for m in self.tags()]
            report["ok"] = True
        except OSError as error:
            report["ok"] = False
            report["detail"] = str(error)
            return report
        inv = inventory()
        report["loaded"] = self.ps()
        if inv.gpus:
            gpu = inv.gpus[0]
            report["gpu"] = {
                "name": gpu.name,
                "vram_mib": gpu.vram_mib,
                "free_mib": gpu.vram_free_mib,
                "backend": gpu.likely_backend,
            }
        return report

    def tags(self) -> list[dict]:
        """Models the server can serve."""
        return self._get("/api/tags").get("models", [])

    def ps(self) -> list[dict]:
        """Models currently resident, with where they are resident."""
        try:
            return [
                {"name": m.get("name"), "size_vram": m.get("size_vram", 0)}
                for m in self._get("/api/ps").get("models", [])
            ]
        except OSError:
            return []

    def start(self, *, wait: float = 60.0) -> Server:
        """Start the server if it is not already up, and wait for readiness.

        Returns as soon as the API answers. Idempotent: an already-running
        server is adopted rather than duplicated, which matters because the
        port is shared with anything the user started themselves.
        """
        if self.is_listening():
            return self
        binary = self.binary or _ollama_binary()
        if binary is None:
            raise RuntimeUnavailable(
                "no ollama binary found. Looked on PATH and in ~/.local/ollama/bin."
                " Install it in user space with scripts/local/install_runtime.sh"
            )
        self.binary = Path(binary)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        environment = dict(os.environ)
        environment["OLLAMA_HOST"] = f"{self.host}:{self.port}"
        # Loopback only. Never bind 0.0.0.0: an unauthenticated inference
        # endpoint on a university network is an open compute service.
        with self.log_file.open("ab") as log:
            process = subprocess.Popen(
                [str(self.binary), "serve"],
                stdout=log,
                stderr=log,
                env=environment,
                start_new_session=True,
            )
        self.pid_file.write_text(str(process.pid))
        deadline = time.time() + wait
        while time.time() < deadline:
            if self.is_listening():
                return self
            if process.poll() is not None:
                raise RuntimeUnavailable(
                    f"ollama exited with code {process.returncode}; see {self.log_file}"
                )
            time.sleep(0.5)
        raise RuntimeUnavailable(f"ollama did not become ready within {wait:.0f}s")

    def stop(self) -> bool:
        """Stop a server this package started. Leaves others alone."""
        if not self.pid_file.is_file():
            return False
        try:
            pid = int(self.pid_file.read_text().strip())
        except ValueError:
            self.pid_file.unlink(missing_ok=True)
            return False
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            self.pid_file.unlink(missing_ok=True)
            return False
        for _ in range(40):
            if not self.is_listening():
                break
            time.sleep(0.25)
        self.pid_file.unlink(missing_ok=True)
        return True

    def unload(self, model: str) -> None:
        """Drop a model from memory without stopping the server.

        Switching tiers on an 8 GiB card means the outgoing model has to go
        first; otherwise the incoming one is silently placed on the CPU.
        """
        self._post("/api/generate", {"model": model, "keep_alive": 0})

    def _get(self, path: str, timeout: float = 10.0) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=timeout) as response:
            return json.loads(response.read())

    def _post(self, path: str, payload: dict, timeout: float = 600.0) -> dict:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            raise OSError(f"{path} returned {error.code}: {error.read()[:300]!r}") from error
