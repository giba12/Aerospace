# sensor-sim: a sensor and state-estimation simulator

> **This is a small educational simulation.** It is not flight software and has not been
> qualified for any use. It does not model a real sensor, real vehicle dynamics, or
> operational sensor fusion. (SYS-006)

**Status: M4 complete (analysis and validation record).** Every stage of the pipeline exists and
runs. The truth model, the seeded noisy sensor and the Kalman filter are real. The filter is checked
three ways: against the baseline's hand-worked vector, against an independent Python
re-computation in exact arithmetic, and against 50 held-out random seeds (the result is recorded in
[docs/VALIDATION.md](docs/VALIDATION.md)). `analyze.py` prints the metrics, writes `metrics.json`
and draws the plot below. See [Limitations](#limitations).

## What this project demonstrates

Simulate an object moving in one dimension, produce imperfect sensor readings of its
position, estimate its hidden state from those readings alone, and compare the estimate with
the known truth. It is also a small demonstration of engineering habits: requirements with
IDs, tests that cite them, a script that checks the citations, CI on every push, and
deterministic runs.

## Data flow

```text
Dynamics ──truth──▶ Runner ──truth (const)──▶ Sensor ──▶ optional Measurement
                      │                                        │
                      │         Estimator ◀── measurement only ┘     (never the truth)
                      │             │
                      └─────────────┴──▶ Recorder ──▶ run.csv ──▶ python/analyze.py ──▶ metrics
```

The truth is kept apart from the estimator so the evaluation is meaningful. The full design
is in [docs/architecture.md](docs/architecture.md) and the
[systems engineering baseline](docs/systems-engineering-baseline.md).

## Units and assumptions

SI units throughout, with the unit in every field and flag name (`_m`, `_s`, `_mps`).
Time is `t = k × dt`, computed per step, never accumulated. The model is one-dimensional,
constant velocity by default, or constant acceleration with `--accel`. Truth is advanced with
explicit Euler, which is exact when the acceleration is 0 and otherwise off by exactly
`a·t·dt/2` (5 m for a = 1 m/s², t = 100 s, dt = 0.1 s; baseline VV-SIM-01).

## Prerequisites

Linux, GCC 13 or Clang 18, CMake ≥ 3.20, Ninja, Python 3.12 with `venv`, and network access on
the first configure (GoogleTest is downloaded, pinned by SHA-256).

## Build, test, run, analyze

```bash
# 1. Python environment (pinned)
python3 -m venv .venv
.venv/bin/pip install -r python/requirements.txt

# 2. Configure and build (warnings are errors; see Troubleshooting)
cmake -S . -B build -G Ninja
cmake --build build

# 3. Test (C++ unit tests, Python system tests; JUnit XML goes to build/test-reports/)
cd build && ctest --output-on-failure && cd ..

# 4. Run the simulator, then analyze its output (needs run.csv.config.json next to the CSV)
./build/sim --steps 1000 --out run.csv     # also writes run.csv.config.json (settings, seed, build)
.venv/bin/python python/analyze.py run.csv --metrics-json metrics.json --plot plot.png

# 5. Cross-check the filter against the independent Python re-computation (exact arithmetic)
.venv/bin/python python/kalman_oracle.py run.csv

# 6. Check requirement traceability
.venv/bin/python tools/req_trace.py --requirements docs/requirements.csv \
    --junit build/test-reports/gtest.xml build/test-reports/pytest.xml
```

`./build/sim --help` lists every flag with its unit and default.

## Expected output

The sensor adds Gaussian noise (default sigma 5 m, seed 42) and the Kalman filter estimates position
and velocity from those readings alone. The RMSEs are taken at the 201 steps that have a reading:
the raw readings are off by 5.46 m, the filter's position estimate by 2.32 m (a ratio of 0.43), and
its velocity estimate, which the sensor never measures, by 1.20 m/s:

```text
n_rows = 1001
n_measurements = 201
rmse_meas_pos_m = 5.4598541120696265
rmse_est_pos_m = 2.32142058992441
rmse_est_vel_mps = 1.2027805245829981
n_within_2sigma = 189
frac_pos_within_2sigma = 0.9402985074626866
```

`frac_pos_within_2sigma` is the share of those 201 positions whose error is inside twice the filter's
own reported standard deviation (94 % for this seed).

This is one seed. Across 50 held-out seeds (never used to choose any setting) the estimate's RMSE is
0.31 to 0.56 times the raw readings' RMSE, against a required 0.75 (EST-008), and 97.6 % of the
true positions fall inside the filter's own +/-2 sigma error bars, against a required 90 %
(EST-012). A perfect filter scores about 95 %.

The noise values come from the C++ standard library's `std::normal_distribution`, which the
standard leaves implementation-defined. The same seed gives identical output on the same platform
and build; the digits above are from GCC 13.3 and other toolchains will print different noise.
`--sigma 0` gives an exact sensor, and the sidecar `run.csv.config.json` records every setting.

The plot (`data/example-plot.png`, from the command in step 4) shows the three things worth seeing. Top:
the truth, the noisy readings and the filter's estimate. Middle: the position *error* of the estimate
against the raw readings' error, with the filter's own +/-2 sigma bars shaded; the blue error stays inside
the band and hugs zero while the orange readings scatter wider. Bottom: the velocity, which the sensor never
measures, converging on the true 10 m/s within about six seconds.

![truth, sensor readings and filter estimate](data/example-plot.png)

`analyze.py` refuses a CSV whose sidecar is missing, has a `schema_version` it does not understand, or
describes a different run (ANA-001); it writes `metrics.json` in the layout of baseline section 8.7
(`improvement_ratio` is `null` for an exact sensor, where the raw error is 0). An example is
`data/example-metrics.json`.

## Repository layout

| Path | Contents |
|---|---|
| `include/simulator/`, `src/` | `simcore` library (all logic) and `main.cpp` (one call into it) |
| `tests/support/` | Framework-neutral test helpers and fakes |
| `tests/gtest/` | GoogleTest adapter. The only place that knows the framework |
| `tests/system/`, `tests/python/` | pytest: black-box tests of `sim`, and unit tests of the Python tools |
| `python/` | `analyze.py` (metrics, JSON, plot), `kalman_oracle.py` (independent re-computation), `ensemble.py` (runs many seeds, VAL-02/03), `seed_sets.py`, and the pinned `requirements.txt` |
| `data/` | A small example plot and metrics file |
| `tools/req_trace.py` | Requirement-to-test traceability and its CI gate |
| `docs/` | Requirements, baseline, architecture, `VALIDATION.md` (the VAL-02/03 record), change requests, and `requirements.csv` (the ID registry) |

## Writing a test

Every test names the requirement it verifies:

```cpp
TEST(Runner, CallOrderMatchesSpecification) {
    RecordProperty("requirements", "RUN-001");   // GoogleTest
```

```python
@pytest.mark.req("OUT-001")                       # pytest
def test_header(...):
```

`tools/req_trace.py` fails on an unknown ID or on a test that cites none.

## Limitations

- The filter assumes constant velocity, so it fails when the truth accelerates. Measured on 200 tuning
  seeds with the real filter: at `--accel 0.1` it still helps (RMSE ratio 0.46, error-bar coverage
  96 %); at `--accel 0.5` it is no better than the raw readings (ratio 1.05) and the true position
  is inside its own error bars only 42 % of the time. The acceptance tests (EST-008, EST-012) use
  the reference scenario with no acceleration and say nothing about this case.
- The filter's `R` and `q` are not tuned for any scenario other than the reference one.
- Sensor noise is reproducible only on the same platform and build (see Expected output).
- One dimension. Acceleration, if any, is constant and known; Euler's error bound is `a·t·dt/2`.
- Validation is on simulated data from the model the filter assumes, and the exact figures depend on the
  C++ standard library's normal distribution. See `docs/VALIDATION.md` for what it does and does not show,
  including a scenario (a reading only every 5 s) where the filter helps much less than in the reference one.
- 12 of 61 Must requirements have no passing test yet. `req_trace.py` prints the list; the
  coverage gate (`--require-coverage`) is switched on in M5.
- CI runs on every push (GCC 13 and Clang 18) and has passed on the pushed branches.

## Next steps

M5 hardening (sanitizers, the coverage gate, coverage report) and M6 release (claim-to-evidence table,
clean-room container run, tagging the baseline). See baseline section 6.7.

## Troubleshooting

- *A newer compiler fails the build on a warning:* configure with `-DSIM_WARNINGS_AS_ERRORS=OFF`.
- *`system.pytest` fails with "No such file":* create the virtual environment (step 1).
- *Offline:* the first configure needs network access to fetch GoogleTest.
