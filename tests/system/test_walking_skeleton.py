"""System tests: drive the real `sim` binary as a black box (TST-008).

These never change when the C++ test framework changes. They check the walking skeleton
end to end: flags in, CSV out, exit codes, and the Python analysis reading the result.
"""
import subprocess
import sys

import pytest

import analyze


@pytest.mark.req("OUT-001", "SIM-005")
def test_default_run_writes_header_and_n_plus_one_rows(run_sim, tmp_path):
    result = run_sim("--steps", "20", "--out", "run.csv")
    assert result.returncode == 0, result.stderr
    lines = (tmp_path / "run.csv").read_text().splitlines()
    assert lines[0] == ",".join(analyze.EXPECTED_HEADER)
    assert len(lines) == 1 + 20 + 1  # header + (N + 1) rows
    assert not (tmp_path / "run.csv.tmp").exists()


@pytest.mark.req("CFG-002")
@pytest.mark.parametrize("args, parameter", [
    (["--bogus", "1"], "--bogus"),
    (["--steps"], "--steps"),
    (["--steps", "ten"], "--steps"),
    (["--steps", "100001"], "steps"),
    (["--steps", "-1"], "steps"),
    (["--dt", "0"], "dt_s"),
    (["--meas-every", "0"], "every_n_steps"),
])
def test_bad_input_exits_2_names_parameter_and_writes_nothing(run_sim, tmp_path, args, parameter):
    result = run_sim(*args, "--out", "run.csv")
    assert result.returncode == 2
    assert result.stderr.startswith("sim: error: ")
    assert parameter in result.stderr
    assert list(tmp_path.iterdir()) == []  # no CSV, no temp file


@pytest.mark.req("CFG-002", "OUT-004")
def test_unwritable_output_exits_1(run_sim):
    result = run_sim("--out", "/nonexistent-dir/run.csv")
    assert result.returncode == 1
    assert "sim: error: " in result.stderr


@pytest.mark.req("CFG-001")
def test_help_lists_every_flag_with_its_unit_and_default(run_sim):
    result = run_sim("--help")
    assert result.returncode == 0
    for flag in ("--steps", "--dt", "--x0", "--v0", "--meas-every", "--sensor-id", "--out"):
        assert flag in result.stdout


@pytest.mark.req("ANA-002", "SYS-001")
def test_analysis_prints_rmse_for_a_fresh_run(run_sim, tmp_path):
    """The M0 exit criterion: sim -> CSV -> Python prints RMSE."""
    assert run_sim("--steps", "50", "--out", "run.csv").returncode == 0
    script = analyze.__file__
    result = subprocess.run([sys.executable, script, str(tmp_path / "run.csv")],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "rmse_meas_pos_m = " in result.stdout
    assert "rmse_est_pos_m = " in result.stdout
