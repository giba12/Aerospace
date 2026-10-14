# The Requirements, Explained in Plain Language

A companion to `systems-engineering-baseline.md` (SEB-001). It walks through every requirement (70 of them) and says, for each one:

- **What it is:** the requirement in everyday words.
- **Why it matters:** what goes wrong without it.
- **Where it fits:** how it connects to the rest of the project.

Priority tags: **Must** = the project is not done without it. **Should** = do it if time allows, it clearly helps. **Could** = a bonus.
Items marked *(new)* or *(changed)* are proposals from the baseline document. The rest come from the original `requirements.md`.

Decisions D1–D7 are accepted (2026-10-11). One note on D1: I recorded it as "GoogleTest is the one required C++ test framework; Catch2 is an optional extra" (that is what the baseline proposed). The original `requirements.md` wanted Catch2 as a second framework from the start. If you meant that version, tell me and I'll change TST-010 back to a Should.

---

## 0. The big picture first

Think of the project as a tiny data pipeline:

```text
 "reality"            "a flaky sensor"          "a smart guess"            "a report card"
 SIM  (truth)  ───▶   SEN  (noisy readings) ───▶ EST (Kalman filter) ───▶  ANA (grading)
   └── RUN: the controller that runs these in order, one time-step at a time
   └── OUT: the file that connects the C++ side to the Python side
   └── CFG: the knobs you can turn from the command line
```

The point of the whole project: because we are the ones simulating reality, we **know the right answer**. So we can hide it from the estimator, let the estimator guess from noisy data, and then check how good the guess was. That is a rare luxury, and almost every requirement either protects that setup or makes the check trustworthy.

The groups of requirements, in order:

| Group | Prefix | In one sentence |
|---|---|---|
| System | SYS | What the whole thing must achieve, from a user's point of view |
| Truth | SIM | The simulated reality (the answer key) |
| Sensor | SEN | The noisy, intermittent way we look at reality |
| Estimator | EST | The Kalman filter that guesses reality from the readings |
| Configuration | CFG | The command-line knobs |
| Runner | RUN | The loop that runs everything in the right order |
| Output | OUT | The files the program writes |
| Analysis | ANA | The Python that grades the run |
| Non-functional | NFR | Quality rules: warnings, speed, repeatability |
| Test architecture | TST | How the tests are built and checked |
| Documentation | DOC | What the README must say |

Two ideas come up again and again, so here they are once:

- **Deterministic / reproducible:** run it twice with the same settings and get exactly the same result. Without that, you can never tell a bug from bad luck.
- **Seed:** a number that starts the random-number generator. Same seed, same "random" noise. Think of it like a saved game: random-looking, but replayable.

---

## 1. System-level requirements (SYS): the top of the pyramid

Everything else exists to make these six true. They answer "what is this project *for*?"

### SYS-001: Anyone can build, test, run and analyze it from the README alone *(new, Must)*
- **What it is:** Start from a fresh download, follow only the written instructions, and you get a working build, passing tests, a run of the reference scenario and a plot.
- **Why it matters:** A project nobody else can run is a project nobody can trust. A reviewer will give it about ten minutes. If the README steps don't work, nothing else you did is seen.
- **Where it fits:** This is the "front door" test for the entire project. It is checked by running everything inside a clean container, and CI runs the same commands so the README can't quietly go stale.

### SYS-002: The estimator never sees the truth *(new, Must)*
- **What it is:** The Kalman filter may only use the noisy measurements and its settings. The true answer is used only afterwards, to grade it.
- **Why it matters:** If the filter could peek at the answer, every score would be meaningless, like grading a student who had the answer sheet.
- **Where it fits:** It is the parent of EST-002 (the code-level lock) and SEN-006. It is the single most important rule of the design.

### SYS-003: Same settings give identical results *(new, Must)*
- **What it is:** Same configuration, same seed, same machine and build gives the same output, bit for bit.
- **Why it matters:** Reproducibility lets you debug (replay the failing run), compare changes fairly, and let a reviewer get your exact numbers.
- **Where it fits:** Parent of SEN-004 and NFR-004. It is why randomness is always seeded.

