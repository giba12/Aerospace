"""Unit tests for python/analyze.py against hand-computed values (oracle: arithmetic by hand)."""
import pytest

import analyze


def _row(step, true_pos, meas, est_pos, true_vel=10.0, est_vel=0.0):
    return {"step": str(step), "t_s": "0", "true_pos_m": str(true_pos), "true_vel_mps": str(true_vel),
            "meas_pos_m": "" if meas is None else str(meas),
            "est_pos_m": str(est_pos), "est_vel_mps": str(est_vel),
            "est_pos_var_m2": "0", "est_vel_var_m2s2": "0"}


@pytest.mark.req("ANA-002")
def test_rmse_uses_only_rows_with_a_measurement():
    rows = [
        _row(0, 0.0, 3.0, 1.0),    # meas error +3, est error +1
        _row(1, 1.0, None, 99.0),  # no measurement: must be ignored, however wrong the estimate
        _row(2, 2.0, -1.0, 2.0),   # meas error -3, est error 0
    ]
    m = analyze.compute_metrics(rows)
    assert m["n_rows"] == 3
    assert m["n_measurements"] == 2
    assert m["rmse_meas_pos_m"] == pytest.approx(3.0)                 # sqrt((9 + 9) / 2)
    assert m["rmse_est_pos_m"] == pytest.approx((1 / 2) ** 0.5)       # sqrt((1 + 0) / 2)
    assert m["rmse_est_vel_mps"] == pytest.approx(10.0)               # |0 - 10| both rows


@pytest.mark.req("ANA-002")
def test_no_measurements_is_an_error_not_a_division_by_zero():
    with pytest.raises(analyze.CsvFormatError):
        analyze.compute_metrics([_row(0, 0.0, None, 0.0)])


@pytest.mark.req("ANA-001")
def test_wrong_header_is_rejected(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("step,t_s\n0,0\n")
    with pytest.raises(analyze.CsvFormatError):
        analyze.read_rows(bad)
