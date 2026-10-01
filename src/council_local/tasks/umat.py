"""Tasks over UMAT sources: what a file is, what it needs, and why it failed.

Every prompt here follows the same shape, because it is the shape that
survived the probes: the file is quoted with line numbers, the question is
about *that text*, and the model is told what it is not being shown. None of
these tasks asks the model to recall the Abaqus interface -- all three models
on this machine get that wrong from memory and right from the page.
"""

from __future__ import annotations

from pathlib import Path

from ..client import LocalClient
from ..envelope import Envelope
from ..policy import Policy
from ..roster import role_for_task
from ..sources import excerpt, read_text, source_form

#: Typed answers each task demands, so a reply is scoreable without a reader.
CLASSIFY_ANSWERS = {
    "verdict": {
        "type": "string",
        "enum": [
            "genuine_umat",
            "other_entry_point",
            "fragment",
            "driver_or_test",
            "not_fortran_subroutine",
        ],
    },
    "entry_routine": {"type": "string"},
    "entry_line": {"type": "integer"},
    "argument_count": {"type": "integer"},
    "writes_stress": {"type": "boolean"},
    "writes_ddsdde": {"type": "boolean"},
    "complete_subroutine": {"type": "boolean"},
}

CONTRACT_ANSWERS = {
    "max_props_index": {"type": "integer"},
    "max_statev_index": {"type": "integer"},
    "kinematics": {"type": "string", "enum": ["small_strain", "finite_strain", "both", "unclear"]},
    "uses_ntens": {"type": "boolean"},
    "inline_constants": {"type": "array", "items": {"type": "string"}},
    "solver_utilities": {"type": "array", "items": {"type": "string"}},
}

DEPENDENCY_ANSWERS = {
    "includes": {"type": "array", "items": {"type": "string"}},
    "modules_used": {"type": "array", "items": {"type": "string"}},
    "external_calls": {"type": "array", "items": {"type": "string"}},
    "solver_provided": {"type": "array", "items": {"type": "string"}},
    "defined_in_this_file": {"type": "array", "items": {"type": "string"}},
}

TRIAGE_ANSWERS = {
    "category": {
        "type": "string",
        "enum": [
            "missing_include",
            "missing_module",
            "missing_symbol",
            "type_mismatch",
            "syntax_error",
            "array_bounds",
            "out_of_memory",
            "licence",
            "solver_convergence",
            "unknown",
        ],
    },
    "first_error_log_line": {"type": "integer"},
    "first_error_text": {"type": "string"},
    "names_source_file": {"type": "string"},
    "cascade": {"type": "boolean"},
}

REVIEW_ANSWERS = {
    "unseeded_shadows": {"type": "array", "items": {"type": "string"}},
    "unwritten_shadows": {"type": "array", "items": {"type": "string"}},
    "unlifted_calls": {"type": "array", "items": {"type": "string"}},
    "defect_found": {"type": "boolean"},
}

#: The real interface, quoted to the model instead of recalled by it.
UMAT_INTERFACE = (
    "SUBROUTINE UMAT(STRESS,STATEV,DDSDDE,SSE,SPD,SCD,RPL,DDSDDT,DRPLDE,DRPLDT,"
    "STRAN,DSTRAN,TIME,DTIME,TEMP,DTEMP,PREDEF,DPRED,CMNAME,NDI,NSHR,NTENS,"
    "NSTATV,PROPS,NPROPS,COORDS,DROT,PNEWDT,CELENT,DFGRD0,DFGRD1,NOEL,NPT,"
    "LAYER,KSPT,KSTEP,KINC)"
)


def _prepare(path, policy, client):
    """Shared setup: policy check, excerpt, client, role."""
    path = Path(path)
    policy = policy or Policy.load(path.parent)
    policy.check(path)
    return path, policy, client or LocalClient()


