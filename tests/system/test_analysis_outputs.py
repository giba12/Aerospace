"""System tests for analyze.py driving a real `sim` run: the metrics file, the plot, and the checks."""
import json
import subprocess
import sys

import pytest

import analyze

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _analyze(*args):
    return subprocess.run([sys.executable, analyze.__file__, *map(str, args)],
                          capture_output=True, text=True)


@pytest.mark.req("ANA-005", "ANA-003", "ANA-004", "SYS-004")
def test_one_command_prints_the_metrics_and_writes_the_json_and_the_plot(run_sim, tmp_path):
    assert run_sim("--out", "run.csv").returncode == 0
    done = _analyze(tmp_path / "run.csv", "--metrics-json", tmp_path / "m.json", "--plot", tmp_path / "p.png")
    assert done.returncode == 0, done.stderr

    saved = json.loads((tmp_path / "m.json").read_text())
    expected = analyze.metrics_for_json(analyze.compute_metrics(analyze.read_rows(tmp_path / "run.csv")))
    assert saved == expected
    assert 0.0 < saved["improvement_ratio"] < 0.75          # the filter helps on the reference scenario
    assert 0.0 <= saved["frac_pos_within_2sigma"] <= 1.0
    for key in ("rmse_est_pos_m", "frac_pos_within_2sigma", "improvement_ratio"):
        assert f"{key} = " in done.stdout                    # also printed
    assert (tmp_path / "p.png").read_bytes().startswith(PNG_SIGNATURE)


@pytest.mark.req("ANA-005")
def test_an_exact_sensor_gives_a_null_improvement_ratio_in_the_file(run_sim, tmp_path):
    assert run_sim("--sigma", "0", "--steps", "100", "--out", "run.csv").returncode == 0
    assert _analyze(tmp_path / "run.csv", "--metrics-json", tmp_path / "m.json").returncode == 0
    assert json.loads((tmp_path / "m.json").read_text())["improvement_ratio"] is None


@pytest.mark.req("ANA-001")
def test_analyze_refuses_a_csv_whose_sidecar_has_an_unknown_version(run_sim, tmp_path):
    assert run_sim("--steps", "50", "--out", "run.csv").returncode == 0
    side_path = tmp_path / "run.csv.config.json"
    side = json.loads(side_path.read_text())
    side["schema_version"] = 2
    side_path.write_text(json.dumps(side))
    done = _analyze(tmp_path / "run.csv", "--metrics-json", tmp_path / "m.json")
    assert done.returncode == 1
    assert "schema_version" in done.stderr
    assert not (tmp_path / "m.json").exists()   # nothing written from a file it does not understand


@pytest.mark.req("ANA-001")
def test_analyze_refuses_a_csv_with_no_sidecar_or_the_wrong_one(run_sim, tmp_path):
    assert run_sim("--steps", "50", "--out", "a.csv").returncode == 0
    assert run_sim("--steps", "80", "--out", "b.csv").returncode == 0
    (tmp_path / "a.csv.config.json").replace(tmp_path / "gone.json")
    assert "not found" in _analyze(tmp_path / "a.csv").stderr
    (tmp_path / "b.csv.config.json").replace(tmp_path / "a.csv.config.json")   # b's settings next to a's CSV
    done = _analyze(tmp_path / "a.csv")
    assert done.returncode == 1 and "same run" in done.stderr


@pytest.mark.req("ANA-003", "ANA-005")
@pytest.mark.parametrize("flag", ["--plot", "--metrics-json"])
def test_an_unwritable_output_path_is_reported_before_any_slow_work(run_sim, tmp_path, flag):
    assert run_sim("--steps", "50", "--out", "run.csv").returncode == 0
    done = _analyze(tmp_path / "run.csv", flag, "/nonexistent-dir/out")
    assert done.returncode == 1
    assert "analyze: error" in done.stderr and flag in done.stderr and "does not exist" in done.stderr
    assert done.stdout == ""   # no metrics printed for a run that could not save what was asked
