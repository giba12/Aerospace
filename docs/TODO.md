# To do

Status as of 2026-11-05: **M0 to M5 are merged into `master` on GitHub** (PRs #1 to #5, CI green).
M6 (release) is in progress on branch `m6-release`. Source for each item: [systems-engineering-baseline.md](systems-engineering-baseline.md)
(SEB-001), section numbers in brackets. Work top to bottom; do not start a milestone before the
previous one meets its exit criteria (baseline 6.7).

Definition of done for any change: builds warning-free, all tests pass, new behavior has a test
citing a requirement ID, interface docs updated if an interface changed, clear commit message.

## 1. Housekeeping

Verified against GitHub on 2026-11-05.

- [x] **Remote exists.** `origin` is `github.com/giba12/Aerospace` (private).
- [x] **CI has run and is green** on GCC 13 and Clang 18, including on `master` after both merges.
- [x] **VS Code CMake path fixed** (`${workspaceFolder}`, commit `3c0c024`, merged).
- [x] **PRs #1 to #5 (M1 to M5) merged** on 2026-11-05 with merge commits. GitHub returned transient HTTP 500s
      when merging #4; retrying the REST call succeeded and nothing was half-merged. (`gh pr edit` fails on the
      installed `gh` 2.45; retarget a PR with `gh api -X PATCH repos/OWNER/REPO/pulls/N -f base=master`.)
- [x] **Local `master` is in sync with `origin/master`; the old worktree and the M1/M2/review branches are gone.**
- [ ] **Delete the merged branches** `m3-estimator`, `m4-analysis` and `m5-hardening` on GitHub.
- [ ] **Choose a `LICENSE`.** GitHub reports none and no branch contains one. Owner's choice (guide section 5).
- [ ] **Confirm OI-01:** GoogleTest via `FetchContent`, pinned by SHA-256. It is implemented and CI is
      green; this is the formal sign-off (S-1 in `docs/architecture.md`).
- [ ] **Owner decision OI-03:** record the covariance cross term in the CSV? M2 left it out
      deliberately and froze schema version 1, so adding it later is a versioned interface change (baseline 8.9).
- [ ] **Record the sprint start date** (OI-04) so the milestone dates in baseline 6.7 can be confirmed.
- [ ] **Review the baseline.** It is still "0.3 DRAFT, not baselined". When accepted, issue
      `requirements.md` v0.2, regenerate `docs/requirements.csv`, and tag it (NFR-010).

## 2. M1: Truth (SIM-001..006): built and merged (PR #1)

Detail in `docs/M1_REPORT.md` and `docs/change-requests/CR-24-position-rounding-allowance.md`.

- [x] Acceleration in the truth model, `--accel`, VV-SIM-01, the SIM-004 envelope test, size-scaled
      tolerance (CR-24).
- [ ] **Be able to explain, in your own words,** what Euler integration is and why the error is exactly
      zero at a = 0 (the project exists to be explained; R-03).

## 3. M2: Sensor and output contract (SEN-001..007, OUT-003): built and merged (PR #2)

Detail in `docs/M2_REPORT.md` and `docs/change-requests/CR-25-sidecar-null-estimator-keys.md`.

- [x] Seeded noisy sensor, `--sigma`, `--seed`, and the `<out>.config.json` sidecar (16 keys, schema version 1).
- [ ] CFG-003 and the sidecar's estimator keys (currently `null`) wait for M3.
- [ ] **Be able to explain** how a randomized component is tested without golden files (D5, NFR-004).

## 4. M3: Estimator (EST-001..013, CFG-003)

Exit: EST-001..013 verified; VV-EST-01 passes; VAL-04 cross-check agrees.

Built on branch `m3-estimator`; all EST-001..013 have passing tests (48 of 61 Musts covered overall).

- [ ] **Work VV-EST-01 by hand** (R-03). Skipped at the owner's request; the worksheet is still in
      `docs/M3_WORKSHEET.md` and its formulas match the code line for line. Worth doing before an interview.
- [x] Hand-written `Mat2`/`Vec2` arithmetic (D6/DD-004) and `KalmanEstimator` (Joseph form).
- [x] `EstimatorConfig` with validation (EST-010) and the `--est-*` flags; R independent of σ (CFG-003).
- [x] Reject non-finite or out-of-order readings, state unchanged (EST-013).
- [x] EST-003, 004, 006, 007, 009 tests; VV-EST-01 at 1e-9.
- [x] Independent Python oracle in exact arithmetic (OI-06, DD-012, VAL-04), agreeing with the C++ in nine scenarios.
- [x] Thresholds re-measured on the tuning seeds only (OI-02): ratio 0.317 to 0.576 (limit 0.75), coverage 0.975 (limit 0.90).
- [x] Disjoint tuning and held-out seed sets with an automated check (TST-012). EST-008 and EST-012 pass on the 50 held-out seeds.
- [ ] **Decide CR-26** (`docs/change-requests/CR-26-oracle-tolerance.md`): exact oracle plus the size-scaled
      tolerance. The code already uses it; the baseline §6.3 row is unchanged until approved.
