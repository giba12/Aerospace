# Sensor and State-Estimation Simulator: Scope and Requirements

**Status:** DRAFT v0.1 (2026-09-27). The decisions marked **[DECIDE]** are still open; see §9.

---

## 1. What this program is, in web and data terms

| Simulator concept | Closest web/data analogy |
|---|---|
| **True state**: where the object really is | The actual value in the database, which clients never see directly |
| **Sensor**: reports position with random error, only every so often | A flaky upstream API that returns approximate values on a polling interval |
| **Measurement**: one sensor reading with a timestamp | One event in an event log |
| **Estimator (Kalman filter)**: best guess of the true state from the readings | A smoothing model, like an exponentially weighted moving average, that also tracks how confident it is and adjusts its weighting automatically |
| **Runner**: advances time and moves data between components | A controller or orchestrator in a request pipeline |
| **CSV output + Python analysis** | An ETL export followed by a notebook or dashboard |

In one sentence: *simulate the truth, hide it behind a noisy sensor, estimate it from the sensor alone, and then measure how close the estimate got.*

The program has an exact answer key. Truth is known in simulation, so every component can be graded objectively. That makes it well suited to testing.

---

## 2. Scope

### In scope (v1)
- A single-process command-line program in C++17 on Linux.
- One-dimensional motion with state = position and velocity.
- One position sensor with configurable noise, sample rate and random seed.
- A linear Kalman filter for the constant-velocity model.
- CSV output of truth, measurements and estimates.
- Python analysis: validate the CSV, compute RMSE, plot.
- Automated tests with a **pluggable C++ test framework** (§7), plus black-box system tests in Python.
- CI on Linux that builds and tests on every push and pull request.

### Out of scope (v1). These may become later extensions.
- 2D/3D motion, orbital mechanics, multiple sensors, sensor fusion.
- Extended/unscented Kalman filters and other nonlinear estimators.
- Networking, message buses, "distributed" deployment, real-time scheduling.
- GUI or web front end.
- Containers (optional once the native build is reliable).
- Any claim of flight qualification or operational fidelity.

---

## 3. Components and data flow

```text
            config (CLI flags)
                   │
                   ▼
┌──────────────────────────── Runner ────────────────────────────┐
│  for step k = 0..N:                                             │
│    truth_k  = Dynamics.propagate(truth_{k-1}, dt)               │
│    meas_k?  = Sensor.observe(truth_k)       (only every M steps)│
│    est_k    = Estimator.predict(dt)                             │
│    if meas_k: est_k = Estimator.update(meas_k)                  │
│    Recorder.write(k, truth_k, meas_k?, est_k)                   │
└─────────────────────────────────────────────────────────────────┘
                   │  run.csv
                   ▼
          Python analyze.py  →  metrics (stdout/JSON) + plot.png
```

**Hard rule:** the Estimator's interface never receives a `TrueState`. That rule is enforced by the type system, not by convention (EST-002).

### Core data types (value types, no hidden state)

| Type | Fields (SI units) |
|---|---|
| `TrueState` | `t_s`, `position_m`, `velocity_mps` |
| `Measurement` | `t_s`, `position_m`, `sensor_id` |
| `Estimate` | `t_s`, `position_m`, `velocity_mps`, covariance `P` (2×2) |

Units are part of the field name, so a mismatch is visible in code review. This avoids the kind of units mix-up that caused the loss of the Mars Climate Orbiter.

---

## 4. Functional requirements

Priorities use MoSCoW: **M**ust, **S**hould, **C**ould. Each requirement is written to be *testable*, and every test will cite at least one requirement ID (TST-005).

### 4.1 Dynamics / truth (SIM)

