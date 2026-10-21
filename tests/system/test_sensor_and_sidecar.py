"""System tests for the M2 sensor and the sidecar, driving the real `sim` binary (TST-008)."""
import json
import math
import statistics

import pytest

import analyze

# IF-08 (baseline 8.5): the required keys, in order.
SIDECAR_KEYS = [
    "schema_version", "steps", "dt_s", "x0_m", "v0_mps", "accel_mps2", "meas_every", "sigma_m",
    "seed", "sensor_id", "est_q_m2ps3", "est_r_m2", "est_p0_pos_m2", "est_p0_vel_m2ps2",
    "compiler", "source_revision",
]


def _rows(tmp_path, name="run.csv"):
    return analyze.read_rows(tmp_path / name)


@pytest.mark.req("SEN-004", "SYS-003", "NFR-004")
def test_same_seed_gives_byte_identical_outputs_and_another_seed_differs(run_sim, tmp_path):
    for name, seed in (("a.csv", "7"), ("b.csv", "7"), ("c.csv", "8")):
        assert run_sim("--steps", "200", "--seed", seed, "--out", name).returncode == 0
    read = lambda n: (tmp_path / n).read_bytes()
    assert read("a.csv") == read("b.csv")
    assert read("a.csv.config.json") == read("b.csv.config.json")
    assert read("a.csv") != read("c.csv")
    truth = lambda n: [(r["true_pos_m"], r["true_vel_mps"]) for r in _rows(tmp_path, n)]
    assert truth("a.csv") == truth("c.csv")  # the seed changes the sensor, never the truth


@pytest.mark.req("SEN-004", "SYS-003")
def test_default_run_is_reproducible(run_sim, tmp_path):
    assert run_sim("--steps", "100", "--out", "a.csv").returncode == 0
    assert run_sim("--steps", "100", "--out", "b.csv").returncode == 0
    assert (tmp_path / "a.csv").read_bytes() == (tmp_path / "b.csv").read_bytes()


@pytest.mark.req("SEN-002")
def test_one_reading_every_m_steps_starting_at_step_zero(run_sim, tmp_path):
    assert run_sim("--steps", "100", "--meas-every", "5", "--out", "run.csv").returncode == 0
    with_reading = [int(r["step"]) for r in _rows(tmp_path) if r["meas_pos_m"] != ""]
    assert with_reading == list(range(0, 101, 5))  # 21 readings


@pytest.mark.req("SEN-003")
def test_sigma_zero_reads_the_exact_truth(run_sim, tmp_path):
    assert run_sim("--sigma", "0", "--meas-every", "1", "--accel", "0.7", "--out", "run.csv").returncode == 0
    rows = _rows(tmp_path)
    assert all(r["meas_pos_m"] == r["true_pos_m"] for r in rows)  # same 17-digit text, so exact


@pytest.mark.req("SEN-003")
def test_default_noise_has_the_requested_mean_and_spread(run_sim, tmp_path):
    assert run_sim("--steps", "9999", "--meas-every", "1", "--sigma", "5", "--out", "run.csv").returncode == 0
    noise = [float(r["meas_pos_m"]) - float(r["true_pos_m"]) for r in _rows(tmp_path)]
    assert len(noise) == 10000
    assert abs(statistics.fmean(noise)) < 0.25
    assert statistics.stdev(noise) == pytest.approx(5.0, rel=0.05)


@pytest.mark.req("OUT-003")
def test_sidecar_has_the_contract_keys_and_records_the_run(run_sim, tmp_path):
    args = ["--steps", "50", "--dt", "0.2", "--x0", "3", "--v0", "-4", "--accel", "0.5",
            "--meas-every", "7", "--sigma", "2.5", "--seed", "18446744073709551615",
            "--sensor-id", "gps1", "--out", "out.csv"]
    assert run_sim(*args).returncode == 0
    side = json.loads((tmp_path / "out.csv.config.json").read_text())
    assert list(side) == SIDECAR_KEYS
    assert (side["schema_version"], side["steps"], side["dt_s"], side["x0_m"], side["v0_mps"]) == (1, 50, 0.2, 3, -4)
    assert (side["accel_mps2"], side["meas_every"], side["sigma_m"], side["sensor_id"]) == (0.5, 7, 2.5, "gps1")
    assert side["seed"] == 2**64 - 1
    assert all(side[k] is None for k in SIDECAR_KEYS if k.startswith("est_"))  # no estimator params until M3
    assert side["compiler"].startswith(("gcc ", "clang "))
    assert side["source_revision"] is None or isinstance(side["source_revision"], str)
    assert all(math.isfinite(v) for v in side.values() if isinstance(v, float))


@pytest.mark.req("OUT-003")
def test_sidecar_escapes_an_awkward_sensor_id(run_sim, tmp_path):
    assert run_sim("--sensor-id", 'a"b\\c', "--steps", "1", "--out", "run.csv").returncode == 0
    assert json.loads((tmp_path / "run.csv.config.json").read_text())["sensor_id"] == 'a"b\\c'


@pytest.mark.req("OUT-004", "CFG-002")
def test_runtime_failure_leaves_no_csv_sidecar_or_temp_file(run_sim, tmp_path):
    # Position overflows to infinity at step 1, so the recorder refuses to write it (OUT-005).
    result = run_sim("--v0", "1e308", "--dt", "100", "--steps", "3", "--out", "run.csv")
    assert result.returncode == 1
    assert "non-finite" in result.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.req("OUT-003", "SYS-001")
def test_analysis_reads_a_noisy_run_end_to_end(run_sim, tmp_path):
    assert run_sim("--steps", "1000", "--out", "run.csv").returncode == 0
    metrics = analyze.compute_metrics(_rows(tmp_path))
    assert metrics["n_measurements"] == 201
    assert metrics["rmse_meas_pos_m"] > 0.0  # the sensor is no longer exact