- [x] M3 pull request merged (#3).

## 5. M4: Analysis (ANA-001..005)

Exit: ANA-001..005 verified; VAL-02 and VAL-03 recorded on held-out seeds.

Built on branch `m4-analysis` (49 of 61 Musts covered overall).

- [x] matplotlib added to `python/requirements.txt`, pinned (pandas was not needed).
- [x] Unknown `schema_version`, missing or mismatched sidecar rejected (ANA-001).
- [x] ±2σ coverage (ANA-004), `improvement_ratio` and `metrics.json` per baseline 8.7 (ANA-005).
- [x] Labelled three-panel plot with a PNG test (ANA-003); example in `data/`.
- [x] EST-008 and EST-012 acceptance tests run through `python/ensemble.py` on the held-out seeds.
- [x] VAL-02 and VAL-03 recorded on the held-out seeds: `docs/VALIDATION.md`.
- [x] S-HIGH-NOISE, S-SPARSE, S-WRONG-R measured (exploratory, tuning seeds). The baseline still lists them as
      [TBD]; update §5.2 if wanted. **S-SPARSE is a surprise:** coverage holds but the filter helps much less.
- [x] `docs/VALIDATION.md` held-out section regenerated from a clean commit (`731465de771b`); the numbers did not change.
- [x] M4 pull request merged (#4).

## 6. M5: Hardening (NFR-001, 006..008, TST-010, TST-011)

Exit: sanitizers clean; traceability gate on; Clang job green; coverage reported.

Built on branch `m5-hardening` (stacked on `m4-analysis`). All 61 Musts now have a passing test.

- [x] ASan + UBSan: `SIM_SANITIZE` option and a CI job (NFR-007). Full suite clean locally; ASan and UBSan
      each shown to catch planted bugs.
- [x] `--require-coverage` on in CI (TST-011, SYS-005).
- [x] Coverage report with pinned `gcovr` (NFR-008): lines 94.0 %, functions 100 %, branches 85.3 %. Reported, not gated.
- [x] 30 s budget check (`tools/check_budget.py`) in CI (NFR-006). **Local margin is thin (about 25 s).**
- [x] Hidden global state: the compiled library has exactly two constant writable symbols (NFR-003).
- [x] The 12 Musts that had no test are closed (see architecture S-38); `req_trace.py` now fails clearly on bad input.
- [x] Docs: SYS-006 banner added where it was missing.
- [x] First GitHub run of the sanitizer and coverage jobs and of the gate and budget steps: all four jobs
      passed (budget 4.8 s GCC, 13.7 s Clang, of 30 s; coverage on CI: lines 94.5 %, branches 86.7 %).
- [ ] Not built (Could): the Catch2 adapter and CI matrix (TST-010). See architecture S-43.
- [ ] Untested: one error path (a failed final write in `AtomicFile::commit`) needs fault injection.
- [x] M5 pull request merged (#5).

## 7. M6: Release (DOC-001, DOC-002, VAL-01/05/06/07/08)

Exit: README complete; validation recorded; baseline tagged.

- [ ] Replace the README's "expected output" with real output and a real plot; update Limitations
      (it currently says the sensor is exact and the estimator is a passthrough).
- [x] Claim-to-evidence table (VAL-07): `docs/EVIDENCE.md`, checked by `tests/python/test_evidence_table.py`. Building it
      corrected 12 README statements and exposed one untested path (a flag with no value), now tested. The README
      claims only; resume or interview claims are not in the repository and are listed as "not supported" there.
- [x] `Dockerfile` and `.dockerignore` for a clean-room run (SYS-001 / VAL-01): the image builds from a fresh
      copy, runs the whole test suite inside it, then runs the reference scenario. A CI `container` job builds
      and runs it on every push. See architecture S-45 to S-50.
- [ ] Update `docs/architecture.md` to match the final design (DOC-002).
- [ ] Write the S-ACCEL-LARGE limitation: the filter fails at 0.5 m/s² (coverage 0.45).
- [ ] Tag the baseline in git (NFR-010).

## 8. Alongside the project (guide sections 1, 11)

Roughly 30 % of the time. Risk R-14 triggers on any week with zero applications.

- [ ] Applications and outreach: junior software, test, simulation and systems-adjacent roles in the
      Colorado Springs area. Read clearance and citizenship requirements per posting; claim nothing not held.
- [ ] Resume version built from this project's evidence, tailored per posting.
- [ ] Practice the two-minute project explanation and the questions in guide section 11 (why separate
      truth/sensor/estimator, what the filter predicts and corrects, how determinism was achieved, how a
      random component is tested, what would change for a distributed or real system).
- [ ] Coding-interview practice: data structures, readable C++, explaining tradeoffs.

## Deferred on purpose (do not start)

2-D motion, RK4, multiple sensors, an experiment runner, a second estimator, serialization or network
transport, Kubernetes, Kafka, GPU, ML, web UI (guide section 4 and 10). Only after M5 and only if a
specific role or goal calls for it (R-02).
