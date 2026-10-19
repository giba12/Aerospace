# Aerospace (`sensor-sim`) — File-by-File Code Report

Scope: every tracked file in the repository at commit `19e8e67` (47 files, about 4,000 lines, of which
about 1,200 are code and the rest are documents). Code files are covered line by line (by line range where
lines do one job together). The six large Markdown documents are summarised, not annotated.

> **Update (after the review).** Four findings from §9 have since been fixed: `.vscode/settings.json`
> now uses `${workspaceFolder}`; `tools/trace.py` was renamed `tools/req_trace.py` (and its test to
> `test_req_trace.py`); `analyze.py` now reports bad cells, ragged rows and non-text files as clean
> `CsvFormatError`s; and `--steps` is capped at `kMaxSteps = 100000`. The line-by-line sections below
> describe the code **as first reviewed**, so line numbers in `analyze.py`, `dynamics.cpp`, `cli.cpp`,
> `config.hpp` and the affected tests have shifted. See `docs/architecture.md` S-11 to S-13.

**A note on "why".** I did not write this code, so the *why* sections are of two kinds, and I label them:

- **Recorded** — the project's own documents state the reason (cited by ID, e.g. `DD-002`, `S-4`).
- **Inferred** — the reason is my reading of the code and its context. Treat these as well-supported
  hypotheses, not quotes from the author.

**What I verified by running it** (GCC 13.3, Ninja, pinned pytest, out-of-tree build): the project builds with
`-Werror`, all 13 CTest entries pass (11 GoogleTest cases, the JUnit re-run, and the whole pytest suite),
`sim` writes the CSV shown in §2, `analyze.py` prints the metrics shown in the README, and `req_trace.py`
reports `22/61 Must requirements have a passing test`, which matches the README's "39 of 61 have no passing test".
Clang 18 and the GitHub CI workflow were **not** run.

---

## 1. The system in one page

### What it is
A deliberately small, one-dimensional simulation: an object moves; a sensor reports its position; an
estimator guesses the state from those reports only; a recorder writes everything to a CSV; Python reads the
CSV and scores the estimate against the truth. It is **milestone M0, the "walking skeleton"**: every stage
exists and runs, but the sensor and estimator are trivial stand-ins (`Passthrough*`). The Kalman filter,
noise, acceleration, plots and sidecar JSON are planned for M1–M5.

The project is as much a demonstration of *engineering process* as of simulation: requirement IDs, tests that
cite those IDs, a script that checks the citations, CI, and determinism.

### Data flow
```text
DynamicsConfig ──▶ initial_state / propagate ──▶ TrueState (t, x, v)
                                                    │ const&
                                                    ▼
                                   ISensor::observe(truth, step) ──▶ optional<Measurement>
                                                                          │ (truth is NOT passed on)
                                                                          ▼
                              IEstimator: initialize | predict | update ──▶ optional<Estimate>
                                                    │
        runner ──── write_row(step, truth, meas, est) ──▶ IRecorder ──▶ run.csv.tmp ─commit()─▶ run.csv
                                                                                                   │
                                                                      python/analyze.py ◀──────────┘
```

### Who owns what
| Concern | Owner | Why it lives there |
|---|---|---|
| Time loop and call order | `run()` in `runner.cpp` | One place defines the order, so one test can pin it (RUN-001) |
| Truth | `dynamics.cpp`, held by the runner | The estimator must never see it (SYS-002) |
| Sampling schedule | the sensor (`observe` returns empty when not due) | DD-002: the runner need not know the rate |
| Estimator lifecycle | the estimator (`Uninitialized → Tracking`) | DD-003: makes the step-0 rule explicit and testable |
| File format and atomicity | `CsvRecorder` | Isolated behind `IRecorder` |
| Flags, errors, exit codes | `cli_main` | Lives in the library so tests can call it (DD-001) |

### Build graph
```text
simcore (static lib: cli, dynamics, estimator, recorder, runner, sensor)  ← all logic
  ├── sim                (src/main.cpp: one call)
  ├── sim_test_support   (header-only fakes/helpers, links simcore)
  │     └── sim_gtest_tests  (+ GoogleTest, fetched by hash)
  └── CTest → system.pytest (drives ./sim as a black box + unit-tests the Python tools)
```

---

## 2. Reference run (verified)

`sim --steps 12 --out r.csv` produced exactly:

```csv
step,t_s,true_pos_m,true_vel_mps,meas_pos_m,est_pos_m,est_vel_mps,est_pos_var_m2,est_vel_var_m2s2
0,0,0,10,0,0,0,0,0
1,0.10000000000000001,1,10,,0,0,0,0
...
5,0.5,5,10,5,5,0,0,0
6,0.60000000000000009,6,10,,5,0,0,0
```

Reading it: a measurement exists on steps 0, 5, 10 (`--meas-every 5`); between them the "estimate" is held
(the stand-in has no motion model); the velocity estimate is always 0 (the stand-in never learns velocity);
variances are 0 (it has no uncertainty model). Hence the README's `rmse_est_vel_mps = 10.0` and 0.0 for the
position metrics — correct for a skeleton, and it proves the *pipeline*, not the *filter*.

---

## 3. Build, tooling and configuration files

