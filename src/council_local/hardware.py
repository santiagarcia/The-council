"""What this machine actually is, measured rather than assumed.

The plan this package was written against described an RTX 5070-class GPU. The
machine it runs on has a Quadro RTX 4000. Model tiers chosen from the stated
hardware would not have fitted, so every figure here is read from the system at
call time and nothing is hard-coded.

Nothing in this module requires privilege: it reads ``/proc``, ``/sys`` and the
output of tools that are already installed, and reports what it could not
determine rather than guessing.
"""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

#: Where a user-space Ollama install is looked for, in order.
OLLAMA_CANDIDATES = (
    Path.home() / ".local/ollama/bin/ollama",
    Path("/usr/local/bin/ollama"),
    Path("/usr/bin/ollama"),
)


@dataclass
class GPU:
    """One accelerator, with the fields that decide whether a model fits."""

    name: str = "unknown"
    vram_mib: int = 0
    vram_free_mib: int = 0
    driver: str = ""
    cuda_version: str = ""
    compute_capability: str = ""
    #: The backend a runtime will actually use, which is not always CUDA: an
    #: old driver makes a modern Ollama fall back to Vulkan on the same card.
    likely_backend: str = "unknown"


@dataclass
class Inventory:
    """A machine's measured capacity, and the runtimes already on it."""

    os_name: str = ""
    kernel: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    cpu_threads: int = 0
    ram_total_gib: float = 0.0
    ram_available_gib: float = 0.0
    disk_free_gib: float = 0.0
    gpus: list[GPU] = field(default_factory=list)
    runtimes: dict[str, str] = field(default_factory=dict)
    models_present: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def vram_mib(self) -> int:
        """Total VRAM of the largest single GPU, which is what a model must fit."""
        return max((g.vram_mib for g in self.gpus), default=0)

    def fits_on_gpu(self, model_bytes: int, *, overhead: float = 1.25) -> bool:
        """Whether a model of ``model_bytes`` plausibly fits in VRAM.

        The overhead covers the KV cache and the runtime's own allocation. It
        is a screening test, not a promise; the benchmark is what decides.
        """
        return model_bytes * overhead <= self.vram_mib * 1024 * 1024

    def to_json(self, indent: int = 2) -> str:
        """The inventory as JSON, for the pilot report and the record."""
        return json.dumps(asdict(self), indent=indent)


def _run(command: list[str], timeout: int = 20) -> str:
    """Run a read-only command, returning '' rather than raising."""
    try:
        done = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return done.stdout if done.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _cpu() -> tuple[str, int, int]:
    """CPU model, physical cores and logical threads from /proc/cpuinfo."""
    model, threads, cores = "", 0, 0
    try:
        text = Path("/proc/cpuinfo").read_text()
    except OSError:
        return model, cores, os.cpu_count() or 0
    ids = set()
    for line in text.splitlines():
        if line.startswith("model name") and not model:
            model = line.split(":", 1)[1].strip()
        elif line.startswith("processor"):
            threads += 1
        elif line.startswith("core id"):
            ids.add(line.split(":", 1)[1].strip())
    cores = len(ids) or threads
    return model, cores, threads


def _memory() -> tuple[float, float]:
    """Total and available RAM in GiB from /proc/meminfo."""
    total = available = 0.0
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                total = int(line.split()[1]) / 1048576
            elif line.startswith("MemAvailable:"):
                available = int(line.split()[1]) / 1048576
    except (OSError, ValueError):
        pass
    return round(total, 1), round(available, 1)


def _gpus() -> list[GPU]:
    """Accelerators via nvidia-smi, with the backend an old driver implies."""
    # compute_cap is not a queryable field on every driver generation -- it is
    # absent on 470 -- and nvidia-smi fails the WHOLE query when one field is
    # unknown rather than omitting it. So ask for the fields that matter and
    # treat the capability as a bonus.
    base = "name,memory.total,memory.free,driver_version"
    out = _run(["nvidia-smi", f"--query-gpu={base},compute_cap", "--format=csv,noheader,nounits"])
    if not out.strip():
        out = _run(["nvidia-smi", f"--query-gpu={base}", "--format=csv,noheader,nounits"])
    gpus: list[GPU] = []
    for line in out.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 4:
            continue
        gpu = GPU(
            name=parts[0],
            vram_mib=int(float(parts[1])),
            vram_free_mib=int(float(parts[2])),
            driver=parts[3],
            compute_capability=parts[4] if len(parts) > 4 else "",
        )
        header = _run(["nvidia-smi"]).splitlines()
        for row in header[:5]:
            if "CUDA Version:" in row:
                gpu.cuda_version = row.split("CUDA Version:")[1].split("|")[0].strip()
        gpu.likely_backend = _backend_for(gpu)
        gpus.append(gpu)
    return gpus


