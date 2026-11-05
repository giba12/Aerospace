"""Unit tests for python/analyze.py against hand-computed values (oracle: arithmetic by hand)."""
import json

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
    (tmp_path / "bad_cell.csv.config.json").write_text(json.dumps(_sidecar(steps=0)))  # one data row
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


# ---- ANA-001: the sidecar and the schema version ----

def _sidecar(**overrides):
    side = {"schema_version": 1, "steps": 2, "dt_s": 0.1, "x0_m": 0.0, "v0_mps": 10.0,
            "accel_mps2": 0.0, "meas_every": 5, "sigma_m": 5.0, "seed": 42, "sensor_id": "pos0",
            "est_q_m2ps3": 0.1, "est_r_m2": 25.0, "est_p0_pos_m2": 25.0, "est_p0_vel_m2ps2": 100.0,
            "compiler": "gcc 13", "source_revision": None}
    side.update(overrides)
    return side


def _write_sidecar(tmp_path, side):
    csv_path = tmp_path / "run.csv"
    (tmp_path / "run.csv.config.json").write_text(json.dumps(side))
    return str(csv_path)


@pytest.mark.req("ANA-001")
def test_a_valid_sidecar_is_read_and_null_estimator_keys_are_allowed(tmp_path):
    side = _sidecar(est_q_m2ps3=None, est_r_m2=None)  # as written by M2, before the filter existed (CR-25)
    assert analyze.read_sidecar(_write_sidecar(tmp_path, side))["steps"] == 2


@pytest.mark.req("ANA-001")
@pytest.mark.parametrize("version", [2, 0, "1", 1.5, None, True])
def test_an_unknown_schema_version_is_rejected(tmp_path, version):
    with pytest.raises(analyze.CsvFormatError, match="schema_version"):
        analyze.read_sidecar(_write_sidecar(tmp_path, _sidecar(schema_version=version)))


@pytest.mark.req("ANA-001")
def test_a_missing_sidecar_a_missing_key_and_bad_json_are_rejected(tmp_path):
    with pytest.raises(analyze.CsvFormatError, match="not found"):
        analyze.read_sidecar(str(tmp_path / "run.csv"))
    side = _sidecar()
    del side["seed"]
    with pytest.raises(analyze.CsvFormatError, match="seed"):
        analyze.read_sidecar(_write_sidecar(tmp_path, side))
    (tmp_path / "run.csv.config.json").write_text("{ not json")
    with pytest.raises(analyze.CsvFormatError, match="not valid JSON"):
        analyze.read_sidecar(str(tmp_path / "run.csv"))
    (tmp_path / "run.csv.config.json").write_text("[1, 2]")
    with pytest.raises(analyze.CsvFormatError, match="JSON object"):
        analyze.read_sidecar(str(tmp_path / "run.csv"))


@pytest.mark.req("ANA-001")
def test_a_csv_that_does_not_match_its_sidecar_is_rejected():
    rows = [_row(i, 0.0, 0.0, 0.0) for i in range(3)]
    analyze.check_consistency(rows, _sidecar(steps=2))  # N + 1 = 3 rows: fine
    with pytest.raises(analyze.CsvFormatError, match="same run"):
        analyze.check_consistency(rows, _sidecar(steps=10))


# ---- ANA-005: metrics.json (baseline 8.7) ----

def _metrics(raw_rmse=4.0, est_rmse=2.0):
    return {"n_rows": 11, "n_measurements": 3, "rmse_meas_pos_m": raw_rmse, "rmse_est_pos_m": est_rmse,
            "rmse_est_vel_mps": 1.0, "n_within_2sigma": 2, "frac_pos_within_2sigma": 2 / 3}


@pytest.mark.req("ANA-005")
def test_metrics_json_has_exactly_the_contract_keys_in_order():
    out = analyze.metrics_for_json(_metrics())
    assert list(out) == ["schema_version", "n_rows", "n_measurements", "rmse_meas_pos_m",
                         "rmse_est_pos_m", "rmse_est_vel_mps", "improvement_ratio",
                         "frac_pos_within_2sigma"]
    assert out["schema_version"] == 1
    assert out["improvement_ratio"] == pytest.approx(0.5)   # estimate / raw = 2 / 4


@pytest.mark.req("ANA-005")
def test_improvement_ratio_is_null_not_nan_when_the_raw_readings_are_exact(tmp_path):
    assert analyze.metrics_for_json(_metrics(raw_rmse=0.0, est_rmse=0.0))["improvement_ratio"] is None
    path = tmp_path / "m.json"
    analyze.write_metrics_json(path, _metrics(raw_rmse=0.0, est_rmse=0.0))
    assert json.loads(path.read_text())["improvement_ratio"] is None
    assert "NaN" not in path.read_text() and "Infinity" not in path.read_text()


@pytest.mark.req("ANA-005")
def test_metrics_json_refuses_non_finite_values_and_leaves_no_file(tmp_path):
    path = tmp_path / "m.json"
    bad = _metrics()
    bad["rmse_est_vel_mps"] = float("nan")
    with pytest.raises(ValueError):
        analyze.write_metrics_json(path, bad)
    assert list(tmp_path.iterdir()) == []   # neither the file nor its temp file
