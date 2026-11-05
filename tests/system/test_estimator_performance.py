"""Acceptance tests for the filter's performance on HELD-OUT seeds (EST-008, EST-012, TST-012).

These run the real `sim` once per held-out seed. They use only `HELD_OUT_SEEDS`; a test in
tests/python/test_seed_sets.py enforces that. Thresholds are the baseline's and were checked
against the separate tuning seeds beforehand (OI-02). If one of these fails, fix the filter or
document the limit. Do not loosen a threshold or change the seeds to make it pass (R-05).
"""
import subprocess

import pytest

import analyze
from seed_sets import HELD_OUT_SEEDS

MAX_RATIO = 0.75       # EST-008: estimate RMSE <= 0.75 x raw-reading RMSE, on every seed
MIN_COVERAGE = 0.90    # EST-012: pooled +/-2 sigma coverage (a perfect filter scores about 0.95)


@pytest.fixture(scope="module")
def ensemble(sim_bin, tmp_path_factory):
    """metrics for the reference scenario (default flags) on each held-out seed, run once."""
    out_dir = tmp_path_factory.mktemp("held_out")
    results = {}
    for seed in HELD_OUT_SEEDS:
        csv_path = out_dir / f"seed{seed}.csv"
        done = subprocess.run([sim_bin, "--seed", str(seed), "--out", str(csv_path)],
                              capture_output=True, text=True)
        assert done.returncode == 0, f"seed {seed}: {done.stderr}"
        results[seed] = analyze.compute_metrics(analyze.read_rows(csv_path))
    return results


@pytest.mark.req("EST-008", "SYS-004")
def test_the_estimate_beats_the_raw_readings_on_every_held_out_seed(ensemble):
    ratios = {s: m["rmse_est_pos_m"] / m["rmse_meas_pos_m"] for s, m in ensemble.items()}
    worst_seed = max(ratios, key=ratios.get)
    assert ratios[worst_seed] <= MAX_RATIO, (
        f"seed {worst_seed}: estimate/raw RMSE ratio {ratios[worst_seed]:.3f} > {MAX_RATIO}")


@pytest.mark.req("EST-012", "SYS-004")
def test_the_filters_error_bars_are_honest_on_the_pooled_held_out_seeds(ensemble):
    inside = sum(m["n_within_2sigma"] for m in ensemble.values())
    total = sum(m["n_measurements"] for m in ensemble.values())
    assert inside / total >= MIN_COVERAGE, (
        f"pooled +/-2 sigma coverage {inside / total:.4f} < {MIN_COVERAGE} "
        f"({inside} of {total} errors inside)")
