#!/usr/bin/env python3
"""Read a `sim` CSV and its sidecar, check them, print error metrics, and optionally write
`metrics.json` and a labelled plot.

  ANA-001  the CSV header and every row are checked, and the sidecar must carry a schema_version
           this script understands and agree with the CSV (the row count is steps + 1);
  ANA-002  RMSE of the raw readings and of the estimate, over rows that have a reading;
  ANA-003  a PNG with axis labels, units and a legend (--plot; needs matplotlib);
  ANA-004  the share of position errors inside the filter's own +/-2 sigma bars;
  ANA-005  the numbers printed, and saved as `metrics.json` (--metrics-json, baseline 8.7).

Everything except the plot uses the standard library only, and matplotlib is imported only when a
plot is asked for.
"""
import argparse
import csv
import json
import math
import os
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


SUPPORTED_SCHEMA_VERSION = 1

# IF-08 (baseline 8.5): every key the sidecar must carry. Estimator keys may be null (CR-25).
REQUIRED_SIDECAR_KEYS = [
    "schema_version", "steps", "dt_s", "x0_m", "v0_mps", "accel_mps2", "meas_every", "sigma_m",
    "seed", "sensor_id", "est_q_m2ps3", "est_r_m2", "est_p0_pos_m2", "est_p0_vel_m2ps2",
    "compiler", "source_revision",
]

# IF-09 (baseline 8.7): the keys of metrics.json, in order.
METRICS_JSON_KEYS = [
    "schema_version", "n_rows", "n_measurements", "rmse_meas_pos_m", "rmse_est_pos_m",
    "rmse_est_vel_mps", "improvement_ratio", "frac_pos_within_2sigma",
]
METRICS_SCHEMA_VERSION = 1


def sidecar_path(csv_path):
    return f"{csv_path}.config.json"


def read_sidecar(csv_path):
    """Read and validate `<csv>.config.json`; return its dict. Raises CsvFormatError otherwise.

    Rejects a missing file, invalid JSON, a missing key, and a schema_version this script does not
    know: reading a newer format as if it were the old one would give silently wrong numbers.
    """
    path = sidecar_path(csv_path)
    try:
        with open(path, encoding="utf-8") as f:
            side = json.load(f)
    except FileNotFoundError:
        raise CsvFormatError(
            f"{path}: not found. The sidecar carries the format version, so a CSV cannot be "
            "analyzed without it") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise CsvFormatError(f"{path}: not valid JSON: {e}") from e
    if not isinstance(side, dict):
        raise CsvFormatError(f"{path}: expected a JSON object")
    version = side.get("schema_version")
    if isinstance(version, bool) or version != SUPPORTED_SCHEMA_VERSION:
        raise CsvFormatError(
            f"{path}: schema_version is {version!r}; this analyze.py understands only "
            f"{SUPPORTED_SCHEMA_VERSION}")
    missing = [k for k in REQUIRED_SIDECAR_KEYS if k not in side]
    if missing:
        raise CsvFormatError(f"{path}: missing key(s): {', '.join(missing)}")
    return side


def check_consistency(rows, side):
    """The CSV and its sidecar must describe the same run: N + 1 rows for N steps (SIM-005)."""
    steps = side["steps"]
    if isinstance(steps, bool) or not isinstance(steps, int) or len(rows) != steps + 1:
        raise CsvFormatError(
            f"the CSV has {len(rows)} rows but the sidecar says steps = {steps!r} "
            f"(expected {steps!r} + 1 rows); are they from the same run?")


def metrics_for_json(metrics):
    """The IF-09 object: exactly the keys of baseline 8.7, in order.

    `improvement_ratio` is the estimate's RMSE divided by the raw readings' RMSE. It is null
    (never NaN or infinity) when the raw RMSE is 0, as with an exact sensor (--sigma 0).
    """
    raw = metrics["rmse_meas_pos_m"]
    out = {
        "schema_version": METRICS_SCHEMA_VERSION,
        "n_rows": metrics["n_rows"],
        "n_measurements": metrics["n_measurements"],
        "rmse_meas_pos_m": raw,
        "rmse_est_pos_m": metrics["rmse_est_pos_m"],
        "rmse_est_vel_mps": metrics["rmse_est_vel_mps"],
        "improvement_ratio": metrics["rmse_est_pos_m"] / raw if raw > 0.0 else None,
        "frac_pos_within_2sigma": metrics["frac_pos_within_2sigma"],
    }
    assert list(out) == METRICS_JSON_KEYS
    return out


def write_metrics_json(path, metrics):
    """Write metrics.json atomically (temp file, then rename); NaN and infinity are refused."""
    text = json.dumps(metrics_for_json(metrics), indent=2, allow_nan=False) + "\n"
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def _series(rows, column):
    """A column as floats, with NaN where the cell is empty (plotting only: matplotlib leaves a gap)."""
    return [float(r[column]) if r[column] != "" else math.nan for r in rows]


