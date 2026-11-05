# Validation record: VAL-02 and VAL-03

> This is a small educational simulation, not flight software, and it makes no claim of flight qualification, operational fidelity or real sensor fusion (SYS-006).

This records how well the Kalman filter performs, as required by baseline section 6.7 for milestone M4
("VAL-02 and VAL-03 recorded on held-out seeds"). Everything below comes from `python/ensemble.py`, which
runs the real `sim` once per seed; the commands to reproduce it are in section 5. It is simulated data
from the same model the filter assumes, so it shows the filter is implemented correctly and behaves
sensibly. It says nothing about real sensors (SYS-006).

| Check | Question | Pass condition |
|---|---|---|
| **VAL-02** (EST-008) | Does the estimator help? | Estimate RMSE is at most 0.75 times the raw readings' RMSE on **every** seed |
| **VAL-03** (EST-012) | Is it honest about its own uncertainty? | At least 90 % of position errors are inside the filter's own +/-2 sigma bars, pooled over the seeds (a perfect filter scores about 95 %) |

## 1. Acceptance result: the reference scenario on the held-out seeds

The held-out seeds (1001 to 1050) were never used to choose a filter setting or a threshold (TST-012).

### Result

- Seeds: `held-out` (50 seeds, 1001 to 1050)
- `sim` flags: `(defaults: the reference scenario)`
- Build: gcc 13.3.0, source revision `731465de771b`
- Run on 2026-11-05

| Check | Requirement | Result | Measured | Limit |
|---|---|---|---|---|
| VAL-02: estimate beats the raw readings on every seed | EST-008 | PASS | worst ratio 0.561 (seed 1026); best 0.313, mean 0.414 | at most 0.75 |
| VAL-03: the error bars are honest (pooled +/-2 sigma coverage) | EST-012 | PASS | 0.9758 (9807 of 10050); per seed 0.910 to 1.000 | at least 0.9 |

<details><summary>Per-seed results</summary>

| Seed | Raw RMSE (m) | Estimate RMSE (m) | Ratio | Coverage |
|---|---|---|---|---|
| 1001 | 4.776 | 2.023 | 0.424 | 0.970 |
| 1002 | 4.915 | 1.968 | 0.400 | 0.960 |
| 1003 | 4.835 | 1.898 | 0.393 | 0.995 |
| 1004 | 5.143 | 1.800 | 0.350 | 0.995 |
| 1005 | 4.855 | 1.520 | 0.313 | 1.000 |
| 1006 | 4.739 | 1.937 | 0.409 | 1.000 |
| 1007 | 4.957 | 2.124 | 0.429 | 0.970 |
| 1008 | 4.795 | 1.807 | 0.377 | 1.000 |
| 1009 | 4.758 | 1.803 | 0.379 | 0.995 |
| 1010 | 4.698 | 2.233 | 0.475 | 0.985 |
| 1011 | 4.912 | 2.016 | 0.410 | 0.955 |
| 1012 | 5.107 | 2.347 | 0.460 | 0.965 |
| 1013 | 4.678 | 1.832 | 0.392 | 0.995 |
| 1014 | 5.075 | 1.905 | 0.375 | 0.975 |
| 1015 | 4.975 | 2.321 | 0.466 | 0.960 |
| 1016 | 4.707 | 1.925 | 0.409 | 0.985 |
| 1017 | 4.702 | 2.225 | 0.473 | 0.965 |
| 1018 | 5.105 | 1.871 | 0.367 | 0.995 |
| 1019 | 4.782 | 1.792 | 0.375 | 0.995 |
| 1020 | 5.040 | 2.149 | 0.426 | 0.960 |
| 1021 | 5.442 | 2.538 | 0.466 | 0.910 |
| 1022 | 4.824 | 2.046 | 0.424 | 0.980 |
| 1023 | 5.054 | 1.976 | 0.391 | 0.975 |
| 1024 | 4.878 | 2.170 | 0.445 | 0.970 |
| 1025 | 4.750 | 2.026 | 0.427 | 0.980 |
| 1026 | 4.859 | 2.726 | 0.561 | 0.955 |
| 1027 | 4.885 | 2.107 | 0.431 | 0.985 |
| 1028 | 4.916 | 1.878 | 0.382 | 0.995 |
| 1029 | 5.268 | 2.514 | 0.477 | 0.910 |
| 1030 | 5.130 | 2.141 | 0.417 | 0.980 |
| 1031 | 5.026 | 2.180 | 0.434 | 0.990 |
| 1032 | 5.069 | 1.963 | 0.387 | 0.980 |
| 1033 | 4.966 | 1.949 | 0.393 | 0.995 |
| 1034 | 4.615 | 2.093 | 0.453 | 0.985 |
| 1035 | 5.079 | 2.050 | 0.404 | 0.975 |
| 1036 | 5.326 | 2.184 | 0.410 | 0.950 |
| 1037 | 4.803 | 2.384 | 0.496 | 0.955 |
| 1038 | 5.017 | 1.990 | 0.397 | 0.965 |
| 1039 | 5.122 | 2.103 | 0.411 | 0.970 |
| 1040 | 4.848 | 1.801 | 0.371 | 0.995 |
| 1041 | 5.048 | 2.072 | 0.411 | 0.980 |
| 1042 | 5.087 | 1.680 | 0.330 | 0.995 |
| 1043 | 5.674 | 2.497 | 0.440 | 0.945 |
| 1044 | 5.618 | 2.279 | 0.406 | 0.950 |
| 1045 | 4.745 | 1.766 | 0.372 | 0.990 |
| 1046 | 5.145 | 2.223 | 0.432 | 0.955 |
| 1047 | 5.443 | 2.293 | 0.421 | 0.970 |
| 1048 | 4.948 | 2.034 | 0.411 | 0.995 |
| 1049 | 4.926 | 1.899 | 0.385 | 0.995 |
| 1050 | 5.018 | 1.991 | 0.397 | 0.990 |

