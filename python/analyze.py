#!/usr/bin/env python3
"""Read a `sim` CSV, check it, and print error metrics.

M0 scope: header validation (ANA-001, partial) and RMSE (ANA-002). The plot (ANA-003), the
+/-2 sigma coverage (ANA-004) and the metrics JSON (ANA-005) arrive in M4. Standard library
only, so M0 needs no plotting or data-frame dependency.

All RMSEs are computed over rows that have a measurement (ANA-002).
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
    """Return the CSV as a list of dicts of strings. Raises CsvFormatError on a bad header."""
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != EXPECTED_HEADER:
            raise CsvFormatError(
                f"{path}: header is {reader.fieldnames}, expected {EXPECTED_HEADER}")
        return list(reader)


def _rmse(errors):
    return math.sqrt(sum(e * e for e in errors) / len(errors))


def compute_metrics(rows):
    """RMSE of the raw measurement and of the estimate, over measurement rows only."""
    meas_rows = [r for r in rows if r["meas_pos_m"] != ""]
    if not meas_rows:
        raise CsvFormatError("no row has a measurement; RMSE is undefined")
    meas_err = [float(r["meas_pos_m"]) - float(r["true_pos_m"]) for r in meas_rows]
    est_pos_err = [float(r["est_pos_m"]) - float(r["true_pos_m"]) for r in meas_rows]
    est_vel_err = [float(r["est_vel_mps"]) - float(r["true_vel_mps"]) for r in meas_rows]
    return {
        "n_rows": len(rows),
        "n_measurements": len(meas_rows),
        "rmse_meas_pos_m": _rmse(meas_err),
        "rmse_est_pos_m": _rmse(est_pos_err),
        "rmse_est_vel_mps": _rmse(est_vel_err),
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