def classify_umat(
    path, *, policy: Policy | None = None, client: LocalClient | None = None
) -> Envelope:
    """Is this file a complete Abaqus UMAT, and if not, what is it?

    The distinction that matters for the corpus is not "does it mention UMAT"
    but "does it define the 37-argument entry point and write STRESS". A file
    can contain a UMAT and not be one -- several corpus sources define a UEL
    that calls a UMAT inside the same file.
    """
    path, policy, client = _prepare(path, policy, client)
    piece = excerpt(path, max_lines=600)
    system = role_for_task("classify_umat").system_prompt(
        "decide what a scraped Fortran file actually is"
    )
    prompt = f"""The Abaqus UMAT entry point has this exact interface:

{UMAT_INTERFACE}

Below is {path.name}, with line numbers. {piece.note()}

{piece.text}

Answer these, each as a separate claim citing the line that shows it:
1. Does this file DEFINE a subroutine named UMAT with that argument list?
   Give the line of the SUBROUTINE statement and how many arguments it takes.
2. If it defines a different Abaqus entry point (UEL, UMATHT, VUMAT, HETVAL,
   USDFLD, SDVINI, UEXPAN), name it and give its line.
3. Does it assign to STRESS? Give the line.
4. Does it assign to DDSDDE? Give the line.
5. Is it a complete subroutine (has an END), a fragment, or a driver/test?
6. Your overall verdict, as one of exactly: genuine_umat, other_entry_point,
   fragment, driver_or_test, not_fortran_subroutine.

Put the short answers in "answers". In "claims", each statement must be the
ANSWER as a complete sentence -- never a restatement of the question -- with
the line that shows it.

If the file is too long to show in full and the deciding line is in a part you
cannot see, say that in uncertainties rather than guessing."""
    return client.ask(
        agent="ada",
        task="classify_umat",
        system=system,
        prompt=prompt,
        files_examined=[str(path)],
        root=path.parent,
        num_predict=900,
        answers=CLASSIFY_ANSWERS,
    )


def extract_umat_contract(
    path, *, policy: Policy | None = None, client: LocalClient | None = None
) -> Envelope:
    """What the routine demands: PROPS, STATEV, components, kinematics.

    This is the highest-volume task in the corpus pipeline and the one most
    worth delegating: it is pure extraction from text, with a registry field
    to score every answer against.
    """
    path, policy, client = _prepare(path, policy, client)
    piece = excerpt(path, max_lines=700)
    system = role_for_task("extract_umat_contract").system_prompt(
        "extract the material contract a UMAT demands"
    )
    prompt = f"""Below is {path.name}, with line numbers. {piece.note()}

{piece.text}

Report, each as a claim citing the line it comes from:
1. The highest PROPS index the routine reads, e.g. PROPS(14) means at least 14
   constants. Cite the highest-index line you can see. If PROPS is read in a
   loop with a computed bound, say so and give the bound's line.
2. The highest STATEV index read or written.
3. Whether NTENS, NDI or NSHR are used to size anything, and where.
4. Whether the routine uses DFGRD0/DFGRD1 (finite strain) or only
   STRAN/DSTRAN (small strain). Cite a line for whichever you find. If it uses
   both, say so.
5. Any constant assigned in the source rather than taken from PROPS, with its
   value and line -- these are materials the author published inside the code.
6. Whether it calls SPRINC, SPRIND, ROTSIG, XIT, STDB_ABQERR or any LAPACK
   routine, each with its line.

Put the short answers in "answers". In "claims", each statement must be the
ANSWER as a complete sentence, never a restatement of the question.

Report only indices you can see in the text. Do not extrapolate a maximum."""
    return client.ask(
        agent="ada",
        task="extract_umat_contract",
        system=system,
        prompt=prompt,
        files_examined=[str(path)],
        root=path.parent,
        num_predict=1100,
        answers=CONTRACT_ANSWERS,
    )


def detect_dependencies(
    path, *, policy: Policy | None = None, client: LocalClient | None = None
) -> Envelope:
    """What this file needs that is not in it: INCLUDE, USE, external calls."""
    path, policy, client = _prepare(path, policy, client)
    text = read_text(path)
    piece = excerpt(path, max_lines=600)
    system = role_for_task("detect_dependencies").system_prompt(
        "find everything a source needs that it does not contain"
    )
    prompt = f"""Below is {path.name} ({source_form(text)}-form Fortran), with line
numbers. {piece.note()}

{piece.text}

List, each as a claim with its line:
1. Every INCLUDE directive and the file it names.
2. Every USE statement and the module it names. Careful: a local variable
   whose name starts with "use_" is NOT a USE statement.
3. Every CALL to a routine that is not defined in this file.
4. Every function referenced that is neither a Fortran intrinsic nor defined
   here.
5. For each of the above, whether a definition appears elsewhere in this same
   file -- if it does, it is not a missing dependency.

Fortran intrinsics (SUM, MATMUL, DOT_PRODUCT, MAXVAL, SQRT, ABS, EXP, LOG,
SIGN, MOD, MIN, MAX, TRANSPOSE, SIZE, ...) are not dependencies. Abaqus
utility routines (SPRINC, SPRIND, ROTSIG, XIT, STDB_ABQERR, SINV) are provided
by the solver -- list them separately as solver-provided, not missing.

Put the lists in "answers". In "claims", each statement must be the ANSWER as
a complete sentence, never a restatement of the question."""
    return client.ask(
        agent="ada",
        task="detect_dependencies",
        system=system,
        prompt=prompt,
        files_examined=[str(path)],
        root=path.parent,
        num_predict=1000,
        answers=DEPENDENCY_ANSWERS,
    )


