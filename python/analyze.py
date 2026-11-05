#!/usr/bin/env python3
"""Read a `sim` CSV, check it, and print error metrics.

Scope so far: header validation (ANA-001, partial), RMSE (ANA-002) and the +/-2 sigma coverage
(ANA-004, numeric part). The plot (ANA-003) and the metrics JSON (ANA-005) arrive in M4. Standard
library only, so there is no plotting or data-frame dependency yet.

All RMSEs and the coverage are computed over rows that have a measurement (ANA-002).
"""
import argparse
import csv
import math
import sys

EXPECTED_HEADER = [
    "step", "t_s", "true_pos_m", "true_vel_mps", "meas_pos_m",
    "est_pos_m", "est_vel_mps", "est_pos_var_m2", "est_vel_var_m2s2",
]


class CsvFormatError(ValueError):
    """The file is not a valid `sim` CSV (schema_version 1)."""


def read_rows(path):
    """Return the CSV as a list of dicts of strings.

    Raises CsvFormatError on a bad header, a row with the wrong number of fields, or a file
    that is not UTF-8 text. (A missing file still raises OSError.)
    """
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        try:
            if reader.fieldnames != EXPECTED_HEADER:
                raise CsvFormatError(
                    f"{path}: header is {reader.fieldnames}, expected {EXPECTED_HEADER}")
            rows = []
            for row in reader:
                # DictReader pads a short row with None and files extra fields under key None.
                if None in row or None in row.values():
                    raise CsvFormatError(
                        f"{path}: line {reader.line_num}: expected "
                        f"{len(EXPECTED_HEADER)} fields")
                rows.append(row)
            return rows
        except (UnicodeDecodeError, csv.Error) as e:
            raise CsvFormatError(f"{path}: not a readable CSV text file: {e}") from e


def _number(row, column, index):
    """Return row[column] as a finite float, or raise CsvFormatError naming row and column."""
    where = f"data row {index} (step {row.get('step')!r}), column {column}"
    text = row.get(column)
    if text is None or text.strip() == "":
        raise CsvFormatError(f"{where}: value is missing")
    try:
        value = float(text)
    except ValueError:
        raise CsvFormatError(f"{where}: not a number: {text!r}") from None
    if not math.isfinite(value):
        raise CsvFormatError(f"{where}: not finite: {text!r}")
    return value


def _rmse(errors):
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def compute_metrics(rows):
    """RMSE of the raw measurement and of the estimate, and the +/-2 sigma coverage of the
    estimate, over measurement rows only.

    Coverage (ANA-004) is the fraction of those rows whose position error |est - true| is at
    most twice the filter's own reported position standard deviation sqrt(est_pos_var_m2). A
    filter whose error bars are honest scores about 0.95. `n_within_2sigma` is returned as well
    as the fraction so that several runs can be pooled exactly (EST-012).
    """
    meas_rows = [(i, r) for i, r in enumerate(rows) if r["meas_pos_m"] != ""]
    if not meas_rows:
        raise CsvFormatError("no row has a measurement; RMSE is undefined")
    meas_err, est_pos_err, est_vel_err = [], [], []
    n_within_2sigma = 0
    for i, r in meas_rows:
        true_pos = _number(r, "true_pos_m", i)
        meas_err.append(_number(r, "meas_pos_m", i) - true_pos)
        est_pos_err.append(_number(r, "est_pos_m", i) - true_pos)
        est_vel_err.append(_number(r, "est_vel_mps", i) - _number(r, "true_vel_mps", i))
        variance = _number(r, "est_pos_var_m2", i)
        if variance < 0.0:
            raise CsvFormatError(
                f"data row {i} (step {r.get('step')!r}), column est_pos_var_m2: "
                f"a variance cannot be negative: {variance!r}")
        if abs(est_pos_err[-1]) <= 2.0 * math.sqrt(variance):
            n_within_2sigma += 1
    return {
        "n_rows": len(rows),
        "n_measurements": len(meas_rows),
        "rmse_meas_pos_m": _rmse(meas_err),
        "rmse_est_pos_m": _rmse(est_pos_err),
        "rmse_est_vel_mps": _rmse(est_vel_err),
        "n_within_2sigma": n_within_2sigma,
        "frac_pos_within_2sigma": n_within_2sigma / len(meas_rows),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", help="path to a CSV written by `sim`")
    args = parser.parse_args(argv)
    try:
        metrics = compute_metrics(read_rows(args.csv))
    except (CsvFormatError, OSError) as e:
        print(f"analyze: error: {e}", file=sys.stderr)
        return 1
    for key, value in metrics.items():
        print(f"{key} = {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
