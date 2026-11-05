"""Unit tests for python/kalman_oracle.py, the independent re-computation of the filter."""
import json
from decimal import Decimal, localcontext

import pytest

import kalman_oracle as oracle

# VV-EST-01 (baseline 6.6): x = [0, 10], P = diag(25, 100), dt = 0.1, q = 0.1, R = 25, z = 3.
START = (0.0, 10.0, 25.0, 0.0, 0.0, 100.0)


@pytest.mark.req("EST-001")
def test_oracle_reproduces_the_hand_vector_vv_est_01():
    """The oracle is a second implementation; it must hit the same hand-worked numbers as the C++."""
    x, v, p00, p01, p10, p11 = oracle.predict_step(START, 0.1, 0.1)
    assert (x, v) == pytest.approx((1.0, 10.0), abs=1e-9)
    assert (p00, p01, p10, p11) == pytest.approx((26.0000333333, 10.0005, 10.0005, 100.01), abs=1e-9)

    x, v, p00, p01, p10, p11 = oracle.update_step(oracle.predict_step(START, 0.1, 0.1), 3.0, 25.0)
    assert (x, v) == pytest.approx((2.0196084839, 10.3921762143), abs=1e-9)
    assert (p00, p01, p10, p11) == pytest.approx(
        (12.7451060490, 4.9022026783, 4.9022026783, 98.0490208846), abs=1e-9)


@pytest.mark.req("EST-009")
def test_replay_starts_at_the_first_reading_without_a_predict_step():
    out = oracle.replay([None, None, 7.0, None], dt=0.1, q=0.1, r=25.0, p0_pos=25.0, p0_vel=100.0)
    assert out[0] is None and out[1] is None                 # nothing to estimate before a reading
    assert out[2] == (7.0, 0.0, 25.0, 100.0)                 # exactly the reading, exactly P0
    assert out[3][0] == pytest.approx(7.0)                   # next step predicts: velocity is 0
    assert out[3][2] > 25.0                                  # and the doubt has grown


@pytest.mark.req("EST-011")
def test_short_update_form_in_doubles_loses_digits_that_the_oracle_keeps():
    """Why the C++ uses the Joseph form. After 20,000 steps with no reading the position variance
    is about 7e8; the update then subtracts two nearly equal huge numbers. In plain doubles the
    short form is off by about 2e-8, already beyond the project's own 1e-9 tolerance (CR-26).
    The oracle's 60-digit arithmetic does not have this problem."""
    steps = 20000
    in_doubles = (0.0, 0.0, 25.0, 0.0, 0.0, 100.0)
    for _ in range(steps):
        in_doubles = oracle.predict_step(in_doubles, 0.1, 0.1)
    short_in_doubles = oracle.update_step(in_doubles, 3.0, 25.0)[2]
    exact = oracle.replay([0.0] + [None] * (steps - 1) + [3.0], 0.1, 0.1, 25.0, 25.0, 100.0)[-1][2]
    assert abs(short_in_doubles - exact) > 1e-9


@pytest.mark.req("EST-001")
def test_allowance_is_the_floor_for_small_values_and_grows_with_step_and_size():
    assert oracle.allowed_difference(10, 5.0) == 1e-9
    big = oracle.allowed_difference(100000, 4.3e10)
    assert big == pytest.approx(2 * 100000 * 2.0 ** -53 * 4.3e10)
    assert big > 0.9  # about one unit in the last place per step at that magnitude, doubled


@pytest.mark.req("EST-001")
def test_sidecar_with_null_estimator_settings_cannot_be_replayed(tmp_path):
    side = tmp_path / "run.csv.config.json"
    side.write_text(json.dumps({"dt_s": 0.1, "est_q_m2ps3": None, "est_r_m2": 25.0,
                                "est_p0_pos_m2": 25.0, "est_p0_vel_m2ps2": 100.0}))
    with pytest.raises(oracle.OracleError, match="est_q_m2ps3"):
        oracle.load_settings(side)
