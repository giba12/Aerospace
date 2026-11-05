"""Unit tests for python/ensemble.py's decisions (the arithmetic behind VAL-02 and VAL-03)."""
import pytest

import ensemble


def _result(seed, ratio, inside, total):
    return {"seed": seed, "ratio": ratio, "n_within_2sigma": inside, "n_measurements": total,
            "frac_pos_within_2sigma": inside / total, "rmse_meas_pos_m": 5.0,
            "rmse_est_pos_m": 5.0 * ratio}


@pytest.mark.req("EST-008")
def test_one_bad_seed_fails_val_02_even_if_the_average_is_fine():
    results = [_result(1, 0.40, 95, 100), _result(2, 0.50, 95, 100), _result(3, 0.76, 95, 100)]
    s = ensemble.summarize(results)
    assert s["ratio_mean"] < ensemble.MAX_RATIO         # the average would pass ...
    assert not s["val02_pass"]                          # ... but EST-008 is "on EVERY seed"
    assert s["seeds_over_limit"] == [3] and s["worst_seed"] == 3


@pytest.mark.req("EST-008")
def test_the_ratio_limit_itself_is_allowed():
    assert ensemble.summarize([_result(1, 0.75, 95, 100)])["val02_pass"]


@pytest.mark.req("EST-012")
def test_coverage_is_pooled_from_counts_not_averaged_over_seeds():
    # Seed 1: 10 of 10 inside (1.0). Seed 2: 80 of 90 inside (0.889). Average of fractions = 0.944,
    # but pooled it is 90 of 100 = exactly 0.90. Averaging would hide how the big seed behaves.
    results = [_result(1, 0.4, 10, 10), _result(2, 0.4, 80, 90)]
    s = ensemble.summarize(results)
    assert s["pooled_coverage"] == pytest.approx(0.90)
    assert s["val03_pass"]
    results[1] = _result(2, 0.4, 79, 90)
    assert not ensemble.summarize(results)["val03_pass"]


@pytest.mark.req("SYS-004")
def test_an_exact_sensor_has_no_ratio_and_summarize_says_so():
    bad = _result(1, 0.5, 1, 1)
    bad["ratio"] = None
    with pytest.raises(ValueError, match="raw RMSE of 0"):
        ensemble.summarize([bad])
