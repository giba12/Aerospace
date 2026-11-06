"""The README's quoted results are checked against fresh runs, so a stale number cannot survive (VAL-07).

The digits in the README come from GCC 13.3 with libstdc++, and Clang 18 with the same library prints the
same ones (CI runs this on both). With any other compiler or standard library the noise differs, so the
checks that compare digits are skipped there, loudly and with the reason, rather than failing for a
documented platform difference.
"""
import json
import pathlib
import re
import subprocess
import sys

import pytest

import analyze

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _raw_readme():
    return (ROOT / "README.md").read_text(encoding="utf-8")


def _readme():
    """The README with every run of whitespace collapsed, so a sentence wrapped over lines still matches."""
    return " ".join(_raw_readme().split())


@pytest.fixture
def reference_run(run_sim, tmp_path):
    """The README's step 4 on the default scenario: the CSV rows and the metrics `analyze.py` prints."""
    assert run_sim("--steps", "1000", "--out", "run.csv").returncode == 0
    compiler = json.loads((tmp_path / "run.csv.config.json").read_text())["compiler"]
    if not compiler.startswith(("gcc 13", "clang 18")):
        pytest.skip(f"the README digits are from GCC 13 / Clang 18 with libstdc++, not {compiler}")
    done = subprocess.run([sys.executable, analyze.__file__, str(tmp_path / "run.csv")],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    printed = dict(line.split(" = ") for line in done.stdout.splitlines())
    return analyze.read_rows(tmp_path / "run.csv"), printed


@pytest.mark.req("DOC-001", "SYS-004")
def test_the_readmes_expected_output_block_is_what_a_fresh_run_prints(reference_run):
    _, printed = reference_run
    block = re.search(r"## Expected output.*?```text\n(.*?)```", _raw_readme(), re.S).group(1)
    quoted = dict(line.split(" = ") for line in block.strip().splitlines())
    assert quoted, "the README has no expected-output block"
    for key, value in quoted.items():
        assert printed[key] == value, f"README says {key} = {value}, a fresh run prints {printed[key]}"


@pytest.mark.req("DOC-001", "SYS-004")
def test_the_readmes_prose_numbers_match_the_same_run(reference_run):
    _, printed = reference_run
    readme = _readme()
    raw, est, vel = (float(printed[k]) for k in ("rmse_meas_pos_m", "rmse_est_pos_m", "rmse_est_vel_mps"))
    assert f"raw readings are off by {raw:.2f} m" in readme
    assert f"position estimate by {est:.2f} m (a ratio of {est / raw:.2f})" in readme
    assert f"by {vel:.2f} m/s" in readme
    assert f"{printed['n_measurements']} steps that have a reading" in readme
    assert f"{printed['n_within_2sigma']} of the {printed['n_measurements']} readings" in readme
    assert f"{100 * float(printed['frac_pos_within_2sigma']):.0f} % for this seed" in readme


@pytest.mark.req("DOC-001", "SYS-004")
def test_the_velocity_estimate_is_within_one_mps_of_the_truth_from_five_seconds_on(reference_run):
    rows, _ = reference_run
    assert "within 1 m/s of the true 10 m/s from about 5 s on" in _readme()
    late = [abs(float(r["est_vel_mps"]) - float(r["true_vel_mps"])) for r in rows if float(r["t_s"]) >= 5.0]
    assert late and max(late) <= 1.0, f"largest late velocity error is {max(late):.3f} m/s"
