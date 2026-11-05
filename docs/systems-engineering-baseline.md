# Systems Engineering Baseline: Sensor and State-Estimation Simulator

## Requirements · Risk · Validation · Verification · Design · Interfaces

| | |
|---|---|
| **Document ID** | SEB-001 |
| **Version / status** | 0.3 DRAFT (CR-24, CR-25 applied). **Tentative proposal; not baselined.** |
| **Date** | 2026-10-10 (v0.1); 2026-10-19 (v0.2, v0.3) |
| **System** | Sensor and State-Estimation Simulator (working name `sensor-sim`) |
| **Prepared for** | Project owner (learner), 30-day sprint |
| **Prepared by** | Claude (proposal, for owner review) |
| **Approval** | None yet. Nothing in this document is binding until the owner dispositions §9 and §11.3 |
| **Source documents** | `CONTINUATION_GUIDE.md` (guide), `requirements.md` v0.1 (REQ), `test-frameworks.md` (TFW) |
| **Supersedes** | Nothing. REQ v0.1 remains in force until this baseline is accepted, then REQ v0.2 is regenerated from §3 |

### How to read this document

| Part | Sections | Content |
|---|---|---|
| **A. Baseline** | §1–§8 | The tentative requirements, risk, validation, verification, design and interface definitions |
| **B. Change proposals** | §9 | Gaps and discrepancies found in the three source documents, and the change proposed for each |
| **C. Rationale annex** | §10 | For each of the six baseline items: what it is, what it does, what is recommended, why, and the likely outcome |
| **Appendices** | §11 | Prototype evidence, verification vectors, decision and TBD register, glossary |

Everything marked **[TBD]** is a value to be confirmed once the C++ implementation exists. Everything marked **[DECIDE]** needs an owner decision. D1–D7 were accepted by the owner on 2026-10-11 (§11.3); the remaining [DECIDE] items are DD-010 and the CSV cross-term (OI-01, OI-03).

### Revision history

| Version | Date | Change |
|---|---|---|
| 0.1 | 2026-10-10 | First proposal, derived from the three source documents and a throwaway prototype of the reference scenario (Appendix A). |
| 0.2 | 2026-10-19 | CR-24 applied: position tolerance now scales with run length and position size (§6.3, SIM-003, SIM-004, §6.5). |
| 0.3 | 2026-10-19 | CR-25 applied: sidecar estimator keys may be `null` (§8.5); §8.3 `--steps` range. |

---

# PART A: BASELINE

## 1. Purpose, scope and conventions

### 1.1 Purpose
Define, in one place, what the system must do (requirements), what could go wrong (risk), how we will know it is the right system (validation) and was built correctly (verification), how it is structured (design) and how its parts talk to each other (interfaces). The three source documents contain most of the substance; this document adds the missing layers (stakeholder needs, system-level requirements, risk, validation, interface control) and resolves the conflicts between them.

### 1.2 System boundary
**Inside the boundary:** the C++ `simcore` library and `sim` executable, the Python analysis tools, the test suites, the build and CI configuration, and the documentation.
**Outside the boundary:** real sensors, real vehicles, flight software, networks, GUIs, containers (optional later), and any claim of operational fidelity.

### 1.3 Conventions

| Item | Convention |
|---|---|
| **Requirement language** | *shall* = mandatory (Must); *should* = Should; *may* = Could. Every requirement states one testable thing. |
| **Priority** | MoSCoW: **M**ust, **S**hould, **C**ould, as in REQ. |
| **Verification methods** | **T** Test (run it, compare to expected) · **A** Analysis (calculation or comparison to an independent model) · **I** Inspection (review code, config or docs) · **D** Demonstration (run it and observe, without precise measurement). |
| **Verification levels** | **U** unit · **I** integration · **S** system · **SIL** software-in-the-loop (the whole simulation as the environment for the estimator). |
| **ID scheme** | `SYS` system, `SIM` dynamics, `SEN` sensor, `EST` estimator, `RUN` runner, `CFG` configuration, `OUT` output, `ANA` analysis, `NFR` non-functional, `TST` test architecture, `DOC` documentation, `R-` risk, `VAL-` validation, `DD-` design decision, `IF-` interface, `CR-` change request. IDs are never reused. |
| **Units** | SI. Unit suffix in every field and flag name (`_m`, `_s`, `_mps`, `_m2`). |
| **Status values** | Proposed → Accepted → Implemented → Verified. Everything here is *Proposed*. |

---

## 2. System context and stakeholder needs

### 2.1 Context

```text
   ┌────────────┐  flags, seed   ┌──────────────────────────────┐   run.csv + run.csv.config.json
   │   User     │───────────────▶│  sim (C++ executable)        │─────────────────────────────┐
   │ (learner,  │◀───────────────│   simcore: dynamics, sensor, │                             │
   │  reviewer) │  exit code,    │   estimator, runner, recorder│                             ▼
   └────────────┘  stderr        └──────────────────────────────┘                  ┌─────────────────────┐
         ▲                                                                         │ analyze.py (Python) │
         │ plot.png, metrics.json, README                                          └──────────┬──────────┘
         └─────────────────────────────────────────────────────────────────────────────────────┘

   CI runner / developer ──▶ CMake + CTest + pytest ──▶ JUnit XML, coverage, traceability matrix
```

### 2.2 Stakeholders and needs

| Need | Statement | Stakeholder | Derived from |
|---|---|---|---|
| **N-01** | Demonstrate the full chain: truth, noisy sensing, estimation, evaluation, with real numbers. | Hiring reviewer, learner | Guide §1–2 |
| **N-02** | Be reproducible by someone else from a fresh checkout. | Reviewer | Guide §1, §6 (days 27–28) |
| **N-03** | Give objective evidence that the code is correct, not just that it runs. | Reviewer, learner | Guide §7, TFW §4 |
| **N-04** | Be small enough to finish and fully understand in 30 days. | Learner | Guide §1, §10 |
| **N-05** | Make only claims that the evidence supports. | Reviewer, learner | Guide §9, §11 |
| **N-06** | Show habits that aerospace and defense employers look for: requirements, traceability, deterministic tests, CI. | Reviewer | TFW §4 |
| **N-07** | Teach the learner the material as it is built. | Learner | Guide §12 |
| **N-08** | Leave enough calendar for the job search. | Learner | Guide §1 (allocation) |

---

## 3. Requirements

### 3.1 Approach
REQ v0.1 starts at component level. This baseline adds a **system level** above it (§3.2) so completeness can be shown against the needs in §2.2, and a **change set** (§3.3) against REQ v0.1. REQ requirements not mentioned in §3.3 are **retained unchanged**, and §3.4 lists those that were reviewed with no change. The full verification mapping is in §6.5.

### 3.2 System-level requirements (new)

| ID | Pri | Requirement | Satisfies | Verification |
|---|---|---|---|---|
| **SYS-001** | M | From a fresh checkout on supported Linux, a user shall be able to build, test, run the reference scenario and analyze its output using only commands documented in the README. | N-01, N-02 | D (clean-room run in a container), T (CI uses the same commands) |
| **SYS-002** | M | The estimator shall use measurements and configuration only. Ground truth shall be used for evaluation only. *(Parent of EST-002, SEN-006.)* | N-03 | I, T (compile-time check) |
| **SYS-003** | M | Identical configuration, seed, platform and build shall produce identical outputs. *(Parent of SEN-004, NFR-004.)* | N-02, N-03 | T |
| **SYS-004** | M | The system shall quantify estimator performance against the raw sensor **and** against the estimator's own reported uncertainty. *(Parent of ANA-002, EST-008, EST-012.)* | N-01, N-03 | T, A |
| **SYS-005** | M | Every Must requirement shall be traceable to at least one verification activity, and the check shall be automated. *(Parent of TST-005, TST-011.)* | N-03, N-06 | T |
| **SYS-006** | M | All documentation shall state that the system is an educational simulation and shall not claim flight qualification, operational fidelity or real sensor fusion. *(Parent of DOC-001.)* | N-05 | I |

### 3.3 Change set against REQ v0.1

**New requirements**

| ID | Pri | Requirement | Verification | CR |
|---|---|---|---|---|
| **SIM-006** | M | `dt` shall be finite and > 0; the step count N shall be an integer ≥ 0; `x0`, `v0` and `accel` shall be finite. Otherwise construction shall fail naming the parameter. | T (U) | CR-05 |
| **EST-009** | M | The estimator shall start **uninitialized**. It shall initialize on its first measurement (`x̂ = [z, 0]`, `P = P0`) **without** a predict step. `predict` before initialization shall be rejected. Rows before initialization shall have empty estimate fields. | T (U) | CR-01 |
| **EST-010** | M | Estimator configuration shall be validated: `R > 0`, `q ≥ 0`, `P0` symmetric with non-negative diagonal and determinant ≥ 0, `dt > 0`. Otherwise fail naming the parameter. | T (U) | CR-04 |
| **EST-011** | S | The covariance update shall use the Joseph form `P⁺ = (I−KH)P⁻(I−KH)ᵀ + KRKᵀ`. | I, T (U) | CR-07 |
| **EST-012** | M | Over the pooled held-out seed set (TST-012, ≥ 20 seeds), the fraction of measurement-time position errors within ±2σ of the estimator's reported position standard deviation shall be ≥ **0.90** **[TBD: re-measure in C++]**. | T (S) | CR-07 |
| **EST-013** | M | A measurement with a non-finite value or a timestamp earlier than the last processed time shall be rejected with an error, leaving estimator state unchanged. | T (U) | CR-05 |
| **CFG-003** | M | Estimator parameters (`q`, `R`, `P0`) shall be set independently of the sensor's true noise `σ`. No default derives one from the other at run time. | T (S) | CR-15 |
| **OUT-004** | M | The output CSV shall be written atomically: write to a temporary file and rename on success. A failed run shall leave no partial CSV. | T (S) | CR-13 |
| **OUT-005** | M | A missing value shall be an empty field. `nan`, `inf` and `-` shall never appear. | T (S) | CR-05, CR-13 |
| **TST-011** | M | A script shall generate the requirement-to-test matrix from test tags and requirement IDs, and shall fail CI if (a) a Must requirement has no test, or (b) a test cites an unknown ID. | T | CR-14 |
| **TST-012** | M | Estimator tuning shall use a tuning seed set. Acceptance tests (EST-008, EST-012) shall use a **disjoint** held-out seed set. An automated check shall verify disjointness. | T, I | CR-06 |
| **NFR-009** | S | All external dependencies (test framework, Python packages) shall be pinned to exact versions. Python tools shall run in a virtual environment built from a pinned requirements file. | I | CR-17 |
| **NFR-010** | S | Each accepted baseline of this document and the source shall be tagged in version control. | I | CR-21 |
| **DOC-001** | M | The README shall include: purpose, data flow, units and assumptions, build/test/run/analyze commands, sample output, limitations and next steps, and the SYS-006 statement. | I | CR-19 |
| **DOC-002** | S | `docs/architecture.md` shall reflect §7 and §8 of this baseline and be updated whenever either changes. | I | CR-19 |

