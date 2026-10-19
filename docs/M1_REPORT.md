# Milestone M1 Report: the Truth Model with Acceleration

Branch `m1-truth-acceleration` · Baseline §6.7 exit criteria for M1: *"SIM-001..006 verified; VV-SIM-01 passes."*

> This is an educational simulation, not flight software (SYS-006).

**Verdict: M1's exit criteria are met.** Every SIM requirement has at least one passing test, VV-SIM-01 passes
in the library and through the real program, and the build is clean on both GCC 13 and Clang 18.
One finding needs your attention (section 6): the requirement's "+1e-9 m" margin is only achievable for
runs up to about 1,000 steps. That is a flaw in the requirement's wording, not a bug in the code.

---

## 1. What M1 does, in plain language

Before M1, the simulated object could only move at a **steady speed**: start at some position, move at 10 m/s
forever. M1 lets it **speed up or slow down at a steady rate**, like a car accelerating or a rock falling.

You choose the rate with a new setting, `--accel`, measured in metres per second per second (m/s²):

```bash
./build/sim --accel 1 --steps 1000      # speeds up by 1 m/s every second
./build/sim --accel -9.81               # slows down (or falls) at 9.81 m/s every second
./build/sim                             # no --accel = 0 = exactly the same behaviour as before
```

With `--accel 1` and the default settings (start at 0 m, 10 m/s, 0.1 s steps, 1000 steps = 100 seconds), the
object ends at **110 m/s** and **5995 m**. This "truth" is what the later sensor and estimator will be judged against.

What changed in the code, in one sentence each:

| File | Change |
|---|---|
| `include/simulator/config.hpp` | Added the `accel_mps2` setting (default 0) |
| `src/dynamics.cpp` | Reject an acceleration that is not a finite number; each step, add `acceleration × step size` to the speed |
| `src/cli.cpp` | Added the `--accel` flag, which also appears automatically in `--help` |
| `tests/support/scenarios.hpp` | Added "exact physics" formulas that the tests compare against |
| `tests/gtest/dynamics_tests.cpp`, `interface_tests.cpp`, `tests/system/test_walking_skeleton.py` | New tests (section 5) |
| `README.md`, `docs/architecture.md` | Updated status, limitations and decision S-14 |

Only **one line of real physics** was added. Most of the work is the checks around it.

---

## 2. Why it was built this way, in plain language

**Step by step, not a formula.** The program moves the object one small time step at a time (0.1 s), updating
position and speed each step. A shortcut formula for the final answer would be exact, but later milestones need
the truth *at every step* (the sensor takes a reading every few steps, and the estimator is scored at each one).
Stepping also matches how real simulators work.

**Position first, then speed.** Each step moves the object using its *old* speed, then updates the speed. This
is called explicit Euler. The order matters: using the new speed gives a slightly different answer (6005 m
instead of 5995 m in the reference case). The baseline names explicit Euler and fixes the expected numbers, so I
followed it exactly (decision S-14).

**Time is multiplied, not added up.** The clock for step *k* is `k × 0.1`, never "previous time + 0.1".
Repeatedly adding 0.1 collects tiny rounding errors. This was already in place (SIM-002) and M1 kept it.

**Zero is the default, and zero changes nothing.** If you do not pass `--accel`, the new line adds
`0 × 0.1 = 0` to the speed, so every old run is bit-for-bit unchanged. I confirmed this by comparing a default
run with `--accel 0`: the files are identical.

**Bad input is refused before anything is written.** `--accel nan` or `--accel inf` stops with
`sim: error: accel_mps2: must be finite` and exit code 2, and no output file is created. This reuses the
existing validation pattern rather than inventing a new one, so the new setting behaves like every other.

**Tests that check a different way of getting the answer.** A test that recomputes the answer with the same
code as the program proves nothing. The tests compare against (a) the textbook formula
`x = x0 + v0·t + ½·a·t²`, and (b) numbers worked out separately by hand in the baseline (VV-SIM-01).

---

## 3. Trade-offs of this approach, in plain language

