"""System tests for the M3 Kalman filter, driving the real `sim` binary (TST-008)."""
import pytest

import analyze


def _rows(tmp_path, name):
    return analyze.read_rows(tmp_path / name)


@pytest.mark.req("CFG-003")
def test_filter_assumption_is_independent_of_the_sensors_true_noise(run_sim, tmp_path):
    """Same sensor (same sigma, same seed), different assumed R: the readings are identical
    but the estimates are not. If R were silently derived from sigma, the estimates would match."""
    common = ["--steps", "300", "--sigma", "5", "--seed", "11"]
    assert run_sim(*common, "--est-r", "25", "--out", "a.csv").returncode == 0
    assert run_sim(*common, "--est-r", "1", "--out", "b.csv").returncode == 0
    a, b = _rows(tmp_path, "a.csv"), _rows(tmp_path, "b.csv")
    assert [r["meas_pos_m"] for r in a] == [r["meas_pos_m"] for r in b]
    assert [r["est_pos_m"] for r in a] != [r["est_pos_m"] for r in b]


@pytest.mark.req("CFG-003")
def test_changing_sigma_alone_does_not_change_the_filters_assumed_r(run_sim, tmp_path):
    for name, sigma in (("a.csv", "1"), ("b.csv", "20")):
        assert run_sim("--sigma", sigma, "--out", name).returncode == 0
    import json
    r = lambda n: json.loads((tmp_path / f"{n}.config.json").read_text())["est_r_m2"]
    assert r("a.csv") == r("b.csv") == 25


@pytest.mark.req("CFG-002", "EST-010")
@pytest.mark.parametrize("args, parameter", [
    (["--est-r", "0"], "r_m2"),
    (["--est-r", "-3"], "r_m2"),
    (["--est-q", "-1"], "q_m2ps3"),
    (["--est-p0-pos", "-1"], "p0_pos_m2"),
    (["--est-p0-vel", "nan"], "p0_vel_m2ps2"),
    (["--est-r", "abc"], "--est-r"),
])
def test_bad_filter_settings_exit_2_name_the_parameter_and_write_nothing(run_sim, tmp_path, args, parameter):
    result = run_sim(*args, "--out", "run.csv")
    assert result.returncode == 2
    assert result.stderr.startswith("sim: error: ")
    assert parameter in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.req("EST-009")
def test_filter_starts_at_the_first_reading_with_no_predict_step(run_sim, tmp_path):
    # The sensor always reads at step 0, so the estimator starts there. (The "empty before the
    # first reading" case is covered by the runner call-order test.)
    assert run_sim("--steps", "10", "--out", "run.csv").returncode == 0
    rows = _rows(tmp_path, "run.csv")
    assert all(r["est_pos_m"] != "" for r in rows)
    first = rows[0]
    assert first["est_pos_m"] == first["meas_pos_m"]  # initialized at the reading, no predict
    assert (first["est_vel_mps"], first["est_pos_var_m2"], first["est_vel_var_m2s2"]) == ("0", "25", "100")