**Amended requirements**

| ID | Pri | Change | Verification | CR |
|---|---|---|---|---|
| **SIM-004** | S | Add: with Euler integration the position error vs `x0 + v0·t + ½·a·t²` shall not exceed `½·abs(a)·t·dt + tol_pos(k)`, where `tol_pos` is the position tolerance of §6.3 (CR-24). (Measured 5.000000 m for a = 1 m/s², t = 100 s, dt = 0.1 s.) | T (U) | CR-16 |
| **RUN-001** | M | Replace the sequence with: propagate → observe (the **sensor** decides whether a measurement is due) → if the estimator is uninitialized, initialize on the first measurement, else predict and, if measured, update → record. | T (I) | CR-01, CR-03 |
| **EST-007** | M | Make concrete: with σ = 0 and `R = 1e-6 m²`, position error < 1e-3 m **and** velocity error < 1e-3 m/s after 10 measurements. (Prototype: 1.8e-11 m and 7.4e-8 m/s.) | T (U) | CR-04 |
| **EST-008** | M | Make concrete: on every held-out seed, estimated-position RMSE at measurement timestamps shall be ≤ **0.75 ×** raw-measurement RMSE. (Prototype: 0.32–0.54 over 200 seeds.) | T (S) | CR-06 |
| **CFG-002** | M | Add: exit code 2 for usage or configuration error, 1 for runtime or I/O failure, message format `sim: error: <parameter>: <reason>`. | T (S) | CR-23 |
| **OUT-003** | **S → M** | Promote. The sidecar `<out>.config.json` shall contain `schema_version`, every effective parameter, the seed, and build info (compiler id and version, source revision if available). | T (S) | CR-13 |
| **ANA-002** | M | Define the sample set: all RMSEs are computed over rows where a measurement exists. | T (U) | CR-08 |
| **ANA-004** | **S → M** | Promote the numeric part: report the fraction of position errors inside ±2σ. The plot of error with bounds remains Should. | T (U) | CR-07 |
| **NFR-001** | M | Name the toolchain baseline: GCC 13.3 and Clang 18.1 (both present on the development machine), CMake ≥ 3.20. | I, D | CR-17 |
| **NFR-004** | M | Add: no golden CSV files are committed. Determinism is tested by comparing two runs on the same machine. | T | CR-18 |
| **NFR-006** | M | Clarify: the 30 s budget includes the seed-ensemble tests (EST-008, EST-012). | T | CR-20 |
| **NFR-008** | C | Add: target ≥ 90 % line coverage on `simcore` as a goal reported in CI, not a gate. | D | CR-20 |
| **TST-010** | **S → C** | Demote. Second framework (Catch2) is a stretch goal; it is not required for v1. | D | CR-09 |

### 3.4 Reviewed, no change
`SIM-001/002/003/005`, `SEN-001..007`, `EST-001..006`, `CFG-001`, `RUN-001` (except as amended above), `OUT-001/002`, `ANA-001/003/005`, `NFR-002/003/005/007`, `TST-001..009`.
Checked numerically: SEN-003's bounds are 5 standard errors on the mean (SE = 5/√10000 = 0.05 m, bound ±0.25 m), so a false failure is vanishingly unlikely; the ±5 % on the standard deviation is about 7 standard errors. Both are safe for a fixed seed.

### 3.5 Allocation of requirements to components

| Component | Allocated requirements |
|---|---|
| **Dynamics** | SIM-001..006, NFR-005 |
| **Sensor** | SEN-001..007, NFR-003 |
| **Estimator** | EST-001..013, CFG-003 |
| **Runner** | RUN-001, SYS-002, NFR-004 |
| **Recorder / config writer** | OUT-001..005 |
| **CLI front end (`main`)** | CFG-001..003, TST-001 |
| **Analysis (Python)** | ANA-001..005 |
| **Test and build infrastructure** | TST-002..012, NFR-001, 006..010 |
| **Documentation** | DOC-001/002, SYS-006 |
| **System (whole)** | SYS-001..005 |

---

## 4. Risk management

### 4.1 Method
Likelihood **L** and impact **I**, each 1–5. Score = L × I. Rating: **Low** 1–6, **Medium** 8–12, **High** 15–25. Strategies: Avoid, Mitigate, Transfer, Accept. The register is reviewed weekly and whenever a trigger fires.

| Scale | L | I |
|---|---|---|
| 1 | < 10 % | Cosmetic |
| 2 | 10–30 % | Rework of < 1 day |
| 3 | 30–50 % | Rework of 1–3 days, or a requirement weakened |
| 4 | 50–80 % | A milestone missed, or a claim would be false |
| 5 | > 80 % | Project goal (a credible, explainable portfolio piece) at risk |

### 4.2 Register

| ID | Risk | L | I | Score | Mitigation (strategy) | Trigger | Related |
|---|---|---|---|---|---|---|---|
| **R-01** | **Schedule.** The docs are dated 2026-09-27 and `Project/` is empty, so no code exists yet. | 4 | 5 | **20 High** | Walking skeleton with CI in the first 3–5 working days (CR-12). Cut-line: Musts only; Shoulds drop first. Weekly burn check. *(Mitigate)* | No green CI by working day 7 | CR-12 |
| **R-03** | **Comprehension gap.** The learner cannot explain what was built, which defeats the project's purpose. | 3 | 5 | **15 High** | Teach-then-build per guide §12; do the one-step Kalman update by hand first (VV-EST-01); explain-back checkpoints recorded in `learning-notes.md`. *(Mitigate)* | Cannot explain a component without reading it | VAL-06 |
| **R-02** | **Scope creep** (four test frameworks, RK4, 2D, containers). | 4 | 3 | 12 Med | Scope freeze; extensions gated on exit criteria (§6.7); TST-010 demoted. *(Avoid)* | Any work not traceable to a Must | CR-09 |
| **R-04** | **Estimator maths or tuning errors** (sign, Q, initialization order). | 3 | 4 | 12 Med | Hand vector (VV-EST-01); independent Python recomputation (VAL-04); noise-free convergence test (EST-007); consistency check (EST-012). *(Mitigate)* | Estimate disagrees with the oracle by > 1e-9 | CR-01, CR-07 |
| **R-14** | **Job-search starvation.** All time goes into the project. | 3 | 4 | 12 Med | Fixed weekly time boxes (guide §1: about 30 %); a project cut-line; applications start now. *(Mitigate)* | A week with zero applications | N-08 |
| **R-05** | **False confidence** from tuning until the test passes. | 3 | 3 | 9 Med | Tuning and held-out seed sets (TST-012); thresholds taken from independent runs. *(Mitigate)* | Threshold changed to fit a failing result | CR-06 |
| **R-06** | **Model mismatch goes unnoticed.** Filter assumes constant velocity; truth may accelerate. | 3 | 3 | 9 Med | Mismatch scenario (VAL-05) shows coverage collapse; limitation in README. *(Mitigate and accept)* | Any scenario with accel ≠ 0 | CR-07 |
| **R-09** | **CI and build plumbing** consume days (framework fetch, runner differences). | 3 | 3 | 9 Med | CI in week 1; pinned dependency source; single primary framework. *(Mitigate)* | CI red for > 1 day | CR-12 |
| **R-10** | **Interface drift** between C++ output and Python reader. | 3 | 3 | 9 Med | Single ICD (§8), `schema_version`, contract test (Python reads freshly generated CSV in CI). *(Mitigate)* | Column added without version bump | CR-13 |
| **R-08** | **Environment gaps.** `pytest`, `pandas`, `matplotlib`, `gcovr` are not installed on the dev machine; GCC 13 lacks `-fcondition-coverage` (needs GCC 14). | 4 | 2 | 8 Med | Virtual environment with pinned requirements (NFR-009); use Clang 18 `-fcoverage-mcdc` if MC/DC is ever wanted. *(Mitigate)* | `pip install` fails offline | CR-17 |
| **R-13** | **Overstated claims** in README or interviews. | 2 | 4 | 8 Med | SYS-006 and DOC-001; claim-to-evidence table (VAL-07). *(Mitigate)* | A claim with no evidence row | CR-19 |
| **R-16** | **No remote or backup** for the repository. | 2 | 4 | 8 Med | Create the repository, push on every working session. *(Mitigate)* | Working tree not pushed for 2 days | NFR-010 |
| **R-07** | **Cross-platform randomness differs** (D5). | 3 | 2 | 6 Low | Statistical bounds, no golden files, same-platform determinism only. *(Accept, documented)* | Test depends on an exact sample value | CR-18 |
| **R-11** | **Floating-point time drift.** | 2 | 3 | 6 Low | `t = k·dt` rule (SIM-002) with test. *(Mitigate)* | Time computed by accumulation | |
| **R-12** | **Covariance loses symmetry or definiteness.** | 2 | 3 | 6 Low | Joseph form (EST-011); symmetry check (EST-006). Prototype showed asymmetry 2.2e-16 after 1000 steps, so residual risk is low. *(Mitigate)* | EST-006 test fails | |
| **R-15** | **Dependency licence or supply chain.** | 2 | 2 | 4 Low | Pin versions and hashes; record licences in the README. *(Accept)* | | NFR-009 |

### 4.3 Heat map (current)

```text
Impact 5 │      R-03   R-01
       4 │      R-16        R-13   R-14  R-04
       3 │ R-11 R-12  R-05 R-06 R-09 R-10  R-02
       2 │ R-15       R-07  R-08
       1 │
         └──────────────────────────────
           L=1   L=2  L=3  L=4   (R-01: L4 I5; R-03: L3 I5)
```
*(Positions are approximate; use the table for exact scores.)*

---

## 5. Validation: are we building the right system?

**Verification** asks "did we build it right?" against requirements. **Validation** asks "is it the right thing?" against the needs in §2.2. Validation criteria below are what an outside reviewer would care about.

### 5.1 Validation objectives