def make_figure(rows, side=None):
    """Build the labelled figure (ANA-003) and return it. Needs matplotlib.

    Three panels sharing the time axis: position (truth, readings, estimate); position error of
    the estimate with its own +/-2 sigma bars, against the raw readings' error (ANA-004, and the
    picture behind EST-012); velocity (truth against the estimate, which the sensor never measures).
    """
    from matplotlib.figure import Figure

    t = _series(rows, "t_s")
    truth_pos = _series(rows, "true_pos_m")
    truth_vel = _series(rows, "true_vel_mps")
    meas = _series(rows, "meas_pos_m")
    est_pos = _series(rows, "est_pos_m")
    est_vel = _series(rows, "est_vel_mps")
    two_sigma = [2.0 * math.sqrt(v) if not math.isnan(v) else math.nan
                 for v in _series(rows, "est_pos_var_m2")]
    est_err = [e - x for e, x in zip(est_pos, truth_pos)]
    meas_err = [m - x for m, x in zip(meas, truth_pos)]

    fig = Figure(figsize=(10, 9), layout="constrained")
    ax_pos, ax_err, ax_vel = fig.subplots(3, 1, sharex=True)

    ax_pos.plot(t, truth_pos, color="black", lw=1.5, label="truth")
    ax_pos.plot(t, est_pos, color="tab:blue", lw=1.2, label="filter estimate")
    ax_pos.plot(t, meas, ls="none", marker="o", ms=3, color="tab:orange", label="sensor readings")
    ax_pos.set_ylabel("position (m)")

    ax_err.axhline(0.0, color="black", lw=0.8)
    ax_err.fill_between(t, [-b for b in two_sigma], two_sigma, color="tab:blue", alpha=0.2,
                        label="estimate $\\pm 2\\sigma$ (filter's own error bars)")
    ax_err.plot(t, est_err, color="tab:blue", lw=1.0, label="estimate error")
    ax_err.plot(t, meas_err, ls="none", marker="o", ms=3, color="tab:orange",
                label="raw reading error")
    ax_err.set_ylabel("position error (m)")

    ax_vel.plot(t, truth_vel, color="black", lw=1.5, label="true velocity")
    ax_vel.plot(t, est_vel, color="tab:blue", lw=1.2, label="estimated velocity")
    ax_vel.set_ylabel("velocity (m/s)")
    ax_vel.set_xlabel("time (s)")

    for ax in (ax_pos, ax_err, ax_vel):
        ax.grid(alpha=0.3)
        ax.legend(loc="best", fontsize=8)
    title = "sensor-sim: truth, sensor readings and Kalman-filter estimate"
    if side is not None:
        title += (f"\nseed {side['seed']}, sensor noise {side['sigma_m']} m, "
                  f"reading every {side['meas_every']} steps, dt {side['dt_s']} s")
    fig.suptitle(title, fontsize=11)
    return fig


def write_plot(path, rows, side=None):
    """Save the figure as a PNG at `path`."""
    make_figure(rows, side).savefig(path, dpi=130, format="png")


def _require_output_directory(path, flag):
    """Fail before any slow work (a plot takes seconds) if an output file cannot be created."""
    directory = os.path.dirname(path) or "."
    if not os.path.isdir(directory):
        raise OSError(f"{flag} {path}: the directory {directory!r} does not exist")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", help="path to a CSV written by `sim` (its .config.json must sit next to it)")
    parser.add_argument("--metrics-json", metavar="PATH", help="also write the metrics as JSON (baseline 8.7)")
    parser.add_argument("--plot", metavar="PATH", help="also write a labelled PNG plot (needs matplotlib)")
    args = parser.parse_args(argv)
    try:
        for path, flag in ((args.metrics_json, "--metrics-json"), (args.plot, "--plot")):
            if path:
                _require_output_directory(path, flag)
        rows = read_rows(args.csv)
        side = read_sidecar(args.csv)
        check_consistency(rows, side)
        metrics = compute_metrics(rows)
        if args.metrics_json:
            write_metrics_json(args.metrics_json, metrics)
        if args.plot:
            write_plot(args.plot, rows, side)
    except (CsvFormatError, OSError) as e:
        print(f"analyze: error: {e}", file=sys.stderr)
        return 1
    except ImportError:
        print("analyze: error: --plot needs matplotlib; install python/requirements.txt", file=sys.stderr)
        return 1
    for key, value in metrics.items():
        print(f"{key} = {value}")
    ratio = metrics_for_json(metrics)["improvement_ratio"]
    print(f"improvement_ratio = {ratio if ratio is not None else 'n/a (raw RMSE is 0)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
