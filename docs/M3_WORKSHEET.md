# M3 worksheet: the Kalman filter by hand (VV-EST-01)

**Why this exists.** The estimator is the part of the project you will be asked about most. The
baseline (R-03) says to work one full predict-and-update step on paper *before* any filter code is
written, so that the code is a translation of something you already understand. Do this worksheet,
then check your numbers against the table in
[systems-engineering-baseline.md](systems-engineering-baseline.md) section 6.6. A calculator or a
Python prompt is fine; use the full precision it gives you.

---

## 1. The idea in plain language

A moving object has a **position** and a **velocity**. The sensor only reports position, and the
reports are noisy. The filter keeps two things:

- a **best guess** `x̂ = [position, velocity]`, and
- a **doubt table** `P` (2×2), the *covariance*: how unsure the filter is about each number, and how the
  two doubts are linked.

Each time step it does one or both of:

| Step | When | What happens to the guess | What happens to the doubt |
|---|---|---|---|
| **Predict** | every step | moved forward: position += velocity × dt | **grows** (time passing makes you less sure) |
| **Update** | only when a reading arrives | pulled toward the reading | **shrinks** (new information) |

How far an update pulls is decided by the **gain** `K`: roughly *how much to trust the sensor versus my
own prediction*. If the filter is very unsure of itself and the sensor is accurate, `K` is large. If the
sensor is noisy and the prediction is solid, `K` is small.

The diagonal of `P` holds the variances: `P[0][0]` is the doubt about position (in m²), `P[1][1]` the doubt
about velocity (in m²/s²). The off-diagonal `P[0][1]` says how the two doubts move together. It is why a
position-only sensor can still teach the filter about velocity.

## 2. The settings and the starting point

| Symbol | Meaning | Value here |
|---|---|---|
| `x̂` | starting guess `[position, velocity]` | `[0, 10]` |
| `P` | starting doubt | `diag(25, 100)`, i.e. `[[25, 0], [0, 100]]` |
| `dt` | time step | `0.1` s |
| `q` | how much unmodelled jiggle to allow (m²/s³) | `0.1` |
| `R` | how noisy the filter *believes* the sensor is (m²) | `25` |
| `z` | the new position reading | `3` |

## 3. The formulas, written out for the 2×2 case

Model: `F = [[1, dt], [0, 1]]` moves position by velocity × dt. `H = [1, 0]` says the sensor sees position
only. `Q = q · [[dt³/3, dt²/2], [dt²/2, dt]]` is the doubt that time adds.

**Predict** (write `p00, p01, p10, p11` for the entries of `P`):

```text
x⁻   = x + dt·v                         v⁻ = v
p00⁻ = p00 + dt·(p01 + p10) + dt²·p11 + q·dt³/3
p01⁻ = p01 + dt·p11 + q·dt²/2
p10⁻ = p10 + dt·p11 + q·dt²/2
p11⁻ = p11 + q·dt
```

(These come from `P⁻ = F P Fᵀ + Q` multiplied out. You can confirm that on paper; the matrix tests added in
`tests/gtest/mat2_tests.cpp` check the product rule they rely on.)

**Update**:

```text
y  = z − x⁻                    innovation: how far off the prediction was
S  = p00⁻ + R                  how much the innovation is expected to vary
K  = [p00⁻ / S,  p10⁻ / S]     gain: one number for position, one for velocity
x  = x⁻ + K0·y                 v  = v⁻ + K1·y
```

Updated doubt, in the "short" form `P = (I − K H) P⁻`:

```text
p00 = (1 − K0)·p00⁻
p01 = (1 − K0)·p01⁻
p10 = p10⁻ − K1·p00⁻
p11 = p11⁻ − K1·p01⁻
```

The project uses the longer **Joseph form** `P = (I−KH) P⁻ (I−KH)ᵀ + K R Kᵀ` (EST-011) because it keeps `P`
symmetric and non-negative under rounding. Part C has you compare the two.

## 4. Predict before you calculate (2 minutes)

Write down your guesses first. Then check them against your results.

1. After predict, will the position guess be larger or smaller than 0? By roughly how much?
2. Will `p00` go up or down? And `p11`?
3. The reading is `z = 3`. The predicted position will be about `1`. Do you expect the updated position
   guess to land nearer `1` or nearer `3`, or in the middle? What does the ratio of doubt (`p00⁻`) to
   sensor noise (`R = 25`) suggest?
4. The sensor measures position only. Will the velocity guess change at all? Why might it?

My guesses: ____________________________________________________________

## 5. The calculation

### Part A: predict

| Quantity | Your value |
|---|---|
| `x⁻` | |
| `v⁻` | |
| `p00⁻` | |
| `p01⁻` | |
| `p10⁻` | |
| `p11⁻` | |

### Part B: update (short form)

| Quantity | Your value |
|---|---|
| `y` (innovation) | |
| `S` | |
| `K0` | |
| `K1` | |
| updated position `x` | |
| updated velocity `v` | |
| `p00` | |
| `p01` | |
| `p10` | |
| `p11` | |

### Part C: Joseph form (optional but recommended)

Compute `P = (I−KH) P⁻ (I−KH)ᵀ + K R Kᵀ` with `H = [1, 0]`. Here `(I−KH) = [[1−K0, 0], [−K1, 1]]`, and
`K R Kᵀ = R · outer(K, K)`. Do the four entries match Part B to the digits you carried? If they do, why does
the project still bother with the longer form? (Baseline section 11.1 has the honest answer.)

## 6. Check your numbers

Compare with baseline section 6.6, table "VV-EST-01", tolerance 1e-9. If something differs:

- Position and velocity right but `P` wrong: re-check which entries of `P⁻` you used in each formula.
- `K` wrong: check you used `p00⁻` (the **predicted** doubt), not the starting `p00`.
- Everything off by a little: you probably rounded early. Carry full precision to the end.

## 7. Explain it back

Answer in your own words, in a sentence or two each. These are the interview questions in the guide.

1. What does the filter *predict*, and what does it *correct*?
2. Why does `P` grow in predict and shrink in update?
3. What does `K` decide? What would happen to it if `R` were much smaller? Much larger?
4. The sensor never measures velocity. How did the velocity guess change anyway? (Look at `K1`.)
5. Why must the estimator never be given the true state? (SYS-002, EST-002)

## 8. What happens next

When you are done, tell me your numbers and any answer you were unsure of. I will then build
`KalmanEstimator` behind the existing `IEstimator` interface, using exactly these formulas, and the
first test will be this very vector at 1e-9 tolerance: the code has to reproduce what you did by hand.
