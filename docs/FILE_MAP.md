# File Map: what runs when, why, and who its parent is

"Parent" means whichever of these applies to the file:
- **caller**: the file whose code calls into it at run time;
- **includer**: the file that `#include`s / `import`s it;
- **builder**: the CMake target or CI step that compiles or launches it.

Everything below was checked against the actual `#include` lines, `import` lines, `CMakeLists.txt` files and
`ci.yml` at the current working tree. Function and line references are to the code after the recent fixes
(`kMaxSteps`, `req_trace.py`, the hardened `analyze.py`).

There are **four separate "worlds"**, each with its own entry point. Nothing in one calls into another except
through a file on disk or a subprocess:

| World | Entry point (the root of the tree) | Started by |
|---|---|---|
| 1. **Simulator at run time** | `src/main.cpp` → `main()` | You, typing `./build/sim …` |
| 2. **Analysis at run time** | `python/analyze.py` → `main()` | You, typing `python python/analyze.py run.csv` |
| 3. **Build** | `CMakeLists.txt` | `cmake -S . -B build` |
| 4. **Tests and CI** | `ctest` (via `tests/CMakeLists.txt`) and `.github/workflows/ci.yml` | You, or GitHub on push/PR |

---

## 1. The simulator at run time (`./build/sim --steps 12 --out r.csv`)

### 1a. Call tree (indentation = "called by the line above")

```text
OS
└─ src/main.cpp            main()                      ← the ONLY entry point; one call, nothing else
   └─ src/cli.cpp          cli_main(args, out, err)
      │
      ├─ [A] PARSE
      │   ├─ cli.cpp       parse()                     reads args against the flag table
      │   │   ├─ cli.cpp   flags()                     the table: 7 flags, each with an apply() lambda
      │   │   ├─ cli.cpp   parse_int()   / parse_double()   convert text → number or UsageError
      │   │   └─ include/simulator/config.hpp           RunConfig, DynamicsConfig, SensorConfig get filled
      │   └─ cli.cpp       print_help()                only if --help (then exit 0, nothing else runs)
      │
      ├─ [B] VALIDATE (before anything is created or written)
      │   ├─ src/dynamics.cpp   DynamicsConfig::validate()   dt, steps (0..kMaxSteps), x0, v0
      │   └─ src/sensor.cpp     SensorConfig::validate()     every_n_steps ≥ 1, sensor_id
      │
      ├─ [C] CONSTRUCT the three components
      │   ├─ src/sensor.cpp     PassthroughSensor(cfg)       validates AGAIN (defensive)
      │   ├─ src/estimator.cpp  PassthroughEstimator()       default-constructed; nothing runs yet
      │   └─ src/recorder.cpp   CsvRecorder(path)            opens <path>.tmp, writes the header line
      │
      ├─ [D] RUN
      │   └─ src/runner.cpp     run(cfg, sensor, estimator, recorder)
      │       ├─ src/dynamics.cpp   DynamicsConfig::validate()   a THIRD check (runner protects itself)
      │       ├─ src/dynamics.cpp   initial_state(cfg)           once, for step 0
      │       └─ loop k = 0 … steps ─────────────────────────────────────────────────────────────┐
      │           ├─ src/dynamics.cpp    propagate(truth, cfg, k)          every step except k = 0   │
      │           ├─ src/sensor.cpp      PassthroughSensor::observe()      every step                │
      │           ├─ src/estimator.cpp   initialized()                     every step                │
      │           ├─ src/estimator.cpp   initialize() | predict() | update()   per the call order   │
      │           └─ src/recorder.cpp    CsvRecorder::write_row()          every step                │
      │               └─ recorder.cpp    number()  (×~9 per row)           format + reject nan/inf   │
      │       ◄─────────────────────────────────────────────────────────────────────────────────────┘
      │       └─ src/recorder.cpp   CsvRecorder::commit()        once, after the last row: rename .tmp → .csv
      │
      └─ [E] EXIT
          ├─ return kExitOk (0)                         from cli.hpp constants
          └─ catch → "sim: error: …" on stderr, return 2 (UsageError, invalid_argument) or 1 (anything else)
```

The destructors run on the way out: `~CsvRecorder()` (recorder.cpp) deletes the `.tmp` file if `commit()` was never reached.

### 1b. Why each step happens in this order

