# Milestone M2 Report: the Noisy Sensor and the Sidecar

Branch `m2-noisy-sensor` (built on `m1-truth-acceleration`) · Baseline §6.7 exit criteria for M2:
*"SEN-001..007 verified; CSV and sidecar contract (§8) verified."*

> This is an educational simulation, not flight software (SYS-006).

**Verdict: M2's exit criteria are met.** All seven sensor requirements and the sidecar requirement have passing
tests, the work is verified on three builds (GCC 13, Clang 18, GCC with address and undefined-behaviour
sanitizers), and the new tests were shown to fail when the code is deliberately broken. The honest limits are in
section 6: noise is reproducible only on the same platform and build, and nothing on the Python side reads the
sidecar yet.

---

## 1. What M2 does, in plain language

Before M2, the "sensor" was a stand-in that reported the object's true position exactly. M2 makes it behave like
a real, imperfect instrument: every few steps it reports where the object is **plus a random error**.

```bash
./build/sim                          # noisy: error of about 5 m, repeatable (seed 42)
./build/sim --sigma 20 --seed 7      # noisier, and a different random pattern
./build/sim --sigma 0                # a perfect sensor: reports the exact truth
```

- `--sigma` is how big the typical error is, in metres (default 5).
- `--seed` picks the random pattern. **The same seed always gives the same pattern**, so a run can be repeated
  exactly, which is what makes experiments trustworthy.

M2 also adds a **settings file** next to every result. Running `sim --out run.csv` now also writes
`run.csv.config.json`, which records every setting used, the seed, the compiler and the source revision. Anyone
holding the CSV can see exactly how it was made and reproduce it.

| File | What changed |
|---|---|
| `include/simulator/sensor.hpp`, `src/sensor.cpp` | `NoisySensor` replaces the exact stand-in; validates its settings |
| `include/simulator/config.hpp` | `SensorConfig` gains `sigma_m` and `seed` |
| `src/cli.cpp` | `--sigma`, `--seed`, a careful unsigned-number parser, writes the sidecar |
| `include/simulator/sidecar.hpp`, `src/sidecar.cpp` | New: builds the settings file |
| `include/simulator/output_util.hpp`, `src/output_util.cpp` | New: shared "write safely" and "format numbers" helpers, moved out of the CSV recorder |
| `src/recorder.cpp`, `include/simulator/recorder.hpp` | Now uses the shared helpers (shorter) |
| `CMakeLists.txt`, `.gitignore` | New sources; records the source revision; ignores sidecar files |
| `tests/…` | 11 new C++ tests and 9 new Python tests (section 5) |
| `README.md`, `docs/architecture.md`, baseline v0.3, `docs/change-requests/CR-25-…` | Updated |

---

## 2. Why it was built this way, in plain language

**Noise is "a standard random draw, multiplied by sigma".** The program draws a random number with typical size 1,
then multiplies by `--sigma`. Two good things follow from that one choice. A sigma of 0 gives an *exact* zero error
with no special case in the code. And using the same seed with a different sigma gives the **same pattern, just
bigger or smaller**, so comparing a 5 m sensor with a 20 m sensor changes only the size of the noise, not which
steps were lucky.

**A seeded generator, never the clock.** Randomness comes from `std::mt19937_64` started from the seed. The
project's own automatic scan (NFR-003) forbids `rand()`, `time()` and `random_device`, so nothing hidden can make
two runs differ.

**The seed is read as an unsigned number with a special guard.** The standard C function that reads big unsigned
numbers quietly turns `-1` into 18,446,744,073,709,551,615. A user typing `--seed -1` would get a valid-looking
run from a seed they never chose. So a leading minus sign is refused outright, and a number too large for 64 bits
is refused too.

**The sidecar is plain JSON with a fixed list of keys.** Python can read it with nothing extra installed (DD-009),
and a fixed list means a reader can rely on every key being there. Strings are escaped so an unusual sensor name
cannot break the file.

