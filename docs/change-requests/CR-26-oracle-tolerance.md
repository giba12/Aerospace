# CR-26: The C++-versus-Python oracle needs an exact oracle and a size-scaled tolerance

**Status: PROPOSED, not yet approved.** The code already follows this proposal (`python/kalman_oracle.py` and
`tests/system/test_oracle_crosscheck.py`), because the cross-check cannot be written correctly otherwise. The
baseline (`docs/systems-engineering-baseline.md`, v0.3) has **not** been edited. If the owner declines, the
fallback in section 5 applies.

| Field | Value |
|---|---|
| Raised | 2026-11-05, while building the independent cross-check at the end of M3 |
| Severity · Type | Medium · Gap (G) |
| Affects | Baseline §6.3 (tolerance table, row "C++ vs Python oracle"), §6.5 (RVCM rows EST-001, EST-011), §7.6 DD-012, §11.1 (the caveat on the Joseph form), VAL-04 |
| Follows | CR-24, which flagged this row as having the same weakness ("will matter at M3") |
| Option chosen | **B** below: an exact oracle and the CR-24 tolerance form |

---

## 1. What it is

Baseline §6.3 says the C++ output and the Python oracle must agree to **1e-9 absolute**, "different operation
order gives about 1e-12 differences". Building the oracle showed two problems with that sentence.

**1. A fixed 1e-9 cannot hold for long runs.** The same reason as CR-24: rounding error grows with the number
of steps k and with the size of the value. After 20,000 steps with no reading the position variance is about
7×10⁸ m²; after 100,000 it is 4×10¹⁰ m², where neighbouring doubles are about 7.6×10⁻⁶ apart.

**2. An oracle written in doubles is not trustworthy in the regime where it matters.** The first oracle used
plain doubles and the short covariance update `P = (I−KH)P⁻`. In the 100,000-step case it disagreed with the C++
by 4.9×10⁻⁷ at the final update. Checking against 60-digit decimal arithmetic showed which side was wrong:

| Implementation (p00 after the update that follows 100,000 steps without a reading, exact value 24.99999998557692…) | Error vs exact |
|---|---|
| C++, Joseph form, doubles | **9.1×10⁻¹⁶** |
| Python oracle, short form, doubles | 4.9×10⁻⁷ |

The update subtracts two nearly equal huge numbers (catastrophic cancellation): its accuracy is set by the size of
the **inputs**, 4.3×10¹⁰, not the output, 25. The short form loses about 7 digits there and the Joseph form does
not. An oracle must be more accurate than what it checks, otherwise a disagreement cannot be assigned to either.

## 2. Recommendation

1. **The oracle computes in exact decimal arithmetic** (60 digits) on the exact values of the doubles the C++ was
   given, keeping its different formulation (scalar arithmetic, expanded predict, short update). Any difference
   from the C++ is then the C++'s own rounding.
2. **Tolerance:** the CR-24 form,

```text
allowed(k, value) = max( 1e-9 ,  2 · k · u · |value| ),     u = 2^-53
   k       the row (step) index
   value   the oracle's value for that column at that row
```

## 3. Evidence

C++ versus the exact oracle, largest difference per column, and the largest fraction of the allowance used by any
row (1.0 would be a failure).

| Scenario (flags) | est_pos | est_vel | pos variance | vel variance | Largest fraction used |
|---|---|---|---|---|---|
| reference (defaults) | 5.7e-13 | 1.4e-13 | 1.4e-14 | 4.3e-14 | 0.0006 |
| `--seed 7 --sigma 20` | 6.8e-13 | 1.5e-13 | 1.4e-14 | 4.3e-14 | 0.0007 |
| `--accel 0.5` | 1.8e-12 | 3.2e-13 | 1.4e-14 | 4.3e-14 | 0.0018 |
| `--meas-every 1` | 3.4e-13 | 1.3e-13 | 3.3e-15 | 2.8e-14 | 0.0003 |
| `--meas-every 50` | 2.5e-12 | 4.1e-13 | 3.3e-12 | 2.6e-13 | 0.0033 |
| `--est-r 1e-6 --sigma 0` | 7.1e-14 | 1.3e-13 | 1.4e-14 | 2.1e-14 | 0.0001 |
| `--est-q 0 --est-p0-pos 0 --est-p0-vel 0` | 0 | 0 | 0 | 0 | 0 |
| `--steps 20000 --meas-every 20000` | 0 | 1.9e-12 | 2.4e-4 | 1.6e-10 | **0.16** |
| `--steps 100000 --meas-every 100000` | 0 | 6.3e-12 | 1.5e-2 | 1.4e-9 | **0.23** |

The worst case uses 23 % of the allowance, so about 4.3× headroom, the same order as CR-24's 4.8×. The
absolute differences at the extremes (1.5e-2 on a value of 4.3e10) are a relative 3×10⁻¹³. A real bug in the filter
produces relative errors around 10⁻³ or larger (the planted bugs in the M3 mutation checks failed the hand-vector
tests by orders of magnitude), so the allowance leaves a huge gap in the right direction.

## 4. Edits proposed to the baseline

- **§6.3 row**, replace "C++ vs Python oracle | 1e-9 absolute | Different operation order gives about 1e-12
  differences" with "C++ vs exact Python oracle | max(1e-9, 2·k·u·|value|) | The oracle uses 60-digit
  decimal arithmetic; the allowance covers accumulated double-precision rounding (CR-26)".
- **DD-012**, append "The oracle computes in exact arithmetic (CR-26)".
- **§11.1 caveat** ("the Joseph form showed no measurable benefit"), append: "A regime where it matters exists:
  after about 20,000 steps without a reading the short form in doubles is off by 2×10⁻⁸ and by 5×10⁻⁷ after
  100,000, while the Joseph form stays within 1e-15 (CR-26). EST-011 stays Should."
- **Revision history:** a row for v0.4.

## 5. If this is declined

Keep the 1e-9 absolute tolerance and restrict the cross-check scenarios to runs of at most about 5,000 steps with a
reading at least every 50 steps, where the differences are below 1e-11. The exact oracle should stay either way;
it is the part that prevents a false alarm like the one in section 1.

## 6. What the tests now check

- `tests/python/test_kalman_oracle.py`: the oracle reproduces the hand vector VV-EST-01 on its own (a second
  independent implementation hitting the same numbers); starts at the first reading with no predict; the
  allowance formula; and a regression that the short form in doubles loses digits at 20,000 steps (EST-011).
- `tests/system/test_oracle_crosscheck.py`: nine scenarios from the table above against the real `sim`, a
  corrupted estimate that must be noticed, a disagreement about when the filter starts that must be noticed, and the
  command-line tool's exit codes.