| Phase | File called | Parent (caller) | Why it is here, and why then |
|---|---|---|---|
| Entry | `main.cpp` | the OS | Deliberately tiny so there is nothing in it to test or get wrong (TST-001) |
| Parse | `cli.cpp` | `main.cpp` | Turns text into a `RunConfig`. Lives in the library, not in `main`, so tests can call it directly with fake streams |
| Defaults | `config.hpp` | `cli.cpp` (the `RunConfig cfg;` line) | Default values live with the structs, so a run with no flags is well-defined |
| Validate | `dynamics.cpp`, `sensor.cpp` | `cli.cpp` | **Before** the recorder is constructed, so a bad flag can never create a file (exit 2, "nothing written") |
| Construct sensor | `sensor.cpp` | `cli.cpp` | The runner is handed interfaces; the CLI is the only place that picks the concrete `Passthrough*` classes. At M2/M3 this is the line that changes to swap in the noisy sensor and Kalman filter |
| Construct estimator | `estimator.cpp` | `cli.cpp` | Same reason |
| Construct recorder | `recorder.cpp` | `cli.cpp` | Opens `<path>.tmp` now so an unwritable path fails *early* (exit 1) before any simulation time is spent |
| Run | `runner.cpp` | `cli.cpp` | The one place that owns the time loop and call order (RUN-001) |
| Re-validate | `dynamics.cpp` | `runner.cpp` | `run()` is a public function; anyone calling it directly (a test) gets the same protection |
| Initial state | `dynamics.cpp` | `runner.cpp` | Step 0 is the starting truth at t = 0 |
| Propagate | `dynamics.cpp` | `runner.cpp` (loop, `k > 0`) | Advances truth one step; pure function, so it is checked against the closed-form formula |
| Observe | `sensor.cpp` | `runner.cpp` | Truth goes in as `const`; the sensor decides if a reading is due |
| Estimator calls | `estimator.cpp` | `runner.cpp` | Receives only the measurement, never truth. See 1c |
| Write row | `recorder.cpp` | `runner.cpp` | One row per step, including steps with no measurement |
| Commit | `recorder.cpp` | `runner.cpp` | Only after the loop finishes; this single call is what publishes the file |
| Error mapping | `cli.cpp` | `main.cpp` (return value) | The one place that turns exceptions into exit codes 1 and 2 |

### 1c. What the runner calls on each step (the order that the tests pin)

For step `k`, with `meas` = whatever the sensor returned:

| Situation | Calls, in order |
|---|---|
| `k = 0` | (no propagate) → `observe` → *(estimator not yet initialised)* → `initialize` if `meas` exists → `write_row` |
| Estimator not yet initialised, no `meas` | `propagate` → `observe` → `write_row` (estimate columns blank) |
| Estimator not yet initialised, `meas` arrives | `propagate` → `observe` → `initialize` (**no predict**) → `write_row` |
| Initialised, no `meas` | `propagate` → `observe` → `predict` → `write_row` |
| Initialised, `meas` present | `propagate` → `observe` → `predict` → `update` → `write_row` |
| After the last step | `commit` |

### 1d. Who throws, who catches