**Estimator settings are written as `null` for now** (your decision, recorded as CR-25). The contract requires four
estimator keys, but the stand-in estimator has no settings. `null` keeps the file's shape identical now and after
M3, and avoids adding command-line flags that would silently do nothing.

**The safe-writing code is shared, not copied.** The CSV already wrote to a temporary file and renamed it only on
success. The sidecar needs the same guarantee, so that logic and the 17-digit number formatting moved into one
small tested helper that both use. The CSV recorder got shorter and its tests passed unchanged.

**The sidecar is prepared before the run and finished after it.** If its location is unwritable, the program fails
immediately instead of after a long run. If something fails later, nothing is left behind.

---

## 3. Trade-offs, in plain language

| Choice | What you gain | What you give up |
|---|---|---|
| **Scale a standard draw by sigma** | Exact at sigma 0; comparable runs across sigmas | Not the textbook "draw from N(0, sigma²)" form; one extra sentence to explain |
| **The C++ standard library's normal distribution** | No extra code or dependency; matches the baseline (DD-005) | The C++ standard does not fix its exact numbers, so another library could give different noise for the same seed |
| **Reproducible per platform and build, not everywhere** | Honest, testable promise (SYS-003 says "same platform and build") | A file made on one machine might not be reproducible byte-for-byte on a very different one. Tests therefore check statistics, not exact noise values |
| **`null` estimator keys at M2** | One stable key set; no misleading flags | A reader must treat `null` as "no parameter", and the baseline needed a one-line note (CR-25) |
| **Hand-written JSON** | No library; fully explainable | I wrote and tested the escaping myself, which is a small risk a library would remove |
| **Seed stored as a JSON integer** | Exact, readable | Python reads all 64 bits; some other tools (for example JavaScript) lose digits above 2⁵³ |
| **Revision read when CMake configures** | Cheap and stable per build | Can be stale after a later commit until `cmake` is re-run; shows `-dirty` while editing |
| **Sensor draws only on steps with a reading** | Fewer draws; the pattern depends only on the schedule | Changing `--meas-every` changes which random numbers land on which step |
| **Default sigma is now 5, not 0** | Matches the baseline's reference scenario; a default run is now realistic | A plain `sim` run is no longer exact, so the README's example output changed |
| **Refactoring the recorder to share code** | Less duplication; one tested implementation of the safety logic | Touched working code. The existing recorder tests are the safety net, and they all passed |

---

## 4. Which requirements M2 fulfils, in plain language

| ID | Pri | What it means in plain language | How M2 satisfies it | Evidence |
|---|---|---|---|---|
| **SEN-001** | Must | A reading is a position only, never a velocity | `Measurement` has no velocity field | A compile-time check fails the build if one is added |
| **SEN-002** | Must | One reading every M steps, starting at step 0 | The sensor reports when `step % M == 0` | For 100 steps and M = 5 there are exactly 21 readings at steps 0, 5, …, 100, in the library and through the program |
| **SEN-003** | Must | Random error of a chosen size; sigma 0 means exact | Standard draw × sigma | Exact equality at sigma 0. Sigma 5, 10,000 samples, seed 42: mean +0.084 m (limit ±0.25), spread 4.980 m (limit 4.75 to 5.25) |
| **SEN-004** | Must | Same seed and settings, identical readings | Seeded generator | Byte-identical CSV and sidecar across runs; a different seed gives different readings but the same truth |
| **SEN-005** | Must | Each reading carries the time it observed and a sensor name | Copies the truth's time and the configured ID | Direct field check |
| **SEN-006** | Must | Looking at the truth must not change it | The truth is passed as read-only | A read-only object is passed in and compared afterwards; it would not compile otherwise |
| **SEN-007** | Must | Bad sensor settings are refused, naming the setting | `sigma_m`, `every_n_steps`, `sensor_id` are validated | Negative, `nan` and infinite sigma; M of 0 and −5; empty and comma names; messages checked for the parameter name |
| **OUT-003** | Must (promoted) | The settings used are saved next to the result | `<out>.config.json`, 16 keys, schema version 1 | Key set and order, values, escaping, 64-bit seed, `null` estimator keys, valid JSON |
| **SYS-003, NFR-004** | Must | Same inputs, same outputs; no stored "golden" files | Two runs compared on the same machine | Byte comparison of CSV and sidecar; no golden files committed |
| **OUT-004** | Must | A failed run leaves no partial files | Both files go through the safe-write helper | A forced numeric overflow exits 1 and leaves no CSV, sidecar or temporary file |
| **CFG-001, CFG-002** | Must | Every setting is a documented flag; bad input is refused cleanly | `--sigma` and `--seed` appear in `--help`; five new bad-input cases | System tests |

