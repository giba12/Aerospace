"""TST-012: the tuning seeds and the held-out seeds must never overlap (baseline CR-06, R-05)."""
import pathlib

import pytest

import seed_sets

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.req("TST-012")
def test_tuning_and_held_out_seeds_are_disjoint():
    assert not set(seed_sets.TUNING_SEEDS) & set(seed_sets.HELD_OUT_SEEDS)


@pytest.mark.req("TST-012", "EST-012")
def test_held_out_set_is_big_enough_and_each_set_is_valid():
    assert len(seed_sets.HELD_OUT_SEEDS) >= 20  # EST-012: "pooled over >= 20 seeds"
    for seeds in (seed_sets.TUNING_SEEDS, seed_sets.HELD_OUT_SEEDS):
        assert len(set(seeds)) == len(seeds), "duplicate seed"
        assert all(isinstance(s, int) and 0 <= s < 2**64 for s in seeds)


@pytest.mark.req("TST-012")
def test_acceptance_tests_use_only_the_held_out_seeds():
    """Inspection made automatic: the acceptance test file must not even name the tuning set."""
    text = (ROOT / "tests" / "system" / "test_estimator_performance.py").read_text()
    assert "HELD_OUT_SEEDS" in text
    assert "TUNING_SEEDS" not in text
