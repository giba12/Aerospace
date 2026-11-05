# CR-24: The fixed 1e-9 m position tolerance cannot be met for long or large runs

**Status: APPROVED and APPLIED, 2026-10-19.** The edits in section 4 have been made to `docs/requirements.md`
and `docs/systems-engineering-baseline.md` (now v0.2). The record of what changed is in section 9.

| Field | Value |
|---|---|
| Raised | 2026-10-19, during M1 verification and validation |
| Severity · Type | Medium · Gap (G) and Ambiguity (A) |
| Affects | SIM-003, SIM-004; baseline §3.3 (SIM-004 amendment), §6.3 (tolerance policy), §6.5 (RVCM rows), §9.1 (this CR's row), revision history |
| Related, not changed here | §6.3 "C++ vs Python oracle: 1e-9 absolute" has the same weakness and will matter at M3 (see section 7) |
| Option chosen | **B** from the options review: replace the fixed tolerance with a shared, size-scaled one. Option C (a separate numeric-accuracy requirement) is deliberately **not** proposed, to keep the change small |

---

## 1. What it is

SIM-003 and the amended SIM-004 compare the simulated position with the textbook formula to within a **fixed
1e-9 m**. A computer adds up one rounding error per step, and each rounding error is proportional to the size of
the position. So the real error grows with the number of steps *and* with how far the object travels.
A fixed 1e-9 m therefore holds only for short, small runs.

- SIM-003 is already limited to "after 1000 steps", so it is **not violated**. Its tolerance is simply stated for
  one point instead of for the family of runs the program accepts.
- SIM-004 has **no such limit**, and `sim` accepts up to 100,000 steps (`kMaxSteps`), so SIM-004 is **not
  satisfiable as written** across the program's own input range.
- No double-precision implementation can meet 1e-9 m once |position| reaches about 8.4 million metres, because the
  gap between neighbouring doubles there (2⁻²⁹ ≈ 1.9e-9 m) is already larger than the tolerance.

The method error (`½·|a|·t·dt`) in SIM-004 is correct and is not in question. Only the rounding allowance is.

### Evidence

Method: reproduce `propagate` in IEEE doubles; compare against the **exact** Euler value computed in rational
arithmetic (isolating pure rounding error from method error); 120 combinations of
`x0 ∈ {0, 1e6}`, `a ∈ {−9.81, 0, 0.1, 1, 25}`, `dt ∈ {0.001, 0.1, 1}`, `v0 ∈ {10, −300}`, `N ∈ {1000, 100000}`,
about 320 sampled steps per combination including the first 40.

| Candidate tolerance | Cases covered (of 120) | Notes |
|---|---|---|
| Current: fixed `1e-9` m | **68** (52 fail) | e.g. 5e-6 m at a = 1, dt = 0.1, 100,000 steps; 2.7e-3 m at a = −9.81, dt = 1, 100,000 steps |
| `1e-9 + 1e-12·X` | not enough | an earlier interim idea; failed 5 of 60 in the narrower study (small `dt`, many steps) |
| **Proposed `max(1e-9, 2·k·u·X)`** | **120 (0 fail)** | the largest fraction of the allowance used by any case is **21%**, about 4.8× headroom |

The headroom figure was cross-checked independently in the C++ test suite: with the factor 2 replaced by 0.5 the
test still passes and with 0.25 it fails, so the C++ test sees at least 4× headroom at the factor chosen.
The raw ratio `error / (k·u·X)` peaks at 0.725, but only at step 2, where the error is 3e-16 m and the 1e-9 floor
applies; it does not bind.

## 2. Recommendation

Define **one** position tolerance in §6.3, and make SIM-003 and SIM-004 refer to it:

```text
tol_pos(k) = max( 1e-9 m ,  2 · k · u · X )
   k   number of steps taken
   u   2^-53, the unit roundoff of IEEE double precision (about 1.1e-16)
   X   |x0| + |v0|·t + ½·|a|·t²,  with t = k·dt   (an upper bound on |position| up to step k)
```

- **The second term only matters when `k·X` exceeds about 4.5e6** (for example 1000 steps with positions above
  4.5 km). Below that the tolerance is exactly today's 1e-9 m: the SIM-003 reference check (k = 1000, X = 1000,
  second term 2.2e-10 m) is unchanged. The SIM-004 reference case (a = 1, X = 6000) becomes 1.3e-9 m instead of
  1e-9 m, against a measured error of 1.5e-11 m there, so no real margin is lost.