def triage_failure(
    log_text: str,
    *,
    source: Path | str | None = None,
    policy: Policy | None = None,
    client: LocalClient | None = None,
) -> Envelope:
    """Read a compiler or job log and name the first cause, not the loudest.

    A build log's last error is usually a consequence. The task asks for the
    earliest diagnostic and the line it points at, which is the one a fix has
    to address.
    """
    client = client or LocalClient()
    files = []
    context = ""
    if source is not None:
        source = Path(source)
        (policy or Policy.load(source.parent)).check(source)
        piece = excerpt(source, max_lines=300)
        context = f"\n\nThe source it was compiling, {source.name}:\n\n{piece.text}"
        files.append(str(source))
    trimmed = _trim_log(log_text)
    system = role_for_task("triage_failure").system_prompt(
        "name the first cause of a build or job failure"
    )
    prompt = f"""Below is a build or Abaqus job log.

{trimmed}{context}

Answer as claims, citing the log line number (the numbers shown at the left):
1. The EARLIEST diagnostic that is an error rather than a warning or a note.
2. What that diagnostic means in plain terms.
3. The file and source line it points at, if it names one.
4. Which later errors are consequences of the first one, and which are
   independent.
5. One of exactly: missing_include, missing_module, missing_symbol,
   type_mismatch, syntax_error, array_bounds, out_of_memory, licence,
   solver_convergence, unknown -- and why.

If the log shows a cascade, say which single fix would remove the most of it.

Put the short answers in "answers". In "claims", each statement must be the
ANSWER as a complete sentence, never a restatement of the question."""
    return client.ask(
        agent="ada",
        task="triage_failure",
        system=system,
        prompt=prompt,
        files_examined=files,
        num_predict=900,
        answers=TRIAGE_ANSWERS,
    )


def review_transformation(
    original, transformed, *, policy: Policy | None = None, client: LocalClient | None = None
) -> Envelope:
    """Compare an original and a transformed source for the seeding invariants.

    Looks for the defect pattern found in the corpus: a shadow variable that
    is declared and zeroed but never seeded from its real counterpart, or
    never written back -- which produces a routine that runs, compiles and
    silently computes from a state that was discarded.
    """
    original, transformed = Path(original), Path(transformed)
    policy = policy or Policy.load(original.parent)
    policy.check(original)
    policy.check(transformed)
    client = client or LocalClient()
    before = excerpt(original, max_lines=300)
    after = excerpt(transformed, max_lines=500)
    system = role_for_task("review_transformation").system_prompt(
        "find what a source-to-source transform silently dropped"
    )
    prompt = f"""ORIGINAL, {original.name}. {before.note()}

{before.text}

TRANSFORMED, {transformed.name}. {after.note()}

{after.text}

The transform promotes real variables on the stress path to a hypercomplex
shadow type. For each of STRESS, STATEV, DSTRAN, STRAN, DROT, DFGRD0, DFGRD1,
PROPS, report as a claim with the line:
1. Whether a shadow variable exists for it in the transformed source.
2. Whether the shadow is SEEDED from the real argument before the body runs.
3. Whether the shadow is WRITTEN BACK to the real argument before RETURN.

A shadow that is declared and zeroed but never seeded, or never written back,
is a defect: the routine then computes from a state that was discarded. Flag
each one you find explicitly.

Also report any CALL in the transformed source that goes to a routine whose
name has not been changed and which is not defined in the transformed file --
the promoted path would stop there.

Put the lists in "answers". In "claims", each statement must be the ANSWER as
a complete sentence, never a restatement of the question."""
    return client.ask(
        agent="vera",
        task="review_transformation",
        system=system,
        prompt=prompt,
        files_examined=[str(original), str(transformed)],
        root=original.parent,
        num_predict=1200,
        answers=REVIEW_ANSWERS,
    )


def _trim_log(text: str, *, head: int = 60, tail: int = 80) -> str:
    """Number a log and keep both ends: the first cause and the final verdict."""
    lines = text.splitlines()
    if len(lines) <= head + tail:
        return "\n".join(f"{n:4d}| {line}" for n, line in enumerate(lines, 1))
    kept = [f"{n:4d}| {line}" for n, line in enumerate(lines[:head], 1)]
    kept.append(f"    |     ... {len(lines) - head - tail} lines not shown ...")
    start = len(lines) - tail + 1
    kept += [f"{n:4d}| {line}" for n, line in enumerate(lines[-tail:], start)]
    return "\n".join(kept)
