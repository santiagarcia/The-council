"""Compiling and running scraped Fortran without trusting it.

The corpus is 391 files pulled from public repositories. Their comments,
READMEs and build scripts are **data**, never instructions, and a build script
that arrives with a source is a program someone else wrote that would run with
this account's credentials.

So a compile happens with no network, no credentials, no view of the home
directory or either repository, under explicit CPU, memory, file-size and
wall-clock limits, in a directory that is thrown away. Bubblewrap is used when
it is present -- it is, on this machine, at /usr/bin/bwrap, and needs no root.
Without it the rlimit path still bounds resources but does not isolate the
filesystem, and ``isolated`` says so rather than implying a guarantee it
cannot give.
"""

from __future__ import annotations

import os
import resource
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

#: Defaults chosen to stop a runaway build, not to make a slow one fail.
CPU_SECONDS = 60
MEMORY_BYTES = 2 * 1024**3
FILE_SIZE_BYTES = 256 * 1024**2
WALL_SECONDS = 120
OUTPUT_LIMIT = 200_000

#: Things that must never be visible to a build of untrusted code.
NEVER_MOUNT = ("/home", "/root", "/etc/ssh", "/var/lib", "/mnt", "/media")

#: Abaqus supplies this to every user subroutine, so a corpus source that
#: INCLUDEs it is not defective for doing so -- it simply cannot compile
#: outside Abaqus without it. The two lines are what Abaqus's own copy
#: contains for a double-precision build; staging them lets a syntax check
#: answer the question actually being asked, which is whether the FORTRAN is
#: well formed, not whether the solver is installed.
ABA_PARAM = "      IMPLICIT REAL*8(A-H,O-Z)\n      PARAMETER (NPRECD=2)\n"


@dataclass
class SandboxResult:
    """What a sandboxed command did, and how contained it actually was."""

    command: list[str]
    returncode: int = -1
    stdout: str = ""
    stderr: str = ""
    seconds: float = 0.0
    timed_out: bool = False
    isolated: bool = False
    isolation: str = "none"
    artifacts: list[str] = field(default_factory=list)
    note: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def available() -> dict:
    """Which isolation mechanisms this machine actually offers."""
    return {
        "bwrap": shutil.which("bwrap"),
        "podman": shutil.which("podman"),
        "docker": shutil.which("docker"),
        "gfortran": shutil.which("gfortran"),
    }


def _limits(cpu: int, memory: int, file_size: int, *, cap_processes: bool):
    """A preexec hook applying hard rlimits to the child.

    RLIMIT_NPROC is deliberately NOT set when bubblewrap is used. It counts
    every process belonging to the UID, not the children of this one, so a
    small cap makes `bwrap` fail to create its namespace with EAGAIN -- which
    looks exactly like successful containment: the command produces no output
    because it never ran. That false negative was observed while writing this
    module, and the pid namespace bounds process count properly anyway.
    """

    def apply() -> None:
        resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
        resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
        resource.setrlimit(resource.RLIMIT_FSIZE, (file_size, file_size))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        if cap_processes:
            soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
            resource.setrlimit(resource.RLIMIT_NPROC, (min(soft, 512), hard))
        os.setsid()

    return apply


def _bwrap(work: Path, command: list[str]) -> list[str]:
    """Wrap a command so it sees a read-only system and one writable directory."""
    argv = [
        "bwrap",
        "--unshare-all",  # no network, no IPC, no pid namespace sharing
        "--die-with-parent",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/lib",
        "/lib",
        "--ro-bind",
        "/bin",
        "/bin",
        "--ro-bind",
        "/sbin",
        "/sbin",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--bind",
        str(work),
        "/work",
        "--chdir",
        "/work",
        "--setenv",
        "HOME",
        "/work",
        "--setenv",
        "PATH",
        "/usr/bin:/bin",
        "--clearenv" if False else "--unsetenv",
        "LD_PRELOAD",
    ]
    for extra in ("/lib64", "/etc/alternatives", "/etc/ld.so.cache"):
        if Path(extra).exists():
            argv += ["--ro-bind", extra, extra]
    return argv + ["--"] + command