- **The factor 2** comes from a first-order error analysis: about `k·u·X` from adding k position increments, and
  about `k·u·X` more from rounding in the velocity feeding back into position. It is an engineering bound with a
  measured 4.8× margin, not a formal proof.
- It is derived from floating-point theory, not fitted to the test data, so it will not need re-tuning for M2 to M4.

## 3. Why, what it does, likely outcome

- **Why:** a requirement that cannot be met is worse than a looser one that can, because it forces either a silent
  deviation or a test that disagrees with the requirement it cites (which defeats the traceability gate, SYS-005).
- **What it does:** makes SIM-003 and SIM-004 achievable and verifiable for every run the program allows, with the
  tolerance stated once in §6.3 so later requirements can reuse it instead of inventing their own.
- **Likely outcome:** no production code change; the tests use one helper, `position_tol_m(cfg, k)`; milestones
  M2 to M4 reuse it; no change to any result the program produces.

## 4. Exact edits on approval

### 4.1 `docs/systems-engineering-baseline.md` §6.3, replace the first row

| | Text |
|---|---|
| **Before** | `\| Position (analytic comparison) \| 1e-9 m \| SIM-003; accumulated rounding over 1000 steps is about 1e-11 \|` |
| **After** | `\| Position (analytic comparison after k steps) \| max(1e-9 m, 2·k·u·X), u = 2⁻⁵³, X = \|x0\| + \|v0\|·t + ½·\|a\|·t² \| SIM-003, SIM-004 (CR-24). Rounding grows with k and with position size; a fixed 1e-9 m is unachievable beyond about 8.4e6 m. The second term exceeds the 1e-9 m floor only when k·X > about 4.5e6, so the SIM-003 reference check keeps 1e-9 m. \|` |

### 4.2 `docs/requirements.md` and baseline §3.3

| ID | Before | After |
|---|---|---|
| SIM-003 acceptance | `Within 1e-9 m after 1000 steps.` | `Within the §6.3 position tolerance after any k ≤ N_max steps; the reference check (k = 1000) tolerance is 1e-9 m.` |
| SIM-004 amended text (baseline §3.3) | `…shall not exceed ½·abs(a)·t·dt + 1e-9 m.` | `…shall not exceed ½·abs(a)·t·dt + tol_pos(k), where tol_pos is the §6.3 position tolerance.` Keep the measured example (5.000000 m for a = 1 m/s², t = 100 s, dt = 0.1 s). |

(`requirements.md` SIM-004 acceptance, "within a tolerance appropriate to the integrator (documented)", already
allows this and needs no change.)

### 4.3 Baseline §6.5 (RVCM), two rows

| ID | Before | After |
|---|---|---|
| SIM-003 | `Constant velocity vs analytic, ± 1e-9 m after 1000 steps` | `Constant velocity vs analytic, within §6.3 position tolerance` |
| SIM-004 | `Euler error ≤ ½·\|a\|·t·dt + 1e-9 (a = 1 gives 5 m)` | `Euler error ≤ ½·\|a\|·t·dt + §6.3 position tolerance (a = 1 gives 5 m)` |

### 4.4 Housekeeping

- Add a CR-24 row to baseline §9.1 and this entry (shortened) to Part B.
- Revision history: `0.2 · <date of approval> · CR-24 applied: position tolerance now scales with run length and position size (SIM-003, SIM-004, §6.3).`
- Unchanged on purpose: VV-SIM-01 keeps its own stated tolerance of 1e-9 m (measured error 1.5e-11 m at that scale).
- `docs/requirements.csv` is unchanged (it carries IDs and priorities only).

## 5. Verification of the proposal (results already obtained)

| Check | Result |
|---|---|
| Exact-rational study, 120 combinations | Proposal fails 0; current text fails 52 |
| C++ sweep test, every step, same grid plus the 100,000-step cap | Passes on GCC 13, Clang 18, and GCC with ASan + UBSan (fatal on any UB) |
| Mutation: drop velocity update | Test fails |
| Mutation: semi-implicit Euler (position uses new velocity, error has the opposite sign) | Test fails |
| Mutation: acceleration applied twice | Test fails |
| Mutation: time accumulated instead of `k·dt` | Test fails |
| Test run with the old fixed 1e-9 | Fails on the same cases the study predicts, so the test reproduces the problem |
| Tolerance factor lowered to 0.5 / 0.25 | Passes / fails: at least 4× real headroom |
| Full suite | 18 CTest entries, 0 failures, on all three builds |
| SIM-006 gap closed | Tests now also reject non-finite `x0` and `v0` (were previously untested) |

## 6. Risks and limits