| ID | Pri | Requirement | Acceptance check |
|---|---|---|---|
| SIM-001 | M | Represent true state as position (m) and velocity (m/s) at time t (s). | Type exists; fields documented with units. |
| SIM-002 | M | Advance state in fixed steps of `dt` > 0. Time for step k is computed as `t = k * dt`, **not** by repeatedly adding `dt`. | At k = 1000, dt = 0.1: `t` equals `100.0` within 1e-9 s. |
| SIM-003 | M | With zero acceleration, propagation matches the analytic solution `x = x0 + v0·t`. | Within 1e-9 m after 1000 steps. |
| SIM-004 | S | Accept an optional constant known acceleration (m/s²). | Matches `x0 + v0·t + ½·a·t²` within a tolerance appropriate to the integrator (documented). |
| SIM-005 | M | Run for a configured number of steps N and produce N+1 truth rows (including t = 0). | Row count check. |

> Why `t = k * dt`? The same reason `0.1 + 0.2 !== 0.3` in JavaScript: adding 0.1 ten thousand times accumulates rounding error. Computing time from an integer step counter avoids the drift.

### 4.2 Sensor (SEN)

| ID | Pri | Requirement | Acceptance check |
|---|---|---|---|
| SEN-001 | M | Measure position only (not velocity). | Measurement type has no velocity field. |
| SEN-002 | M | Produce a measurement every M simulation steps (M ≥ 1, configurable), starting at step 0. | For N = 100, M = 5: exactly 21 measurements at k = 0, 5, …, 100. |
| SEN-003 | M | Add zero-mean Gaussian noise with standard deviation σ (m), configurable, σ ≥ 0. σ = 0 returns the exact true position. | σ = 0 → exact equality. σ = 5, 10,000 samples, fixed seed → sample mean within ±0.25 m and sample std within ±5% of σ. |
| SEN-004 | M | The same seed and configuration produce an identical measurement sequence on the same platform and build. | Two runs → byte-identical CSV. |
| SEN-005 | M | Each measurement carries the timestamp of the truth it observed and a sensor ID. | Field check. |
| SEN-006 | M | Observing truth does not modify truth. | Truth before == truth after (the sensor receives it by `const` reference). |
| SEN-007 | M | Reject invalid configuration (σ < 0, M < 1) with a clear error. | Construction fails; message names the bad parameter. |

### 4.3 Estimator (EST)

| ID | Pri | Requirement | Acceptance check |
|---|---|---|---|
| EST-001 | M | Implement a linear Kalman filter with state `[position, velocity]` and 2×2 covariance `P`. | Unit tests of predict and update math against hand-calculated values. |
| EST-002 | M | The public interface accepts only `Measurement`s, `dt` and configuration. It has no access to `TrueState`. | Compile-time: no overload accepts `TrueState`. |
| EST-003 | M | **Predict** every step, whether or not a measurement is available. | After predict with no update, position advances by `v·dt` and uncertainty grows. |
| EST-004 | M | **Update** (correct) when a measurement is available. | The estimate moves toward the measurement, and position variance decreases. |
| EST-005 | M | Configurable: initial state, initial covariance, process noise intensity `q`, measurement noise variance `R`. | Config round-trip test. |
| EST-006 | M | `P` stays symmetric with non-negative diagonal after every step. | Checked over a 1000-step run within 1e-9. |
| EST-007 | M | With σ = 0 and small `R`, the estimate converges to truth. | Position error < 1e-3 m after 50 measurements. |
| EST-008 | M | Reference scenario (§6): estimated-position RMSE is lower than raw-measurement RMSE, evaluated at measurement timestamps. | End-to-end check. |

The math is written here for reference and will be taught step by step before it is implemented:
`F = [[1, dt], [0, 1]]`, `H = [1, 0]`, `R = σ²`, `Q = q·[[dt³/3, dt²/2], [dt²/2, dt]]`.

### 4.4 Runner, configuration and output (RUN / CFG / OUT)