### `CMakeLists.txt` (43 lines)
| Lines | What | Why |
|---|---|---|
| 1–2 | CMake ≥ 3.20, project `sensor_sim` 0.1.0, C++ only | Inferred: 3.20 is old enough to be common, new enough for `$<TARGET_FILE:>` in test properties and `FetchContent` URL hashing |
| 4–6 | C++17, required, **extensions off** | Extensions off gives `-std=c++17` not `gnu++17`, so non-portable GNU features fail early. C++17 is needed for `std::optional`, `std::filesystem`, `std::void_t`, nested namespaces |
| 7 | Export `compile_commands.json` | Inferred: editor/clang-tidy support |
| 9–11 | If no build type is given, force `RelWithDebInfo` | Inferred: optimised yet debuggable by default; `FORCE` so it also applies on a first configure. The guard skips multi-config generators, which choose the type at build time |
| 13–14 | Options `SIM_WARNINGS_AS_ERRORS` (ON), `SIM_BUILD_TESTS` (ON) | Recorded (S-6, NFR-001): the toolchain is pinned, so `-Werror` is safe; easy to turn off locally |
| 16–22 | Function `sim_enable_warnings(target)` adds `-Wall -Wextra -Wpedantic`, plus `-Werror` if enabled | Recorded: "one place defines the warning policy". Applied per target with `PRIVATE`, so it never leaks into GoogleTest, whose warnings we do not control |
| 24–32 | Static library `simcore` with six sources; public include dir `include` | Recorded (TST-001, DD-001): all logic in a library so tests link it. Public include means anything linking `simcore` gets `#include "simulator/..."`. The "standard library only" claim (NFR-002) is true: no `target_link_libraries` at all |
| 35–38 | Executable `sim` from `main.cpp`, links `simcore` privately | "Deliberately tiny": `main` is untestable, so it holds nothing |
| 40–43 | If tests are on, `enable_testing()` and descend into `tests/` | `enable_testing()` must be called at the top-level directory for `ctest` to work from `build/` |

### `.gitignore` (11 lines)
Ignores `build/`, `.venv/`, Python caches, and run outputs (`run.csv`, `*.csv.tmp`). The comment says small
curated example outputs go in `data/` and are added with `git add -f` — an intentional escape hatch so that
accidental run output is never committed but deliberate samples can be.

### `.vscode/settings.json` (3 lines)
Sets `cmake.sourceDirectory` to `/wsl.localhost/Ubuntu/home/gsals/aerospace/tests`. **This looks wrong**: it
is a machine-specific absolute path (WSL), and it points at `tests/` rather than the repository root where the
top-level `CMakeLists.txt` is. See §9.