| ID | Need | Question | Method | Acceptance criterion | Evidence | When |
|---|---|---|---|---|---|---|
| **VAL-01** | N-01, N-02 | Can someone else run it? | D | A fresh container checkout reaches `plot.png` and metrics in ≤ 15 min using only README commands. | Container log | Day 27–28 |
| **VAL-02** | N-01, N-03 | Does the estimator help? | T, A | Estimate RMSE ≤ 0.75 × raw RMSE on every held-out seed. Prototype baseline: 0.32–0.54. | `metrics.json` ensemble | After estimator |
| **VAL-03** | N-03 | Is the estimator *honest* about its own uncertainty? | A | Pooled ±2σ coverage ≥ 0.90. Prototype baseline: 0.975. | Ensemble report | After estimator |
| **VAL-04** | N-03 | Does an independent implementation agree? | A | A Python re-computation from the CSV's `meas_pos_m` column and sidecar config reproduces `est_*` columns within 1e-9. | pytest cross-check | After estimator |
| **VAL-05** | N-03, N-05 | Where does it stop working? | A, D | Scenario sweep (§5.2) is run and the failures are written into the README limitations. | Scenario table | Before README |
| **VAL-06** | N-07, N-04 | Does the learner understand it? | D | The seven explain-back questions in guide §11 are answered aloud to a reviewer; answers are recorded. | `learning-notes.md` | Day 29–30 |
| **VAL-07** | N-05 | Are the claims true? | I | Every README claim has a row in a claim-to-evidence table; no claim is unsupported; SYS-006 is present. | The table | Day 29–30 |
| **VAL-08** | N-01, N-06 | Does the landing page communicate? | D | A reviewer can say in two minutes what the project demonstrates, using only the README. | Reviewer note | Day 29–30 |

### 5.2 Validation scenarios

| Scenario | Parameters (changes from the reference) | Expected behavior | Status |
|---|---|---|---|
| **S-REF** | §6 of REQ: σ = 5, M = 5, q = 0.1, R = 25 | RMSE ratio 0.32–0.54, coverage ≈ 0.975 | **Measured in prototype** |
| **S-NOISEFREE** | σ = 0, R = 1e-6 | Converges to truth within 1e-3 m and 1e-3 m/s after 10 measurements | **Measured in prototype** |
| **S-ACCEL-SMALL** | accel = 0.1 m/s² | Filter still helps (RMSE 2.21 vs 5.04 raw), coverage 0.96 | **Measured** |
| **S-ACCEL-LARGE** | accel = 0.5 m/s² | **Filter fails**: RMSE 5.10 vs 5.04 raw, coverage 0.45, mean NEES 5.35. This is the limitation to document, and it shows why EST-012 matters (RMSE alone barely flags it). | **Measured** |
| **S-HIGH-NOISE** | σ = 20, R = 400 | Larger absolute error; ratio should improve | [TBD] |
| **S-SPARSE** | M = 50 (0.2 Hz) | Covariance grows between measurements; coverage should remain ≥ 0.90 | [TBD] |
| **S-WRONG-R** | σ = 5 but R = 1 | Overconfident filter: coverage falls below 0.90 | [TBD] |

---

## 6. Verification: did we build it right?

### 6.1 Strategy
A V-model in miniature: each requirement level has a matching test level (§6.2). Where a test would need to reproduce the implementation's own maths, use an **independent oracle** instead (hand-computed vectors, analytic solutions, a separate Python implementation). Tests describe behavior through public interfaces only.

### 6.2 Levels and tools

| Level | Scope | Tool | Example |
|---|---|---|---|
| **Unit** | One component in isolation, fakes for neighbours | GoogleTest (primary) | `Estimator.PredictOnlyGrowsUncertainty` |
| **Integration** | Components together, or sequencing with fakes | GoogleTest | RUN-001 call-order test |
| **System** | The built `sim` binary through flags and CSV | pytest | EST-008 across held-out seeds |
| **SIL** | Whole simulation as the environment for the estimator | pytest ensembles | EST-012 coverage |
| **Static** | Warnings, sanitizers, source rules | `-Wall -Wextra -Wpedantic -Werror`, ASan, UBSan, grep rules | NFR-001, 003, 007 |

### 6.3 Tolerance and determinism policy

| Quantity | Tolerance | Basis |
|---|---|---|
| Position (analytic comparison after k steps) | `max(1e-9 m, 2·k·u·X)`, u = 2⁻⁵³, X = \|x0\| + \|v0\|·t + ½·\|a\|·t² (t = k·dt) | SIM-003, SIM-004 (CR-24). Rounding grows with k and with position size; a fixed 1e-9 m is unachievable beyond about 8.4e6 m. The second term exceeds the 1e-9 m floor only when k·X > about 4.5e6, so the SIM-003 reference check keeps 1e-9 m. |
| Time | 1e-9 s | SIM-002 |
| Covariance symmetry | 1e-9 | EST-006 |
| C++ vs Python oracle | 1e-9 absolute | Different operation order gives about 1e-12 differences |
| Statistical checks | ≥ 5 standard errors, fixed seed | SEN-003 |
| CSV round trip | exact | 17 significant digits (OUT-002) |

Rules: never compare floating-point values with `==` except where a quantity is exact by construction (σ = 0 returns the exact position). No committed golden CSV files (NFR-004). Randomized tests fix the seed and use bounds, not exact samples.

### 6.4 Test architecture
As in REQ §7, with two changes: GoogleTest is the only required C++ framework (Catch2 is a Could, TST-010), and traceability is generated by a script (TST-011).

```text
 simcore (library, zero test deps) ─┬─▶ sim (main only)
                                    ├─▶ tests/support  (neutral helpers, no framework headers)
                                    │        └─▶ tests/gtest   (thin adapter) ─▶ CTest ─▶ JUnit XML
                                    └─▶ tests/system   (pytest, drives the binary) ─▶ JUnit XML
 tools/trace.py:  requirement IDs + test tags + JUnit XML ─▶ traceability matrix + CI gate (TST-011)
```
Requirement tagging in GoogleTest: `RecordProperty("requirements", "SIM-003")`. In pytest: `@pytest.mark.req("SEN-004")`.

### 6.5 Requirements verification cross-reference matrix (RVCM)

| ID | Pri | Method | Level | Planned verification |
|---|---|---|---|---|
| SYS-001 | M | D, T | S | Clean-room container run; CI runs same commands |
| SYS-002 | M | I, T | U | Compile-time check (EST-002) plus review |
| SYS-003 | M | T | S | Same as SEN-004 |
| SYS-004 | M | T, A | S | ANA-002, EST-008, EST-012 |
| SYS-005 | M | T | S | TST-011 script |
| SYS-006 | M | I | – | README checklist (DOC-001) |
| SIM-001 | M | I | – | Header review: fields and units |
| SIM-002 | M | T | U | k = 1000, dt = 0.1 gives 100.0 ± 1e-9 |
| SIM-003 | M | T, A | U | Constant velocity vs analytic, within the §6.3 position tolerance |
| SIM-004 | S | T | U | Euler error ≤ ½·\|a\|·t·dt + §6.3 position tolerance (a = 1 gives 5 m) |
| SIM-005 | M | T | U, S | N + 1 rows |
| SIM-006 | M | T | U | Invalid or non-finite config rejected |
| SEN-001 | M | I | – | `Measurement` has no velocity field |
| SEN-002 | M | T | U | N = 100, M = 5 gives 21 measurements at k = 0, 5, …, 100 |
| SEN-003 | M | T | U | σ = 0 exact; σ = 5 statistical bounds, fixed seed |
| SEN-004 | M | T | S | Two runs, byte-identical CSV |
| SEN-005 | M | T | U | Timestamp and sensor ID present |
| SEN-006 | M | I, T | U | `const&` parameter; truth unchanged after observe |
| SEN-007 | M | T | U | σ < 0 and M < 1 rejected, message names the parameter |
| EST-001 | M | T, A | U | VV-EST-01 hand-computed vector |
| EST-002 | M | T | U | `static_assert(!std::is_invocable_v<…, TrueState>)` |
| EST-003 | M | T | U | Predict only: position advances by v·dt, variance grows |
| EST-004 | M | T | U | Update moves toward measurement, variance falls |
| EST-005 | M | T | U | Config round trip |
| EST-006 | M | T | U | 1000-step symmetry and non-negative diagonal |
| EST-007 | M | T | U | σ = 0, R = 1e-6, error bounds after 10 measurements |
| EST-008 | M | T | S | Ratio ≤ 0.75 on held-out seeds |
| EST-009 | M | T | U | First measurement initializes without predict; early predict rejected |
| EST-010 | M | T | U | Invalid R, q, P0, dt rejected |
| EST-011 | S | I, T | U | Review and VV-EST-01 check of P |
| EST-012 | M | T | SIL | Pooled coverage ≥ 0.90 on held-out seeds |
| EST-013 | M | T | U | NaN, inf, out-of-order time rejected; state unchanged |
| CFG-001 | M | T | S | Test parses `--help` and compares to the flag table in §8.3 |
| CFG-002 | M | T | S | Bad input: exit code, stderr, no file |
| CFG-003 | M | T | S | R set differently from σ² gives different output |
| RUN-001 | M | T | I | Fake components record call order |
| OUT-001 | M | T | S | Header and column count exact |
| OUT-002 | M | T | U | Write, read, equal at 17 digits |
| OUT-003 | M | T | S | Sidecar contains required fields |
| OUT-004 | M | T | S | Injected failure leaves no CSV |
| OUT-005 | M | T | S | No `nan`, `inf` in any output; empty = missing |
| ANA-001 | M | T | U | Malformed CSV rejected |
| ANA-002 | M | T | U | Small known input matches hand values |
| ANA-003 | M | T | U | PNG produced (smoke) |
| ANA-004 | M | T | U | Coverage fraction on a known input |
| ANA-005 | S | T | U | JSON and stdout metrics |
| NFR-001 | M | I, D | – | CI builds with GCC and Clang, `-Werror` |
| NFR-002 | M | I | – | `simcore` links only the standard library |
| NFR-003 | M | I, T | – | Grep rule: no `rand(`, `time(`, global state |
| NFR-004 | M | T | S | Same as SEN-004; no golden files |
| NFR-005 | M | I | – | Naming review; CSV header check |
| NFR-006 | M | T | – | CI step time check |
| NFR-007 | S | T | – | ASan and UBSan CI job |
| NFR-008 | C | D | – | Coverage artefact uploaded |
| NFR-009 | S | I | – | Pinned versions present |
| NFR-010 | S | I | – | Tags exist |
| TST-001 | M | I | – | `main.cpp` contains flag parsing and one call into `simcore` |
| TST-002 | M | D | – | CI builds with each adapter; changes outside `tests/` are empty |
| TST-003 | M | T | – | `ctest -N` lists every test |
| TST-004 | M | I | – | JUnit files exist and parse |
| TST-005 | M | T | – | TST-011 script |
| TST-006 | M | I | – | Grep: no framework headers in `tests/support` |
| TST-007 | M | I, T | I | Fakes used in RUN-001 test |
| TST-008 | M | I | S | pytest drives the binary |
| TST-009 | M | D | – | CI run on push and pull request |
| TST-010 | C | D | – | CI matrix with Catch2 (if attempted) |
| TST-011 | M | T | – | Script unit test with a missing-ID fixture |
| TST-012 | M | T, I | – | Disjointness check on the seed lists |
| DOC-001 | M | I | – | README checklist |
| DOC-002 | S | I | – | Compare against §7, §8 |