</details>

## 2. How the thresholds were set

The limits 0.75 and 0.90 are the baseline's, taken from an independent prototype. Before the held-out run
they were re-measured on the separate tuning seeds (1 to 200) only: the ratio ranged 0.317 to 0.576 and the
pooled coverage was 0.975, so both limits had room (baseline OI-02). No limit and no seed was changed
after seeing a held-out result (baseline risk R-05). The held-out results were looked at after the
acceptance tests were written, and nothing was adjusted afterwards.

## 3. Exploratory scenarios (tuning seeds, report only)

The same two checks on other settings, on the 200 **tuning** seeds, to see where the filter stops working.
These are not acceptance results and the formal scenario record (VAL-05) is an M6 item. The baseline's
section 5.2 still lists S-HIGH-NOISE, S-SPARSE and S-WRONG-R as `[TBD]`; these are their measured values,
and the baseline has not been edited.

| Scenario | Flags | Mean ratio | Worst ratio | Pooled coverage | VAL-02 | VAL-03 | What it is |
|---|---|---|---|---|---|---|---|
| S-ACCEL-SMALL | `--accel 0.1` | 0.46 | 0.62 | 0.957 | pass | pass | The truth accelerates a little; the filter assumes it does not. |
| S-ACCEL-LARGE | `--accel 0.5` | 1.05 | 1.31 | 0.423 | **fail** | **fail** | The truth accelerates a lot. **The filter's model is wrong.** |
| S-HIGH-NOISE | `--sigma 20 --est-r 400` | 0.34 | 0.57 | 0.959 | pass | pass | A noisier sensor, and the filter told so. |
| S-SPARSE | `--meas-every 50` | 0.81 | 0.99 | 0.963 | **fail** | pass | A reading only every 5 seconds. |
| S-WRONG-R | `--est-r 1` | 0.57 | 0.69 | 0.346 | pass | **fail** | Sensor noise is 5 m, but the filter is told it is 1 m. |

How to read it:

- **S-ACCEL-SMALL** behaves as the prototype found: the filter still helps and its error bars stay honest.
- **S-ACCEL-LARGE** is the documented limitation. With true acceleration the constant-velocity filter is
  no better than the raw readings (mean ratio about 1) and the truth is inside its error bars only 42 % of the time.
- **S-HIGH-NOISE**: a noisier sensor, with the filter told so, gives a larger improvement (mean ratio 0.34 against 0.41).
- **S-SPARSE** is a result the baseline did not predict. Coverage stays honest (0.963) as expected, but with a
  reading only every 5 s the filter helps much less (mean ratio 0.81, and the worst seed 0.99): there is little
  to average. The 0.75 limit of EST-008 is therefore a statement about the reference scenario, not about every setting.
- **S-WRONG-R** shows why EST-012 exists. The estimate still beats the raw readings (worst ratio 0.69), so an
  RMSE check alone would pass, but with the filter told the sensor is five times more accurate than it is,
  the error bars are far too narrow and only 35 % of errors fall inside them.

## 4. What this does and does not show

- It shows the filter is correct for its own model, helps in the reference scenario on 50 unseen seeds, and
  reports honest uncertainty there.
- It does not show anything about real data, a model other than constant velocity, or a sensor whose noise
  is not Gaussian.
- All of it depends on the C++ standard library's normal-distribution implementation, so the exact figures
  hold for the same compiler and library (GCC 13.3 here). The conclusions should not.
- The source revision in the report shows `-dirty` if it was generated before the code was committed;
  regenerate it from a clean commit to pin the record to one.

## 5. Reproduce

```bash
# Acceptance evidence (also run by `ctest` through tests/system/test_estimator_performance.py)
.venv/bin/python python/ensemble.py --sim build/sim --seeds held-out

# One exploratory scenario (everything after -- goes to sim); exit code 1 means a check failed
.venv/bin/python python/ensemble.py --sim build/sim --seeds tuning --summary-only -- --accel 0.5
```