def run(
    command: list[str],
    *,
    work: Path | str,
    cpu: int = CPU_SECONDS,
    memory: int = MEMORY_BYTES,
    file_size: int = FILE_SIZE_BYTES,
    wall: int = WALL_SECONDS,
    isolate: bool = True,
) -> SandboxResult:
    """Run one command against untrusted material, as contained as possible."""
    import time

    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    for forbidden in NEVER_MOUNT:
        if str(work).startswith(forbidden) and shutil.which("bwrap") is None:
            # Without bwrap the child really can see this path's neighbours.
            pass

    argv = list(command)
    isolation = "rlimit"
    if isolate and shutil.which("bwrap"):
        argv = _bwrap(work, argv)
        isolation = "bwrap+rlimit"

    environment = {"PATH": "/usr/bin:/bin", "HOME": str(work), "LC_ALL": "C", "TMPDIR": str(work)}
    started = time.time()
    try:
        done = subprocess.run(
            argv,
            cwd=str(work),
            env=environment,
            capture_output=True,
            text=True,
            timeout=wall,
            preexec_fn=_limits(
                cpu, memory, file_size, cap_processes=not isolation.startswith("bwrap")
            ),
        )
        result = SandboxResult(
            command=argv,
            returncode=done.returncode,
            stdout=done.stdout[:OUTPUT_LIMIT],
            stderr=done.stderr[:OUTPUT_LIMIT],
        )
    except subprocess.TimeoutExpired as expired:
        result = SandboxResult(
            command=argv,
            returncode=-9,
            timed_out=True,
            stdout=(expired.stdout or b"").decode("utf-8", "replace")[:OUTPUT_LIMIT]
            if isinstance(expired.stdout, bytes)
            else (expired.stdout or "")[:OUTPUT_LIMIT],
            stderr=f"killed after {wall}s",
        )
    except OSError as error:
        result = SandboxResult(command=argv, returncode=-1, stderr=str(error))

    result.seconds = round(time.time() - started, 2)
    result.isolation = isolation
    result.isolated = isolation.startswith("bwrap")
    if not result.isolated:
        result.note = (
            "bubblewrap is not available, so resource limits applied but"
            " the filesystem was not isolated; do not run untrusted code"
            " that writes outside the work directory"
        )
    result.artifacts = sorted(p.name for p in work.iterdir() if p.is_file())
    return result


def syntax_check(
    source: Path | str,
    *,
    include_dir: Path | str | None = None,
    work: Path | str | None = None,
    abaqus_shim: bool = True,
) -> SandboxResult:
    """Compile one scraped source for syntax only, in the sandbox.

    Copies the source in rather than binding its directory: a file that is
    read where it lives is a file whose neighbours are also reachable.

    ``abaqus_shim`` stages a minimal ``ABA_PARAM.INC`` when the source
    includes one and no real copy was supplied. Without it every genuine UMAT
    stops at its first INCLUDE and the check reports "cannot open
    ABA_PARAM.INC" for all of them, which says nothing about the Fortran. The
    staged copy is named in the note, so the result cannot be mistaken for a
    compile against the real Abaqus headers.
    """
    source = Path(source)
    owned = work is not None
    work = Path(work) if owned else Path(tempfile.mkdtemp(prefix="council-sandbox-"))
    work.mkdir(parents=True, exist_ok=True)
    shimmed = False
    try:
        staged = work / source.name
        shutil.copyfile(source, staged)
        supplied = set()
        if include_dir:
            for extra in Path(include_dir).glob("*.[iI][nN][cC]"):
                shutil.copyfile(extra, work / extra.name)
                supplied.add(extra.name.upper())
        if abaqus_shim and "ABA_PARAM.INC" not in supplied:
            text = staged.read_bytes().decode("utf-8", "replace").upper()
            if "ABA_PARAM.INC" in text:
                for name in ("ABA_PARAM.INC", "aba_param.inc"):
                    (work / name).write_text(ABA_PARAM)
                shimmed = True
        result = run(
            ["gfortran", "-fsyntax-only", "-ffree-line-length-none", "-I", ".", staged.name],
            work=work,
        )
        note = [result.note.strip(), f"source={source.name}"]
        if shimmed:
            note.append(
                "a minimal ABA_PARAM.INC was staged; this is not a compile"
                " against the real Abaqus headers"
            )
        result.note = " ".join(part for part in note if part)
        return result
    finally:
        if not owned:
            shutil.rmtree(work, ignore_errors=True)