- **Not a formal proof.** The factor 2 is a first-order analysis plus a measured 4.8× margin over 120 combinations.
  If a future model adds new rounding sources (for example a second integration stage), re-measure.
- **Larger tolerance for large runs.** At 100,000 steps and 5e7 m the allowance is about 1e-3 m (the measured error
  was 5e-6 m). That is intended: it is a statement about arithmetic, not about the physics model.
- **The test oracle is evaluated in doubles too.** It contributes a one-off error of a few `u·X`, independent of
  `k`. Within the swept range (|x0| ≤ 1e6 m) that is below the 1e-9 floor. Beyond |x0| ≈ 1e7 m a test using a
  double oracle could need an exact reference instead. No test goes there today.
- **Scope of evidence:** x86-64 Linux, GCC 13.3, Clang 18.1.3. Other platforms are not claimed.
- **The study script is not committed** (it lives in a scratch directory) to avoid adding code. The method is
  described in section 1; it is about 30 lines of Python and can be added under `tools/` if you want it archived.

## 7. Follow-up (separate CR if wanted)

Baseline §6.3's row "C++ vs Python oracle: 1e-9 absolute (different operation order gives about 1e-12
differences)" will hit the same limit at M3 for long runs. This CR does not change it. Revisit with the Kalman
filter, where covariance entries and estimates have their own scales.

## 8. Decision

| | |
|---|---|
| ☒ Approve as written | |
| ☐ Approve with changes | |
| ☐ Reject (keep current text, accept that SIM-004 is verified only up to ~1000 steps) | |
| Decided by / date | Project owner (giba12), 2026-10-19, via chat |

## 9. Implementation record (applied 2026-10-19)

### 9.1 What changed

| Area | File | Change |
|---|---|---|
| Tolerance policy | `docs/systems-engineering-baseline.md` §6.3 | First row now defines `tol_pos(k) = max(1e-9 m, 2·k·u·X)` once |
| Requirements | `docs/requirements.md` SIM-003; baseline §3.3 SIM-004 | Both now cite the §6.3 tolerance instead of a fixed 1e-9 m |
| Verification matrix | baseline §6.5, rows SIM-003 and SIM-004 | Method text matches the new wording |
| Change control | baseline §9.1 and Part B, revision history, header | CR-24 listed and described; document is now v0.2 |
| Test support | `tests/support/tolerances.hpp` | `position_tol_m(cfg, k)` implements the §6.3 formula |
| Test support | `tests/support/scenarios.hpp` | Reusable `make_cfg`, `time_s`, `walk_truth`; exact-physics oracle; `euler_error_m` |
| Tests | `tests/gtest/dynamics_tests.cpp` | One sweep test checked at every step across 120 combinations up to the 100,000-step cap; validation tests merged and extended to `x0` and `v0` |
| Reports | `docs/M1_REPORT.md`, `docs/architecture.md` (S-15) | Updated to match |
| Production code | `src/`, `include/` | **None.** The program's output is unchanged |

### 9.2 Why

The written tolerance could not be met by the program it describes. Leaving it would have meant either a test that
quietly disagrees with its requirement or a requirement nobody can check. The new tolerance is the smallest change
that makes the requirement both true and checkable, and it is stated in one place so other requirements reuse it.

### 9.3 How it affects the big picture

- **Nothing the program produces changes.** `sim` writes byte-identical files before and after. This is a change to
  how correctness is judged, not to what is computed.
- **The truth model is now fully trustworthy as the project's answer key.** Every later stage is scored against it:
  the sensor adds noise to it (M2), the Kalman filter estimates it (M3), and the analysis measures the gap (M4).
  M1's exit criteria can now be claimed honestly over the whole input range, not only the 1000-step reference.
- **The tolerance policy becomes shared infrastructure.** `position_tol_m` and the helpers in `scenarios.hpp` are
  what M2 and M3 tests build on, so they do not each invent their own numbers (the rule §6.3 exists to enforce).
- **A known follow-up is queued, not forgotten.** §6.3's "C++ vs Python oracle: 1e-9 absolute" row has the same
  weakness and will bite at M3, when the Python reimplementation (VAL-04) must agree with the C++ filter.
- **The process worked as designed.** A finding from verification became a documented, approved change with
  evidence, exact wording and a decision record, rather than a quiet edit to a test. This is the habit the
  project exists to demonstrate (SYS-005, traceability).
- **Traceability numbers are unchanged:** 23 of 61 Must requirements have a passing test. SIM-003 and SIM-004 are
  now verified over the full range rather than a slice of it.
