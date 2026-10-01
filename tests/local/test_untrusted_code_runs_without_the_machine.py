"""Scraped Fortran compiles with no home directory, no network and a clock.

These tests run real commands under the sandbox. They are not mocked: a mocked
sandbox test passes on a machine where the sandbox does not work, which is
exactly the failure that happened while this module was written -- an rlimit
made bubblewrap fail to start, every escape attempt produced empty output, and
the emptiness looked like containment.
"""

from __future__ import annotations

import shutil

import pytest

from council_local.sandbox import available, run, syntax_check

needs_bwrap = pytest.mark.skipif(
    shutil.which("bwrap") is None, reason="bubblewrap is not installed"
)
needs_gfortran = pytest.mark.skipif(
    shutil.which("gfortran") is None, reason="gfortran is not installed"
)


@needs_bwrap
def test_the_sandbox_actually_starts(tmp_path):
    """The guard against the false negative: prove a command ran at all."""
    result = run(["sh", "-c", "echo RAN"], work=tmp_path)
    assert result.returncode == 0
    assert "RAN" in result.stdout
    assert result.isolated


@needs_bwrap
def test_the_home_directory_is_not_visible(tmp_path):
    result = run(["sh", "-c", "ls /home"], work=tmp_path)
    assert "softwarex_work" not in result.stdout
    assert "No such file" in result.stdout or result.returncode != 0


@needs_bwrap
def test_there_is_no_network(tmp_path):
    result = run(["sh", "-c", "getent hosts github.com || echo NO_NETWORK"], work=tmp_path)
    assert "NO_NETWORK" in result.stdout


@needs_bwrap
def test_the_work_directory_is_writable(tmp_path):
    result = run(["sh", "-c", "echo hi > out.txt && cat out.txt"], work=tmp_path)
    assert "hi" in result.stdout
    assert "out.txt" in result.artifacts


@needs_bwrap
def test_a_runaway_command_is_killed(tmp_path):
    result = run(["sh", "-c", "sleep 30"], work=tmp_path, wall=2)
    assert result.timed_out
    assert not result.ok


@needs_bwrap
@needs_gfortran
def test_a_valid_source_compiles_and_an_invalid_one_reports_why(tmp_path):
    good = tmp_path / "good.f90"
    good.write_text("program p\n  print *, 1\nend program\n")
    assert syntax_check(good, work=tmp_path / "w1").ok

    bad = tmp_path / "bad.f90"
    bad.write_text("program p\n  this is not fortran (\nend program\n")
    result = syntax_check(bad, work=tmp_path / "w2")
    assert not result.ok
    assert "Error" in result.stderr


def test_the_report_says_how_contained_the_run_really_was(tmp_path):
    """Never claim isolation that was not achieved."""
    result = run(["sh", "-c", "echo x"], work=tmp_path, isolate=False)
    assert not result.isolated
    assert result.isolation == "rlimit"
    assert "not isolated" in result.note


def test_available_reports_what_this_machine_offers():
    offered = available()
    assert set(offered) == {"bwrap", "podman", "docker", "gfortran"}


@needs_bwrap
@needs_gfortran
def test_a_real_umat_compiles_once_the_abaqus_include_is_staged(tmp_path):
    """Every genuine UMAT includes ABA_PARAM.INC, which Abaqus supplies.

    Without the shim the check reports "cannot open ABA_PARAM.INC" for the
    whole corpus, which is a fact about the solver's absence and not about
    the Fortran. With it, the result has to say so.
    """
    source = tmp_path / "umat.for"
    source.write_text(
        "      SUBROUTINE UMAT(STRESS,NTENS)\n"
        "      INCLUDE 'ABA_PARAM.INC'\n"
        "      DIMENSION STRESS(NTENS)\n"
        "      STRESS(1) = 1.D0\n"
        "      RETURN\n"
        "      END\n"
    )

    shimmed = syntax_check(source, work=tmp_path / "with")
    assert shimmed.ok
    assert "ABA_PARAM.INC was staged" in shimmed.note
    assert "real Abaqus headers" in shimmed.note

    bare = syntax_check(source, work=tmp_path / "without", abaqus_shim=False)
    assert not bare.ok
    assert "ABA_PARAM.INC" in bare.stderr


@needs_bwrap
@needs_gfortran
def test_the_shim_is_not_staged_for_a_source_that_does_not_ask_for_it(tmp_path):
    source = tmp_path / "plain.f90"
    source.write_text("program p\n  print *, 1\nend program\n")
    result = syntax_check(source, work=tmp_path / "w")
    assert result.ok
    assert "ABA_PARAM" not in result.note
