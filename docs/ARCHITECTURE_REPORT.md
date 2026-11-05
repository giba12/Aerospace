# Architecture Report: `sensor-sim`

State described: branch `m2-noisy-sensor` (milestones M0, M1 and M2 complete; M3 to M6 not started).
All sizes, timings and counts below were measured on this tree. Where a statement is my reading of the code and
not a measurement, it is marked **(inferred)**.

> This is an educational simulation, not flight software (SYS-006).

**Provenance of the decisions.** The design of record is the *systems engineering baseline* (`docs/systems-engineering-baseline.md`,
decisions DD-001 to DD-012), which was written as a proposal for the owner; the owner accepted decisions D1 to D7 on
2026-10-11. Decisions S-1 to S-21 (`docs/architecture.md`) were made while building M0 to M2. Two were explicit owner
choices: CR-24 (the position tolerance) and CR-25 (the sidecar's `null` estimator keys). Section 11 labels each.

---

## 1. Summary

### What the system is
A single-process, single-threaded C++17 program, `sim`, that simulates an object moving in one dimension, produces
noisy position readings of it, estimates its state from those readings alone, and writes everything to a CSV file
plus a JSON settings file. A small Python script, `analyze.py`, scores the result. A second Python tool,
`req_trace.py`, checks that every requirement has a test.

### The architecture in one paragraph
**A small, dependency-free core library (`simcore`) behind a deliberately tiny `main()`.** The core is a *pure-ish
pipeline*: value types flow through three components (sensor, estimator, recorder) that the *runner* calls in a
fixed order through *interfaces*. The runner and the components never learn which concrete classes they are
talking to; only one file, the command-line layer, chooses them. Truth is owned by the runner and is **structurally
unreachable** from the estimator. Files are written all-or-nothing. Everything is deterministic given a seed.
Correctness is enforced by an unusually heavy test and traceability apparatus around a very small amount of code.

### The shape

```text
                        ┌─────────────────────────────  composition root  ───────────────────────────┐
   argv ──▶ main.cpp ──▶│ cli.cpp: parse flags ▶ validate ▶ pick concrete classes ▶ run ▶ exit code │
                        └───────────────┬────────────────────────────────────────────────────────────┘
                                        │ references to INTERFACES only
                                        ▼
                        ┌──────────────  runner.cpp: owns the time loop and the call order  ─────────┐
   DynamicsConfig ─────▶│ truth (private) ─const&─▶ ISensor ─▶ optional<Measurement> ─▶ IEstimator    │
                        │                                                                  │         │
                        │ IRecorder  ◀── row(step, truth, measurement?, estimate?) ◀───────┘         │
                        └───────────────────────────────────────────────┬─────────────────────────────┘
                                                                        ▼
                         CsvRecorder ──▶ run.csv (atomic)        sidecar ──▶ run.csv.config.json (atomic)
                                                  │
                                       python/analyze.py ──▶ metrics
```

### Scale (measured)

| Measure | Value |
|---|---|
| Production C++ (non-blank lines, headers + sources) | **695** in 20 files |
| Tests (C++ and Python, non-blank) | **910**, i.e. about 1.3 lines of test per line of code |
| Python tools | 170 |
| Third-party libraries linked into the product | **0** (standard library only, NFR-002) |
| Third-party libraries in tests | GoogleTest 1.17.0 (pinned by SHA-256), pytest 8.3.4 (pinned) |
| Interfaces (abstract classes) | 3: `ISensor`, `IEstimator`, `IRecorder` |
| Concrete production implementations | 3: `NoisySensor`, `PassthroughEstimator` (stand-in), `CsvRecorder` |
| Test doubles | 3: `ScriptedSensor`, `RecordingEstimator`, `RecordingRecorder` |
| Include cycles | **0** |
| Binary / library size (RelWithDebInfo) | 1.2 MB / 2.7 MB |

---

## 2. Goals and the quality attributes that drove the design

The project's purpose is **credibility**: a small piece of software whose correctness claims can be checked by a
stranger. That ranks the quality attributes unusually:

| Rank | Attribute | Why it ranks here | Where it is delivered |
|---|---|---|---|
| 1 | **Verifiability** | Every claim must be provable by a test or script | Interfaces + fakes, oracles, tolerance policy, traceability gate (section 9) |
| 2 | **Correctness of numbers** | The whole point is comparing estimates to truth | `t = k·dt`, explicit Euler with a known error bound, 17-digit output, CR-24 tolerance |
| 3 | **Determinism and reproducibility** | A result nobody can repeat is not evidence | Seeded RNG, no clock, settings sidecar, byte-identical reruns |
| 4 | **Explainability** | A learner must be able to defend every line | Hand-written parts, no framework, one idea per file |
| 5 | **Safety of outputs** | A half-written CSV would silently corrupt an analysis | `AtomicFile`, exit codes, validate-before-write |
| 6 | **Evolvability** | Five more milestones must slot in | Interfaces, config structs, flag table, schema versions |
| 7 | **Performance** | Not a goal; the step cap bounds it | Streaming output, O(1) memory (section 5.5) |

Not goals: real-time behaviour, concurrency, numerical generality, operational fidelity, or a graphical interface.

---

## 3. Architectural style and principles

The style is best described as **"ports and adapters, in miniature, around a pure core"**, with three supporting ideas.

1. **Dependency inversion at the three seams that matter.** The runner depends on `ISensor`, `IEstimator` and
   `IRecorder`, never on `NoisySensor` and friends. Why: the runner's *call order* is the most error-prone logic in the
   program (RUN-001, EST-009); making the components swappable lets a test replace them with recording fakes and
   assert the whole call sequence.
2. **A pure, side-effect-free numerical core.** `initial_state` and `propagate` are free functions of their inputs
   (IF-03). They are not behind an interface, because nothing needs to swap them and a pure function is the easiest
   thing in the world to test against a closed-form answer.
3. **A single composition root.** Exactly one file (`cli.cpp`) constructs concrete classes. That keeps "what is
   plugged in" in one visible place; at M3 the Kalman filter replaces one line.
4. **Value types and no global state.** `TrueState`, `Measurement`, `Estimate` and the config structs are plain data.
   The only mutable state lives inside a few objects (RNG, open file, estimator belief) and is never shared.
5. **RAII for everything that must be cleaned up.** `AtomicFile` deletes its temporary file in its destructor unless
   `commit()` was reached, so an exception anywhere unwinds into a clean directory with no explicit cleanup code.
6. **Contracts in the type system first, then tests, then documents.** "The estimator cannot see truth" is not a
   comment: no `IEstimator` method accepts a `TrueState`, and a `static_assert` fails the build if one is added.

What the architecture deliberately **is not**: no inheritance hierarchy beyond three flat interfaces, no templates in
the product (only in test helpers), no plugin loading, no dependency-injection framework, no events or callbacks, no
threads. Each of those would add machinery with no requirement behind it.

---

## 4. Structure

### 4.1 Layers

```text
Layer 3  composition      cli.cpp ── main.cpp                         (knows every concrete class)
Layer 2  orchestration    runner.cpp        sidecar.cpp               (knows interfaces / config only)
Layer 1  components       dynamics.cpp  sensor.cpp  estimator.cpp  recorder.cpp  output_util.cpp
Layer 0  vocabulary       state.hpp  mat2.hpp  config.hpp  cli.hpp (exit codes)     (no logic dependencies)
```

Rule: a file may depend only on its own layer or lower, and **never on a concrete class above the interface line**.
Checked against the include graph: the rule holds, and there are no cycles.

### 4.2 Component catalogue

| Component | Files | Responsibility (one sentence) | Collaborators | Status |
|---|---|---|---|---|
| **Vocabulary** | `state.hpp`, `mat2.hpp` | Name the three kinds of data (truth, measurement, estimate) with units in every field | none | Real |
| **Configuration** | `config.hpp` (+ `validate()` in `dynamics.cpp`, `sensor.cpp`) | Hold every setting with a default; refuse nonsense | none | Real |
| **Dynamics (truth)** | `dynamics.hpp/.cpp` | Advance the true state one step; explicit Euler with constant acceleration | config, state | Real (M1) |
| **Sensor** | `sensor.hpp/.cpp` | Decide *whether* a reading is due and produce it: truth + σ·z | config, state, `<random>` | Real (M2) |
| **Estimator** | `estimator.hpp/.cpp` | Maintain a belief from readings only; explicit Uninitialized→Tracking states | state | **Stand-in** (M3 replaces) |
| **Recorder** | `recorder.hpp/.cpp` | Turn rows into the CSV contract, all-or-nothing | state, output_util | Real |
| **Output utilities** | `output_util.hpp/.cpp` | `AtomicFile` (write-then-rename) and `format_double` (17 digits, finite only) | none | Real (M2) |
| **Sidecar** | `sidecar.hpp/.cpp` | Render the settings JSON (16 keys, schema 1) | config, output_util | Real (M2) |
| **Runner** | `runner.hpp/.cpp` | Own the time loop and the exact call order | all three interfaces, dynamics | Real |
| **CLI** | `cli.hpp/.cpp` | Parse flags, validate, wire concrete classes, run, map failures to exit codes | everything | Real |
| **Entry point** | `main.cpp` | One call into `cli_main` | cli | Real |
| **Analysis** | `python/analyze.py` | Read the CSV, check the header, compute RMSE | the CSV file only | Partial (M4 adds plot, coverage, sidecar) |
| **Traceability** | `tools/req_trace.py` | Map tests to requirement IDs; fail on unknown IDs or orphan tests | JUnit XML, `requirements.csv` | Real; coverage gate off until M5 |

### 4.3 The three interfaces

| Interface | Methods | Notable design point |
|---|---|---|
| `ISensor` | `observe(const TrueState&, int64 step) → optional<Measurement>` | The **sensor owns the sampling schedule** (DD-002): "not due" is an empty optional. Truth arrives `const`, so reading cannot change it (SEN-006) |
| `IEstimator` | `initialized()`, `initialize(first)`, `predict(dt)`, `update(z)` | **No parameter is a `TrueState`** (SYS-002). The lifecycle is explicit rather than hidden in `update`, so the "first reading initializes, no predict" rule (EST-009) is testable |
| `IRecorder` | `write_row(step, truth, optional<meas>, optional<est>)`, `commit()` | `commit()` is the explicit "publish now" signal; the optionals map straight onto "empty CSV field = missing" (OUT-005) |

### 4.4 Dependency analysis (measured from `#include`)

| File | Depends on (project headers) | Fan-out | Included by (headers) | Fan-in |
|---|---|---|---|---|
| `state.hpp` | `mat2.hpp` | 1 | dynamics, estimator, recorder, sensor | 4 |
| `config.hpp` | none | 0 | dynamics, sensor, runner, sidecar | 4 (+ `cli.cpp`) |
| `output_util.hpp` | none | 0 | recorder; `sidecar.cpp`, `cli.cpp` | 1 (+2) |
| `runner.hpp` | config, estimator, recorder, sensor | 4 | none (`runner.cpp`, `cli.cpp`) | 0 |
| `cli.cpp` | 8 headers | **8** (highest) | none | 0 |

Reading: the vocabulary headers are the stable core (high fan-in, no logic); `cli.cpp` is the only file with
high fan-out, which is exactly what a composition root should look like. It is also the largest source file
(182 of 695 lines, 26%); see section 13.

---

## 5. Runtime behaviour

### 5.1 One run, in order

```text
main ─▶ cli_main
  1 parse            flags → RunConfig (syntax errors → UsageError)
  2 validate         DynamicsConfig::validate, SensorConfig::validate (semantic errors → invalid_argument)
  3 construct        NoisySensor (re-validates, seeds RNG)  ·  PassthroughEstimator  ·  CsvRecorder (opens run.csv.tmp, writes header)
  4 stage sidecar    AtomicFile(run.csv.config.json.tmp), JSON written to it
  5 run()            re-validate; initial_state; loop k = 0..N: propagate, observe, estimator call(s), write_row; recorder.commit()
  6 commit sidecar   rename; if it fails, delete the published CSV and exit 1
  7 return           0 on success
```
Failure at any step unwinds through destructors: no temporary files remain, and nothing is published before step 5's
final `commit()`.

### 5.2 Inside one time step

| Situation at step k | Calls, in order |
|---|---|
| k = 0 | observe → (initialize if a reading exists) → write_row |
| not yet initialized, reading arrives | propagate → observe → **initialize** (no predict) → write_row |
| not yet initialized, no reading | propagate → observe → write_row (estimate columns blank) |
| initialized, no reading | propagate → observe → **predict** → write_row |
| initialized, reading | propagate → observe → **predict → update** → write_row |

The order is pinned by one test that compares the *entire* call log against the expected sequence.

### 5.3 Estimator state machine

```text
 [Uninitialized] ──initialize(first reading)──▶ [Tracking] ◀─┐
       │                                            │  predict(dt), update(z)
       └── predict / update ──▶ std::logic_error ───┴────────┘   (a rejected call changes nothing)
```

### 5.4 Error architecture

Exceptions are used for *errors*, never for control flow (DD-007). Each is thrown **before any state changes**, so a
failed call is a no-op. All of them are caught in exactly one place, `cli_main`, and mapped to the exit-code contract.

| Raised as | By | Meaning | Exit code | Files left behind |
|---|---|---|---|---|
| `UsageError` (file-local to `cli.cpp`) | flag parsing | bad syntax: unknown flag, missing value, not a number, `--seed -1` | **2** | none |
| `std::invalid_argument` | `validate()` | bad value: `dt ≤ 0`, `σ < 0`, `steps > 100000`, non-finite | **2** | none |
| `std::runtime_error` | recorder, `AtomicFile`, `format_double` | I/O failure or a non-finite number about to be written | **1** | none (RAII) |
| `std::logic_error` | estimator | `predict`/`update` before `initialize` | **1** | none |

Validation is deliberately **defence in depth**: the same rule can be checked at the CLI, in the sensor constructor
and again at the top of `run()`. A library caller (or a test) that skips the CLI still gets the guarantee.

### 5.5 Resources (measured)

| Run | Wall time | Peak memory | Output |
|---|---|---|---|
| 1,000 steps | 0.02 s | 4.2 MB | small |
| 100,000 steps (the cap), a reading on every row | 2.4 s | **4.3 MB** | 7.5 MB CSV |

- **Memory is O(1):** rows are streamed to disk as they are produced and the trajectory is never held. (The Python
  analysis, by contrast, loads every row, O(N), which is part of why the step cap exists.)
- **Time is dominated by number formatting.** A standalone microbenchmark of `format_double` (an `ostringstream`
  built per number) gives 3.9 µs per call, against 0.18 µs for `std::to_chars`, about 20× faster. A 100,000-row run makes
  roughly 800,000 such calls. **(inferred: the benchmark accounts for the bulk of the 2.4 s; I did not profile the
  binary itself.)** This is irrelevant at the project's scale and is recorded as a known, optional optimization
  (section 13). Note that `to_chars` writes the *shortest* round-trip text, not 17 significant digits, so adopting it
  would change the CSV text and OUT-002 would need amending.

### 5.6 Concurrency

None. One thread, a synchronous loop, no shared state. This is a feature: determinism needs no synchronization story.

---

## 6. Data and interface contracts

| ID | Interface | Contract | Versioning |
|---|---|---|---|
| IF-01 | Command line | 10 flags from one table that also generates `--help`: `--steps --dt --x0 --v0 --accel --meas-every --sigma --seed --sensor-id --out` | Defaults live in `config.hpp` and as text in the table (hand-synchronised, section 13) |
| IF-02 | Exit codes | 0 ok · 1 runtime/I-O · 2 usage/config; messages `sim: error: <parameter>: <reason>` on stderr | Stable |
| IF-03 | `propagate(prev, cfg, k)` | Pure; `t = k·dt`; explicit Euler | Header comment states the error bound `½·a·t·dt` |
| IF-04..06 | C++ interfaces | As in section 4.3 | Source-level |
| IF-07 | `run.csv` | 9 fixed columns, N+1 rows, UTF-8, `\n`, 17 significant digits, empty = missing, never `nan`/`inf`; posterior estimate; variances only (no cross-term) | `schema_version` 1; `analyze.py` checks the exact header |
| IF-08 | `run.csv.config.json` | Flat JSON, 16 keys in fixed order, `schema_version` 1; estimator keys `null` until M3 (CR-25) | Additive keys are minor, renames are major (baseline §8.9) |
| IF-09 | Metrics JSON | Planned for M4 | n/a |

**Where the schema lives.** The CSV header string exists in three places that must agree: `recorder.cpp`
(`kCsvHeader`), `analyze.py` (`EXPECTED_HEADER`) and a test literal. They are cross-checked by tests, so drift fails
the build, but a schema change is a three-file edit.

---

## 7. Cross-cutting concerns

| Concern | Policy | Mechanism | Evidence |
|---|---|---|---|
| **Units** | SI everywhere; the unit is in every identifier (`position_m`, `velocity_mps`, `accel_mps2`, `dt_s`) and flag help | Naming convention (NFR-005) | Inspection; CSV header check. No automated enforcement yet |
| **Time** | `t = k·dt`, computed by multiplication, never accumulated | One place: `propagate` | Test: `t = 100.0` after 1000 steps |
| **Integration** | Explicit Euler; position uses the *old* velocity | `propagate` | VV-SIM-01 (5995.0 m, 110.0 m/s); error = `a·t·dt/2`; mutation test catches the semi-implicit variant |
| **Floating-point tolerance** | `max(1e-9 m, 2·k·u·X)`, defined once (CR-24) | `position_tol_m` in test support; baseline §6.3 | 0 of 120 sweep cases fail |
| **Randomness** | Only `std::mt19937_64` seeded from config; a grep rule forbids `rand`, `srand`, `time(`, `random_device` | `NoisySensor` | `test_repo_rules.py`; byte-identical reruns |
| **Determinism scope** | Same platform and build only; the C++ standard leaves `std::normal_distribution` implementation-defined | Documented limit | GCC 13 and Clang 18 (same libstdc++) give a byte-identical CSV; other libraries untested |
| **Number output** | 17 significant digits round-trips any double; classic locale; non-finite refused | `format_double` | Round-trip test with `0.1 + 0.2` |
| **File safety** | Write to `.tmp`, rename on success, delete on failure; stage the sidecar early | `AtomicFile` | Mutation test: removing the cleanup makes the recorder and system tests fail |
| **Validation** | Syntax at the CLI, semantics in `validate()`, repeated at the library boundary | Config structs | Negative cases in the C++ unit tests (10 for dynamics, 7 for the sensor) plus a parametrised table of bad command lines in the system tests |
| **Logging / observability** | None. One stderr line on failure, nothing on success | n/a | Deliberate: outputs are files, not logs |
| **Configuration** | Command-line flags only; effective settings recorded in the sidecar | Flag table | `--help` is generated from the same table |

---

## 8. Build architecture

```text
CMakeLists.txt ─┬─ simcore (static library, 8 sources; PUBLIC include/)      ← all logic
                ├─ sim (executable, main.cpp only)
                └─ tests/ ─┬─ sim_test_support (INTERFACE: fakes, oracles, tolerances; links simcore)
                           ├─ gtest/ → sim_gtest_tests (+ GoogleTest, fetched, SHA-256 pinned)
                           └─ system.pytest (CTest entry → pytest against ./sim)
```

| Decision | Choice | Why |
|---|---|---|
| Library vs executable split | All logic in `simcore`; `main.cpp` is one call | The library is linkable by tests; `main` is untestable so it holds nothing (checked by a test that greps it) |
| Warning policy | One function `sim_enable_warnings()`; `-Wall -Wextra -Wpedantic -Werror` default ON, applied per target `PRIVATE` | One definition; third-party code is not held to it |
| Language | C++17, extensions OFF | `std::optional`, `std::filesystem`, `std::void_t`; no GNU-only code |
| Build type | `RelWithDebInfo` unless chosen | Optimised yet debuggable |
| Dependencies | GoogleTest by URL **and** SHA-256; Python by exact version | A tag can move, a hash cannot (NFR-009) |
| Test framework | `SIM_TEST_FRAMEWORK` option, adapter directory per framework | Swapping frameworks touches only `tests/` (IF-11, TST-002) |
| Build info | `git describe --always --dirty` captured at configure time into `sidecar.cpp` only | Only one file recompiles; may be stale until re-configure |
| CI | GitHub Actions, Ubuntu 24.04 pinned, GCC 13 and Clang 18 matrix, same commands as the README | If CI and README diverge, SYS-001 fails |

---

## 9. Test and verification architecture

### 9.1 Layers

```text
              ┌────────────────────────────────────────────────────────────────────┐
  SYSTEM      │ pytest drives the real ./sim: flags in, files out, exit codes      │  tests/system
              ├────────────────────────────────────────────────────────────────────┤
  PYTHON UNIT │ analyze.py and req_trace.py against hand-computed values           │  tests/python
              ├────────────────────────────────────────────────────────────────────┤
  C++ UNIT    │ GoogleTest: components in isolation; runner with fakes             │  tests/gtest
              ├────────────────────────────────────────────────────────────────────┤
  STATIC      │ -Werror, static_asserts, source-grep rules, sanitizers (one-off)   │
              └────────────────────────────────────────────────────────────────────┘
```

### 9.2 Techniques and why

| Technique | Used for | Why it is strong |
|---|---|---|
| **Fakes that record calls** (`fakes.hpp`) | The runner's order of calls | The sequence *is* the specification, so the whole log is compared |
| **Independent oracles** (`scenarios.hpp`) | Truth: textbook `x0 + v0t + ½at²` and baseline hand-worked vectors | Never recompute with the code under test |
| **Compile-time tests** (`static_assert`) | "Estimator cannot accept truth"; "measurement has no velocity" | Cannot be skipped, cannot rot |
| **Statistical tests with a fixed seed** | Noise mean and spread within 5 standard errors | Bounds, not exact samples, because the RNG distribution is platform-defined |
| **Sweeps checked at every step** | Euler error across 120 parameter combinations up to the step cap | One failure message per case, not per step |
| **Black-box system tests** | Determinism, exit codes, sidecar contract, no files left behind | Independent of C++ internals and of the C++ test framework |
| **Mutation checking (manual)** | M1: 4 mutants; M2: 10 mutants, all caught | Shows the tests can fail |
| **Source-grep rules** | `main.cpp` makes one call; no hidden randomness; no framework headers in test support | Turns inspection requirements into automatic checks |

### 9.3 Traceability, as an architecture element

Each test names the requirement IDs it verifies: `RecordProperty("requirements", …)` in GoogleTest,
`@pytest.mark.req(…)` in pytest. A hook copies pytest markers into the JUnit XML. `req_trace.py` reads both XML files
and `docs/requirements.csv` and fails on an unknown ID or an orphan test; with `--require-coverage` (switched on at
M5) it also fails on any uncovered Must. Current coverage: **33 of 61 Must requirements** have a passing test.

### 9.4 Current results

29 CTest entries pass (27 C++ cases, 51 Python cases) on GCC 13, on Clang 18, and on GCC with ASan + UBSan.
GitHub CI has passed on every pushed branch.

---

## 10. Process architecture

The project treats **documents as part of the system**:

```text
requirements.md ─▶ baseline (design, interfaces, tolerances, RVCM) ─▶ tests cite IDs ─▶ req_trace.py ─▶ CI gate
        ▲                                                                                   │
        └──────── change request (CR-nn): evidence, exact wording, owner decision ◀─────────┘ (a finding from V&V)
```

Two change requests have been run through this loop so far: **CR-24** (a verification finding showed a fixed
tolerance was unachievable; resolved with a shared formula) and **CR-25** (an owner decision on `null` sidecar keys).
Per-milestone reports (`M1_REPORT.md`, `M2_REPORT.md`) record what was built, why, trade-offs and V&V.

---

## 11. Decision log

"Source": **B** = baseline decision (owner-accepted D1 to D7 or part of the proposal), **S** = scaffolding or milestone
decision made during the build, **O** = explicit owner decision.

| # | Decision | Alternatives considered | Why this one | Cost accepted | Source |
|---|---|---|---|---|---|
| 1 | All logic in a static library; `main` is one call | Logic in `main` | Testability (TST-001, DD-001) | An extra CMake target | B |
| 2 | Three flat interfaces, injected into the runner | Concrete classes; templates; one fat interface | The call order is the riskiest logic and needs fakes | Virtual call per step (negligible) | B |
| 3 | The **sensor** owns the sampling schedule | Runner decides when to sample | Matches SEN-002; fakes can script any cadence, including dropouts | Runner cannot see the schedule | B (DD-002) |
| 4 | Explicit estimator lifecycle (`initialize` / `predict` / `update`) | Auto-initialize inside `update` | Makes "no predict on the first reading" explicit and testable | Slightly more ceremony | B (DD-003) |
| 5 | Truth is never reachable from the estimator, by type | A convention plus review | A compile-time wall (SYS-002) | None; it is the point | B |
| 6 | Hand-written `Mat2`, no Eigen | Eigen | No dependency; fully explainable (NFR-002) | Must write and test the arithmetic (M3) | B (DD-004) |
| 7 | Exceptions for errors, thrown before any state change | Error codes; `std::expected` | Simple; gives "failed call changes nothing" | Exception-safety discipline | B (DD-007) |
| 8 | Config structs with `validate()`, hand-written parser, one flag table | `getopt`; CLI11 | No dependency; help cannot drift from the parser | Parser maintained by hand | B (DD-008), S-4 |
| 9 | `propagate(prev, cfg, k)`; `t = k·dt` | Accumulate `t += dt` | No time drift (R-11) | `prev` and `k` both passed | B (CR-02) |
| 10 | Explicit Euler; position uses the **old** velocity | RK4; closed form; semi-implicit | Baseline names Euler; VV-SIM-01 fixes the numbers; error is a known, testable quantity | Not exact under acceleration (error `½·a·t·dt`) | B (DD-006), S-14 |
| 11 | Position tolerance `max(1e-9, 2·k·u·X)` shared in test support | Fixed 1e-9; per-test tolerances | A fixed value is unachievable beyond about 8.4e6 m | Looser for very long runs | **O** (CR-24), S-15 |
| 12 | Cap on `--steps` (100,000) | No limit | A typo cannot run for hours | Large studies need a source edit | S-12 |
| 13 | Noise = σ × standard draw | Draw from N(0, σ²) | σ = 0 exact with no branch; same seed, different σ gives scaled noise | One more sentence to explain | S-16 |
| 14 | `std::mt19937_64` and `std::normal_distribution` | A hand-written normal generator | No code; baseline choice | Output reproducible per platform only | B (DD-005) |
| 15 | Dedicated unsigned parser rejecting a minus sign | `strtoull` alone | `strtoull("-1")` wraps to 2⁶⁴−1 | Another parser function | S-20 |
| 16 | `AtomicFile` + `format_double` shared by recorder and sidecar | Copy the logic | One tested implementation of safety-critical code | A refactor of working code | S-17 |
| 17 | Stage the sidecar before the run, commit after the CSV | Write it after; write it before the CSV | Bad path fails early; exit 1 still leaves no CSV | Two files are not one atomic unit | S-18 |
| 18 | Sidecar estimator keys `null` at M2 | Omit them; add `--est-*` flags now | One key set for schema 1; no flags a stand-in would ignore | `null` must be explained | **O** (CR-25), S-19 |
| 19 | Hand-written flat-JSON writer | A JSON library | No dependency (DD-009) | Escaping written and tested by hand | B |
| 20 | Source revision read at configure time | At build or run time | Cheap; one file recompiles | Can be stale; shows `-dirty` | S-21 |
| 21 | GoogleTest pinned by URL and SHA-256 | System package; tag | Cannot move; identical on laptop and CI | Needs network on first configure | S-1 |
| 22 | Traceability gate with unknown-ID and orphan checks now, coverage later | Gate on from day one | Most Musts are future work at M0 | Coverage not yet enforced | S-7 |
| 23 | CI matrix GCC 13 + Clang 18, Ubuntu 24.04 pinned | `ubuntu-latest` | A moving image silently changes the toolchain | Manual image bumps | B |

---

## 12. How well does it deliver the quality attributes?

| Attribute | Verdict | Evidence | Where it is weak |
|---|---|---|---|
| Verifiability | **Strong** | 33/61 Musts traced; mutants all caught; independent oracles; compile-time walls | 28 Musts still untested (by schedule); two inspection items (NFR-005 units, parts of TST) have no automated check |
| Numerical correctness | **Strong** | VV-SIM-01; 120-case sweep; exact-arithmetic study behind CR-24 | The estimator is a stand-in, so the headline claim ("the estimator beats the sensor") is not yet demonstrable |
| Determinism | **Good, with a stated limit** | Byte-identical reruns, GCC = Clang = ASan build | Platform-defined `normal_distribution`; untested on libc++ and MSVC |
| Explainability | **Good** | ~700 lines of product code, no framework, one concept per file | `cli.cpp` mixes several concerns (section 13) |
| Output safety | **Good** | RAII file; forced failure leaves nothing; exit-code contract tested | CSV and sidecar are two renames, not one transaction |
| Evolvability | **Good for M3 to M5, strained beyond** | Interfaces and config/flag table are the right extension points | See section 14 |
| Performance | **Adequate, not a goal** | 100k steps in 2.4 s at 4.3 MB | Formatting cost (about 20× avoidable) |

---

## 13. Weaknesses and technical debt (honest list)

Ordered by how much they are likely to matter. None blocks M3.

1. **`cli.cpp` is a "big composition root".** At 182 lines (26% of the product) it parses flags, assembles config,
   wires classes, sequences the sidecar and CSV, and maps exceptions to exit codes. M3 adds about four flags and a
   second set of parameters. **Suggested split when it passes about 250 lines:** `cli_args.cpp` (table, parsing),
   keep `cli_main` for wiring and exit codes.
2. **Config structs declare `validate()` in `config.hpp` but define it in `dynamics.cpp` and `sensor.cpp`.** It keeps
   the rules next to the code that cares, but a reader looking for validation must know to look elsewhere. A
   `config.cpp` would be more conventional.
3. **Defaults are written twice** (struct initialisers and the flag table's text). They are hand-synchronised;
   no test compares them. `--help` therefore *could* drift from reality.
4. **The CSV header lives in three places** (section 6). Cross-tested, but a three-file edit.
5. **`IRecorder::write_row` takes four arguments** (step, truth, optional measurement, optional estimate). Every
   additional column (for example the covariance cross-term, open item OI-03) changes the interface and every fake.
   A small `Row` struct would absorb future columns. Cheap to do before M3.
6. **The truth model is not injectable.** The runner calls free functions directly, so runner tests use the real
   dynamics. Right for a pure function today; if a second dynamics model is ever wanted, an interface is a small step.
7. **Number formatting is slow** (3.9 µs per value vs 0.18 µs for `to_chars`). Harmless at the cap; changing it
   alters the CSV text and needs a requirement change (OUT-002).
8. **The two output files are not one atomic unit.** A crash in the instant between the two renames could leave a
   CSV without its sidecar. The failure path is handled; the crash window is not.
9. **`source_revision` can be stale** until CMake is re-run, and shows `-dirty` during development.
10. **Stand-in names are misleading by design.** `PassthroughEstimator` is honestly labelled in comments, but a casual
    reader could mistake it for the real estimator until M3.
11. **Reproducibility is per platform** (section 7). Accepted and documented, not eliminated.
12. **Documentation lag:** `docs/CODE_REPORT.md` and `docs/FILE_MAP.md` describe the code before M1; this report and
    `architecture.md` are current.

---

## 14. Evolution: where M3 to M6 plug in

| Milestone | Change | Extension point used | Pressure on the architecture |
|---|---|---|---|
| **M3 Estimator** | `KalmanEstimator` behind `IEstimator`; `Vec2` and `Mat2` arithmetic; `EstimatorConfig` (`q`, `R`, `P0`) with `validate()`; four `--est-*` flags; sidecar `est_*` become numbers | `IEstimator`, `RunConfig`, flag table, sidecar fields | `cli.cpp` grows (item 1); `Row` struct decision (item 5); the C++ vs Python tolerance needs its own change request |
| **M4 Analysis** | Plot, ±2σ coverage, metrics JSON, reads the sidecar and rejects unknown `schema_version` | Python only; CSV and sidecar contracts | `analyze.py` loads all rows (O(N)); pin matplotlib |
| **M5 Hardening** | Sanitizer CI job, coverage gate on, coverage report | CI file, `req_trace.py --require-coverage` | None |
| **M6 Release** | README completion, validation record, baseline tagged | Documents | None |

**What would strain the design** (not planned): more than one sensor or estimator (the runner assumes one of each);
more than one dimension (`TrueState` and `Mat2` are 1-D / 2×2 by construction); a changing acceleration; streaming
output to something other than a file (the recorder interface would hold, `AtomicFile` would not).

**Recommended small refactors before M3**, in priority order, all low risk:
1. Introduce a `Row` struct for `write_row` (item 5).
2. Add a test comparing `--help` defaults with the config structs' defaults (item 3).
3. Split flag parsing out of `cli.cpp` once M3's flags land (item 1).

---

## 15. Appendix

### 15.1 File inventory (non-blank lines)

| Group | Files | Lines |
|---|---|---|
| Vocabulary and config | `state.hpp` 25, `mat2.hpp` 10, `config.hpp` 35, `cli.hpp` 14 | 84 |
| Components | `dynamics` 15+36, `sensor` 29+26, `estimator` 27+27, `recorder` 31+30, `output_util` 27+49 | 297 |
| Orchestration | `runner` 11+30, `sidecar` 12+72 | 125 |
| Composition | `cli.cpp` 182, `main.cpp` 7 | 189 |
| **Production total** | 20 files | **695** |

### 15.2 Related documents

`docs/systems-engineering-baseline.md` (design of record, v0.3) · `docs/architecture.md` (decision log S-1 to S-21) ·
`docs/FILE_MAP.md` (call map; predates M1) · `docs/CODE_REPORT.md` (line-by-line review; predates M1) ·
`docs/M1_REPORT.md`, `docs/M2_REPORT.md` · `docs/change-requests/CR-24…`, `CR-25…`.

### 15.3 Glossary

**Truth**: what really happened, known only to the runner. **Measurement**: what the sensor reports.
**Estimate**: what the estimator believes. **RAII**: cleanup tied to an object's lifetime. **Composition root**: the one
place where concrete classes are chosen. **Oracle**: an independent way of computing the right answer. **Mutation
check**: deliberately breaking the code to prove a test can fail. **Schema version**: a number that says which file
layout a reader should expect.