### 6.6 Verification vectors (independent oracles)

**VV-EST-01: one predict-and-update step by hand.** Inputs: `x̂ = [0, 10]`, `P = diag(25, 100)`, `dt = 0.1`, `q = 0.1`, `R = 25`, measurement `z = 3`.

| Quantity | Expected value |
|---|---|
| Predicted state | `[1.0, 10.0]` |
| Predicted `P` | `[[26.0000333333, 10.0005], [10.0005, 100.01]]` |
| Innovation covariance `S` | 51.0000333333 |
| Gain `K` | `[0.5098042420, 0.1960881071]` |
| Updated state | `[2.0196084839, 10.3921762143]` |
| Updated `P` (Joseph) | `[[12.7451060490, 4.9022026783], [4.9022026783, 98.0490208846]]` |

Tolerance 1e-9. Values come from the independent prototype (Appendix A) and should also be re-derived by hand by the learner, which is the point of the exercise (R-03).

**VV-SIM-01: Euler with acceleration.** `x0 = 0`, `v0 = 10`, `a = 1`, `dt = 0.1`, 1000 steps: `x = 5995.0`, `v = 110.0`; the exact kinematic answer is `6000.0`; difference `5.0 = ½·a·t·dt`.

### 6.7 Entry and exit criteria

| Milestone (guide days) | Exit criteria |
|---|---|
| **M0 Skeleton** (1–5; moved earlier, CR-12) | Repo with remote; CMake builds `simcore` and `sim`; one trivial GoogleTest and one pytest run under CTest; **CI green**; fake sensor and passthrough estimator write a valid CSV; Python prints RMSE. |
| **M1 Truth** (6–11) | SIM-001..006 verified; VV-SIM-01 passes. |
| **M2 Sensor** (12–15) | SEN-001..007 verified; CSV and sidecar contract (§8) verified. |
| **M3 Estimator** (16–20) | EST-001..013 verified; VV-EST-01 passes; VAL-04 cross-check agrees. |
| **M4 Analysis** (21–23) | ANA-001..005 verified; VAL-02 and VAL-03 recorded on held-out seeds. |
| **M5 Hardening** (24–26) | Sanitizers clean; traceability gate on; clang job green; coverage reported. |
| **M6 Release** (27–30) | README complete (DOC-001); VAL-01, 05, 06, 07, 08 recorded; baseline tagged. |

**Definition of done (any change):** builds warning-free, all tests pass, new behavior has a test citing a requirement ID, interface documents updated if an interface changed, committed with a clear message.

### 6.8 CI pipeline

```text
push / PR ─▶ configure (Ninja, pinned deps) ─▶ build GCC 13 (-Werror) ─▶ ctest (JUnit)
          ─▶ pytest (venv, pinned) ─▶ traceability gate ─▶ build Clang 18 ─▶ ASan+UBSan job
          ─▶ coverage report (goal) ─▶ upload JUnit, plot.png, metrics.json, matrix as artefacts
```
CI commands are identical to the README's. If the README and CI diverge, SYS-001 fails.

---

## 7. Design

### 7.1 Architecture

```text
┌──────────────────────────── sim (executable) ────────────────────────────┐
│ main.cpp: parse flags ─▶ Config ─▶ validate ─▶ run ─▶ write ─▶ exit code │
└───────────────────────────────┬──────────────────────────────────────────┘
                                ▼
┌─────────────────────────── simcore (library) ────────────────────────────┐
│                                                                          │
│   Dynamics ──TrueState──▶ Runner ──TrueState (const&)──▶ ISensor         │
│                             │  ◀── optional<Measurement> ────┘           │
│                             │                                            │
│                             ├──Measurement only──▶ IEstimator (Kalman)   │
│                             │  ◀──────────── Estimate ───────┘           │
│                             └──all of the above──▶ Recorder ──▶ CSV      │
│                                                    ConfigWriter ─▶ JSON  │
└──────────────────────────────────────────────────────────────────────────┘
      TrueState never crosses into IEstimator. That is enforced by types.

python/analyze.py: CSV + sidecar ─▶ validate ─▶ metrics.json + plot.png
tools/trace.py:    tags + JUnit  ─▶ traceability matrix
```

### 7.2 Design drivers and constraints
Time (30 days), learner comprehension (every line must be explainable), determinism, testability (fakes for every component), and honesty about fidelity. Constraints: C++17, standard library only in `simcore`, hand-written 2×2 matrices, Linux, CMake.

### 7.3 Components

| Component | Responsibility | Inputs | Outputs | State owned |
|---|---|---|---|---|
| **Dynamics** | Compute the true state at step k | previous `TrueState`, `DynamicsConfig`, step index k | `TrueState` | None (pure function) |
| **Sensor** (`ISensor`) | Decide if a measurement is due at step k; if so, produce a noisy position reading | `const TrueState&`, step index | `std::optional<Measurement>` | Seeded RNG, config |
| **Estimator** (`IEstimator`, Kalman) | Maintain estimate and covariance | `Measurement`, `dt` | `Estimate` | `x̂`, `P`, initialized flag, last time |
| **Runner** | Own the time loop and the call order (RUN-001) | Config, the three components above | Stream of rows to Recorder | Step counter only |
| **Recorder / ConfigWriter** | Serialize rows and the effective configuration | Rows, config | CSV and JSON files (atomic) | Open file handle |
| **CLI front end** | Parse flags, validate, map errors to exit codes | `argv` | Config, exit code | None |
| **Analysis** | Validate CSV, compute metrics, plot | CSV, sidecar | `metrics.json`, `plot.png` | None |

### 7.4 Behavior

**Runner sequence (resolves CR-01, CR-03):**
```text
validate(config)
truth = initial_state(config)                          # step 0, t = 0
for k in 0..N:
    if k > 0:  truth = propagate(truth, dyn_cfg, k)    # t = k * dt, never accumulated
    meas = sensor.observe(truth, k)                    # optional; sensor owns the schedule
    if not estimator.initialized():
        if meas: estimator.initialize(*meas)           # x̂ = [z, 0], P = P0, NO predict
    else:
        estimator.predict(dt)
        if meas: estimator.update(*meas)
    recorder.write_row(k, truth, meas, estimator.estimate_if_initialized())
recorder.commit()                                      # atomic rename (OUT-004)
```

**Estimator state machine:**
```text
 [Uninitialized] ──initialize(meas)──▶ [Tracking] ◀──┐
       │                                   │  predict(dt), update(meas)
       └── predict / update ──▶ error      └──────────┘   (rejected inputs leave state unchanged)
```

### 7.5 Algorithms

**Truth** (explicit Euler): `x_k = x_{k-1} + v_{k-1}·dt`, `v_k = v_{k-1} + a·dt`, `t_k = k·dt`. For `a = 0` this is exact.
**Sensor:** `z = x_true + N(0, σ²)` from `std::mt19937_64(seed)` and `std::normal_distribution`. σ = 0 returns `x_true` exactly (no RNG draw affects the value).
**Kalman filter** (state `[x, v]`, measure `x`):

```text
F = [[1, dt], [0, 1]]     H = [1, 0]     R > 0
Q = q · [[dt³/3, dt²/2], [dt²/2, dt]]          (q has units m²/s³)
predict:  x̂⁻ = F x̂            P⁻ = F P Fᵀ + Q
update:   S = H P⁻ Hᵀ + R     K = P⁻ Hᵀ / S
          x̂ = x̂⁻ + K (z − H x̂⁻)
          P = (I − K H) P⁻ (I − K H)ᵀ + K R Kᵀ        (Joseph form, EST-011)
```

### 7.6 Design decisions

| ID | Decision | Alternatives considered | Rationale | Resolves |
|---|---|---|---|---|
| **DD-001** | All logic in `simcore`; `main` only parses and calls. | Logic in `main` | Testability (TST-001); lets the test framework change without touching production code. | |
| **DD-002** | `ISensor::observe(const TrueState&, int64 step) → optional<Measurement>`: the sensor owns the sampling schedule. | Runner decides which steps to sample | Matches SEN-002 wording; fakes can control cadence; the runner does not need to know M. | CR-03 |
| **DD-003** | Estimator has explicit `initialize`, `predict`, `update`, `initialized`, and rejects calls in the wrong state. | Auto-initialize inside `update` | Makes the step-0 rule explicit and testable (EST-009). | CR-01 |
| **DD-004** | Hand-written `Vec2`, `Mat2` value types. | Eigen | D6: smaller, fully explainable, no dependency (NFR-002). | CR-10 |
| **DD-005** | RNG is `std::mt19937_64` seeded by config and passed to the sensor by value. | Global RNG; `rand()` | NFR-003. `std::normal_distribution` is implementation-defined (D5), so tests use bounds. | CR-18 |
| **DD-006** | Truth uses explicit Euler by default; `t = k·dt`. | RK4; closed form | Guide days 8–11 start with Euler. RK4 equals Euler for constant velocity, so it is deferred. | CR-16 |
| **DD-007** | Library errors are exceptions (`std::invalid_argument`) thrown before any state change. `main` catches them and maps to exit codes. No exceptions for normal control flow. | Error codes; `std::expected` (C++23) | Simple; strong exception guarantee gives "state unchanged" (EST-013). | CR-05 |
| **DD-008** | Config structs with `validate()`; hand-written flag parser. | `getopt`, CLI11 | No dependency; flag set is small (§8.3). | CR-23 |
| **DD-009** | Sidecar is a flat JSON written by a tiny hand-written writer. Python reads it with the standard `json` module. | YAML; TOML; JSON library | No dependency; flat key/value is enough. | CR-13 |
| **DD-010** | CMake option `SIM_TEST_FRAMEWORK`, default `gtest`. GoogleTest acquired by one pinned method **[DECIDE: `FetchContent` at a pinned tag, or the system package]**. | Catch2 first | GoogleTest is the most common in job postings (D1). | CR-09 |
| **DD-011** | Python tools run from a virtual environment with a pinned `requirements.txt`; `analyze.py` is importable and has a CLI. | System Python | Reproducibility; this machine lacks pytest, pandas, matplotlib. | CR-17 |
| **DD-012** | A separate Python reference implementation recomputes estimates from the CSV for cross-checking (VAL-04). | Trust the C++ only | Independent oracle (R-04). | CR-07 |

