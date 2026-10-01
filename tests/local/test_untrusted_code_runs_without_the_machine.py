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