| ID | Pri | Requirement | Acceptance check |
|---|---|---|---|
| CFG-001 | M | All parameters are settable through command-line flags with documented defaults. **[DECIDE D3]** | `--help` lists every flag, its unit and its default. |
| CFG-002 | M | Invalid input → message on stderr, non-zero exit code, no partial output file. | System test. |
| RUN-001 | M | The runner performs, in order: propagate → observe (if due) → predict → update (if measured) → record. | Sequencing test using fake components. |
| OUT-001 | M | Write one CSV with a header row. Columns: `step,t_s,true_pos_m,true_vel_mps,meas_pos_m,est_pos_m,est_vel_mps,est_pos_var_m2,est_vel_var_m2s2`. `meas_pos_m` is empty when no measurement was taken. **[DECIDE D4]** | Python can parse it; column names match exactly. |
| OUT-002 | M | Doubles are written with enough precision to round-trip (17 significant digits). | Write → read → equality. |
| OUT-003 | S | Write the effective configuration (including seed) next to the CSV for reproducibility. | File exists and records the seed. |

### 4.5 Analysis (ANA), in Python

| ID | Pri | Requirement | Acceptance check |
|---|---|---|---|
| ANA-001 | M | Load the CSV and validate the required columns; fail with a clear message if any are missing. | pytest with a malformed file. |
| ANA-002 | M | Compute position and velocity RMSE of the estimate, and position RMSE of the raw measurements. | Known small input → hand-computed values. |
| ANA-003 | M | Plot truth, measurements and estimate versus time, with labeled axes, units and a legend, saved as a PNG. | File produced; smoke test. |
| ANA-004 | S | Plot estimation error with ±2σ bounds from the covariance. | Visual check; fraction of points inside the bounds reported. |
| ANA-005 | S | Print metrics to stdout and optionally write them as JSON. | pytest. |

---

## 5. Non-functional requirements (NFR)

| ID | Pri | Requirement |
|---|---|---|
| NFR-001 | M | C++17; builds warning-free with GCC 13 and Clang using `-Wall -Wextra -Wpedantic`. Warnings are treated as errors in CI. |
| NFR-002 | M | The core library depends only on the C++ standard library. Hand-written 2×2 matrix math. **[DECIDE D6]** |
| NFR-003 | M | No global mutable state. Randomness is injected through a seeded generator, never `rand()` or a time-based seed. |
| NFR-004 | M | Deterministic: identical inputs give identical outputs (see D5 for the cross-platform question). |
| NFR-005 | M | SI units throughout; unit suffixes in field and column names. |
| NFR-006 | M | The full C++ and Python test suite runs in under 30 s on a laptop. |
| NFR-007 | S | A sanitizer build (AddressSanitizer and UndefinedBehaviorSanitizer) runs the tests cleanly. |
| NFR-008 | C | A line-coverage report (gcov/gcovr) is generated in CI. |

---

## 6. Reference scenario (used by EST-008 and the demo)

| Parameter | Value |
|---|---|
| Initial truth | x0 = 0 m, v0 = 10 m/s, a = 0 |
| dt / steps | 0.1 s / 1000 steps (100 s) |
| Sensor | every 5 steps (2 Hz), σ = 5 m, seed = 42 |
| Estimator | x̂0 = [first measurement, 0], P0 = diag(25, 100), q = 0.1, R = 25 |

These values are placeholders to be tuned once the estimator runs.

---

## 7. Test architecture: designed to swap frameworks

The goal is to be able to change the C++ test framework **without touching any production code**, and with only thin, mechanical changes to test code.

```text
                    ┌───────────────────────────┐
                    │   simcore (static library) │  ← all logic; zero test deps
                    └─────────────┬─────────────┘
          ┌───────────────────────┼───────────────────────┐
          ▼                       ▼                       ▼
   sim (executable)     tests/support/ (neutral)   tests/system/ (pytest)
   main.cpp only        scenario builders,         runs the `sim` binary as a
                        analytic reference         black box; checks the CSV.
                        solutions, fakes,          Framework-independent.
                        tolerances, req IDs
                                  │
          ┌──────────────┬────────┴─────┬──────────────┐
          ▼              ▼              ▼              ▼
   tests/gtest/   tests/catch2/   tests/doctest/  tests/boost/     ← thin adapters
          └──────────────┴──────┬───────┴──────────────┘
                                ▼
                   CTest (single runner interface)
                                ▼
                   JUnit XML  →  CI test report
```