### 7.7 Data dictionary

| Type | Fields | Notes |
|---|---|---|
| `TrueState` | `t_s`, `position_m`, `velocity_mps` | Owned by Runner. Never given to the estimator. |
| `Measurement` | `t_s`, `position_m`, `sensor_id` | No velocity (SEN-001). |
| `Estimate` | `t_s`, `position_m`, `velocity_mps`, `P` (`Mat2`) | `P` symmetric, non-negative diagonal (EST-006). |
| `DynamicsConfig` | `dt_s`, `steps`, `x0_m`, `v0_mps`, `accel_mps2` | Validated by SIM-006. |
| `SensorConfig` | `sigma_m`, `every_n_steps`, `seed`, `sensor_id` | Validated by SEN-007. |
| `EstimatorConfig` | `q_m2ps3`, `r_m2`, `p0_pos_m2`, `p0_vel_m2ps2` | Validated by EST-010. |

### 7.8 Directory layout (reconciles guide §5 and REQ §8)

```text
sensor-sim/
├── CMakeLists.txt                  # option SIM_TEST_FRAMEWORK (default gtest)
├── README.md   LICENSE   .gitignore
├── .github/workflows/ci.yml
├── include/simulator/              # state.hpp, config.hpp, dynamics.hpp, sensor.hpp,
│                                   #   estimator.hpp, runner.hpp, recorder.hpp, mat2.hpp
├── src/                            # simcore sources; main.cpp
├── tests/
│   ├── CMakeLists.txt
│   ├── support/                    # framework-neutral helpers and fakes
│   ├── gtest/                      # primary adapter (catch2/ is a stretch goal)
│   └── system/                     # pytest black-box tests
├── python/                         # analyze.py, requirements.txt (pinned)
├── tools/                          # trace.py
├── docs/                           # requirements.md, architecture.md, learning-notes.md, this baseline
└── data/                           # small example output only
```

---

## 8. Interfaces

### 8.1 Interface inventory

| ID | From → To | Kind | Contract | Verified by |
|---|---|---|---|---|
| **IF-01** | User → `sim` | Command line | §8.3 | CFG-001, CFG-002 |
| **IF-02** | `sim` → User | Exit code, stderr | §8.6 | CFG-002 |
| **IF-03** | Runner → Dynamics | C++ function | §8.2 | SIM tests |
| **IF-04** | Runner ↔ `ISensor` | C++ interface | §8.2 | SEN tests, RUN-001 |
| **IF-05** | Runner ↔ `IEstimator` | C++ interface | §8.2, EST-002 | EST tests, RUN-001 |
| **IF-06** | Runner → Recorder | C++ interface | §8.2 | OUT tests |
| **IF-07** | `sim` → `analyze.py` | CSV file | §8.4 | OUT-001, ANA-001 |
| **IF-08** | `sim` → `analyze.py` | Sidecar JSON | §8.5 | OUT-003 |
| **IF-09** | `analyze.py` → User | `metrics.json`, `plot.png` | §8.7 | ANA-002..005 |
| **IF-10** | pytest → `sim` | Process, flags, files | IF-01, IF-02, IF-07 | TST-008 |
| **IF-11** | Build → Test framework | CMake option, CTest, JUnit | §8.8 | TST-002..004 |
| **IF-12** | Repository → CI | Workflow file | §6.8 | TST-009 |

### 8.2 C++ interfaces (header-level sketch; names tentative)

```cpp
namespace sim {

struct TrueState   { double t_s; double position_m; double velocity_mps; };
struct Measurement { double t_s; double position_m; std::string sensor_id; };   // no velocity
struct Estimate    { double t_s; double position_m; double velocity_mps; Mat2 P; };

// IF-03: pure function. k is the index of the NEW state; t = k * dt (SIM-002).
TrueState propagate(const TrueState& prev, const DynamicsConfig& cfg, std::int64_t k);

// IF-04: the sensor owns the schedule (DD-002). Truth is const (SEN-006).
class ISensor {
public:
    virtual ~ISensor() = default;
    virtual std::optional<Measurement> observe(const TrueState& truth, std::int64_t step) = 0;
};

// IF-05: no overload accepts TrueState (EST-002, SYS-002).
class IEstimator {
public:
    virtual ~IEstimator() = default;
    virtual bool      initialized() const = 0;
    virtual Estimate  initialize(const Measurement& first) = 0;   // EST-009: no predict
    virtual Estimate  predict(double dt_s) = 0;                   // throws if uninitialized
    virtual Estimate  update(const Measurement& z) = 0;           // throws on non-finite (EST-013)
};

// IF-06
class IRecorder {
public:
    virtual ~IRecorder() = default;
    virtual void write_row(std::int64_t step, const TrueState&,
                           const std::optional<Measurement>&,
                           const std::optional<Estimate>&) = 0;
    virtual void commit() = 0;       // atomic rename (OUT-004)
};
}  // namespace sim
```

### 8.3 Command-line interface (IF-01)

