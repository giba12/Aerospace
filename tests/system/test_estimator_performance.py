"""Acceptance tests for the filter's performance on HELD-OUT seeds (EST-008, EST-012, TST-012).

These run the real `sim` once per held-out seed through python/ensemble.py, the same code that
writes the validation record (docs/VALIDATION.md). They use only `HELD_OUT_SEEDS`; a test in
tests/python/test_seed_sets.py enforces that. Thresholds are the baseline's and were checked
against the separate tuning seeds beforehand (OI-02). If one of these fails, fix the filter or
document the limit. Do not loosen a threshold or change the seeds to make it pass (R-05).
"""
import pathlib

import pytest

import ensemble
from seed_sets import HELD_OUT_SEEDS


@pytest.fixture(scope="module")
def held_out(sim_bin):
    """The reference scenario (default flags) on each held-out seed, run once."""
    results, sidecar = ensemble.run_ensemble(sim_bin, HELD_OUT_SEEDS)
    return results, ensemble.summarize(results), sidecar


@pytest.mark.req("EST-008", "SYS-004")
def test_the_estimate_beats_the_raw_readings_on_every_held_out_seed(held_out):
    _, summary, _ = held_out
    assert summary["val02_pass"], (
        f"seed {summary['worst_seed']}: estimate/raw RMSE ratio {summary['ratio_max']:.3f} "
        f"> {ensemble.MAX_RATIO} (seeds over the limit: {summary['seeds_over_limit']})")


@pytest.mark.req("EST-012", "SYS-004")
def test_the_filters_error_bars_are_honest_on_the_pooled_held_out_seeds(held_out):
    _, summary, _ = held_out
    assert summary["val03_pass"], (
        f"pooled +/-2 sigma coverage {summary['pooled_coverage']:.4f} < {ensemble.MIN_COVERAGE} "
        f"({summary['pooled_inside']} of {summary['pooled_total']} errors inside)")


@pytest.mark.req("DOC-001", "SYS-004")
def test_the_readme_and_the_validation_record_quote_the_figures_this_ensemble_produces(held_out):
    """VAL-07: the headline numbers in the README and docs/VALIDATION.md are the ones the tool computes now.
    Like the README's other digits, they depend on the C++ standard library's noise, so any other
    compiler than GCC 13 / Clang 18 is skipped with the reason."""
    _, s, sidecar = held_out
    if not sidecar["compiler"].startswith(("gcc 13", "clang 18")):
        pytest.skip(f"figures recorded with GCC 13 / Clang 18 and libstdc++, not {sidecar['compiler']}")
    root = pathlib.Path(__file__).resolve().parents[2]
    readme = " ".join((root / "README.md").read_text(encoding="utf-8").split())
    assert f"{s['ratio_min']:.2f} to {s['ratio_max']:.2f} times the raw readings' RMSE" in readme
    assert f"{100 * s['pooled_coverage']:.1f} % of the true positions" in readme
    record = (root / "docs" / "VALIDATION.md").read_text(encoding="utf-8")
    assert f"worst ratio {s['ratio_max']:.3f} (seed {s['worst_seed']})" in record
    assert f"{s['pooled_coverage']:.4f} ({s['pooled_inside']} of {s['pooled_total']})" in record