| Thrown by (file) | Exception | Caught by | Result |
|---|---|---|---|
| `cli.cpp` `parse_int` / `parse_double` / `parse` | `UsageError` | `cli.cpp` `cli_main` | exit **2**, nothing written |
| `dynamics.cpp` / `sensor.cpp` `validate()` | `std::invalid_argument` | `cli.cpp` `cli_main` | exit **2**, nothing written |
| `recorder.cpp` constructor (cannot open) | `std::runtime_error` | `cli.cpp` `cli_main` | exit **1** |
| `recorder.cpp` `number()` (nan/inf) | `std::runtime_error` | `cli.cpp` `cli_main` | exit **1**, temp file deleted by the destructor |
| `recorder.cpp` `commit()` (write or rename failed) | `std::runtime_error` | `cli.cpp` `cli_main` | exit **1**, temp file deleted |
| `estimator.cpp` `predict`/`update` before `initialize` | `std::logic_error` | `cli.cpp` `cli_main` | exit **1** (cannot happen via `runner.cpp`'s order; guards misuse) |

### 1e. Header files: who includes whom (compile-time parents)

Headers do not "run"; this is the dependency order, which decides what must recompile when one changes.

```text
mat2.hpp                      (no includes)  ← leaf
 └─ state.hpp                 TrueState, Measurement, Estimate
     ├─ dynamics.hpp          also includes config.hpp
     ├─ estimator.hpp
     ├─ recorder.hpp
     └─ sensor.hpp            also includes config.hpp
config.hpp                    (no includes)  ← leaf. RunConfig, DynamicsConfig, SensorConfig, kMaxSteps
cli.hpp                       (no includes)  ← leaf. exit codes, cli_main declaration
runner.hpp                    includes config, estimator, recorder, sensor
```

| Header | Included by (source) | Included by (other headers) |
|---|---|---|
| `mat2.hpp` | – | `state.hpp` |
| `state.hpp` | – | `dynamics.hpp`, `estimator.hpp`, `recorder.hpp`, `sensor.hpp` |
| `config.hpp` | `cli.cpp` | `dynamics.hpp`, `sensor.hpp`, `runner.hpp` |
| `dynamics.hpp` | `dynamics.cpp`, `runner.cpp` | – |
| `sensor.hpp` | `sensor.cpp`, `cli.cpp` | `runner.hpp` |
| `estimator.hpp` | `estimator.cpp`, `cli.cpp` | `runner.hpp` |
| `recorder.hpp` | `recorder.cpp`, `cli.cpp` | `runner.hpp` |
| `runner.hpp` | `runner.cpp`, `cli.cpp` | – |
| `cli.hpp` | `cli.cpp`, `main.cpp` | – |

Note `cli.cpp` never includes `dynamics.hpp` or `state.hpp` directly. It only needs the validators (declared in
`config.hpp`) and the concrete component classes.

---

## 2. Analysis at run time (`python python/analyze.py r.csv`)

```text
OS
└─ python/analyze.py   main(argv)
   ├─ argparse                        reads the csv path
   ├─ analyze.py  read_rows(path)     opens the CSV; checks header against EXPECTED_HEADER,
   │                                  checks every row has 9 fields, converts decode errors
   ├─ analyze.py  compute_metrics(rows)
   │   ├─ analyze.py  _number()  (×4 per measurement row)   text → finite float, or CsvFormatError
   │   └─ analyze.py  _rmse()    (×3)                       √ mean of squares
   └─ prints "key = value"; on CsvFormatError / OSError prints "analyze: error: …" and returns 1
```

| File | Parent | Why |
|---|---|---|
| `python/analyze.py` | you (CLI), or `tests/system/test_walking_skeleton.py` via `subprocess`, or imported by tests | Reads the file the simulator wrote. This CSV is the **only** connection between world 1 and world 2 |
| `run.csv` (data, not code) | written by `recorder.cpp`, read by `analyze.py` | The contract between C++ and Python (schema_version 1). The header string lives in three places that must match: `recorder.cpp` `kCsvHeader`, `analyze.py` `EXPECTED_HEADER`, and `recorder_tests.cpp` |

`tools/req_trace.py` is **not** part of this flow. It reads test reports, not simulator output (see §4).

---

## 3. Build time (`cmake -S . -B build && cmake --build build`)

```text
CMakeLists.txt  (root, the parent of everything below)
├─ defines function sim_enable_warnings()          used by every target below
├─ add_library(simcore STATIC)   ← compiles: src/cli.cpp, dynamics.cpp, estimator.cpp,
│                                              recorder.cpp, runner.cpp, sensor.cpp
│                                  exposes:    include/  (so "simulator/…" headers resolve)
├─ add_executable(sim)           ← compiles: src/main.cpp ; links simcore
└─ add_subdirectory(tests)       (only if SIM_BUILD_TESTS is ON)
   └─ tests/CMakeLists.txt
      ├─ add_library(sim_test_support INTERFACE)   exposes tests/support/ ; links simcore
      ├─ add_subdirectory(gtest)
      │  └─ tests/gtest/CMakeLists.txt
      │     ├─ FetchContent googletest (URL + SHA-256)         ← downloads once
      │     ├─ add_executable(sim_gtest_tests)  ← 5 *_tests.cpp ; links sim_test_support + gtest_main
      │     ├─ gtest_discover_tests(...)         registers each TEST as its own CTest entry
      │     └─ add_test(junit.gtest ...)         re-runs the binary to produce gtest.xml
      └─ add_test(system.pytest ...)             runs pytest against ./sim  → pytest.xml
```

| File | Parent (builder) | Why |
|---|---|---|
| `src/*.cpp` except `main.cpp` | target `simcore` in the root `CMakeLists.txt` | All logic is in one library so tests can link it |
| `src/main.cpp` | target `sim` | Kept out of the library so `simcore` has no `main()` and tests can supply their own |
| `include/simulator/*.hpp` | not compiled alone; pulled in through `target_include_directories(simcore PUBLIC include)` | `PUBLIC` means anything that links `simcore` can also `#include "simulator/…"` |
| `tests/support/*.hpp` | target `sim_test_support` | Shared fakes and tolerances, free of any test-framework header |
| `tests/gtest/*_tests.cpp` | target `sim_gtest_tests` | The GoogleTest-specific layer |
| `pytest.ini` | read by `pytest`, launched by the `system.pytest` CTest entry | Sets `pythonpath = python tools` so tests can `import analyze` and `import req_trace` |

---

## 4. Tests and CI

### 4a. What `ctest` runs and what each one calls

```text
ctest  (entry point; run from build/)
├─ 12 × <Suite>.<Test>           [label: unit]   ← from gtest_discover_tests; each is sim_gtest_tests --gtest_filter=…
│    └─ sim_gtest_tests          calls simcore code in-process (see 4b)
├─ junit.gtest                   [label: report] ← sim_gtest_tests again, writes build/test-reports/gtest.xml
└─ system.pytest                 [label: system] ← $SIM_PYTHON -m pytest, writes build/test-reports/pytest.xml
     │   env: SIM_BIN = path to the built ./sim
     ├─ tests/conftest.py                     parent of all pytest tests: supplies fixtures sim_bin, run_sim,
     │                                        and the autouse hook that writes the `requirements` property
     ├─ tests/system/test_walking_skeleton.py  → runs ./sim as a subprocess (via run_sim); also runs analyze.py
     ├─ tests/python/test_analyze.py           → imports python/analyze.py directly
     ├─ tests/python/test_req_trace.py         → imports tools/req_trace.py directly
     └─ tests/python/test_repo_rules.py        → reads src/, include/, tests/support/ as TEXT (greps them); runs no code
```

### 4b. Which test file exercises which production file (child → what it calls)

| Test file | Parent (builder / runner) | Production code it calls | Support files it includes | Requirement IDs |
|---|---|---|---|---|
| `tests/gtest/dynamics_tests.cpp` | `sim_gtest_tests` | `dynamics.cpp` (`initial_state`, `propagate`, `validate`) | `scenarios.hpp`, `tolerances.hpp` | SIM-002/003/006 |
| `tests/gtest/estimator_tests.cpp` | `sim_gtest_tests` | `estimator.cpp` (`PassthroughEstimator`) | – | EST-009 |
| `tests/gtest/interface_tests.cpp` | `sim_gtest_tests` | none at run time; `static_assert`s on `estimator.hpp` types, checked at **compile** time | – | EST-002, SYS-002 |
| `tests/gtest/recorder_tests.cpp` | `sim_gtest_tests` | `recorder.cpp` (`CsvRecorder`, `kCsvHeader`) | – | OUT-001/002/004/005 |
| `tests/gtest/runner_tests.cpp` | `sim_gtest_tests` | `runner.cpp` `run()` (which in turn calls `dynamics.cpp`) | `fakes.hpp` | RUN-001, SIM-005/006, EST-009 |
| `tests/system/test_walking_skeleton.py` | `system.pytest` via `conftest.py` | the whole of world 1 (`main.cpp` → everything) as a black box, plus `analyze.py` | – | OUT-001, SIM-005, CFG-001/002, OUT-004, ANA-002, SYS-001 |
| `tests/python/test_analyze.py` | `system.pytest` | `python/analyze.py` | – | ANA-001/002 |
| `tests/python/test_req_trace.py` | `system.pytest` | `tools/req_trace.py` | – | TST-011, TST-005 |
| `tests/python/test_repo_rules.py` | `system.pytest` | none; text-scans `src/*.cpp`, `include/**`, `tests/support/*`, `src/main.cpp` | – | TST-001/006, NFR-003 |

Note the contrast: `runner_tests.cpp` reaches `cli.cpp`, `sensor.cpp`, `estimator.cpp` and `recorder.cpp` **not at all** (it uses fakes
from `fakes.hpp` instead) and only the real `dynamics.cpp`. That isolation is the point: it tests the call order
and nothing else. `cli.cpp`, `main.cpp` and `sensor.cpp` are covered only through the black-box system tests; there
are no C++ unit tests for them yet.

### 4c. Support files (children of the C++ tests)

| File | Included by | What it provides |
|---|---|---|
| `tests/support/fakes.hpp` | `runner_tests.cpp` | `ScriptedSensor`, `RecordingEstimator`, `RecordingRecorder`, `CallLog` |
| `tests/support/scenarios.hpp` | `dynamics_tests.cpp` | `analytic_position_m()`, the independent oracle |
| `tests/support/tolerances.hpp` | `dynamics_tests.cpp` | `kPositionTol_m`, `kTimeTol_s` |

### 4d. The traceability chain (a second, test-side flow)

```text
each test            → names requirement IDs  (RecordProperty in C++ / @pytest.mark.req in Python)
tests/conftest.py    → copies the pytest marker into the JUnit XML
gtest.xml, pytest.xml → written by the junit.gtest and system.pytest CTest entries
tools/req_trace.py   → reads both XML files + docs/requirements.csv ; prints coverage ; exit 1 on unknown ID / orphan test
```

`tools/req_trace.py` is called by **CI** and by you (README step 5); it is not called by `ctest`. It is
unit-tested by `tests/python/test_req_trace.py`.

### 4e. CI (`.github/workflows/ci.yml`), the parent of the sequence on GitHub

```text
GitHub push / pull_request
└─ job build-test  (matrix: gcc-13, clang-18)
   ├─ checkout
   ├─ install toolchain
   ├─ python venv + pip install -r python/requirements.txt     ← python/requirements.txt
   ├─ cmake configure     → root CMakeLists.txt (world 3)
   ├─ cmake build
   ├─ ctest               → world 4a
   ├─ python tools/req_trace.py …                              ← tools/req_trace.py, docs/requirements.csv
   └─ upload build/test-reports/
```

CI runs the same commands as the README, so the README is the human-readable parent of the CI file.

---

## 5. Master index: every file, its parent, and when it is used

Legend: **R** run time · **B** build time · **T** test time · **D** documentation only.

| File | When | Parent (caller / includer / builder) | Called or used when |
|---|---|---|---|
| `src/main.cpp` | R | OS; built by target `sim` | Process start; makes one call and returns |
| `src/cli.cpp` | R | `main.cpp` (`cli_main`) | Right after start; parses, validates, wires components, maps errors to exit codes |
| `include/simulator/cli.hpp` | B | `main.cpp`, `cli.cpp` | Compile time; declares `cli_main`, exit codes |
| `include/simulator/config.hpp` | R, B | `cli.cpp`, `dynamics.hpp`, `sensor.hpp`, `runner.hpp` | Defaults, config structs, `kMaxSteps` |
| `src/dynamics.cpp` | R | `cli.cpp` (validate), `runner.cpp` (validate, initial_state, propagate) | Validation at start; one `initial_state`; `propagate` once per step after step 0 |
| `include/simulator/dynamics.hpp` | B | `dynamics.cpp`, `runner.cpp`, `dynamics_tests.cpp` | Declares the two pure functions |
| `src/sensor.cpp` | R | `cli.cpp` (validate, construct), `runner.cpp` (`observe`) | Validation at start; `observe` every step |
| `include/simulator/sensor.hpp` | B | `sensor.cpp`, `cli.cpp`, `runner.hpp`, `fakes.hpp` | Declares `ISensor` and `PassthroughSensor` |
| `src/estimator.cpp` | R | `runner.cpp` | `initialize` once; `predict`/`update` each step after that |
| `include/simulator/estimator.hpp` | B | `estimator.cpp`, `cli.cpp`, `runner.hpp`, `fakes.hpp`, two test files | Declares `IEstimator`; the type-level wall against seeing truth |
| `src/recorder.cpp` | R | `cli.cpp` (construct), `runner.cpp` (`write_row`, `commit`) | Opens file at start; one row per step; publishes at end; cleans up in destructor if failed |
| `include/simulator/recorder.hpp` | B | `recorder.cpp`, `cli.cpp`, `runner.hpp`, `fakes.hpp`, `recorder_tests.cpp` | Declares `IRecorder`, `CsvRecorder`, `kCsvHeader` |
| `src/runner.cpp` | R | `cli.cpp` | Once, after setup; owns the whole time loop |
| `include/simulator/runner.hpp` | B | `runner.cpp`, `cli.cpp`, `runner_tests.cpp` | Declares `run()` |
| `include/simulator/state.hpp` | B | `dynamics.hpp`, `estimator.hpp`, `recorder.hpp`, `sensor.hpp`, `interface_tests.cpp`, `scenarios.hpp` | Defines `TrueState`, `Measurement`, `Estimate` |
| `include/simulator/mat2.hpp` | B | `state.hpp` | Defines `Mat2` (the covariance container) |
| `CMakeLists.txt` | B | you / CI (`cmake -S . -B build`) | Configure time; parent of the whole build |
| `tests/CMakeLists.txt` | B | root `CMakeLists.txt` | Configure time, if tests are on |
| `tests/gtest/CMakeLists.txt` | B | `tests/CMakeLists.txt` | Configure time; downloads GoogleTest |
| `python/analyze.py` | R, T | you; `test_walking_skeleton.py` (subprocess); `test_analyze.py`, `test_walking_skeleton.py` (import) | After a simulator run |
| `python/requirements.txt` | B | README step 1 / CI `pip install` | Environment setup |
| `tools/req_trace.py` | T | CI step; you (README step 5); `test_req_trace.py` (import) | After `ctest`, to check traceability |
| `docs/requirements.csv` | T | `tools/req_trace.py` (`--requirements`) | Whenever `req_trace.py` runs |
| `pytest.ini` | T | `pytest` (launched by `system.pytest`) | Pytest startup: import paths, markers, report format |
| `tests/conftest.py` | T | `pytest` (auto-discovered) | Pytest startup, before any Python test; provides fixtures `sim_bin`, `run_sim` |
| `tests/system/test_walking_skeleton.py` | T | `system.pytest` | Black-box checks of `./build/sim` |
| `tests/python/test_analyze.py` | T | `system.pytest` | Unit tests of `analyze.py` |
| `tests/python/test_req_trace.py` | T | `system.pytest` | Unit tests of `req_trace.py` |
| `tests/python/test_repo_rules.py` | T | `system.pytest` | Text scans for inspection-type requirements |
| `tests/gtest/dynamics_tests.cpp` | T | target `sim_gtest_tests` | Runs inside the gtest binary |
| `tests/gtest/estimator_tests.cpp` | T | target `sim_gtest_tests` | ″ |
| `tests/gtest/interface_tests.cpp` | T, B | target `sim_gtest_tests` | Compile time (`static_assert`); trivially at run time |
| `tests/gtest/recorder_tests.cpp` | T | target `sim_gtest_tests` | ″ |
| `tests/gtest/runner_tests.cpp` | T | target `sim_gtest_tests` | ″ |
| `tests/support/fakes.hpp` | T | `runner_tests.cpp` | Test doubles |
| `tests/support/scenarios.hpp` | T | `dynamics_tests.cpp` | Analytic oracle |
| `tests/support/tolerances.hpp` | T | `dynamics_tests.cpp` | Numeric tolerances |
| `.github/workflows/ci.yml` | T | GitHub (push / PR) | Every push and pull request |
| `.gitignore` | – | git | Whenever git decides what to track |
| `.vscode/settings.json` | – | VS Code CMake extension | Editor open only; not part of the build |
| `README.md` | D | humans; mirrored by `ci.yml` | First read; its commands are what CI runs |
| `docs/*.md` | D | humans | Design record; `architecture.md` is the "as built" page |
| `docs/CODE_REPORT.md` | D | humans | The line-by-line review |
| `docs/FILE_MAP.md` | D | humans | This file |

---

## 6. One-page picture

```text
                          ┌──────────────────────────  BUILD  ──────────────────────────┐
                          │ CMakeLists.txt ─▶ simcore (6 .cpp) ─▶ sim (main.cpp)         │
                          │        └─ tests/CMakeLists ─▶ gtest/ ─▶ sim_gtest_tests      │
                          └──────────────────────────────────────────────────────────────┘

 you ─▶ ./sim ─▶ main.cpp ─▶ cli.cpp ──validate──▶ dynamics.cpp / sensor.cpp
                                  │ construct
                                  ├──────────────▶ sensor.cpp, estimator.cpp, recorder.cpp
                                  └─ run ────────▶ runner.cpp ─┬─▶ dynamics.cpp  (truth)
                                                               ├─▶ sensor.cpp    (measurement)
                                                               ├─▶ estimator.cpp (estimate)
                                                               └─▶ recorder.cpp ──▶  run.csv
                                                                                        │
 you ─▶ python/analyze.py ◀──────────────────────────────────────────────────────────────┘
          └─▶ metrics on stdout

 ctest ─▶ sim_gtest_tests ─▶ (simcore, in-process; fakes for the runner)
       ─▶ system.pytest ─▶ conftest.py ─▶ test_*.py ─▶ ./sim, analyze.py, req_trace.py
 CI ────▶ build + ctest + req_trace.py ─▶ traceability.md
```