| Flag | Unit | Type and rule | Default |
|---|---|---|---|
| `--steps` | steps | integer 0 to 100000 (CR-25) | 1000 |
| `--dt` | s | finite > 0 | 0.1 |
| `--x0` | m | finite | 0 |
| `--v0` | m/s | finite | 10 |
| `--accel` | m/s² | finite | 0 |
| `--meas-every` | steps | integer ≥ 1 | 5 |
| `--sigma` | m | finite ≥ 0 (sensor's **true** noise) | 5 |
| `--seed` | – | unsigned 64-bit | 42 |
| `--sensor-id` | – | non-empty string, no commas | `pos0` |
| `--est-q` | m²/s³ | finite ≥ 0 | 0.1 |
| `--est-r` | m² | finite > 0 (**independent of `--sigma`**, CFG-003) | 25 |
| `--est-p0-pos` | m² | finite ≥ 0 | 25 |
| `--est-p0-vel` | m²/s² | finite ≥ 0 | 100 |
| `--out` | path | writable path; the sidecar is `<out>.config.json` | `run.csv` |
| `--help` | – | prints every flag with unit and default | – |

### 8.4 Output CSV contract (IF-07), `schema_version = 1`

| Property | Value |
|---|---|
| Encoding, line ending, delimiter | UTF-8 without BOM, `\n`, comma |
| Header (exact, in order) | `step,t_s,true_pos_m,true_vel_mps,meas_pos_m,est_pos_m,est_vel_mps,est_pos_var_m2,est_vel_var_m2s2` |
| Rows | N + 1, `step` = 0..N ascending, no gaps (SIM-005) |
| Numbers | 17 significant digits (OUT-002); `.` decimal separator; no thousands separators |
| Missing values | Empty field. `nan`, `inf` never appear (OUT-005) |
| `meas_pos_m` | Empty on steps with no measurement |
| `est_*` | Posterior at that step: after predict and, if a measurement existed, after update. Empty before the estimator is initialized (EST-009) |
| `est_pos_var_m2`, `est_vel_var_m2s2` | `P[0][0]` and `P[1][1]`; the covariance cross term is not recorded in v1 **[DECIDE: add `est_cov_pv_m2ps` if needed]** |

### 8.5 Sidecar JSON contract (IF-08), file `<out>.config.json`

Flat object. Required keys: `schema_version` (integer), `steps`, `dt_s`, `x0_m`, `v0_mps`, `accel_mps2`, `meas_every`, `sigma_m`, `seed`, `sensor_id`, `est_q_m2ps3`, `est_r_m2`, `est_p0_pos_m2`, `est_p0_vel_m2ps2`, `compiler`, `source_revision` (string or `null`).

An estimator key (`est_*`) is `null` when the estimator in use has no such parameter (the M0/M2 stand-in), so the key set is the same in every `schema_version` 1 file (CR-25).

### 8.6 Exit codes and messages (IF-02)

| Exit code | Meaning |
|---|---|
| 0 | Success. CSV and sidecar written. |
| 1 | Runtime or I/O failure. No CSV left behind (OUT-004). |
| 2 | Usage or configuration error. Nothing written. |

Error text goes to stderr as `sim: error: <parameter>: <reason>`. Normal output goes to stdout only when requested.

### 8.7 Metrics JSON contract (IF-09)

`schema_version`, `n_rows`, `n_measurements`, `rmse_meas_pos_m`, `rmse_est_pos_m`, `rmse_est_vel_mps`, `improvement_ratio` (= est ÷ meas), `frac_pos_within_2sigma`. All RMSEs are computed over rows that have a measurement (ANA-002).

### 8.8 Build and test interface (IF-11)

CMake option `-DSIM_TEST_FRAMEWORK=gtest` (default). `ctest --output-on-failure` is the one documented test command. JUnit XML is written under `build/test-reports/`. System tests are registered with CTest through a wrapper test that runs `pytest` with `--junitxml`.

### 8.9 Interface change control
Any change to §8.3–§8.7 requires: update this section, bump `schema_version` if the CSV, sidecar or metrics shape changes incompatibly (added optional columns at the end are minor; rename, removal or reorder is major), update the affected tests, and note it in the revision history. `analyze.py` shall reject a `schema_version` it does not know (ANA-001). The contract test in CI reads a freshly generated CSV, so drift fails the build rather than a user.

---

# PART B: CHANGE PROPOSALS

## 9. Gaps and discrepancies in the source documents, with proposed changes

Severity: **High** the project could produce a wrong or unverifiable result; **Medium** ambiguity or rework likely; **Low** tidiness. Type: **D** discrepancy between documents, **G** gap, **A** ambiguity.

### 9.1 Summary

| CR | Severity | Type | Title | Resolved in |
|---|---|---|---|---|
| CR-01 | High | D | Step-0 sequencing conflicts with first-measurement initialization | EST-009, RUN-001, §7.4 |
| CR-02 | Medium | D | `propagate` signature differs between documents | §8.2 |
| CR-03 | Medium | A | Who owns the sampling schedule | DD-002 |
| CR-04 | High | G | No estimator configuration validation; "small R" undefined | EST-010, EST-007 |
| CR-05 | Medium | G | No handling of non-finite values | SIM-006, EST-013, OUT-005 |
| CR-06 | High | G | EST-008 can be satisfied by tuning to the test | EST-008, TST-012 |
| CR-07 | High | G | RMSE alone does not prove filter correctness | EST-012, ANA-004, EST-011, DD-012 |
| CR-08 | Medium | A | Sample set for RMSE undefined | ANA-002 |
| CR-09 | Medium | D | Framework scope: guide says one, requirements say four | TST-010, DD-010 |
| CR-10 | Low | D | Linear algebra: library allowed vs hand-written | DD-004 |
| CR-11 | Medium | D | Repository layout differs | §7.8 |
| CR-12 | High | D | Tests and CI scheduled at day 24–26 though CI is a requirement | §6.7 |
| CR-13 | Medium | G | Output metadata, atomic write and blank rules missing or weak | OUT-003/004/005 |
| CR-14 | Medium | G | No traceability tool or per-requirement verification method | TST-011, §6.5 |
| CR-15 | Medium | A | Estimator R coupled to sensor σ | CFG-003 |
| CR-16 | Low | D | Integrator named inconsistently (Euler, RK4, unnamed) | SIM-004, DD-006 |
| CR-17 | Medium | G | Toolchain and Python environment not baselined | NFR-001, NFR-009, DD-011 |
| CR-18 | Low | A | Determinism wording invites golden-file tests | NFR-004 |
| CR-19 | Medium | G | Documentation and honesty requirements live only in the guide | DOC-001/002, SYS-006 |
| CR-20 | Low | G | Time budget and coverage target unclear | NFR-006, NFR-008 |
| CR-21 | Low | G | No document control or baselining | Header, NFR-010 |
| CR-22 | Medium | G | No stakeholder-need or system-requirement layer | §2, §3.2 |
| CR-23 | Medium | G | Command-line contract incomplete | §8.3, §8.6, CFG-002 |
| CR-24 | Medium | G, A | Fixed 1e-9 m position tolerance cannot be met for long or large runs | §6.3, SIM-003, SIM-004 |
| CR-25 | Low | G | Sidecar estimator keys before the Kalman filter exists | §8.5, §8.3 |

Each change request below states: **what it is** (the finding), **what I recommend**, **why**, **what it does**, and **likely outcome** for the system.

---

### CR-01: Step-0 sequencing conflicts with first-measurement initialization
*High · Discrepancy · REQ §3 diagram vs REQ §6 · Affects RUN-001, EST-003*
- **What it is:** The runner diagram calls `Estimator.predict(dt)` at every step, including k = 0. REQ §6 initializes the estimator from the first measurement (`x̂₀ = [first measurement, 0]`). At k = 0 there is no previous state to predict from.
- **Recommend:** Add EST-009 (start uninitialized; initialize on first measurement without predicting), amend RUN-001, and use the sequence and state machine in §7.4.
- **Why:** As written, an implementer must guess. Predicting first would advance the estimate by `dt` beyond the measurement time, a silent bias.
- **What it does:** Removes the ambiguity, makes the rule testable, and also defines behavior if a future sensor misses step 0.
- **Likely outcome:** No bias at the start of runs, a clear unit test, and a smaller risk of the sort of off-by-one-step error that is hard to find later (R-04).

### CR-02: `propagate` signature differs between documents
*Medium · Discrepancy · REQ §3 vs TFW §2 examples · Affects SIM-002/003*
- **What it is:** REQ §3 shows `propagate(truth_{k-1}, dt)`; the TFW examples call `propagate(s, 0.1, k)`. SIM-002 requires `t = k·dt`, which needs `k`.
- **Recommend:** Use `propagate(prev, cfg, k)` (§8.2) and update the REQ §3 diagram.
- **Why:** The k-based form is the only one that satisfies SIM-002 without accumulating time.
- **What it does:** Fixes one function contract for code, tests and diagrams.
- **Likely outcome:** Tests copied from the examples will compile against the real code; no time drift (R-11).

### CR-03: Who owns the sampling schedule
*Medium · Ambiguity · REQ §3 diagram vs SEN-002*
- **What it is:** The diagram shows the runner sampling "only every M steps"; SEN-002 says the sensor produces a measurement every M steps.
- **Recommend:** The sensor owns the schedule: `observe(truth, step) → optional<Measurement>` (DD-002).
- **Why:** Keeps M and cadence inside the component that SEN-002 describes, and lets a fake sensor drive any pattern, including dropouts, in tests.
- **What it does:** Simplifies the runner to one uniform call per step.
- **Likely outcome:** Simpler runner, easier sequencing test (RUN-001), and later extensions (multi-rate sensors) need no runner change.

### CR-04: No estimator configuration validation; "small R" undefined
*High · Gap · EST-005, EST-007 · SEN-007 has no estimator counterpart*
- **What it is:** Sensor config is validated (SEN-007) but estimator config is not. `R = 0` makes the innovation covariance singular when `P⁻₀₀ = 0`; EST-007 says "small R" without a value, and its position-only criterion is met almost immediately.
- **Recommend:** Add EST-010 (validate R, q, P0, dt) and make EST-007 concrete: `R = 1e-6`, position < 1e-3 m **and** velocity < 1e-3 m/s after 10 measurements.
- **Why:** Prototype: position error is 1e-7 m after two measurements, but velocity error is still 5 m/s then and 8.3e-4 m/s after three; the velocity check is what exercises the filter.
- **What it does:** Prevents NaN, division by zero and silent misconfiguration, and turns a vague convergence test into a meaningful one.
- **Likely outcome:** Clear error messages for bad configs, and a convergence test that fails if the velocity update is wrong.

### CR-05: No handling of non-finite values
*Medium · Gap · SIM, EST, OUT*
- **What it is:** Nothing says what happens on NaN or infinity in configuration, measurements or output.
- **Recommend:** SIM-006, EST-013 and OUT-005; errors thrown before any state change (DD-007).
- **Why:** One NaN poisons the covariance permanently and writes unparseable CSV.
- **What it does:** Rejects bad inputs at the boundary and guarantees clean output.
- **Likely outcome:** Failures become loud and local instead of silent and global.

### CR-06: EST-008 can be satisfied by tuning to the test
*High · Gap · REQ §6 ("placeholders to be tuned"), EST-008*
- **What it is:** The filter's parameters are tuned after the estimator runs, then EST-008 checks that the estimate beats the raw measurements, probably on the same seed. This is circular.
- **Recommend:** Quantify EST-008 (ratio ≤ 0.75) and add TST-012: tuning seeds and held-out seeds are disjoint and checked by script.
- **Why:** The prototype shows a ratio of 0.32–0.54 over 200 seeds (max 0.537), so 0.75 leaves about 40 % margin without being trivially weak.
- **What it does:** Separates "chosen to look good" from "performs well on unseen data".
- **Likely outcome:** A defensible statement in interviews ("verified on N unseen seeds") and no flaky failures.

### CR-07: RMSE alone does not prove filter correctness
*High · Gap · ANA-004 (Should), EST-006/008*
- **What it is:** The only performance check is "RMSE improves". A mis-modelled filter can still look acceptable on RMSE. The ±2σ check is only a Should-level plot.
- **Recommend:** Add EST-012 (pooled ±2σ coverage ≥ 0.90), promote the numeric part of ANA-004, add the Joseph form as EST-011 and an independent Python recomputation (DD-012, VAL-04).
- **Why:** Prototype with true acceleration 0.5 m/s²: RMSE 5.10 m vs 5.04 m raw, and coverage 0.45 and mean NEES 5.35. Coverage exposes overconfidence that RMSE only hints at. Reference scenario coverage is 0.975 (conservative, since `q > 0` against a truth with no process noise).
- **What it does:** Tests whether the filter's *claimed* uncertainty is credible, which is the main thing a Kalman filter provides beyond a smoother.
- **Likely outcome:** Real evidence of correctness, an honest documented limit, and a strong interview answer on "how do you know your filter works?".

### CR-08: Sample set for RMSE undefined
*Medium · Ambiguity · ANA-002 vs EST-008*
- **What it is:** EST-008 evaluates "at measurement timestamps", ANA-002 does not say which rows count; est RMSE over all rows and raw RMSE over measurement rows would not be comparable.
- **Recommend:** All RMSEs use rows with a measurement (ANA-002, §8.7).
- **Why:** A like-for-like comparison is the only fair one.
- **What it does:** Fixes one definition for the code, the report and the tests.
- **Likely outcome:** Numbers that match between Python, tests and README.

### CR-09: Framework scope: guide says one, requirements say four
*Medium · Discrepancy · Guide §4 vs REQ §7, TST-002, TST-010*
- **What it is:** The guide says to "select one test framework and use it consistently" and not to build abstractions to show off. REQ §7 and TFW describe four swappable adapters and a CI matrix.
- **Recommend:** GoogleTest as the single required framework; TST-010 demoted to Could; keep the seam (`tests/support/` neutral helpers) so a second adapter stays cheap.
- **Why:** The multi-framework work is real effort (R-02) and the pytest layer already gives framework independence at the system level. The seam is a good design to explain, but building four adapters is not on the critical path.
- **What it does:** Reduces schedule risk while preserving the architectural benefit.
- **Likely outcome:** Same design story in interviews with less to build; Catch2 can be added in a day if time allows.

### CR-10: Linear algebra: library allowed vs hand-written
*Low · Discrepancy · Guide §6 days 16–20 vs NFR-002, D6*
- **What it is:** The guide permits a small vetted library; NFR-002/D6 say hand-written 2×2.
- **Recommend:** Hand-written (DD-004) and amend the guide.
- **Why:** 2×2 is small, a dependency adds build risk, and the learner needs to explain every line.
- **What it does:** Removes a dependency decision.
- **Likely outcome:** Smaller build, fully explainable maths.

### CR-11: Repository layout differs
*Medium · Discrepancy · Guide §5 vs REQ §8*
- **What it is:** Different file names (`sensor_tests.cpp` vs per-framework directories; `state.hpp` vs `dynamics.hpp`) and test directory structure.
- **Recommend:** Adopt the layout in §7.8.
- **Why:** One structure is needed before the first commit; moving files later churns history.
- **What it does:** Combines guide names with REQ's test architecture.
- **Likely outcome:** A clean initial commit and no layout rework.

### CR-12: Tests and CI scheduled at day 24–26 though CI is a requirement
*High · Discrepancy · Guide §6 vs TST-009, NFR-001*
- **What it is:** The guide builds the estimator before establishing tests and CI, but this baseline requires tests that cite requirements and CI on every push.
- **Recommend:** Shift left: a walking skeleton with a green CI by day 5 (M0, §6.7).
- **Why:** Late integration is the classic way a schedule slips (R-01, R-09). Build plumbing problems are cheapest to find when there is almost nothing to build.
- **What it does:** Provides a working pipeline that every later feature drops into.
- **Likely outcome:** Continuous evidence of progress, no end-of-sprint integration crunch, and CI red/green status from the first week.

### CR-13: Output metadata, atomic write and blank rules missing or weak
*Medium · Gap · OUT-003 (Should), CFG-002*
- **What it is:** CFG-002 requires "no partial output file" but nothing says how; the config sidecar is only a Should; there is no schema version or build info; missing-value representation is only partly defined.
- **Recommend:** Promote OUT-003, add OUT-004 (temp file and rename) and OUT-005 (empty means missing; never `nan`).
- **Why:** Reproducibility (SYS-003) needs the exact configuration and seed; interface stability (R-10) needs a version.
- **What it does:** Makes every run self-describing and failures clean.
- **Likely outcome:** Anyone can re-run any CSV exactly; Python can reject incompatible files instead of misreading them.

### CR-14: No traceability tool or per-requirement verification method
*Medium · Gap · TST-005*
- **What it is:** TST-005 says every test cites a requirement "so a matrix can be generated", but nothing generates or enforces it; requirements have acceptance checks but no declared method (T/A/I/D).
- **Recommend:** TST-011 (generated matrix with CI gate) and the RVCM in §6.5.
- **Why:** Two-way traceability is the main habit aerospace reviewers look for (TFW §4.1); it only has value if it is checked automatically.
- **What it does:** Finds untested requirements and orphan tests.
- **Likely outcome:** A concrete artefact to show in interviews and a guard against silent coverage gaps.

### CR-15: Estimator R coupled to sensor σ
*Medium · Ambiguity · REQ §6 (R = 25 = σ²), CFG-001*
- **What it is:** The reference scenario sets `R` equal to `σ²`; the flags do not say whether they are independent.
- **Recommend:** CFG-003: independent flags (`--sigma` for truth, `--est-r` for the filter).
- **Why:** In a real system the filter's assumed noise is never exactly the true noise. Independence lets the project test mismatch (S-WRONG-R).
- **What it does:** Makes a realistic class of test possible.
- **Likely outcome:** An honest demonstration of filter sensitivity and a better limitations section.

### CR-16: Integrator named inconsistently
*Low · Discrepancy · Guide §6 days 8–11, SIM-004*
- **What it is:** The guide mentions Euler then RK4; SIM-004's tolerance depends on "the integrator" without naming it.
- **Recommend:** Euler for v1 with a stated error bound `½·|a|·t·dt`; RK4 deferred.
- **Why:** For constant velocity RK4 equals Euler, so it adds nothing to show; the bound is exact in this case (measured 5.000000 m for a = 1).
- **What it does:** Makes SIM-004 a precise, checkable statement.
- **Likely outcome:** A clean teaching point about integration error without extra code.

### CR-17: Toolchain and Python environment not baselined
*Medium · Gap · NFR-001*
- **What it is:** NFR-001 names GCC 13 and "Clang" without versions. A check of the development machine on 2026-10-10 found GCC 13.3.0, Clang 18.1.3, CMake 3.28.3, Ninja 1.11.1, Python 3.12.3, Podman 4.9.3 and numpy, but **no** pytest, pandas, matplotlib or gcovr, and GCC 13 does not support `-fcondition-coverage` (added in GCC 14).
- **Recommend:** Name the versions in NFR-001, add NFR-009 (pinned dependencies), and use a virtual environment (DD-011).
- **Why:** Reproducibility starts with knowing what you build on. The missing Python packages would otherwise be found at the moment they block progress.
- **What it does:** Turns an unknown environment into a documented one.
- **Likely outcome:** No first-week surprises, and a README that matches reality.

### CR-18: Determinism wording invites golden-file tests
*Low · Ambiguity · SEN-004, NFR-004, D5*
- **What it is:** "Byte-identical on the same platform" is correct, but a committed expected CSV would pass on the laptop and fail in CI, because `std::normal_distribution` differs across standard libraries.
- **Recommend:** NFR-004 amendment: no golden CSVs; compare two runs on the same machine.
- **Why:** Prevents a test that is brittle by design.
- **What it does:** Keeps determinism tests meaningful.
- **Likely outcome:** Tests that pass wherever the code is correct.

### CR-19: Documentation and honesty requirements live only in the guide
*Medium · Gap · Guide §9, §11 vs REQ*
- **What it is:** README contents, limitations and "no claim of flight qualification" appear in the guide and one out-of-scope bullet in REQ, but are not requirements, so they are not verified.
- **Recommend:** SYS-006, DOC-001, DOC-002 and a claim-to-evidence table (VAL-07).
- **Why:** The project's value is its credibility; unverifiable claims are the main way to lose it (R-13).
- **What it does:** Puts documentation under the same discipline as code.
- **Likely outcome:** A README that survives a skeptical reader.

### CR-20: Time budget and coverage target unclear
*Low · Gap · NFR-006, NFR-008*
- **What it is:** The 30 s limit does not say whether ensemble tests count; coverage has no target.
- **Recommend:** Ensemble tests count; coverage goal ≥ 90 % line on `simcore`, reported not gated.
- **Why:** A gate on coverage invites low-value tests; a reported goal is honest.
- **What it does:** Clarifies two numbers.
- **Likely outcome:** Fast feedback loop kept; coverage used as a diagnostic.

### CR-21: No document control or baselining
*Low · Gap · All three documents*
- **What it is:** No document IDs, revision history or baseline marks; REQ says "DRAFT v0.1" only.
- **Recommend:** Header and revision history as in this document; NFR-010 (tag baselines).
- **Why:** Changes to requirements must be traceable to avoid arguing later about what was agreed.
- **What it does:** Gives each decision a date and a version.
- **Likely outcome:** Simple, defensible history.

### CR-22: No stakeholder-need or system-requirement layer
*Medium · Gap · REQ §4*
- **What it is:** All requirements are component-level; there is nothing to check completeness against.
- **Recommend:** §2.2 needs and §3.2 SYS requirements, with parent links.
- **Why:** Without needs you can verify a system that nobody asked for.
- **What it does:** Provides the top of the traceability chain and the basis for validation.
- **Likely outcome:** Every requirement answers "why does this exist?" and validation has something to test against.

### CR-23: Command-line contract incomplete
*Medium · Gap · CFG-001, CFG-002*
- **What it is:** REQ lists no flag names for the estimator, no default output path, no sidecar naming, no exit-code scheme, no error format.
- **Recommend:** §8.3 and §8.6; CFG-002 amended.
- **Why:** pytest system tests (TST-008) and users need a stable interface to code against.
- **What it does:** Fixes names, units, defaults and failure behavior.
- **Likely outcome:** Black-box tests that survive refactoring and a `--help` that is itself tested.

### CR-25: Sidecar estimator keys before the Kalman filter exists
*Low · Gap · §8.5 · Raised and approved 2026-10-19 (record: `docs/change-requests/CR-25-sidecar-null-estimator-keys.md`)*
- **What it is:** §8.5 requires four estimator keys whose values do not exist until M3.
- **Recommend:** Write them as `null` until then.
- **Why:** One key set for `schema_version` 1 across M2 and M3, and no stand-in flags.
- **What it does:** Adds one sentence to §8.5; also syncs the §8.3 `--steps` range with the cap.
- **Likely outcome:** A complete, stable sidecar from M2 onward.

### CR-24: Fixed 1e-9 m position tolerance cannot be met for long or large runs
*Medium · Gap and Ambiguity · SIM-003, SIM-004, §6.3 · Raised and approved 2026-10-19 (full record: `docs/change-requests/CR-24-position-rounding-allowance.md`)*
- **What it is:** Floating-point rounding grows with the number of steps and the size of the position, so a fixed 1e-9 m cannot hold across the run lengths the program accepts (it failed 52 of 120 measured cases, and no double can meet it beyond about 8.4e6 m). SIM-003 was already limited to 1000 steps; SIM-004 was not.
- **Recommend:** One shared tolerance in §6.3, `max(1e-9 m, 2·k·u·X)`, referenced by SIM-003 and SIM-004.
- **Why:** A requirement that cannot be met forces a silent deviation or a test that disagrees with the requirement it cites.
- **What it does:** Keeps 1e-9 m for small runs and scales for large ones, stated once for reuse.
- **Likely outcome:** SIM-003 and SIM-004 verifiable across the whole input range (0 of 120 cases fail); no production code change.

---

# PART C: RATIONALE ANNEX

## 10. The six baseline items: recommendation, rationale, definition, function and outcome

### 10.1 Requirements

| | |
|---|---|
| **What I recommend** | Keep REQ v0.1's component requirements, add a system-level layer (SYS-001..006) above them, apply the change set in §3.3, and make every requirement testable with a declared verification method. Keep Musts few and precise; push everything else to Should or Could. |
| **Why** | The existing requirements are already well written and mostly testable. What is missing is the top of the chain (nothing says why the system exists), some quantification (the "small R" and "RMSE improves" criteria), and handling of bad inputs. Fixing those costs hours now and prevents rework later. |
| **What it is** | A set of numbered, testable statements about what the system must do and be, each with a priority, a parent need and a verification method. It is the contract between the owner and the build. |
| **What it does** | Defines done. It tells the implementer what to build, tells the tester what to check, and tells a reviewer what was promised. Priorities (MoSCoW) tell the owner what to cut first when time runs short. |
| **Likely outcome in the greater system** | Requirements are the root of every other artefact here: risks come from them, validation checks the needs behind them, tests verify them, design allocates them, interfaces carry them. A tight set makes the whole 30-day plan achievable and explainable; a loose set would leave the estimator unspecified exactly where bugs hide (initialization, validation, tuning). |

### 10.2 Risk

| | |
|---|---|
| **What I recommend** | Adopt the register in §4 and review it weekly. Treat R-01 (schedule) and R-03 (comprehension) as the top two risks, above any technical risk, and let them drive the plan: skeleton and CI first, hand calculation before code. |
| **Why** | The project's technical risk is low because the maths is small and well known; the prototype matched expectations on the first run. The dominant risks are human and schedule: an empty `Project/` directory, a learner who must be able to explain every line, and a parallel job search. |
| **What it is** | A structured list of things that could prevent the project from meeting its needs, each scored (likelihood × impact), with a mitigation strategy, a trigger and a link to the requirement or change that addresses it. |
| **What it does** | Makes uncertainty visible and actionable. The triggers tell the owner when to change course (for example, "no green CI by day 7"), and the mitigations are already built into requirements and milestones. |
| **Likely outcome in the greater system** | Several risks are retired by design before any code is written: scope creep (TST-010 demoted), false confidence (TST-012), interface drift (schema version), environment surprises (venv, pinned deps). The remaining risks are monitored rather than discovered late. It also gives the owner an authentic, concrete answer to "what was the biggest risk and what did you do about it?" |

### 10.3 Validation

| | |
|---|---|
| **What I recommend** | Run eight validation activities (VAL-01..08), including an independent Python recomputation of the estimates (VAL-04) and a deliberate scenario sweep that documents where the filter fails (VAL-05). Include comprehension and claim accuracy as validation, not just the numbers. |
| **Why** | Verification only shows the code matches the requirements. If the requirements are wrong or the claims overstated, a fully verified system can still be the wrong deliverable. For a portfolio project the "customer" is a skeptical reviewer, so validation includes their questions. |
| **What it is** | Evidence that the finished system satisfies the stakeholder needs in §2.2, using criteria and scenarios that are independent of the implementation. |
| **What it does** | Answers "is this the right thing, and is it honest?" It generates the numbers that go in the README (RMSE ratio, coverage), the limitations section (the 0.5 m/s² failure) and the interview story. |
| **Likely outcome in the greater system** | The prototype already supplies baselines (ratio 0.32–0.54, coverage 0.975, mismatch failure) so thresholds are evidence-based. VAL-04 gives a second implementation that catches maths errors in either. The scenario sweep converts a weakness (constant-velocity assumption) into a demonstrated understanding of the model's limits, which is what engineers at this level are expected to show. |

### 10.4 Verification

| | |
|---|---|
| **What I recommend** | Use a layered plan (unit, integration, system, SIL, static), independent oracles (hand-computed vectors, analytic solutions, Python recomputation), a stated tolerance policy, a generated traceability matrix with a CI gate, and one required C++ framework (GoogleTest) plus pytest. |
| **Why** | The system is small enough that tests can be fast and deterministic, and random components can be tested honestly with fixed seeds and statistical bounds. Traceability is the habit aerospace reviewers value (TFW §4.1) and costs little if automated. Limiting to one required framework protects the schedule (R-02). |
| **What it is** | The planned set of tests, analyses, inspections and demonstrations (§6.5), the tolerances they use, the pipeline that runs them (§6.8) and the criteria for finishing each milestone (§6.7). |
| **What it does** | Proves, requirement by requirement, that the build does what the requirements say, and detects regressions on every push. |
| **Likely outcome in the greater system** | A green CI badge, a generated matrix showing every Must verified, and a measured baseline for each numeric claim. Together with validation, it supports statements of the form "verified against requirement X by test Y" rather than "it seems to work". Shifting CI to week one means verification grows with the code instead of being bolted on. |

### 10.5 Design

| | |
|---|---|
| **What I recommend** | Keep the single-process, library-plus-thin-executable architecture; make components small value types and interfaces; fix the runner sequence (including initialization), the sensor-owns-schedule rule, hand-written 2×2 maths, exceptions thrown before state change, and the layout in §7.8. |
| **Why** | Each choice either removes an ambiguity found in the documents (CR-01, 02, 03) or reduces schedule and comprehension risk (hand-written maths, no dependencies). The architecture also matches the way the project will be explained: truth, sensor, estimator, analysis, with truth kept away from the estimator by types. |
| **What it is** | The structure of the software: components and their responsibilities, how data and control flow between them, the algorithms, and the recorded decisions with alternatives and reasons (DD-001..012). |
| **What it does** | Turns requirements into something buildable and testable, and records *why* so the choices can be defended or revisited. The design makes the "estimator never sees truth" rule structural, and gives fakes a place to plug in. |
| **Likely outcome in the greater system** | A codebase small enough to read in an afternoon and explain line by line. The same structure is the natural seed for the "distributed" future: the interfaces already look like message contracts, so moving a component behind a network later would change transport, not logic. |

### 10.6 Interfaces

| | |
|---|---|
| **What I recommend** | Treat the command line, the CSV, the sidecar JSON, the metrics JSON, exit codes and the C++ component interfaces as controlled contracts (§8), versioned with `schema_version`, tested by a contract test in CI, and changed only through the rule in §8.9. |
| **Why** | The two biggest integration seams are C++ to Python (a file) and test to program (a process). Both are text contracts that can drift silently. Making them explicit and tested is the cheapest way to avoid integration failures and rework (R-10). |
| **What it is** | The precise definition of every boundary where one part hands something to another: names, units, types, ordering, defaults, error behavior, and who owns each. |
| **What it does** | Lets each side be built, tested and replaced independently. It is also what lets the pytest system tests stay unchanged when the C++ test framework changes. |
| **Likely outcome in the greater system** | Components can be developed in any order, Python and C++ cannot disagree unnoticed, and the sidecar plus version number mean any CSV can be reproduced and read years later. It is also the document that would let a second person write a compatible analyzer or sensor without reading the code. |

---

# APPENDICES

## 11. Appendices

### 11.1 Appendix A: Prototype evidence (2026-10-10)

A throwaway Python prototype (not part of the repository) implemented the reference scenario (REQ §6) with the equations in §7.5 and ran it. It uses Python's random generator, so numbers will differ slightly from C++; thresholds must be re-measured on the real implementation **[TBD]**. Proposed use: keep a cleaned-up copy as the independent oracle (DD-012).

| Measurement | Result |
|---|---|
| Raw measurement RMSE, 20 seeds | 4.55 to 5.60 m (mean 5.04) |
| Estimate position RMSE, 20 seeds | 1.69 to 2.68 m (mean 2.05) |
| Ratio estimate ÷ raw, 20 seeds | 0.32 to 0.53 (mean 0.41) |
| Ratio estimate ÷ raw, 200 seeds | maximum 0.537 |
| Velocity RMSE, 20 seeds | mean 1.11 m/s |
| ±2σ coverage, 200 seeds | pooled 0.975; per-seed 0.915 to 1.000 |
| Mean NEES (ideal 1.0) | 0.78 (filter is conservative: `q > 0` but truth has no process noise) |
| Final `P`, seed 1 | `[[4.765, 1.006], [1.006, 0.449]]` |
| Noise-free (σ = 0, R = 1e-6) | After 2 measurements: position error 1e-7 m, velocity error 5.0 m/s. After 3: velocity 8.3e-4 m/s. After 10: 1.8e-11 m, 7.4e-8 m/s |
| Covariance asymmetry after 1000 steps (Joseph form) | 2.2e-16 |
| Euler error, a = 1 m/s², t = 100 s, dt = 0.1 s | 5.000000 m (= ½·a·t·dt) |
| Mismatch, truth accel 0.0 / 0.1 / 0.5 m/s² | Estimate RMSE 2.05 / 2.21 / 5.10 m (raw 5.04); coverage 0.978 / 0.960 / 0.449; NEES 0.78 / 0.92 / 5.35 |

Caveat: the Joseph form showed no measurable benefit over the simple form in this scenario, so EST-011 is Should and justified by theory (guaranteed symmetric positive-semidefinite update), not by an observed failure.

### 11.2 Appendix B: Toolchain observed on the development machine (2026-10-10)

| Tool | Found |
|---|---|
| g++ / gcc | 13.3.0 (Ubuntu 24.04) |
| clang++ | 18.1.3 |
| CMake / Ninja / Make | 3.28.3 / 1.11.1 / 4.3 |
| Git | 2.43.0 |
| Python | 3.12.3, numpy 2.5.2 |
| Podman | 4.9.3 (`docker` is an emulation shim) |
| Missing | pytest, pandas, matplotlib, gcovr |
| Machine | 12 logical CPUs, 15 GB RAM (WSL2) |

### 11.3 Appendix C: Decision register and TBD list (owner action required)

| # | Decision (from REQ §9) | Proposed disposition | Status |
|---|---|---|---|
| D1 | Primary framework and a second | GoogleTest required; Catch2 a Could (TST-010) | Accepted 2026-10-11 |
| D2 | Shared vs per-framework test code | Neutral support plus thin adapters | Accepted 2026-10-11 |
| D3 | Configuration input | CLI flags | Accepted 2026-10-11 |
| D4 | Output shape | One wide CSV plus sidecar JSON | Accepted 2026-10-11 |
| D5 | Cross-platform randomness | Same-platform determinism only; statistical bounds | Accepted 2026-10-11 |
| D6 | Matrix math | Hand-written 2×2 | Accepted 2026-10-11 |
| D7 | C++ standard | C++17 | Accepted 2026-10-11 |

| # | Open item | Owner | Needed by |
|---|---|---|---|
| OI-01 | How to acquire GoogleTest: pinned `FetchContent` tag, or system package (DD-010) | Owner | M0 |
| OI-02 | Re-measure thresholds (0.75, 0.90, S-HIGH-NOISE, S-SPARSE, S-WRONG-R) on the C++ implementation | Owner | M3–M4 |
| OI-03 | Whether to record the covariance cross term in the CSV (§8.4) | Owner | M2 |
| OI-04 | Sprint start date and current day, to confirm milestone dates in §6.7 | Owner | Now |
| OI-05 | Repository name and remote location (R-16) | Owner | M0 |
| OI-06 | Clean up the prototype as the independent oracle and place it in `python/` or `tools/` | Owner | M3 |

### 11.4 Appendix D: Glossary

| Term | Meaning |
|---|---|
| **Baseline** | A reviewed, versioned set of documents that later changes are measured against. |
| **ICD** | Interface Control Document: the exact definition of an interface (here §8). |
| **Innovation** | Difference between a measurement and the filter's prediction of it. |
| **NEES** | Normalized estimation error squared: error² ÷ reported variance. Averages 1.0 for a consistent filter in one dimension. |
| **Oracle** | An independent source of the right answer used to check a result. |
| **RVCM** | Requirements verification cross-reference matrix (§6.5). |
| **SIL** | Software-in-the-loop: software under test run against a simulated environment. |
| **Walking skeleton** | The thinnest complete end-to-end implementation, with every stage present and trivial, used to prove the pipeline before adding real logic. |