### SYS-004: Measure the estimator against the raw sensor and against its own uncertainty *(new, Must)*
- **What it is:** The system must report two things: "is the estimate closer to the truth than the raw readings?" and "does the estimate's own claimed error bar match its real error?"
- **Why it matters:** The first question shows the filter helps. The second shows it is *honest*, which is the whole reason to use a Kalman filter instead of simple smoothing.
- **Where it fits:** Parent of ANA-002 (the error numbers), EST-008 (the "beats raw" test) and EST-012 (the honesty test).

### SYS-005: Every Must has a test, and a script checks that *(new, Must)*
- **What it is:** Each essential requirement points to at least one test, and a script, not a person, verifies that nothing is left untested.
- **Why it matters:** "I think I tested everything" is how gaps survive. Aerospace reviewers expect two-way traceability (every requirement has a test, every test has a reason).
- **Where it fits:** Parent of TST-005 and TST-011. This is also a strong portfolio talking point.

### SYS-006: Be honest about what this is *(new, Must)*
- **What it is:** All documents say plainly this is an educational simulation, not flight-qualified, not a real sensor-fusion system.
- **Why it matters:** Overclaiming is the fastest way to lose a skeptical reader's trust. Accurate claims are a professional habit.
- **Where it fits:** Parent of DOC-001. It also protects you in interviews, since everything you say is backed by evidence.

---

## 2. Truth / dynamics (SIM): the answer key

This is the simulated "reality": an object moving along a line.

### SIM-001: Represent the true state: position, velocity, time *(Must)*
- **What it is:** A data type holding where the object is (meters), how fast it is moving (meters per second) and the time (seconds).
- **Why it matters:** Everything else refers to this. Putting the unit in the name (`position_m`) makes unit mix-ups visible in code review. A famous example is the Mars Climate Orbiter, lost partly to a pounds-versus-newtons error.
- **Where it fits:** It is the "database value clients never see directly". The sensor reads it and the grader compares against it, but the estimator never touches it.

### SIM-002: Fixed time steps, and time is computed as `k × dt` *(Must)*
- **What it is:** The simulation advances in equal steps of `dt` seconds. The time at step *k* is calculated as `k × dt`, not by repeatedly adding `dt`.
- **Why it matters:** Computers can't store 0.1 exactly. In JavaScript `0.1 + 0.2 !== 0.3`, and C++ behaves the same. Adding 0.1 ten thousand times drifts slightly; multiplying a whole-number counter does not.
- **Where it fits:** Every timestamp in the whole project comes from here, so a drift would quietly spoil sensor timing, estimator timing and plots.

### SIM-003: With no acceleration, the simulation matches the textbook formula *(Must)*
- **What it is:** When nothing speeds the object up, its position must equal `start + speed × time`, to within one-billionth of a meter.
- **Why it matters:** It's a sanity check against a known right answer. If the simulation can't reproduce high-school physics, nothing built on it can be trusted.
- **Where it fits:** It is the first and simplest "oracle" test (an independently known answer). It gives you confidence in the truth before you build anything on it.

### SIM-004: Optionally support a constant acceleration, with a known error bound *(Should, changed)*
- **What it is:** Let the user give a steady acceleration. The simple "Euler" stepping method is slightly off when there is acceleration, and we state exactly how much (`½ × acceleration × time × dt`; for 1 m/s² over 100 s with 0.1 s steps, that is exactly 5 m).
- **Why it matters:** It lets you test what happens when reality doesn't match the filter's assumptions (the filter assumes constant velocity). Stating the error bound turns "roughly right" into a checkable fact.
- **Where it fits:** It powers the "model mismatch" experiment, which shows the filter's limits. That experiment becomes the honest limitations section of the README.

### SIM-005: N steps produce N+1 rows *(Must)*
- **What it is:** If you run 1000 steps, you get 1001 rows of truth, because time 0 is included.
- **Why it matters:** Off-by-one mistakes are the most common bug in loops. Fixing the count removes any doubt.
- **Where it fits:** The output file, the Python reader and the tests all rely on this count.

### SIM-006: Reject nonsense settings *(new, Must)*
- **What it is:** If the step size is zero, negative, infinite or "not a number", or the step count is negative, the program refuses and names the bad setting.
- **Why it matters:** A step size of zero would divide by zero; infinity would poison every number after it. Failing early with a clear message beats a strange result 500 steps later.
- **Where it fits:** It is one of a family (SEN-007, EST-010, EST-013, CFG-002) that guard the edges of the system.

---

## 3. Sensor (SEN): the flaky witness

The sensor looks at the truth but never reports it perfectly, like an unreliable upstream API.