| Choice | What you gain | What you give up |
|---|---|---|
| **Explicit Euler** (simple stepping) | Easy to explain and to check by hand; matches the baseline and its published numbers; the error has a simple formula | It is **not exact** when accelerating: always short by `½·a·t·dt` (5 m over 100 s in the reference case) |
| **Keeping the error instead of using an exact formula** | The error is a known, testable quantity; it later lets you study what happens when the estimator's model is wrong (acceleration it doesn't know about) | The "truth" is a numerical approximation, not perfect physics. Anyone comparing with the textbook formula must know about the 5 m gap |
| **Smaller steps shrink the error** | Halving `dt` halves the error | More steps per run, bigger files; and, as section 6 shows, more rounding noise on very long runs |
| **Acceleration is constant** | One setting, simple to test | No changing forces (drag, thrust profiles); not realistic flight dynamics |
| **One dimension only** | Keeps every formula and test small | No turning, no 3-D motion |
| **Checks in several places** (CLI, `validate()`, runner) | A bad value is caught wherever it enters, including from tests calling the library directly | A little repeated checking; the cost is negligible |
| **A fixed `--steps` cap of 100,000** (from the earlier fix) | A typo cannot run for hours | Large studies need the constant changed in `config.hpp` |
| **Default 0 for the new setting** | Existing behaviour and expected outputs are untouched | None worth noting |

---

## 4. Which requirements M1 fulfils, in plain language

"Must" = required; "Should" = wanted but not essential.

| ID | Pri | What it means in plain language | How M1 satisfies it | Evidence (test names) |
|---|---|---|---|---|
| **SIM-001** | Must | The program has a "true state" holding time, position and speed, with units in the names | `TrueState` has `t_s`, `position_m`, `velocity_mps`. M1 added a test that checks the field names and that they are numbers | `Interfaces.TrueStateHoldsTimePositionAndVelocity` |
| **SIM-002** | Must | Time moves in equal steps and each step's time is `k × dt`, never added up | Unchanged in M1; re-checked: after 1000 steps the time is 100.0 s, also in the accelerating case | `Dynamics.ConstantVelocityMatchesAnalyticSolution`, `Dynamics.EulerWithAccelerationMatchesVvSim01` |
| **SIM-003** | Must | With no acceleration, the result matches the textbook formula `x0 + v0·t` | Still true; also proved that with zero acceleration the speed stays **exactly** the same, not just close | `Dynamics.ConstantVelocityMatchesAnalyticSolution`, `Dynamics.ZeroAccelerationLeavesVelocityUnchanged` |
| **SIM-004** | Should | You can supply a steady acceleration, and the error versus the textbook formula is stated and checked | `--accel` / `accel_mps2`. The error bound `½·\|a\|·t·dt` is documented in `dynamics.hpp`, the README and `architecture.md`, and tested | 4 dynamics tests, plus 2 through the real program |
| **SIM-005** | Must | N steps produce N+1 rows (step 0 is included) | Unchanged; re-run with acceleration enabled | `Runner.NSTepsProduceNPlusOneRows`, `test_default_run_writes_header_and_n_plus_one_rows` |
| **SIM-006** | Must | Nonsense settings are refused, and the message names the setting | Added: non-finite acceleration is refused (`accel_mps2: must be finite`). Existing checks for `dt`, `steps`, `x0`, `v0` still pass | `Dynamics.RejectsNonFiniteAcceleration` and 3 others; `test_bad_input_exits_2_...[--accel nan]` |
| **CFG-001** | Must | Every setting is a documented flag with a default | `--accel` is in `--help` with its unit (m/s^2) and default (0) | `test_help_lists_every_flag_...`, `test_accel_equals_form_...` |
| **NFR-003** | Must | No hidden randomness or clock readings in the core | M1 adds none; the repo's automatic scan still passes | `test_simcore_uses_no_hidden_randomness_or_clock` |