Not covered at M2 (by design): **CFG-003** (estimator settings independent of sigma) needs the M3 estimator
settings, so it stays untested until then.

---

## 5. Verification and validation

*Verification*: did we build it right (against the written requirements)? *Validation*: is it the right thing (does
it behave like the real idea)?

### 5.1 Verification results

| Check | Result |
|---|---|
| Build, GCC 13.3, `-Wall -Wextra -Wpedantic -Werror` | Clean |
| Build, Clang 18.1.3, same flags | Clean |
| Build, GCC with AddressSanitizer + UndefinedBehaviorSanitizer (fatal on any problem) | Clean, no findings |
| All tests (CTest), all three builds | **29 / 29 passed** on each |
| C++ test cases / Python test cases | 27 / 51, none failed or skipped |
| Traceability | **33 of 61** Must requirements have a passing test (was 23). All SEN requirements and OUT-003 are covered |
| Re-run on the exact tree committed | Rebuilt from scratch and passed |

New tests: 11 C++ cases (7 sensor, 3 sidecar, 1 measurement-has-no-velocity) and 9 Python test functions plus 5
new bad-input cases.

**Do the new tests catch mistakes?** I deliberately broke the code ten ways. Every one made at least one test fail:

| Mistake introduced | Caught |
|---|---|
| Noise not multiplied by sigma | Yes |
| Seed ignored | Yes |
| Reading schedule off by one | Yes |
| Wrong timestamp on readings | Yes |
| Sigma of exactly 0 rejected | Yes |
| Negative sigma accepted | Yes |
| `--seed -1` accepted | Yes |
| Seed missing from the sidecar | Yes |
| Sidecar strings not escaped | Yes |
| Temporary file not deleted after a failure | Yes |

### 5.2 Verification against each requirement's own acceptance criterion

| Criterion (from the requirements) | Measured | Verdict |
|---|---|---|
| SEN-002: N = 100, M = 5 → 21 readings at k = 0, 5, …, 100 | Exactly that | Pass |
| SEN-003: sigma 0 → exact equality | Exactly equal (values including 1e12 and 0.1 + 0.2) | Pass |
| SEN-003: sigma 5, 10,000 samples, fixed seed → mean within ±0.25 m, spread within ±5 % | +0.084 m; 4.980 m (0.4 % off) | Pass |
| SEN-004: two runs → byte-identical CSV | Identical (CSV and sidecar) | Pass |
| OUT-003: file exists and records the seed | Present; a seed of 18446744073709551615 round-trips exactly | Pass |

### 5.3 Validation: does it behave like a real noisy sensor?

- **Noise size is right at scale.** With 100,001 readings the measured error was:

  | Sigma set | Measured RMSE | Expected |
  |---|---|---|
  | 0 | 0.0 (exact) | 0 |
  | 5 | 5.006 m | 5 ± 0.011 |
  | 20 | 20.024 m | 20 ± 0.045 |

  Both non-zero results are within about half a standard error of the target.