### SEN-001: The sensor measures position only *(Must)*
- **What it is:** Its readings contain position and nothing else. There is no velocity field.
- **Why it matters:** Real sensors often give one kind of reading. It makes the estimator's job interesting: it must work out velocity, which it never directly sees (a "hidden state").
- **Where it fits:** This is exactly why a Kalman filter is needed rather than just reading a number off.

### SEN-002: A reading every M steps, starting at step 0 *(Must)*
- **What it is:** The sensor reports on a schedule. With M = 5, it reports at steps 0, 5, 10 … and for 100 steps that is exactly 21 readings.
- **Why it matters:** Real sensors are slower than the simulation. The steps in between are where the filter must *predict* without new information.
- **Where it fits:** It gives the estimator both of its jobs: predict on every step (EST-003) and correct whenever a reading arrives (EST-004). In the design, the sensor itself owns this schedule, so the runner does not need to know M.

### SEN-003: Random noise with a chosen size; zero noise means exact *(Must)*
- **What it is:** Each reading is the true position plus random error following a bell curve whose width is σ (sigma, in meters). If σ is 0, the reading is exactly the truth.
- **Why it matters:** The bell-curve noise is the standard model for sensor error. The σ = 0 case gives a clean testing path (no noise, so the answer must be exact). The test for σ = 5 uses wide, justified bounds, so it won't fail by bad luck.
- **Where it fits:** The noise is what the filter has to fight. Dialing σ up and down lets you explore how filter performance changes.

### SEN-004: Same seed gives the same readings *(Must)*
- **What it is:** Running twice with the same seed and settings produces byte-identical output.
- **Why it matters:** Replayable randomness is the difference between debugging and guessing.
- **Where it fits:** It underpins SYS-003. Note it holds on the same machine and build only. Different compilers can turn the same raw random numbers into slightly different bell-curve values, which is why tests use statistical bounds instead of exact sample values.

### SEN-005: Each reading carries a timestamp and a sensor ID *(Must)*
- **What it is:** Every reading says when it was taken and by which sensor.
- **Why it matters:** The estimator needs the time to know how far to predict. The ID prepares for a future with several sensors, like a source field in an event log.
- **Where it fits:** It is the "event" record that flows from sensor to estimator.

### SEN-006: Looking at the truth must not change it *(Must)*
- **What it is:** The sensor receives the truth as read-only, and a test confirms the truth is unchanged afterwards.
- **Why it matters:** A sensor that nudges reality would quietly corrupt the answer key.
- **Where it fits:** It's a code-level protection of SYS-002, enforced with C++'s `const` (read-only) references.

### SEN-007: Reject bad sensor settings *(Must)*
- **What it is:** A negative noise size or a schedule of less than one step is refused, with a message naming the problem.
- **Why it matters:** Clear errors save debugging time and stop invalid runs from producing plausible-looking nonsense.
- **Where it fits:** It is the sensor's share of the edge-guarding family (see SIM-006).

---

## 4. Estimator (EST): the smart guess

The Kalman filter keeps a best guess of the position and velocity, plus a measure of how unsure it is. Each step it does two things: **predict** (move the guess forward in time; the doubt grows) and **update** (nudge the guess toward a new reading; the doubt shrinks).

### EST-001: Implement a linear Kalman filter for position and velocity *(Must)*
- **What it is:** The filter itself. It tracks two numbers (position, velocity) and a 2×2 table of uncertainty (called the covariance, `P`).
- **Why it matters:** This is the heart of the project and the main thing you will be asked to explain in interviews.
- **Where it fits:** Everything before it feeds it; everything after it judges it. It is checked against a one-step calculation done by hand (see the verification vector in the baseline).

### EST-002: The estimator's interface has no way to accept the truth *(Must)*
- **What it is:** The code is written so that passing the true state to the estimator won't even compile.
- **Why it matters:** A rule enforced by the compiler can't be broken by accident, tiredness or a hurried edit. It beats "we promise not to".
- **Where it fits:** It is the code-level implementation of SYS-002.

### EST-003: Predict on every step, with or without a reading *(Must)*
- **What it is:** Each time step, the filter moves its guess forward by speed × time, and its uncertainty grows.
- **Why it matters:** Time passing makes you less sure. If predictions only happened on reading steps, the estimate would be stale for four out of five steps.
- **Where it fits:** It works together with SEN-002 and is the "between readings" half of the filter's cycle.

