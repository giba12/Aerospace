"""Unit tests for python/analyze.py against hand-computed values (oracle: arithmetic by hand)."""
import pytest

import analyze


def _row(step, true_pos, meas, est_pos, true_vel=10.0, est_vel=0.0, est_var=0.0):
    return {"step": str(step), "t_s": "0", "true_pos_m": str(true_pos), "true_vel_mps": str(true_vel),
            "meas_pos_m": "" if meas is None else str(meas),
            "est_pos_m": str(est_pos), "est_vel_mps": str(est_vel),
            "est_pos_var_m2": str(est_var), "est_vel_var_m2s2": "0"}


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


def _csv_text(*data_lines):
    return ",".join(analyze.EXPECTED_HEADER) + "\n" + "".join(line + "\n" for line in data_lines)


GOOD_LINE = "0,0,1,10,1,1,0,0,0"


@pytest.mark.req("ANA-001", "ANA-002")
@pytest.mark.parametrize("column, bad, fragment", [
    ("true_pos_m", "abc", "not a number"),
    ("meas_pos_m", "1.2.3", "not a number"),
    ("est_pos_m", "", "missing"),
    ("est_vel_mps", "   ", "missing"),
    ("true_vel_mps", "nan", "not finite"),
    ("est_pos_m", "inf", "not finite"),
])
def test_bad_numeric_cell_is_a_clean_error_naming_row_and_column(column, bad, fragment):
    row = _row(7, 1.0, 1.0, 1.0)
    row[column] = bad
    with pytest.raises(analyze.CsvFormatError) as e:
        analyze.compute_metrics([_row(0, 0.0, 0.0, 0.0), row])
    message = str(e.value)
    assert fragment in message
    assert column in message
    assert "data row 1" in message and "step '7'" in message


@pytest.mark.req("ANA-001")
@pytest.mark.parametrize("line", ["0,0,1,10", GOOD_LINE + ",extra"])
def test_row_with_wrong_field_count_is_rejected(tmp_path, line):
    path = tmp_path / "ragged.csv"
    path.write_text(_csv_text(GOOD_LINE, line))
    with pytest.raises(analyze.CsvFormatError, match="line 3"):
        analyze.read_rows(path)


@pytest.mark.req("ANA-001")
def test_non_text_file_is_rejected_not_a_traceback(tmp_path):
    path = tmp_path / "binary.csv"
    path.write_bytes(b"\xff\xfe\x00\x80")
    with pytest.raises(analyze.CsvFormatError):
        analyze.read_rows(path)


@pytest.mark.req("ANA-001", "ANA-002")
def test_cli_reports_bad_cell_on_stderr_with_exit_1(tmp_path, capsys):
    path = tmp_path / "bad_cell.csv"
    path.write_text(_csv_text("0,0,abc,10,1,1,0,0,0"))
    assert analyze.main([str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.err.startswith("analyze: error: ")
    assert "true_pos_m" in captured.err
    assert captured.out == ""


@pytest.mark.req("ANA-001")
def test_good_file_still_reads(tmp_path):
    path = tmp_path / "good.csv"
    path.write_text(_csv_text(GOOD_LINE))
    assert analyze.compute_metrics(analyze.read_rows(path))["n_measurements"] == 1


@pytest.mark.req("ANA-004")
def test_two_sigma_coverage_on_a_known_input():
    # Variance 4 means the filter reports a standard deviation of 2, so the +/-2 sigma bound is 4.
    rows = [
        _row(0, 0.0, 0.0, 3.0, est_var=4.0),    # error 3.0: inside
        _row(1, 0.0, 0.0, -4.0, est_var=4.0),   # error 4.0: exactly on the bound counts as inside
        _row(2, 0.0, 0.0, 4.5, est_var=4.0),    # error 4.5: outside
        _row(3, 0.0, None, 99.0, est_var=4.0),  # no measurement: not part of the sample (ANA-002)
    ]
    m = analyze.compute_metrics(rows)
    assert m["n_measurements"] == 3
    assert m["n_within_2sigma"] == 2
    assert m["frac_pos_within_2sigma"] == pytest.approx(2 / 3)


@pytest.mark.req("ANA-004")
def test_a_zero_variance_covers_only_a_zero_error():
    rows = [_row(0, 5.0, 5.0, 5.0, est_var=0.0), _row(1, 5.0, 5.0, 5.0001, est_var=0.0)]
    assert analyze.compute_metrics(rows)["n_within_2sigma"] == 1


@pytest.mark.req("ANA-004", "ANA-001")
def test_a_negative_variance_is_rejected_not_square_rooted():
    with pytest.raises(analyze.CsvFormatError, match="est_pos_var_m2"):
        analyze.compute_metrics([_row(0, 0.0, 0.0, 0.0, est_var=-1.0)])