| ID | Pri | Requirement |
|---|---|---|
| TST-001 | M | All logic lives in the `simcore` library. `main.cpp` only parses flags and calls the library. (Web analogy: keep business logic out of the route handler.) |
| TST-002 | M | The framework is chosen at configure time with one CMake option, e.g. `-DSIM_TEST_FRAMEWORK=gtest`. No file outside `tests/` changes when switching. |
| TST-003 | M | Every C++ test registers with **CTest**. `ctest` is the single documented command, locally and in CI, whatever the framework. |
| TST-004 | M | Each run produces **JUnit XML**, the common report format that CI systems read. |
| TST-005 | M | Every test cites at least one requirement ID, using the framework's native mechanism (tag, property or description), so a traceability matrix can be generated. |
| TST-006 | M | Framework-neutral test support (scenario builders, reference solutions, fake sensor/estimator, tolerance constants) lives in `tests/support/` and includes no framework headers. |
| TST-007 | M | Components depend on small interfaces (e.g. `ISensor`, `IEstimator`, or a template parameter), so tests can substitute fakes. (Web analogy: dependency injection.) |
| TST-008 | M | System tests in pytest drive the built executable and check its outputs. They form a stable safety net that never changes when the C++ framework is swapped. |
| TST-009 | M | CI runs configure → build → `ctest` → `pytest` on Linux for every push and pull request. |
| TST-010 | S | CI runs the C++ suite under at least two frameworks (a matrix job) to prove the swap works. |

**Proposed approach to shared vs. per-framework code (D2):** the test *logic* (for example, "run 1000 steps and return the maximum error") lives in `tests/support/` as plain C++ functions. Each framework adapter is a few lines that call those functions and assert on the result in its own idiom. This avoids a home-grown macro layer that would hide the framework you're trying to learn and demonstrate.

---

## 8. Planned directory layout

```text
sensor-sim/
├── CMakeLists.txt                  # option SIM_TEST_FRAMEWORK
├── include/simulator/              # public headers: types, dynamics, sensor, estimator, runner
├── src/                            # simcore library sources + main.cpp
├── tests/
│   ├── CMakeLists.txt              # selects adapter dir from SIM_TEST_FRAMEWORK
│   ├── support/                    # framework-neutral helpers (TST-006)
│   ├── gtest/  catch2/  doctest/  boost/
│   └── system/                     # pytest black-box tests (TST-008)
├── python/analyze.py
├── docs/ (requirements.md, test-frameworks.md, architecture.md)
└── .github/workflows/ci.yml
```

---

## 9. Open decisions

| # | Decision | Options | Recommendation |
|---|---|---|---|
| D1 | Primary C++ framework, plus a second one to prove the swap | GoogleTest, Catch2, doctest, Boost.Test | **GoogleTest** as primary (most common in job postings). **Catch2** as second, because its style differs the most and so tests the seam well. |
| D2 | How much test code is shared | (a) neutral support + thin adapters; (b) one macro shim so each test is written once | **(a)**: idiomatic tests, less magic, easier to explain in an interview |
| D3 | Configuration input | CLI flags; key=value file; JSON (needs a library) | **CLI flags** for v1; a config file later |
| D4 | Output shape | One wide CSV; separate truth/measurement/estimate files | **One wide CSV**: simplest for Python and diffing |
| D5 | Cross-platform bit-identical randomness | Same-platform only; or write our own normal-distribution sampler | See the note below. Recommend **same-platform only for v1**, documented, with an own sampler as a stretch goal. |
| D6 | Matrix math | Hand-written 2×2; Eigen library | **Hand-written**: 2×2 is small, and you'll understand every line |
| D7 | C++ standard | C++17; C++20 | **C++17**: widely used in the industry and supported by every framework above |

> **D5 note:** `std::mt19937` produces the same numbers everywhere, but `std::normal_distribution` is *implementation-defined*. GCC's and Clang/MSVC's standard libraries can turn the same raw numbers into different Gaussian samples. Test expectations must therefore use statistical bounds, not hard-coded sample values, unless we write our own sampler.