### EST-004: Update when a reading arrives: move toward it and become more certain *(Must)*
- **What it is:** When a measurement comes in, the guess shifts toward it (by an amount weighted by how much the filter trusts it), and the uncertainty shrinks.
- **Why it matters:** This is how new information improves the guess. If it didn't shrink the uncertainty, the filter would never become confident.
- **Where it fits:** It is the "correct" half of the cycle, and where noise gets averaged out.

### EST-005: The filter's settings are adjustable *(Must)*
- **What it is:** You can set the starting guess, the starting uncertainty (`P0`), how much unmodeled jiggle to allow (`q`) and how noisy the filter believes the sensor is (`R`).
- **Why it matters:** These are the filter's tuning knobs. `q` and `R` in particular decide whether it trusts its own prediction or the sensor more.
- **Where it fits:** They arrive via the command line (CFG-001, CFG-003) and are validated by EST-010.

### EST-006: The uncertainty table must stay valid *(Must)*
- **What it is:** After every step the covariance `P` must be symmetric and have no negative numbers on its diagonal (variance can't be negative).
- **Why it matters:** A negative variance is mathematically impossible, so seeing one means a bug or numerical decay.
- **Where it fits:** It is an internal "health check" run over a long simulation. EST-011 helps make it hold.

### EST-007: With no noise, the filter finds the truth exactly *(Must, changed)*
- **What it is:** If the sensor has zero noise and the filter trusts it fully (a tiny `R` of 1e-6), then after 10 readings both position and velocity must be within 0.001 of the truth.
- **Why it matters:** It's the simplest correctness test of all: with perfect data, a correct filter can't be wrong. Checking velocity too is important, since position is easy to match, and velocity is where an error in the filter's logic shows up. In the prototype, velocity was still 5 m/s off after two readings, then correct to under 0.001 m/s after three.
- **Where it fits:** It is the first estimator test to build, before any noise complicates things.

### EST-008: With noise, the estimate beats the raw readings, on data never used for tuning *(Must, changed)*
- **What it is:** On a set of held-out random seeds, the filter's position error must be no more than 0.75 times the raw sensor's error.
- **Why it matters:** This is the headline result: "the filter improves on the sensor". Using held-out seeds prevents fooling yourself by adjusting settings until one test passes. The prototype gave 0.32–0.54, so 0.75 leaves a comfortable margin.
- **Where it fits:** It is the filter's main performance claim, and it only counts because of TST-012 (separate tuning and test seeds).

### EST-009: Start with no guess, then initialize from the first reading, without predicting first *(new, Must)*
- **What it is:** Before any reading arrives the filter has no opinion. On the first reading it starts at `[reading, 0 velocity]` with the starting uncertainty. It must **not** run a predict step first. Calling predict too early is an error.
- **Why it matters:** The original documents were contradictory here. Predicting first would push the guess a step ahead of the reading, a hidden bias that is easy to miss.
- **Where it fits:** It fixes the first step of the runner loop (RUN-001) and gives the filter two clear states: "not started" and "tracking".

### EST-010: Reject bad filter settings *(new, Must)*
- **What it is:** Refuse `R` ≤ 0, negative `q`, an invalid starting uncertainty or a bad `dt`, naming the culprit.
- **Why it matters:** If `R` were zero, the filter could divide by zero. These mistakes are easy to make from the command line.
- **Where it fits:** It's the filter's share of the edge-guarding family.

### EST-011: Use the "Joseph form" for the uncertainty update *(new, Should)*
- **What it is:** A slightly longer but numerically safer formula for updating `P`.
- **Why it matters:** The short formula can, over very long runs, make `P` slightly asymmetric or negative through rounding. The Joseph form keeps it valid. In honesty, my prototype showed no practical difference in this scenario, so it's a Should based on good practice, not an observed problem.
- **Where it fits:** It supports EST-006 and is cheap insurance.

### EST-012: The filter's uncertainty must be believable *(new, Must)*
- **What it is:** The filter reports an error bar (±2σ). Across many held-out seeds, the true position should fall inside those bars at least 90% of the time (a perfect filter would be about 95%).
- **Why it matters:** A good estimate with a false error bar is dangerous in real systems, because other parts trust the stated uncertainty. In the prototype, when reality accelerated and the filter assumed constant speed, the RMSE looked almost normal, but the true value was inside the bars only 45% of the time. This test catches that.
- **Where it fits:** It's the second half of SYS-004 and the strongest evidence of correctness in the project.

### EST-013: Reject garbage readings and leave the filter untouched *(new, Must)*
- **What it is:** A reading with an invalid number ("not a number", infinity) or a timestamp older than one already processed is refused, and the filter's state doesn't change.
- **Why it matters:** One bad number would corrupt the filter permanently (every later number would also become invalid).
- **Where it fits:** It keeps errors local. The input is rejected, the run continues or stops cleanly, and state stays sane.

---

## 5. Configuration (CFG): the knobs

### CFG-001: Every setting is a documented command-line flag with a default *(Must)*
- **What it is:** All parameters are given as flags like `--seed 42`. `--help` lists each one with its unit and default.
- **Why it matters:** A program you can't configure can't be explored. Printing units in `--help` stops mistakes such as entering feet where meters are expected. It also lets the tests drive the program like a user would. (Decision D3: flags, not config files, for version 1.)
- **Where it fits:** It's the front door of the program and the contract that the system tests are written against.

### CFG-002: Bad input gives a clear error, a non-zero exit code and no half-written file *(Must, changed)*
- **What it is:** If the settings are invalid the program prints `sim: error: <setting>: <reason>`, exits with code 2 (or 1 for a run-time/file problem), and leaves no output behind.
- **Why it matters:** Scripts and CI decide pass/fail from the exit code. A half-written file looks valid but is not, which is worse than no file.
- **Where it fits:** It is how every earlier "reject bad settings" requirement finally reaches the user.

### CFG-003: The filter's assumed noise is set separately from the sensor's real noise *(new, Must)*
- **What it is:** There are two flags: `--sigma` (how noisy the sensor really is) and `--est-r` (how noisy the filter *believes* it is). They aren't linked.
- **Why it matters:** In real life you never know the sensor's true noise exactly. Keeping them separate lets you test what happens when the filter is wrong about it, an important real-world failure.
- **Where it fits:** It enables the "wrong R" scenario in the validation plan.

---

## 6. Runner (RUN): the conductor

### RUN-001: Do things in this exact order every step *(Must, changed)*
- **What it is:** Each step: advance the truth, ask the sensor for a reading, then either initialize the filter (first reading only) or predict-then-update, and finally record a row.
- **Why it matters:** Order matters. If the filter updated before predicting, or the sensor looked at an old truth, results would be subtly wrong while still looking plausible. It was also where the step-0 contradiction was hiding.
- **Where it fits:** It's the only place where all the components meet. A test using fake components records the order of calls and checks it.

---

## 7. Output (OUT): the handoff between C++ and Python

### OUT-001: One CSV with an exact header and columns *(Must)*
- **What it is:** A single spreadsheet-style file with columns for the step, time, truth, the reading (blank if none), the estimate and its variances.
- **Why it matters:** The CSV is the contract between the C++ program and the Python analysis. Exact column names mean neither side can drift unnoticed. (Decision D4: one wide CSV.)
- **Where it fits:** Everything downstream (metrics, plots, the cross-check) reads this file.

### OUT-002: Numbers are written with full precision *(Must)*
- **What it is:** Decimal numbers are written with 17 significant digits.
- **Why it matters:** Fewer digits would round the numbers slightly, so the file couldn't reproduce the run exactly. 17 digits is enough to round-trip a double precisely.
- **Where it fits:** It makes "the file equals the run" true, which in turn makes exact comparisons and the independent Python re-check possible.

### OUT-003: Save the exact settings next to the CSV *(Must, was Should)*
- **What it is:** A small `.config.json` file records every setting, the seed, the format version and which compiler built the program.
- **Why it matters:** With it, any CSV can be recreated and explained months later. I promoted it because reproducibility is a Must (SYS-003).
- **Where it fits:** It's the "label on the sample". The Python analysis also uses it to check it's reading a compatible version.

### OUT-004: Write the file safely, all or nothing *(new, Must)*
- **What it is:** The program writes to a temporary file and renames it only when finished.
- **Why it matters:** If the program crashes midway, you'd otherwise be left with a truncated CSV that looks real. The rename trick is the standard fix.
- **Where it fits:** It's how CFG-002's "no partial file" promise is actually kept.

### OUT-005: Missing means empty, never "nan" *(new, Must)*
- **What it is:** When a value doesn't exist (for example, no reading on this step), the field is empty. The text `nan` or `inf` never appears.
- **Why it matters:** Different programs read "nan" differently, and a stray one hides bugs. Empty is unambiguous.
- **Where it fits:** The Python reader treats empty as "missing", which is also how it knows which steps had a reading.

---

## 8. Analysis (ANA): the report card (Python)

### ANA-001: Check the CSV before using it *(Must)*
- **What it is:** The analysis refuses files with missing columns (or an unknown format version) and says what's wrong.
- **Why it matters:** Better a clear message than a confusing crash or, worse, wrong numbers.
- **Where it fits:** It's the receiving end of the C++/Python contract and catches any drift between the two sides.

### ANA-002: Compute the error numbers (RMSE) *(Must, changed)*
- **What it is:** RMSE ("root mean squared error") is the typical size of the error: square the errors, average them, take the square root. We compute it for the estimated position, the estimated velocity and the raw readings, **only on steps that had a reading**.
- **Why it matters:** It turns "looks good" into a number. Using the same steps for both comparisons keeps it fair, and the original documents didn't say which steps to use.
- **Where it fits:** These numbers feed EST-008 and the README's headline result.

### ANA-003: Make a labeled plot *(Must)*
- **What it is:** A PNG chart of truth, readings and estimate against time, with axis labels, units and a legend.
- **Why it matters:** A picture is how a reviewer grasps in five seconds what the project does. Unlabeled charts look careless.
- **Where it fits:** It goes in the README as the sample output.

### ANA-004: Report how often the truth falls inside the filter's error bars *(Must, was Should)*
- **What it is:** Compute the fraction of positions within ±2σ of the estimate. Plotting that error band remains optional.
- **Why it matters:** It's the measurement behind EST-012. I promoted it because RMSE alone can hide an overconfident filter.
- **Where it fits:** It's the number that links the analysis to the "honesty" requirement.

### ANA-005: Print metrics, and optionally save them as JSON *(Should)*
- **What it is:** The numbers appear on screen, and can also be written to a `metrics.json`.
- **Why it matters:** Machine-readable output lets tests and CI check results automatically, and lets later experiments be compared easily.
- **Where it fits:** It's the output side of the analysis, used by the system tests.

---

## 9. Non-functional requirements (NFR): quality rules

These don't say what the program does; they say how well-made it must be.

### NFR-001: Modern C++, builds without warnings on two compilers *(Must, changed)*
- **What it is:** C++17, compiled cleanly by GCC 13 and Clang 18 (the versions on your machine), with the strict warning flags on and warnings treated as errors in CI.
- **Why it matters:** Compiler warnings catch real bugs (unused variables, unsafe conversions). Using two compilers catches things one misses. (Decision D7: C++17.)
- **Where it fits:** It's the first quality gate in the CI pipeline.

### NFR-002: The core uses only the standard library, with hand-written 2×2 matrices *(Must)*
- **What it is:** No outside math libraries. The 2×2 matrix operations are short and written by you.
- **Why it matters:** No dependencies means nothing to install or break, and you can explain every line. (Decision D6.)
- **Where it fits:** It supports the comprehension goal (you must be able to explain it) and keeps the build simple.

### NFR-003: No hidden global state; randomness is passed in with a seed *(Must)*
- **What it is:** Components don't share secret global variables, and nothing uses `rand()` or the clock for randomness.
- **Why it matters:** Hidden state is what makes programs unpredictable and hard to test. Passing the random generator in is what makes the seed work.
- **Where it fits:** It makes SEN-004 and SYS-003 possible and lets tests swap in fakes.

### NFR-004: Identical inputs give identical outputs; no stored "golden" files *(Must, changed)*
- **What it is:** Reproducibility is verified by running twice and comparing, not by comparing against a saved reference file.
- **Why it matters:** A saved expected-output file would pass on your laptop and fail on a CI machine, because different compilers generate slightly different bell-curve numbers. That's a test that breaks for the wrong reason. (Decision D5.)
- **Where it fits:** It sets the philosophy for all randomized tests: fix the seed, use sensible bounds.

### NFR-005: SI units everywhere, with unit suffixes in names *(Must)*
- **What it is:** Meters, seconds and m/s throughout, and each name says so (`position_m`).
- **Why it matters:** It prevents unit mix-ups, the classic aerospace failure.
- **Where it fits:** Applies to the code, the CSV header, the flags and the documentation.

### NFR-006: The whole test suite runs in under 30 seconds *(Must, changed)*
- **What it is:** All tests, including the many-seed ones, finish in 30 seconds on a laptop.
- **Why it matters:** Tests that take minutes don't get run. Fast tests become a habit.
- **Where it fits:** It forces tests to stay small and keeps the edit-build-test loop quick.

### NFR-007: The tests also pass under the sanitizers *(Should)*
- **What it is:** Run the tests with AddressSanitizer and UndefinedBehaviorSanitizer, tools that catch memory mistakes and undefined behavior.
- **Why it matters:** C++ lets you make memory mistakes that don't crash immediately. Sanitizers find them.
- **Where it fits:** A separate CI job. It's what makes the C++ trustworthy, and it is a skill employers value.

### NFR-008: Produce a coverage report *(Could, changed)*
- **What it is:** A report showing which lines of code the tests ran, with a goal of 90% on the core library (reported, not enforced).
- **Why it matters:** It shows what the tests *don't* check. It's a guide, not a score to chase.
- **Where it fits:** An optional CI artifact. gcovr isn't installed yet, so it would go in the Python environment.

### NFR-009: Pin every dependency to an exact version *(new, Should)*
- **What it is:** The test framework and Python packages are locked to specific versions, and Python runs in a virtual environment.
- **Why it matters:** "Works on my machine" usually means "on my versions". Your machine currently lacks pytest, pandas and matplotlib, so this is needed in practice.
- **Where it fits:** It makes SYS-001 (anyone can build it) real.

### NFR-010: Tag each agreed baseline in version control *(new, Should)*
- **What it is:** When the requirements are accepted, mark that moment with a Git tag. Do the same for the release.
- **Why it matters:** It lets you say precisely what was agreed when, and return to it.
- **Where it fits:** Basic configuration management, which is standard practice on real programs.

---

## 10. Test architecture (TST): how the tests are built

### TST-001: All logic lives in a library; `main` just parses flags and calls it *(Must)*
- **What it is:** The real work is in `simcore`, a library. The executable `main.cpp` is a thin shell. The web analogy: keep business logic out of the route handler.
- **Why it matters:** Tests can call the library directly, and only a thin layer is untested.
- **Where it fits:** It's the foundation of the whole test design.

### TST-002: Pick the test framework with one build option *(Must)*
- **What it is:** A CMake setting such as `-DSIM_TEST_FRAMEWORK=gtest` chooses the framework, and nothing outside the `tests/` folder changes when you switch.
- **Why it matters:** It keeps the production code independent of the test tool. With D1 accepted, GoogleTest is the default.
- **Where it fits:** It's the "seam" in the test design. It's good architecture to explain, even if only one framework is built.

### TST-003: Every C++ test is run through CTest *(Must)*
- **What it is:** One command, `ctest`, runs every test, whichever framework wrote it.
- **Why it matters:** A single standard command is easy to document and works the same locally and in CI.
- **Where it fits:** CTest is the common layer that makes frameworks interchangeable.

### TST-004: Each test run produces a JUnit XML report *(Must)*
- **What it is:** A standard machine-readable results file.
- **Why it matters:** CI systems display and track these automatically.
- **Where it fits:** It's the input to the traceability script (TST-011) and to the CI test report.

### TST-005: Every test names the requirement it checks *(Must)*
- **What it is:** Each test is labeled with one or more requirement IDs (SIM-003, EST-007 …).
- **Why it matters:** It's the link that proves a requirement is verified, and tells you why a test exists.
- **Where it fits:** It's the raw material for the traceability matrix (TST-011).

### TST-006: Shared test helpers contain no framework code *(Must)*
- **What it is:** Reusable pieces (scenario builders, known-answer calculations, fake sensors, tolerance constants) are plain C++ with no test-framework includes.
- **Why it matters:** It means test logic is written once and the framework-specific part is a few lines. (Decision D2.)
- **Where it fits:** It's what makes switching or adding frameworks cheap.

### TST-007: Components talk through small interfaces so tests can use fakes *(Must)*
- **What it is:** The runner works with abstract "a sensor" and "an estimator", so a test can supply a scripted fake instead of the real one.
- **Why it matters:** To test the runner's order of operations you need to see what it calls. Fakes let you do that without any randomness.
- **Where it fits:** It's the web idea of dependency injection, and it supports RUN-001 and TST-001.

### TST-008: System tests in Python drive the real program *(Must)*
- **What it is:** pytest launches the built `sim` program, like a user would, and checks the files it writes.
- **Why it matters:** These tests never depend on internal code, so they're a stable safety net while the C++ is changed.
- **Where it fits:** Where the end-to-end results (the EST-008 and EST-012 checks across many seeds) are verified.

### TST-009: CI builds and tests on every push and pull request *(Must)*
- **What it is:** An automatic pipeline that configures, builds and runs all tests on a clean Linux machine.
- **Why it matters:** It catches "works on my machine" problems and keeps the main branch always working. In this plan CI starts in week one, not the last week.
- **Where it fits:** It's the project's heartbeat and what the green badge on the README shows.

### TST-010: Optionally run a second C++ framework in a CI matrix *(Could, was Should)*
- **What it is:** Build and run the same tests with Catch2 as well as GoogleTest to show the swap works.
- **Why it matters:** It's a nice demonstration of the architecture, but not needed to meet any user need, and costs real time.
- **Where it fits:** A bonus once everything else is done. See the D1 note at the top.

### TST-011: A script builds the requirement-to-test matrix and fails CI on gaps *(new, Must)*
- **What it is:** It reads the requirement IDs and the test labels. CI fails if a Must requirement has no test, or a test cites an ID that doesn't exist.
- **Why it matters:** It turns traceability from a hope into a rule that is enforced automatically.
- **Where it fits:** It implements SYS-005 and produces a portfolio-worthy artifact.

### TST-012: Tune on some random seeds, grade on different ones *(new, Must)*
- **What it is:** Two separate lists of seeds: one for adjusting the filter, one for the acceptance tests. A script verifies they don't overlap.
- **Why it matters:** If you tune and test on the same data, you can't tell "works" from "memorized". It's the same reason machine learning has train and test sets.
- **Where it fits:** It's what gives EST-008 and EST-012 real meaning.

---

## 11. Documentation (DOC)

### DOC-001: The README answers the standard questions and states the limits *(new, Must)*
- **What it is:** The README covers what the project demonstrates, data flow, assumptions and units, how to build/test/run/analyze, sample output, limitations, next steps and the "educational simulation" statement.
- **Why it matters:** The README is what a reviewer reads first, and often the only thing. It's where honesty (SYS-006) becomes visible.
- **Where it fits:** It's the last step in the sprint and draws on results from every other group, including the limitations found by the mismatch experiment.

### DOC-002: Keep the architecture document current *(new, Should)*
- **What it is:** `docs/architecture.md` reflects the design and interfaces in the baseline, and changes when they do.
- **Why it matters:** A design document that no longer matches the code is worse than none.
- **Where it fits:** It's the explanation a new reader uses to understand how the pieces connect before reading code.

---

## 12. How the requirements chain together (a few worked examples)

**"The filter beats the sensor" claim:** SYS-004 → EST-008 and ANA-002 (what is measured) → TST-012 (on seeds you didn't tune with) → TST-008 (system test drives the program) → SEN-004 and NFR-004 (so the result is repeatable) → DOC-001 (reported honestly, with limits).

**"The estimator can't cheat":** SYS-002 → EST-002 (compiler-enforced) and SEN-006 (truth is read-only) → TST-007 (fakes show what each component receives).

**"Anyone can reproduce it":** SYS-001 and SYS-003 → OUT-003 (settings saved with output) → NFR-009 (pinned versions) → TST-009 (CI runs the README's commands) → SEN-004 (seeded randomness).

**"Bad inputs fail safely":** SIM-006, SEN-007, EST-010, EST-013 (each component checks its own inputs) → CFG-002 (the user sees a clear error and exit code) → OUT-004 (nothing half-written is left behind).

## 13. If you only have time to understand five things first

1. **SYS-002 / EST-002:** truth is hidden from the estimator. The rest of the project is built around this rule.
2. **EST-003 and EST-004:** predict every step, update when a reading arrives. That is a Kalman filter in two sentences.
3. **SEN-004 and NFR-003:** seeded randomness is what makes everything testable.
4. **EST-008 and EST-012 with TST-012:** "better than raw", "honest about uncertainty", and "measured on data you didn't tune with". This is the evidence a reviewer will care about.
5. **TST-011:** every Must requirement has a test, enforced by a script.