- **The fixed-seed test is not a lucky draw.** SEN-003 is checked at one seed. Over 300 *other* seeds, **none**
  violated the same bounds (worst mean error 0.163 m against a limit of 0.25; worst spread error 0.088 m against
  0.25).
- **Reproducible across the toolchains tried.** GCC 13, Clang 18 and the sanitizer build produce a
  **byte-identical CSV** for the same seed. All three use the same C++ standard library (libstdc++), so this shows
  the code is deterministic, not that other libraries agree.
- **The pipeline still works end to end.** `analyze.py` reads a noisy run and reports a non-zero error; the README's
  example numbers now come from a real run (`rmse_meas_pos_m = 5.4598541120696265`).
- **Scenarios needing the filter remain unvalidated.** The baseline's S-REF, S-HIGH-NOISE and S-WRONG-R scenarios
  require the estimator (M3). M2 supplies their sensor side.

### 5.4 What is NOT verified at M2

- Output on a different standard library (for example libc++ or MSVC) or another operating system.
- Anything reading the sidecar in Python beyond the `json` module in tests. `analyze.py` does not use it until M4
  (where it must reject an unknown `schema_version`, ANA-001).
- The Kalman filter, its settings, and CFG-003 (M3). The sidecar's estimator keys are `null`.
- 28 of 61 Must requirements still have no passing test; the enforcing gate switches on at M5.
- No code-coverage figure, and no sanitizer job in CI yet (the one-off run above passed).

---

## 6. Findings and observations

1. **Reproducibility is per platform.** The C++ standard does not define the exact output of its normal
   distribution, so identical noise for the same seed is promised only on the same platform and build. The README
   and requirements already say "same platform and build"; the README now also warns that its example digits come
   from GCC 13.3.
2. **The negative-seed trap was found by design review, not by a failing test.** The unsigned-number parser guard
   exists because of a known quirk of the C library; tests were then written to pin it.
3. **CSV and sidecar are two files, not one atomic unit.** Each is written safely, and if the sidecar cannot be
   finished the already-published CSV is removed, so the stated exit-code promise holds. A crash in the instant
   between the two renames could still leave a CSV without its sidecar. The window is tiny and was left as is.
4. **`source_revision` can be stale** (read at configure time) and shows `-dirty` during development. In a
   release build from a clean tree it is a plain commit hash.
5. **Baseline housekeeping done under CR-25:** the `--steps` row in §8.3 now matches the 100,000 cap that the code
   has enforced since the code review.
6. **Still stale:** `docs/CODE_REPORT.md` and `docs/FILE_MAP.md` describe the code before M1.

---

## 7. How M2 fits the big picture

The pipeline now has a real **answer key** (M1's truth model) and a real **imperfect witness** (M2's noisy
sensor). The only stand-in left is the estimator. That makes the central question of the project finally
meaningful: *does estimating from noisy readings beat trusting them directly?* Today the answer is "no, by
construction", because the stand-in estimator just repeats the reading, so its error equals the sensor's. M3
replaces it with the Kalman filter, and the gap between the two RMSE numbers becomes the result.

M2 also lays the **reproducibility foundation** the later milestones rely on: a seed, a settings file that
records it, and byte-for-byte repeatable runs. VAL-04 (an independent Python re-computation of the filter from the
CSV and sidecar) can only exist because of the sidecar.

## 8. Next: M3 (the estimator)

Add the matrix arithmetic (`Mat2`, `Vec2`), a Kalman filter behind the existing estimator interface, its settings
(`--est-q`, `--est-r`, `--est-p0-pos`, `--est-p0-vel`), the worked test vector VV-EST-01, and the Python
cross-check. The sidecar's four `null` keys become numbers, and CFG-003 (estimator settings independent of sigma)
becomes testable. A related open item is already recorded: baseline §6.3's "C++ vs Python oracle, 1e-9 absolute"
tolerance will need the same kind of review as CR-24.
