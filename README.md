# sensor-sim: a sensor and state-estimation simulator

> **This is a small educational simulation.** It is not flight software and has not been
> qualified for any use. It does not model a real sensor, real vehicle dynamics, or
> operational sensor fusion. (SYS-006)

**Status: M0 skeleton.** Every stage of the pipeline exists and runs, but the stages are
deliberately trivial stand-ins. See [Limitations](#limitations).

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
constant velocity.

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
./build/sim --steps 1000 --out run.csv
.venv/bin/python python/analyze.py run.csv

# 5. Check requirement traceability
.venv/bin/python tools/trace.py --requirements docs/requirements.csv \
    --junit build/test-reports/gtest.xml build/test-reports/pytest.xml
```

`./build/sim --help` lists every flag with its unit and default.

## Expected output

At M0 the "sensor" reads the truth exactly and the "estimator" repeats the latest reading, so
every error metric is zero. That is correct for a skeleton and proves the pipeline, not the
filter:

```text
n_rows = 1001
n_measurements = 201
rmse_meas_pos_m = 0.0
rmse_est_pos_m = 0.0
rmse_est_vel_mps = 10.0
```

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
| `tools/trace.py` | Requirement-to-test traceability and its CI gate |
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

`tools/trace.py` fails on an unknown ID or on a test that cites none.

## Limitations

- The sensor is exact and the estimator is a passthrough. There is no noise, no Kalman filter,
  no plot, and no sidecar JSON yet (milestones M1 to M4).
- One dimension, constant velocity, no acceleration.
- 39 of 61 Must requirements have no passing test yet. `trace.py` prints the list; the
  coverage gate (`--require-coverage`) is switched on in M5.
- CI configuration is written but has not run on GitHub yet.

## Next steps

M1 truth with acceleration, M2 seeded noisy sensor and the sidecar, M3 Kalman filter checked
against the hand-computed vector VV-EST-01, M4 analysis plot and coverage metrics, M5
sanitizers and the coverage gate. See baseline section 6.7.

## Troubleshooting

- *A newer compiler fails the build on a warning:* configure with `-DSIM_WARNINGS_AS_ERRORS=OFF`.
- *`system.pytest` fails with "No such file":* create the virtual environment (step 1).
- *Offline:* the first configure needs network access to fetch GoogleTest.