def _backend_for(gpu: GPU) -> str:
    """Which backend a current Ollama will use on this driver.

    Ollama's shipped CUDA runtime needs a driver new enough for CUDA 12. On an
    older driver the card still works, through Vulkan, at lower throughput --
    so this is a performance fact, not a compatibility failure, and the
    difference is large enough that it belongs in the inventory.
    """
    try:
        major = int(gpu.driver.split(".")[0])
    except (ValueError, IndexError):
        return "unknown"
    return "cuda" if major >= 525 else "vulkan (driver too old for the CUDA 12 runtime)"


def _ollama_binary() -> Path | None:
    """A usable Ollama, including a user-space install that is not on PATH."""
    found = shutil.which("ollama")
    if found:
        return Path(found)
    return next((p for p in OLLAMA_CANDIDATES if p.is_file() and os.access(p, os.X_OK)), None)


def _models(binary: Path | None) -> list[dict]:
    """Models already pulled, so the setup never re-downloads one it has."""
    root = Path(os.environ.get("OLLAMA_MODELS", Path.home() / ".ollama/models"))
    manifests = root / "manifests"
    if not manifests.is_dir():
        return []
    models = []
    for path in sorted(manifests.rglob("*")):
        if not path.is_file():
            continue
        name = path.relative_to(manifests).as_posix()
        # registry/library/<model>/<tag> -> <model>:<tag>
        parts = name.split("/")
        tag = f"{parts[-2]}:{parts[-1]}" if len(parts) >= 2 else name
        size = 0
        try:
            manifest = json.loads(path.read_text())
            size = sum(layer.get("size", 0) for layer in manifest.get("layers", []))
        except (OSError, ValueError):
            pass
        models.append({"name": tag, "bytes": size, "gib": round(size / 2**30, 2)})
    return models


def inventory() -> Inventory:
    """Measure this machine. Safe to call anywhere; starts nothing."""
    model, cores, threads = _cpu()
    total, available = _memory()
    usage = shutil.disk_usage(Path.home())
    inv = Inventory(
        os_name=_distro(),
        kernel=platform.release(),
        cpu_model=model,
        cpu_cores=cores,
        cpu_threads=threads,
        ram_total_gib=total,
        ram_available_gib=available,
        disk_free_gib=round(usage.free / 2**30, 1),
        gpus=_gpus(),
    )

    binary = _ollama_binary()
    if binary:
        inv.runtimes["ollama"] = str(binary)
        version = _run([str(binary), "--version"])
        for line in version.splitlines():
            if "version is" in line:
                inv.runtimes["ollama_version"] = line.split("version is")[-1].strip()
    for name in ("llama-server", "docker", "podman", "nvcc", "bwrap", "firejail"):
        path = shutil.which(name)
        if path:
            inv.runtimes[name] = path
    inv.models_present = _models(binary)

    if not inv.gpus:
        inv.notes.append("no GPU detected; every model will run on CPU")
    for gpu in inv.gpus:
        if gpu.likely_backend.startswith("vulkan"):
            inv.notes.append(
                f"{gpu.name}: driver {gpu.driver} predates the CUDA 12 runtime, so a current"
                " Ollama uses Vulkan. The card works; throughput is below its CUDA figure."
            )
    if (
        "docker" not in inv.runtimes
        and "podman" not in inv.runtimes
        and "bwrap" not in inv.runtimes
    ):
        inv.notes.append(
            "no container or bubblewrap runtime: untrusted Fortran can only be compiled"
            " under the rlimit sandbox, which is weaker than a container"
        )
    return inv


def _distro() -> str:
    """A readable OS name from /etc/os-release, falling back to platform."""
    try:
        for line in Path("/etc/os-release").read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


def main() -> int:
    """Print the inventory as JSON."""
    print(inventory().to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