**Verification vector VV-SIM-01** (the baseline's worked example): start 0 m, 10 m/s, acceleration 1 m/s²,
0.1 s steps, 1000 steps. Expected: **5995.0 m** and **110.0 m/s**; textbook answer 6000.0 m; difference 5.0 m.
Result: **passes** in the library (tolerance 1e-9) and through the real program.

---

## 5. Verification and validation

*Verification* asks "did we build it right?" (against the written requirements). *Validation* asks
"is it the right thing?" (does it behave as the real-world idea says it should).

### 5.1 Verification: results

| Check | Result |
|---|---|
| Build, GCC 13.3, `-Wall -Wextra -Wpedantic -Werror` | Clean, no warnings |
| Build, Clang 18.1.3, same flags | Clean, no warnings |
| All tests (CTest) on GCC | **20 / 20 passed** (1.7 s) |
| All tests (CTest) on Clang | **20 / 20 passed** |
| C++ test cases (GoogleTest) | 18 run, 0 failed |
| Python test cases (pytest) | 37 run, 0 failed |
| GitHub CI on the pushed M1 commit (GCC 13 and Clang 18) | Passed (56 s) |
| Traceability (`req_trace.py`) | 23 of 61 Must requirements have a passing test (up from 22). **All five SIM "Must" requirements are covered**, and SIM-004 (Should) is covered by 6 tests |
| VV-SIM-01 | Passes (library and program) |

**Do the new tests actually catch mistakes?** A passing test only means something if it can fail. I deliberately
broke the code two ways and confirmed the tests failed each time (then restored the code):
1. Removed the line that updates speed: 4 CTest entries failed (2 dynamics tests, the pytest suite, and the JUnit re-run).
2. Switched to "use the new speed for position" (the 6005 m variant): the same 4 entries failed.

(These two checks were run before the envelope test of section 6 was added.)

### 5.2 Verification against each requirement's own acceptance criterion

| Criterion (from the requirements) | Measured | Verdict |
|---|---|---|
| SIM-002: at k = 1000, dt = 0.1, time = 100.0 within 1e-9 s | 100.0 | Pass |
| SIM-003: zero acceleration matches `x0 + v0·t` within 1e-9 m after 1000 steps | Within tolerance | Pass |
| SIM-004 (amended): `\|exact − Euler\| ≤ ½·\|a\|·t·dt + 1e-9` m | Reference case: error = bound within **1.5e-11 m**. Holds at all 400 steps of a negative-speed, negative-acceleration run. Holds across 24 combinations of acceleration (−9.81 to 25), step size (0.01, 0.1) and start speed (10, −300) at 1000 steps | Pass **within the stated envelope**; see section 6 |
| SIM-005: N + 1 rows | 1001 rows for 1000 steps | Pass |
| SIM-006: non-finite acceleration refused, parameter named | `sim: error: accel_mps2: must be finite`, exit 2, no file created | Pass |
| VV-SIM-01: 5995.0 m, 110.0 m/s, gap 5.0 m | Match to within 1e-9 | Pass |

### 5.3 Validation: does it behave like the real idea?

**Independent hand calculation.** For each of the baseline's scenario accelerations I computed the expected
Euler answer from a separate formula (`x = 1000 + a·dt²·N(N−1)/2`) and compared it with the actual program output:

| Acceleration (m/s²) | Program output: final position / speed | Hand calculation | Textbook (exact) position | Gap to textbook |
|---|---|---|---|---|
| 0 | 1000.0 / 10.0 | 1000.0 / 10.0 | 1000.0 | 0 |
| 0.1 (baseline S-ACCEL-SMALL) | 1499.5 / 20.0 | 1499.5 / 20.0 | 1500.0 | 0.5 |
| 0.5 (baseline S-ACCEL-LARGE) | 3497.5 / 60.0 | 3497.5 / 60.0 | 3500.0 | 2.5 |
| 1 (VV-SIM-01) | 5995.0 / 110.0 | 5995.0 / 110.0 | 6000.0 | 5.0 |

The program's outputs agree with the hand calculation to about 1e-11 m. The gap grows in proportion to
acceleration, as the formula predicts.

**Other validation checks:**
- *Repeatable:* two runs with the same settings produce byte-identical files.
- *Backward compatible:* default run and `--accel 0` produce identical files.
- *The downstream tool still works:* `analyze.py` reads an accelerating run without error.
- *Fit for purpose:* the baseline's S-ACCEL-SMALL and S-ACCEL-LARGE scenarios (the filter fails at 0.5 m/s²) need
  exactly this capability. M1 now supplies the truth for them. The scenarios themselves can only be run once the
  sensor (M2) and estimator (M3) exist, so they remain **not yet validated**.

### 5.4 What is NOT verified at M1

Honest limits, so nothing is overclaimed:
- The sensor, noise, Kalman filter, plot and sidecar file do not exist yet (M2 to M4). SEN, EST and most ANA/OUT
  requirements are untested by design.
- 38 of 61 Must requirements still have no passing test; the gate that enforces coverage is switched on in M5.
- Validation scenarios VAL-01 to VAL-08 are not run at M1. Only the truth-side inputs to them were checked.
- No sanitizer run (planned for M5), and no code-coverage figure.
- The result applies to the platform tested (x86-64 Linux, GCC 13.3 and Clang 18.1.3). Identical output on other
  platforms is not claimed.

---

## 6. Finding: the "+1e-9 m" margin in SIM-004 is too tight for long runs

**What I found.** The amended SIM-004 says the error must not exceed `½·|a|·t·dt + 1e-9` metres. The first term is
exactly right. The `+1e-9` is a fixed allowance for computer rounding, and rounding error grows as the numbers get
bigger. I reproduced the program's arithmetic across many settings:

| Case | Rounding error beyond the bound | Within the 1e-9 allowance? |
|---|---|---|
| Reference: a = 1, dt = 0.1, 1000 steps | 1.5e-11 m | Yes |
| Any tested case up to 1000 steps with dt ≤ 0.1 | below 1e-9 | Yes |
| a = −9.81, dt = 1, 1000 steps | 4.3e-9 m | **No** |
| a = 1, dt = 0.1, 100,000 steps (the new cap) | 4.7e-6 m | **No** |
| a = −9.81, dt = 1, 100,000 steps | 2.7e-3 m | **No** |
| Even zero acceleration, dt = 0.001, 100,000 steps, v0 = −300 | 5e-8 m | **No** |

**What it means.** This is not a bug. The error bound itself is correct, and the rounding is only
micro-to-milli-metres on kilometre-scale distances. But the requirement as worded cannot be guaranteed for the
longest runs the program now allows, and SIM-003's identical `1e-9` has the same limitation.

**What I did.** I added a test, `EulerErrorWithinRequirementBoundAcrossReferenceEnvelope`, that proves the
requirement exactly as written over the envelope where it does hold (up to 1000 steps, dt ≤ 0.1), with a comment
saying where it stops being true.

**What I recommend (your decision, I did not edit the controlled baseline).** Replace the fixed allowance with one
that scales with size, for example `1e-9 m + 1e-12 × |position|`, in both SIM-003 and SIM-004, at the next baseline
revision. Alternatively, state in the requirement that it applies to runs of at most 1000 steps.

---

## 7. Other observations

- **Docs lag:** `docs/CODE_REPORT.md` and `docs/FILE_MAP.md` describe the code before M1 (no `--accel`). The
  baseline's §8.3 flag table still says `--steps` is "integer ≥ 0" (the cap was added later).
- **NFR-005** (units in every name) has no automated check yet; it shows as "none" in the traceability matrix.
  M1 follows the rule (`accel_mps2`, `--accel` documented as m/s^2) but nothing enforces it.
- The unit label in `--help` is written `m/s^2` (plain text) rather than `m/s²`, to keep the source file ASCII.
- Residual risk is low: M1 is a one-line physics change surrounded by tests that fail when the line is wrong.

---

## 8. Where M1 leaves the project

M0 (skeleton) and M1 (truth) are complete. **M2 (the sensor)** is next: add measurement noise (`--sigma`) and a
repeatable random seed (`--seed`), plus the sidecar settings file. The truth model from M1 is what that sensor
will observe.
