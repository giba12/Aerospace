"""VAL-04: an independent Python re-computation reproduces the C++ filter's output.

Each scenario runs the real `sim`, then rebuilds the `est_*` columns from the CSV's readings and the
sidecar's settings in exact arithmetic. The allowed difference is max(1e-9, 2*k*u*|value|) (CR-26).
"""
import json

import pytest

import analyze
import kalman_oracle as oracle

SCENARIOS = {
    "reference": [],
    "high-noise-other-seed": ["--sigma", "20", "--seed", "7"],
    "accelerating-truth": ["--accel", "0.5"],
    "reading-every-step": ["--meas-every", "1"],
    "sparse-readings": ["--meas-every", "50"],
    "filter-trusts-sensor": ["--est-r", "1e-6", "--sigma", "0"],
    "no-process-noise-certain-start": ["--est-q", "0", "--est-p0-pos", "0", "--est-p0-vel", "0"],
    "mismatched-R": ["--est-r", "1", "--sigma", "5"],
    # Rare readings over a long run make P huge (about 7e8 m^2), then one update collapses it:
    # the ill-conditioned regime where a double-precision oracle itself goes wrong (CR-26).
    "ill-conditioned-long-gap": ["--steps", "20000", "--meas-every", "20000"],
}


def _worst_ratio(csv_path):
    rows = analyze.read_rows(csv_path)
    result = oracle.compare(rows, oracle.load_settings(str(csv_path) + ".config.json"))
    return rows, max(ratio for _, ratio in result.values())


@pytest.mark.req("EST-001")
@pytest.mark.parametrize("name", SCENARIOS)
def test_cpp_filter_agrees_with_the_independent_oracle(run_sim, tmp_path, name):
    assert run_sim(*SCENARIOS[name], "--out", "run.csv").returncode == 0
    _, worst = _worst_ratio(tmp_path / "run.csv")
    assert worst <= 1.0, f"{name}: C++ and oracle differ by {worst:.2f}x what rounding can explain"


@pytest.mark.req("EST-001")
def test_the_crosscheck_notices_a_corrupted_estimate(run_sim, tmp_path):
    """A check that cannot fail proves nothing: nudge one estimate by 1e-6 and it must be caught."""
    assert run_sim("--steps", "100", "--out", "run.csv").returncode == 0
    path = tmp_path / "run.csv"
    lines = path.read_text().splitlines()
    cells = lines[50].split(",")
    cells[5] = repr(float(cells[5]) + 1e-6)   # est_pos_m
    lines[50] = ",".join(cells)
    path.write_text("\n".join(lines) + "\n")
    _, worst = _worst_ratio(path)
    assert worst > 1.0


@pytest.mark.req("EST-009")
def test_the_crosscheck_notices_a_disagreement_about_when_the_filter_starts(run_sim, tmp_path):
    assert run_sim("--steps", "10", "--out", "run.csv").returncode == 0
    path = tmp_path / "run.csv"
    lines = path.read_text().splitlines()
    lines[1] = ",".join(lines[1].split(",")[:5] + ["", "", "", ""])   # blank the step-0 estimate
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(oracle.OracleError, match="started"):
        _worst_ratio(path)


@pytest.mark.req("EST-001")
def test_command_line_tool_reports_success_and_failure(run_sim, tmp_path):
    import subprocess
    import sys
    assert run_sim("--steps", "50", "--out", "run.csv").returncode == 0
    ok = subprocess.run([sys.executable, oracle.__file__, str(tmp_path / "run.csv")],
                        capture_output=True, text=True)
    assert ok.returncode == 0 and "est_pos_m" in ok.stdout
    missing = subprocess.run([sys.executable, oracle.__file__, str(tmp_path / "nope.csv")],
                             capture_output=True, text=True)
    assert missing.returncode == 1 and "kalman_oracle: error" in missing.stderr