### `pytest.ini` (8 lines)
- `pythonpath = python tools` makes `import analyze` and `import trace` work in tests without packaging.
- `testpaths = tests/system tests/python` so a bare `pytest` finds only Python tests (C++ tests are CTest's job).
- `--strict-markers` turns a misspelt marker into an error; `-p no:cacheprovider` avoids writing `.pytest_cache`.
- Registers the custom `req(*ids)` marker (TST-005) and selects `xunit1` JUnit format so properties are written
  as `<property>` children, which is what `req_trace.py` reads.

### `python/requirements.txt` (6 lines)
Exact pins (`==`) for pytest and its transitive dependencies (NFR-009, reproducibility). The comment notes that
pandas/matplotlib are added only in M4 when first imported — recorded as S-10.

### `.github/workflows/ci.yml` (56 lines)
| Lines | What | Why |
|---|---|---|
| 1–10 | Runs on every push and pull request | TST-009 |
| 12 | `ubuntu-24.04`, not `ubuntu-latest` | Recorded in the comment: "latest" would silently change the toolchain |
| 13–20 | Matrix: `gcc-13`/`g++-13` and `clang-18`/`clang++-18`, `fail-fast: false` | Two compilers catch different warnings; `fail-fast: false` lets one compiler's failure not hide the other's |
| 22 | `actions/checkout@v5` | Standard |
| 24–27 | Installs Ninja, `python3-venv`, both compilers | |
| 29–32 | Creates `.venv` at the repo root and installs pinned requirements | The path matters: `tests/CMakeLists.txt` defaults `SIM_PYTHON` to `<source>/.venv/bin/python` |
| 34–41 | Configure → build → `ctest --output-on-failure` | Comment says these are the README's commands; if they diverge, SYS-001 is failing |
| 43–49 | Traceability gate via `tools/req_trace.py` over both JUnit files, writing a matrix | Without `--require-coverage` until M5 (S-7) |
| 51–56 | Uploads `build/test-reports/` even on failure (`if: always()`) | So a failed run's XML is inspectable |

Caveat: the README states the workflow "has not run on GitHub yet". The action versions (`checkout@v5`,
`upload-artifact@v6`) were not verified by me.

---

## 4. Public headers (`include/simulator/`)

### `state.hpp` (32 lines) — the data dictionary
- 1–5: `#pragma once`; includes `<string>` (for `sensor_id`) and `mat2.hpp` (for `P`).
- 7: comment ties it to baseline §7.7 and the **unit-in-the-name rule** (NFR-005): `position_m`, `velocity_mps`,
  `t_s`. *Why:* units are the classic source of aerospace bugs; encoding them in names makes a mismatch visible
  at the call site.
- 11–15 `TrueState {t_s, position_m, velocity_mps}`: plain aggregate, no invariants, no constructor. The comment
  is the architectural rule: *owned by the runner, never given to the estimator*.
- 18–22 `Measurement {t_s, position_m, sensor_id}`: **no velocity field exists** (SEN-001) — the physics
  forces the estimator to *infer* velocity, which is the whole point of a Kalman filter demo.
- 25–30 `Estimate {t_s, position_m, velocity_mps, Mat2 P}`: `P` is the 2×2 covariance of [position, velocity].
- *Why value types:* cheap to copy, trivially testable, no hidden state (the continuation guide asks for
  "small value-like structures" and "no global mutable state").

### `mat2.hpp` (13 lines)
`struct Mat2` with four doubles, default `0.0`. DD-004: hand-written, no Eigen, to stay dependency-free
(NFR-002) and fully explainable. At M0 it is only a container for `P`; arithmetic arrives with the Kalman
filter (M3). The `{0.0, 0.0}` default initialisers mean `Mat2{}` is a zero matrix.

### `config.hpp` (36 lines)
- 10–18 `DynamicsConfig`: `dt_s=0.1`, `steps=1000`, `x0_m=0`, `v0_mps=10`, plus `validate() const`.
  `steps` is `std::int64_t` so a very large step count cannot overflow a 32-bit `int`.
- 22–27 `SensorConfig`: `every_n_steps=5`, `sensor_id="pos0"`, `validate() const`.
- 30–34 `RunConfig` aggregates both plus `out_path="run.csv"`.
- *Why this shape:* DD-008 — plain config structs with a `validate()` method, hand-written, no library. The
  defaults here are duplicated in the CLI help table (`cli.cpp`); the two must agree by hand. Comments
  ("M2 adds sigma_m and seed") show the structs are designed to grow.
- `validate()` is declared here but **defined** in `dynamics.cpp` / `sensor.cpp` next to the code that cares.

### `dynamics.hpp` (18 lines)
Two free functions, not a class: `initial_state(cfg)` and `propagate(prev, cfg, k)`. IF-03: **pure functions**
(no hidden state), which makes them trivially testable against an analytic formula. The comment explains the
key numerical decision: `k` is the index of the *new* state and `t = k * dt` is **computed by multiplication,
not accumulated** (SIM-002), so rounding error does not grow with run length.

### `sensor.hpp` (29 lines)
- 12–16 `ISensor::observe(const TrueState&, std::int64_t step) → std::optional<Measurement>`. Three decisions
  in one signature: **truth is `const`** (SEN-006: looking can't change it), **the sensor owns the schedule**
  (DD-002 — empty optional means "no reading due"), and the **step index** is passed in rather than the sensor
  counting calls itself (so it is stateless and fakes can be scripted).
- 20–27 `PassthroughSensor final`: reports exact position every `every_n_steps` starting at step 0 (SEN-002).
  `final` because it is a leaf; the constructor is `explicit`.

### `estimator.hpp` (33 lines)
- 10–17 `IEstimator` with `initialized()`, `initialize`, `predict(dt)`, `update(z)`. **No method takes a
  `TrueState`** — this is how SYS-002/EST-002 is enforced *by the type system*, and
  `tests/gtest/interface_tests.cpp` proves it at compile time.
- The comment defines the state machine `Uninitialized → Tracking` (DD-003) and the failure rule: calling
  `predict`/`update` first throws `std::logic_error` and changes nothing.
- `initialize` is separate from `update` so the "first reading initialises the filter, no predict step" rule
  (EST-009) is explicit rather than a hidden branch.
- 21–31 `PassthroughEstimator final`: honest comment — "no model, so it is not a filter". Holds `initialized_`
  and the latest `Estimate`.

### `recorder.hpp` (47 lines)
- 13–20 `IRecorder` with `write_row(step, truth, optional meas, optional est)` and `commit()`. Optionals map
  directly to the CSV's "empty field means missing" rule (OUT-005). `commit()` is the explicit "publish now"
  signal (OUT-004).
- 23 `extern const char* const kCsvHeader;` — `extern` is **required**: a `const` at namespace scope otherwise
  has internal linkage, so the test could not see the one definition in `recorder.cpp`. One definition,
  used by both the writer and the test.
- 28–45 `CsvRecorder final`: **RAII** — the comment explains the contract: write to `<path>.tmp`, rename on
  `commit()`, delete the temp file in the destructor if never committed. Copy is deleted (it owns an open
  file stream and a "committed" flag; copying either would be a bug).

### `runner.hpp` (15 lines)
One free function `run(cfg, ISensor&, IEstimator&, IRecorder&)`. Components arrive as **interface references**
so tests can substitute fakes (TST-007). Contract in the comment: throws on invalid config *before touching any
component*, and calls `commit()` only after the last row.

### `cli.hpp` (19 lines)
- 10–12 Exit codes as `inline constexpr int` (IF-02): 0 ok, 1 runtime/I-O failure ("no CSV left behind"),
  2 usage error ("nothing written"). The 1-vs-2 split lets a script tell "you called it wrong" from "the world
  failed".
- 17 `cli_main(args, std::ostream& out, std::ostream& err)`. Taking streams and a `vector<string>` instead of
  `argc/argv` and `std::cout` is what makes the whole CLI unit-testable (TST-001). Error text format:
  `sim: error: <parameter>: <reason>` (CFG-002). Uses `<iosfwd>` so the header doesn't pull in `<iostream>`.

---

## 5. Source files (`src/`)

### `main.cpp` (9 lines)
Line 8 is the whole program: wrap `argv[1..argc)` in a `std::vector<std::string>` and return
`sim::cli_main(args, std::cout, std::cerr)`. Skipping `argv[0]` (the program name) is the `argv + 1`. *Why so
small:* TST-001; `tests/python/test_repo_rules.py` literally greps this file to enforce "exactly one call, no
`validate`, no `Estimator`".

### `dynamics.cpp` (34 lines)
- 8–21 `DynamicsConfig::validate()`: rejects `dt_s` non-finite or ≤ 0, `steps < 0`, and non-finite `x0_m`/`v0_mps`
  with `std::invalid_argument`. Messages start with the *config field name* (`dt_s: ...`) — CFG-002 says errors
  name the parameter. `std::isfinite` catches both NaN and ±inf, which `<= 0` alone would miss for NaN. Order
  matters only for which error you see first when several are wrong.
- 23–25 `initial_state`: `{t=0, x0, v0}` — step 0 is at t = 0 exactly.
- 27–32 `propagate`: explicit Euler. `t = k * dt` (multiplication, per SIM-002); `position = prev.pos + prev.vel*dt`;
  velocity unchanged. The comment is correct that with no acceleration this is exact. **Subtle point:** time is
  recomputed but *position is still accumulated* each step, so position drifts by floating-point rounding over
  long runs; the test tolerates 1e-9 m over 1000 steps. DD-006: Euler chosen because RK4 equals Euler for
  constant velocity, so it was deferred.

### `sensor.cpp` (27 lines)
- 7–14 `SensorConfig::validate()`: `every_n_steps >= 1` (guards the `%` below against divide-by-zero), and
  `sensor_id` non-empty with no comma. The no-comma rule exists because sensor ID is destined for a
  comma-separated format (the sidecar/CSV), not because the current CSV writes it.
- 16–18 Constructor copies the config and **validates again**. Defensive: a `PassthroughSensor` built directly
  (e.g. by a test) can never hold an invalid config, so `step % 0` is impossible.
- 20–25 `observe`: `if (step % every_n_steps != 0) return nullopt;` else `Measurement{truth.t_s,
  truth.position_m, id}`. Step 0 always measures (0 % n == 0) — which is what makes "initialise from the first
  reading on step 0" the normal case. The stand-in adds no noise; M2 will.

### `estimator.cpp` (34 lines)
- 7–9 `initialized()` returns the flag.
- 11–15 `initialize`: estimate = first measurement's time and position, **velocity 0**, covariance zero;
  sets the flag. No predict (EST-009).
- 17–23 `predict`: throws `std::logic_error` if uninitialised **before modifying anything** (so "changes
  nothing" holds, DD-007); otherwise advances only the clock `est_.t_s += dt_s` — position is *held*.
- 25–32 `update`: same guard; copies the measurement's time and position into the estimate.
- Observation: `est_.t_s` is *accumulated* here, unlike the truth's `k*dt`. It is harmless at M0 because the
  estimate's time is not written to the CSV, but it is the one place that contradicts the project's own
  time-handling rule, and the Kalman filter will need to handle it deliberately.

### `recorder.cpp` (87 lines)
- 12–14 The header string, one definition. Splits across two string literals; must equal the test's and
  `analyze.py`'s `EXPECTED_HEADER` (three places that must agree — see §9).
- 20–30 `number(value, column)`: (a) **rejects non-finite** values by throwing `std::runtime_error` naming the
  column, so `nan`/`inf` can never reach the file (OUT-005); (b) formats through an `ostringstream` imbued with
  `std::locale::classic()` so the decimal separator is always `.` regardless of the user's locale; (c)
  `precision(17)` — 17 significant digits **round-trips any IEEE double exactly** (OUT-002). The visible
  consequence is values like `0.10000000000000001`; that is correct, not noise.
- 34–40 Constructor: initialiser list builds `tmp_path_ = path + ".tmp"` and opens it with `std::ios::trunc`;
  if the open failed throws `runtime_error("<path>: cannot open for writing")` (→ exit 1). Because the
  constructor throws, no destructor runs, and since the file never opened there is nothing to clean up. Writes
  the header line.
- 42–48 Destructor: if not committed, close the stream and delete the temp file, using the
  `error_code` overload of `remove` so a destructor **cannot throw**. This is the "failed run leaves nothing"
  guarantee (OUT-004).
- 50–67 `write_row`: builds the row as a string *first*, then writes it once. That ordering means that if
  `number()` throws on a bad value, no partial row has been written. Columns: step (integer, no formatting),
  `t_s`, true pos, true vel, then measurement (empty string if absent), then four estimate fields, or `",,,,"`
  (four empty fields) if absent. Only `P.m00` and `P.m11` (the variances) are written; the cross-covariance
  `m01` is deliberately not in the schema (the baseline lists the cross term as an open decision, OI-03).
- 69–85 `commit`: idempotent (second call returns). Flush, check the stream state, close; throw if the write
  failed; `std::filesystem::rename(tmp, path)` (atomic on POSIX when both are on one filesystem — they are,
  same directory); throw on error; only then set `committed_`. If anything throws, `committed_` stays false and
  the destructor deletes the temp file.
- Behaviour worth knowing: a failed run **preserves a previous good `run.csv`** (it never touches the target
  until the final rename).

### `runner.cpp` (38 lines) — the heart of the system
- 10 `cfg.validate()` first, so an invalid config touches no component (SIM-006; tested with fakes).
- 12–13 `truth = initial_state(cfg)`; `std::optional<Estimate> est` starts empty = "estimator has no belief yet"
  (EST-009).
- 15 Loop `k = 0 … steps` **inclusive** → N steps give N+1 rows (SIM-005; step 0 is the initial state).
- 16–18 Propagate only for `k > 0`; step 0 is the initial state itself.
- 19–21 Ask the sensor for a measurement. The comment names the design rule: the estimator only ever receives
  `meas`, never `truth`.
- 23–32 The estimator state machine, which is the specified call order:
  - uninitialised and a reading exists → `initialize` (no predict);
  - uninitialised and no reading → do nothing, `est` stays empty (so the CSV has blank estimate cells);
  - already initialised → `predict(dt)` **every step**, then `update` **only if** there is a reading
    (predict-then-correct, EST-003/004).
- 33 Record the row with whatever exists.
- 35 `commit()` only after the last row — an exception anywhere above skips it, which, together with the RAII
  recorder, is how "no partial CSV" is achieved.
- Design note: `runner_tests.cpp` compares the *entire* call log, because "the order of calls IS the
  specification".

### `cli.cpp` (158 lines)
- 1–14 Includes: `<cerrno>`/`<cstdlib>` for `strtod`/`strtoll` error handling, `<functional>` for `std::function`,
  plus the project headers needed to assemble a run. (It relies on `cli.hpp` to bring in `<string>`/`<vector>`.)
- 17–21 Anonymous namespace (internal linkage). `UsageError : std::runtime_error`, inheriting constructors —
  a distinct type so `cli_main` can map "bad invocation" to exit code 2 separately from other runtime errors.
- 23–31 `parse_double`: resets `errno`, calls `strtod`, and rejects (a) empty text, (b) trailing garbage
  (`end != text.end`), (c) `ERANGE`. The error names the flag and quotes the value. The comment notes that
  finiteness is **not** checked here: `strtod` happily parses `nan`/`inf`, and `validate()` rejects them (this
  gives a parameter-named message such as `dt_s: must be finite`). I confirmed `--dt nan` → `dt_s: must be
  finite and > 0`.
- 33–41 `parse_int`: same pattern with `strtoll` base 10, so `--steps 1.5` and `--steps ten` fail with "not an
  integer".
- 43–51 `FlagSpec`: a row = name, unit, default text, help text, and an `apply` lambda that writes into
  `RunConfig`. **The table drives both parsing and `--help`** (S-4, CFG-001) so documentation can't drift from
  behaviour. `std::function` is chosen over a raw function pointer so the lambdas could capture, at a small
  cost that is irrelevant here.
- 53–81 The seven flags: `--steps`, `--dt`, `--x0`, `--v0`, `--meas-every`, `--sensor-id`, `--out`. The table is a
  function-local `static const` (initialised on first use; avoids static-initialisation-order issues).
  `--sensor-id` and `--out` ignore the flag-name argument (`const std::string&` unnamed to avoid an
  unused-parameter warning under `-Werror`).
- 83–92 `print_help`: generates the usage text from the table; "Educational … (not flight software)" repeats
  SYS-006's honesty statement.
- 95–127 `parse`: loops over args; `--help` short-circuits (`return false`); a token containing `=` is split
  into name/value (`--dt=0.2`); otherwise the **next** argument is the value (so negative numbers work:
  `--v0 -5`, which I ran and it exited 0); unknown flag → `UsageError`; missing value → `UsageError`. Linear
  search of the table is fine for seven entries. Note `--help` is matched *before* `=` splitting, so
  `--help=x` is reported as an unknown flag (I confirmed this; harmless).
- 131–156 `cli_main`: one `try` around everything.
  - builds a default `RunConfig`, parses, prints help and returns 0 if asked;
  - validates **both** configs *before* constructing the recorder, so a usage error never creates a file
    (confirmed by the system test: the directory is empty after bad input);
  - builds `PassthroughSensor`, `PassthroughEstimator`, `CsvRecorder`, calls `run`;
  - `catch` ladder, order matters: `UsageError` → 2; `std::invalid_argument` (failed `validate()`) → 2; any
    other `std::exception` (I/O, recorder, logic errors) → 1. `UsageError` derives from `runtime_error` and
    `invalid_argument` from `logic_error`, so the two specific handlers do not shadow each other.
  - all three print `sim: error: <what>` to `err`.
  - The recorder is a local, so unwinding destroys it uncommitted, deleting the temp file.

---

## 6. Python

### `python/analyze.py` (71 lines)
| Lines | What | Why |
|---|---|---|
| 1–9 | Docstring: M0 scope; standard library only | S-10: no pandas/matplotlib until they're needed (M4). The first docstring line doubles as `--help` description |
| 15–18 | `EXPECTED_HEADER` list | The Python-side copy of the schema; any mismatch is rejected (ANA-001) |
| 21–22 | `CsvFormatError(ValueError)` | A distinct error type so `main` can report format problems cleanly |
| 25–32 | `read_rows`: opens with `newline=""` (the `csv` module's required mode), `utf-8`, `DictReader`; if `fieldnames` differs from the expected list, raise | Fails early with both the actual and expected header in the message. Returns **strings**, not floats, so "empty" stays distinguishable from "0" |
| 35–36 | `_rmse` = √(mean(e²)) | |
| 39–54 | `compute_metrics`: keep only rows with non-empty `meas_pos_m`; raise if none (avoids ÷0); compute measurement error, estimated-position error, estimated-velocity error against truth; return counts and three RMSEs | ANA-002/CR-08: RMSE is taken over *measurement rows only*, so the raw sensor and the estimator are compared on the same sample set |
| 57–67 | `main`: argparse with a single `csv` argument; catches `CsvFormatError`/`OSError` → message to stderr, exit 1; prints `key = value` | |
| 70–71 | `if __name__ == "__main__": sys.exit(main())` | `main(argv=None)` takes an argv list so tests can call it |

Limitations: `float(...)` on a malformed cell raises an uncaught `ValueError` (not a `CsvFormatError`) and
produces a traceback instead of a clean message; only the header is validated, not every row.

### `tools/req_trace.py` (103 lines) — the traceability gate
| Lines | What | Why |
|---|---|---|
| 1–18 | Docstring: inputs, three checks | Check 3 (uncovered Must) is a report until M5 |
| 26–30 | `load_registry`: drops `#` comment lines, then `csv.DictReader` → `{id: priority}` | The registry CSV carries comment lines for provenance |
| 33–34 | `_split_ids`: normalises `;` to `,`, strips, drops empties | Tolerant of how tests write the list |
| 37–49 | `load_tests`: for every `<testcase>` in each JUnit file, read IDs from (a) a `requirements` **attribute** (how GoogleTest's `RecordProperty` is written) and (b) `<property name="requirements">` **children** (how pytest writes it); a test is "failed" if it has `failure`, `error` **or `skipped`**; name = `classname.name` | Handles both frameworks' JUnit dialects. Counting `skipped` as not-passing means a silently skipped test never counts as coverage |
| 52–64 | `analyze`: no IDs → "orphan test"; ID not in registry → "unknown requirement"; passing and known → coverage | Checks 1–2 always fail the build |
| 67–73 | `write_matrix`: Markdown table of ID, priority, passing tests (`**none**` if empty) | A human-readable artefact uploaded by CI |
| 76–99 | `main`: counts Musts (`priority == "M"`), prints coverage, prints the gap list, only turns gaps into errors if `--require-coverage` is set, writes the matrix, prints errors to stderr, returns 1 if any | Gate behaviour per S-7 |

Verified: it reports `22/61 Must requirements have a passing test` on the current JUnit files.

---

## 7. Tests

### Test architecture in one paragraph
Three layers: **framework-neutral support** (`tests/support/`, header-only fakes and helpers), a
**GoogleTest adapter** (`tests/gtest/`, the only place that knows the framework — TST-002/IF-11), and
**pytest** (black-box system tests of the real binary plus unit tests of the Python tools). Every test names the
requirement IDs it verifies, in a property that `req_trace.py` reads from JUnit XML. The system tests never change
if the C++ framework is swapped.

### `tests/CMakeLists.txt` (29 lines)
- 3–8 Cache variable `SIM_TEST_FRAMEWORK` (default `gtest`); fails configuration if no adapter directory of
  that name exists. Swapping framework = adding a directory; nothing outside `tests/` changes.
- 10 Creates `build/test-reports` so JUnit output has a home (TST-004).
- 13–15 `sim_test_support` is an `INTERFACE` library (header-only) that links `simcore`.
- 22–29 `system.pytest` CTest entry: runs `$SIM_PYTHON -m pytest -q --junitxml=…/pytest.xml` from the source
  root; `SIM_BIN=$<TARGET_FILE:sim>` is injected so tests find the freshly built binary. `SIM_PYTHON`
  defaults to the pinned venv; the comment says a missing venv should **fail** rather than skip silently
  (a skipped safety net is worse than a loud failure). Labelled `system`.

### `tests/gtest/CMakeLists.txt` (28 lines)
- 2–6 `FetchContent` GoogleTest v1.17.0 **by URL plus SHA-256** (S-1, NFR-009): a tag can be moved, a hash
  cannot. It downloaded and configured successfully in my run, so the hash is valid.
- 7 `INSTALL_GTEST OFF` so it doesn't pollute `install`.
- 10–17 Test executable from five files, links `sim_test_support` and `GTest::gtest_main` (supplies `main`),
  with the project's warning policy.
- 19–21 `gtest_discover_tests` registers each `TEST` as its own CTest entry (TST-003), labelled `unit`.
- 23–28 `junit.gtest` re-runs the whole binary once with `--gtest_output=xml:…` because CTest's own JUnit
  output would lose the `requirements` property (S-5). Costs ~0.02 s.

### `tests/conftest.py` (36 lines)
- 15–19 An `autouse` fixture reads `@pytest.mark.req(...)` markers and records a `requirements` property —
  this is the bridge from pytest to `req_trace.py`.
- 22–28 Session fixture `sim_bin`: reads `SIM_BIN`; if absent or non-existent it calls `pytest.fail` (not
  skip) with a message to use `ctest`.
- 31–36 `run_sim`: returns a function that runs the binary with `cwd=tmp_path` (every test gets a clean
  scratch directory, so "no file left behind" can be checked by listing it), capturing text output.

### `tests/support/` (header-only, no framework includes — TST-006)
- `tolerances.hpp` (9 lines): `kPositionTol_m = kTimeTol_s = 1e-9`, "one definition, so no test invents its own"
  (baseline §6.3).
- `scenarios.hpp` (15 lines): `analytic_position_m(cfg, k) = x0 + v0 * (k*dt)` — the **independent oracle**
  (closed form) for the Euler integrator.
- `fakes.hpp` (90 lines): a shared `CallLog` (vector of strings).
  - `ScriptedSensor` (23–39): measures on exactly the listed steps, with `truth + 0.5` so a test can tell a
    measurement from truth; logs `observe(k)`.
  - `RecordingEstimator` (41–63): logs `initialize`/`predict`/`update` and returns trivial estimates.
  - `RecordingRecorder` (65–88): logs `write_row(k)`/`commit` and counts rows, rows with an estimate, rows with a
    measurement.
  - These are what allow the runner's ordering to be tested without any real maths.

### `tests/gtest/dynamics_tests.cpp` (31 lines)
- `ConstantVelocityMatchesAnalyticSolution` (SIM-003, SIM-002): steps 1000 times via `propagate`, compares to the
  closed form within 1e-9 m, and checks `t == 100.0` within 1e-9 s ("k × dt, not accumulated").
- `RejectsNonFiniteOrNonPositiveDt` (SIM-006): `dt = 0` and `dt = NaN` both throw `std::invalid_argument`.

### `tests/gtest/estimator_tests.cpp` (15 lines)
`PredictBeforeInitializeIsRejected` (EST-009): predict on a new estimator throws `logic_error` and
`initialized()` is still false afterwards ("the rejected call changed nothing").

### `tests/gtest/interface_tests.cpp` (31 lines)
A `void_t` detection idiom, `CanUpdateWith<E, Arg>`, is true iff `E::update(Arg)` compiles. Two `static_assert`s
(accepts `Measurement`; **does not** accept `TrueState`) do the real work **at compile time**: if anyone adds an
overload taking the truth, the test binary stops compiling. The `TEST` body is just `SUCCEED()` so the
requirement tag (EST-002, SYS-002) shows up in the JUnit/traceability output. This is the strongest check in the
suite, since it is a property of the type system, not of one execution.

### `tests/gtest/recorder_tests.cpp` (103 lines)
`TempPath` RAII helper (unique file in the system temp dir, removed before and after) and a `slurp` reader.
- `HeaderIsExact` (OUT-001): a committed empty recorder contains exactly `kCsvHeader + "\n"`, and the header
  equals the spelled-out literal (so the constant can't be changed in lock-step with its test by accident).
- `NoFileLeftBehindWithoutCommit` (OUT-004): a row is written; the final file does not exist mid-run; after the
  recorder goes out of scope uncommitted, neither the file nor `.tmp` exists.
- `MissingValuesAreEmptyAndNumbersRoundTrip` (OUT-005, OUT-002): writes `0.1 + 0.2` (a famously inexact
  value); reads back the row, `stod`s it and `EXPECT_EQ`s exactly (proving 17 digits round-trip); the five
  trailing columns are empty and "nan" never appears. `f.resize(9)` is needed because `getline` drops a
  trailing empty field.
- `RejectsNonFiniteValues` (OUT-005): a NaN position throws `runtime_error`.

### `tests/gtest/runner_tests.cpp` (65 lines)
- `CallOrderMatchesSpecification` (RUN-001, EST-009): a sensor that first reports at step 1 (not step 0) over 3
  steps; the **entire expected log** is spelled out — no predict at initialisation, predict-only on a no-reading
  step, predict-then-update on a reading step, `commit` last; also asserts 3 of 4 rows have an estimate.
- `NSTepsProduceNPlusOneRows` (SIM-005): 10 steps → 11 rows.
- `InvalidConfigTouchesNothing` (SIM-006): `dt = -1` throws and the call log is empty.
- Test name `NSTepsProduceNPlusOneRows` has an odd capital `T` in "NSTeps" — cosmetic only.

### `tests/python/test_analyze.py` (40 lines)
Hand-computed oracles ("arithmetic by hand"): `test_rmse_uses_only_rows_with_a_measurement` builds three rows
where the middle one has no measurement and a wildly wrong estimate (99.0) and asserts it is ignored
(RMSE meas = 3, est pos = √½, est vel = 10). Also: no-measurement input raises `CsvFormatError` rather than
dividing by zero, and a wrong header is rejected (ANA-001, ANA-002).

### `tests/python/test_req_trace.py` (61 lines)
Builds a tiny registry and JUnit XML in `tmp_path` and drives `trace.main(...)`: all Musts covered passes with
the gate on; an uncovered Must fails **only** with `--require-coverage`; unknown IDs and orphan tests always fail;
a failing test does not count as coverage; the pytest-style `<property>` child is read. This is the "test of the
test tool" (TST-011).

### `tests/python/test_repo_rules.py` (29 lines)
Turns inspection-type requirements into automated checks by regex over source files: no test-framework headers
in `tests/support` (TST-006); no `rand`/`srand`/`time(`/`std::random_device` in `src/` and `include/`
(NFR-003 determinism); `main.cpp` contains exactly one `sim::cli_main(` and neither "validate" nor "Estimator"
(TST-001). These are crude by design (text, not AST) but cheap and effective.

### `tests/system/test_walking_skeleton.py` (64 lines)
Black-box tests of the real binary:
- default run writes the exact header and N+1 rows, no `.tmp` left (OUT-001, SIM-005);
- a parametrised table of five bad inputs (`--bogus`, missing value, non-integer, `dt=0`, `meas-every=0`) each
  exits **2**, stderr starts with `sim: error: `, names the parameter, and the working directory is empty
  (CFG-002);
- an unwritable output path (`/nonexistent-dir/run.csv`) exits **1** (CFG-002, OUT-004);
- `--help` mentions every flag (CFG-001);
- the M0 exit criterion: run `sim`, then run `analyze.py` as a subprocess on the output and check the RMSE lines
  print (ANA-002, SYS-001).

---

## 8. Documentation files (summary)

| File | Lines | Content |
|---|---|---|
| `README.md` | 132 | Safety/honesty banner (SYS-006), data-flow diagram, build/test/run/analyze commands (the same ones CI uses), expected output, repo layout, how to tag a test, limitations, next steps |
| `docs/architecture.md` | 38 | "As built at M0": table of what is real vs stub, and ten scaffolding decisions S-1…S-10 with alternatives and reasons |
| `docs/systems-engineering-baseline.md` | 1,018 | The design of record: stakeholders, requirements, risks, validation/verification strategy, RVCM, design decisions DD-001…DD-012, data dictionary, interfaces, 23 change requests (CR-01…23), rationale annex |
| `docs/requirements.md` | 248 | The requirement text |
| `docs/requirements-explained.md` | 473 | Plain-language explanation of each requirement |
| `docs/requirements.csv` | 74 | Machine-readable registry (`id,priority,method,level`): 61 Must, plus Should/Could. Read by `req_trace.py` |
| `docs/test-frameworks.md` | 254 | Test-framework background |
| `docs/CONTINUATION_GUIDE.md` | 253 | Brief for continuing the project with a learner: 30-day job-sprint context, teach-before-coding preference |

Note the registry in `requirements.csv` is generated from baseline §6.5, so there are two sources until
requirements v0.2 is issued (S-8).

---

## 9. Observations and risks

Ordered roughly by how much they matter. None block M0; I made no changes to the code.

1. **FIXED. `.vscode/settings.json` looked wrong and is machine-specific.** It hard-codes a WSL path and points CMake
   at `tests/` rather than the repo root, so VS Code's CMake extension would configure the wrong project for
   anyone else (and probably for its author). Remove it, add `.vscode/` to `.gitignore`, or set `${workspaceFolder}`.
2. **FIXED. `tools/trace.py` was imported as `import trace`, which shadows the Python standard-library `trace`
   module.** It works today because `pytest.ini`'s `pythonpath` puts `tools/` first, but it is fragile (any
   tool that imports stdlib `trace` in the same process would break). Renaming to e.g. `req_trace.py` removes the risk.
3. **The CSV header exists in three places** (`recorder.cpp`, `analyze.py`, and the test's literal). They are
   cross-checked by tests, which is good, but a schema change is a three-file edit.
4. **FIXED. `analyze.py` only validated the header.** A malformed numeric cell raises a raw `ValueError` traceback
   instead of a clean `analyze: error:`.
5. **FIXED (cap 100000). There was no upper bound on `--steps`.** `--steps 9000000000000` is accepted and would run for a very long time and
   try to write an enormous file. Reasonable for a teaching tool; worth a limit eventually.
6. **`strtod`'s `ERANGE` rejects subnormal numbers too** (I confirmed `--dt 1e-320` gives "not a number"). The
   message is slightly misleading but the behaviour is safe.
7. **`sensor_id` is validated only for emptiness and commas**, not newlines or quotes. It is not yet written to
   any file, so this only matters once the sidecar (M2) exists.
8. **`PassthroughEstimator::predict` accumulates time** (`est_.t_s += dt`), unlike the truth's `k*dt`. Not
   visible now; relevant when the Kalman filter lands.
9. **`cli.cpp` uses `std::vector` without including `<vector>`** (it arrives through `cli.hpp`). Compiles on
   both toolchains, but include-what-you-use would add it.
10. **The default values are written twice** (struct initialisers in `config.hpp` and `default_text` strings in
    `cli.cpp`). Hand-synchronised; a test comparing `--help` output to the struct defaults would close this.
11. **POSIX assumption:** the "atomic" rename guarantee, and the README's Linux-only prerequisites, match; on
    Windows `rename` onto an existing file behaves differently.
12. **Coverage is incomplete by design:** 22 of 61 Must requirements have a passing test; the gate
    (`--require-coverage`) is intentionally off until M5.
13. **CI is unproven.** The workflow has never run on GitHub (stated in the README), Clang 18 was not exercised
    here, and the third-party action versions are unverified.

### What is done well
- The estimator's inability to see truth is enforced by **types and a compile-time test**, not by convention.
- The recorder's **RAII + temp-file + rename** design makes partial output structurally impossible, and a failed
  run does not destroy a previous good file.
- Errors are thrown before any state changes, validation happens before any file is created, and exit codes
  distinguish usage from runtime failure.
- The flag table drives both the parser and `--help`.
- Dependencies are pinned by content hash (GoogleTest) and by exact version (Python).
- Tests cite requirement IDs, and a script checks the citations, so the process claims are mechanically checked.
- The code is honest about being a stand-in: comments say "not a filter", and the README says every metric is
  zero for a reason.

---

## 10. ID glossary

Prefixes used throughout the code and comments, from `docs/requirements.csv`:
**SYS** system-level · **SIM** truth/dynamics · **SEN** sensor · **EST** estimator · **CFG** configuration/CLI ·
**RUN** runner · **OUT** output/CSV · **ANA** analysis · **NFR** non-functional · **TST** test/verification ·
**DOC** documentation. **DD-nnn** design decision, **CR-nn** change request, **S-n** scaffolding decision,
**OI-nn** open item, **IF-nn** interface, **M0–M5** milestones. Priorities: **M**ust, **S**hould, **C**ould.
