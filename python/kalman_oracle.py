#!/usr/bin/env python3
"""Independent re-computation of the filter's output from a `sim` run (VAL-04, DD-012, R-04).

Given the CSV and its sidecar, this rebuilds the estimator's `est_*` columns from ONLY the
`meas_pos_m` readings and the recorded settings, then reports how far the C++ output is from it.
It never looks at the truth columns and never imports the C++.

It is a re-derivation, not a port, and it is more accurate than what it checks:
  * It computes in 60-digit decimal arithmetic on the exact values of the doubles the C++ was
    given, so any difference from the C++ is the C++'s own floating-point rounding. A first version
    used doubles and was WRONG in one regime: after 100,000 steps without a reading the position
    variance reaches 4e10 m^2, and the update that follows subtracts two nearly equal huge numbers.
    The short update form lost 7 digits there (error 4.9e-7); the C++ Joseph form was within 9e-16
    of the exact answer (see docs/change-requests/CR-26-oracle-tolerance.md).
  * Plain scalar arithmetic on the four entries of P, no matrix helpers.
  * The algebraically expanded predict formulas (see docs/M3_WORKSHEET.md).
  * The "short" covariance update P = (I - K H) P-, where the C++ uses the Joseph form. In exact
    arithmetic the two are identical, so any difference is rounding.
Standard library only.
"""
import argparse
import json
import sys
from decimal import Decimal, localcontext

import analyze

# The `est_*` columns this checks.
COMPARED = ("est_pos_m", "est_vel_mps", "est_pos_var_m2", "est_vel_var_m2s2")

# Tolerance (CR-26, the same idea as the position tolerance of CR-24): a fixed 1e-9 is below the
# spacing of doubles once a value is large (a variance reaches 4e10 m^2 in a long run with rare
# readings), and rounding error grows with the number of steps k. So the allowed difference for a
# value `want` at step k is
#       max( 1e-9 ,  2 * k * u * |want| ),      u = 2^-53 (unit roundoff of a double).
UNIT_ROUNDOFF = 2.0 ** -53


class OracleError(ValueError):
    """The CSV or sidecar cannot be replayed (a missing reading, a null setting, ...)."""


def load_settings(sidecar_path):
    """Return the settings the replay needs, from the sidecar JSON; raise OracleError if absent."""
    with open(sidecar_path, encoding="utf-8") as f:
        side = json.load(f)
    needed = ("dt_s", "est_q_m2ps3", "est_r_m2", "est_p0_pos_m2", "est_p0_vel_m2ps2")
    missing = [k for k in needed if side.get(k) is None]
    if missing:
        raise OracleError(f"sidecar has no value for {', '.join(missing)}")
    return {k: float(side[k]) for k in needed}


def predict_step(state, dt, q):
    """One predict. state = (x, v, p00, p01, p10, p11). x- = x + dt v ; P- = F P F^T + Q, with
    the matrix product written out entry by entry. Works on floats or Decimals."""
    x, v, p00, p01, p10, p11 = state
    return (x + dt * v, v,
            p00 + dt * (p01 + p10) + dt * dt * p11 + q * dt ** 3 / 3,
            p01 + dt * p11 + q * dt * dt / 2,
            p10 + dt * p11 + q * dt * dt / 2,
            p11 + q * dt)


def update_step(state, z, r):
    """One update with H = [1, 0]: S = p00 + R, K = [p00, p10] / S, then the SHORT form of the
    covariance update P = (I - K H) P (the C++ uses the Joseph form). Works on floats or Decimals."""
    x, v, p00, p01, p10, p11 = state
    s = p00 + r
    k0, k1 = p00 / s, p10 / s
    y = z - x
    return (x + k0 * y, v + k1 * y,
            (1 - k0) * p00, (1 - k0) * p01,
            p10 - k1 * p00, p11 - k1 * p01)


def replay(readings, dt, q, r, p0_pos, p0_vel, digits=60):
    """Run the filter over `readings` (a list: a float, or None where no reading was taken).

    Returns one entry per input: None while uninitialized, else (pos, vel, var_pos, var_vel) as
    floats rounded from `digits`-digit decimal results. The call order is the project's: the first
    reading initializes with no predict; after that every step predicts, and a reading then updates.
    Each float input is converted to the exact decimal value of that double, so the oracle starts
    from precisely what the C++ was given.
    """
    out = []
    with localcontext() as ctx:
        ctx.prec = digits
        dt, q, r, p0_pos, p0_vel = (Decimal(v) for v in (dt, q, r, p0_pos, p0_vel))
        state = None
        for z in readings:
            z = None if z is None else Decimal(z)
            if state is None:
                if z is not None:
                    state = (z, Decimal(0), p0_pos, Decimal(0), Decimal(0), p0_vel)
            else:
                state = predict_step(state, dt, q)
                if z is not None:
                    state = update_step(state, z, r)
            out.append(None if state is None
                       else (float(state[0]), float(state[1]), float(state[2]), float(state[5])))
    return out


def allowed_difference(step, want, floor=1e-9):
    """The largest |C++ - oracle| accepted for `want` at step `step` (CR-26)."""
    return max(floor, 2.0 * step * UNIT_ROUNDOFF * abs(want))


def _cell(row, column):
    return None if row[column] == "" else float(row[column])


def compare(rows, settings, floor=1e-9):
    """Replay `rows` and compare with the C++ output. Returns, per column, a pair
    (largest absolute difference, largest difference as a fraction of what is allowed there).
    A fraction above 1 means the C++ and the oracle disagree by more than rounding can explain.

    An estimate that is present in one and missing in the other is an OracleError: that would be
    a disagreement about when the filter starts.
    """
    readings = [_cell(r, "meas_pos_m") for r in rows]
    expected = replay(readings, settings["dt_s"], settings["est_q_m2ps3"], settings["est_r_m2"],
                      settings["est_p0_pos_m2"], settings["est_p0_vel_m2ps2"])
    worst = {c: (0.0, 0.0) for c in COMPARED}
    for k, (row, want) in enumerate(zip(rows, expected)):
        got = [_cell(row, c) for c in COMPARED]
        if (want is None) != (got[0] is None):
            raise OracleError(f"step {row['step']}: the C++ and the oracle disagree on whether "
                              "the estimator has started")
        if want is None:
            continue
        for column, g, w in zip(COMPARED, got, want):
            diff = abs(g - w)
            ratio = diff / allowed_difference(k, w, floor)
            worst[column] = (max(worst[column][0], diff), max(worst[column][1], ratio))
    return worst


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv", help="path to a CSV written by `sim` (its .config.json must sit next to it)")
    parser.add_argument("--floor", type=float, default=1e-9,
                        help="smallest allowed absolute difference (default 1e-9, baseline 6.3)")
    args = parser.parse_args(argv)
    try:
        rows = analyze.read_rows(args.csv)
        worst = compare(rows, load_settings(args.csv + ".config.json"), args.floor)
    except (analyze.CsvFormatError, OracleError, OSError, ValueError) as e:
        print(f"kalman_oracle: error: {e}", file=sys.stderr)
        return 1
    bad = False
    for column, (diff, ratio) in worst.items():
        flag = "" if ratio <= 1.0 else "   <-- exceeds what rounding explains"
        bad = bad or ratio > 1.0
        print(f"{column}: max |C++ - oracle| = {diff:.3e} ({ratio:.2g} of the allowance){flag}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
