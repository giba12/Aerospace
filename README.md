# sensor-sim: a sensor and state-estimation simulator

> **This is a small educational simulation.** It is not flight software and has not been
> qualified for any use. It does not model a real sensor, real vehicle dynamics, or
> operational sensor fusion. (SYS-006)

**Status: M2 (truth model and noisy sensor complete).** Every stage of the pipeline exists and runs.
The truth model (constant velocity or constant acceleration) and the seeded noisy sensor are real;
the estimator is still a deliberately trivial stand-in. See [Limitations](#limitations).

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

# 4. Run the simulator, then analyze its output
./build/sim --steps 1000 --out run.csv     # also writes run.csv.config.json (settings, seed, build)
.venv/bin/python python/analyze.py run.csv

# 5. Check requirement traceability
.venv/bin/python tools/req_trace.py --requirements docs/requirements.csv \
    --junit build/test-reports/gtest.xml build/test-reports/pytest.xml
```

`./build/sim --help` lists every flag with its unit and default.

## Expected output

The sensor adds Gaussian noise (default sigma 5 m, seed 42) and, until M3, the "estimator" just
repeats the latest reading. So the estimate is exactly as noisy as the sensor, and its velocity is
always 0 against a true 10 m/s. That proves the pipeline, not the filter:

```text
n_rows = 1001
n_measurements = 201
rmse_meas_pos_m = 5.4598541120696265
rmse_est_pos_m = 5.4598541120696265
rmse_est_vel_mps = 10.0
```

The noise values come from the C++ standard library's `std::normal_distribution`, which the
standard leaves implementation-defined. The same seed gives identical output on the same platform
and build; the digits above are from GCC 13.3 and other toolchains will print different noise.
`--sigma 0` gives an exact sensor, and the sidecar `run.csv.config.json` records every setting.

(The velocity error is 10 because the stand-in estimator reports a velocity of 0.) A real plot
and sample output arrive in M4.

## Repository layout

| Path | Contents |
|---|---|
| `include/simulator/`, `src/` | `simcore` library (all logic) and `main.cpp` (one call into it) |
| `tests/support/` | Framework-neutral test helpers and fakes |
| `tests/gtest/` | GoogleTest adapter. The only place that knows the framework |
| `tests/system/`, `tests/python/` | pytest: black-box tests of `sim`, and unit tests of the Python tools |
| `python/` | `analyze.py` and the pinned `requirements.txt` |
| `tools/req_trace.py` | Requirement-to-test traceability and its CI gate |
| `docs/` | Requirements, baseline, architecture, and `requirements.csv` (the ID registry) |

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

- The estimator is a passthrough: it repeats the latest reading, so it is no better than the
  sensor. There is no Kalman filter and no plot yet (milestones M3 and M4). The sidecar's
  estimator keys are `null` until M3.
- Sensor noise is reproducible only on the same platform and build (see Expected output).
- One dimension. Acceleration, if any, is constant and known; Euler's error bound is `a·t·dt/2`.
- 28 of 61 Must requirements have no passing test yet. `req_trace.py` prints the list; the
  coverage gate (`--require-coverage`) is switched on in M5.
- CI runs on every push (GCC 13 and Clang 18) and has passed on the pushed branches.

## Next steps

M3 Kalman filter checked
against the hand-computed vector VV-EST-01, M4 analysis plot and coverage metrics, M5
sanitizers and the coverage gate. See baseline section 6.7.

## Troubleshooting

- *A newer compiler fails the build on a warning:* configure with `-DSIM_WARNINGS_AS_ERRORS=OFF`.
- *`system.pytest` fails with "No such file":* create the virtual environment (step 1).
- *Offline:* the first configure needs network access to fetch GoogleTest.
