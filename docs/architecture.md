# Architecture (as built at M0)

The design of record is [systems-engineering-baseline.md](systems-engineering-baseline.md)
sections 7 (design) and 8 (interfaces). This page records only what the code does today and
the choices made while building the skeleton (DOC-002). Update it whenever either changes.

## What exists at M0

| Piece | State |
|---|---|
| `Dynamics` (`propagate`) | Real, constant velocity only. Acceleration is M1 |
| `PassthroughSensor` | Stand-in: exact position every M steps. Seeded noise is M2 |
| `PassthroughEstimator` | Stand-in: repeats the latest reading. Kalman filter is M3 |
| `Runner` | Real: implements the call order of baseline 7.4 exactly |
| `CsvRecorder` | Real: exact header, 17 digits, empty = missing, atomic rename |
| CLI | Real subset: the seven flags the skeleton uses, exit codes 0/1/2 |
| Sidecar JSON (IF-08) | Not built (M2) |
| `analyze.py` | Header check and RMSE. Plot, coverage, metrics JSON are M4 |

## Decisions made while scaffolding

| # | Decision | Alternatives | Why |
|---|---|---|---|
| S-1 | **OI-01:** GoogleTest v1.17.0 via `FetchContent` with a URL and SHA-256 hash | System package; git tag; vendoring | Pinned by content, so the tag cannot move (NFR-009); identical on laptop and CI. **Awaiting owner confirmation** |
| S-2 | The repository root is `aerospace/`; `docs/` was already there | A `sensor-sim/` subfolder; the empty `Project/` folder | Matches the layout in baseline 7.8 with no nesting. `Project/` is left untouched |
| S-3 | `cli_main` lives in `simcore` (`cli.hpp`); `main.cpp` makes one call | Flag parsing in `main.cpp` | Lets tests call the CLI directly (TST-001, DD-001). Adds one header beyond baseline 7.8 |
| S-4 | Flag table drives both parsing and `--help` | Separate help string | The documentation cannot drift from the parser (CFG-001) |
| S-5 | `junit.gtest` re-runs the whole suite once, in addition to per-test discovery | One CTest entry for the binary; CTest's own JUnit output | Per-test listing satisfies TST-003; gtest's XML carries the requirement tags that CTest's does not |
| S-6 | `-Werror` defaults ON | Default OFF, ON only in CI | Baseline NFR-001, and the toolchain is pinned. Easy to turn off locally |
| S-7 | Traceability gate: unknown IDs and orphan tests fail now; uncovered Musts fail only with `--require-coverage` | Gate on from day one | At M0 most Musts are future work; baseline 6.7 turns coverage on at M5 |
| S-8 | Registry `docs/requirements.csv` generated from baseline 6.5 | Parse the markdown at run time | A CSV is stable to parse. Cost: two sources until REQ v0.2 is issued |
| S-9 | `tests/python/` added for unit tests of the Python tools | Put them in `tests/system/` | They are not system tests. One directory beyond baseline 7.8 |
| S-10 | `analyze.py` uses the standard library only; `requirements.txt` pins pytest only | Add pandas/matplotlib now | Nothing imports them yet; add them, pinned, in M4 |
| S-11 | `tools/trace.py` renamed `tools/req_trace.py` | Keep the name | `import trace` shadowed the standard-library `trace` module and only worked because `pytest.ini` puts `tools/` first on the path |
| S-12 | `steps` is bounded above by `kMaxSteps = 100000` in `config.hpp`, checked in `DynamicsConfig::validate()`; `--help` text is built from the constant | No limit; limit only in the CLI | A typo such as `--steps 1000000000000` would run for hours and fill the disk. Checking in `validate()` makes the runner enforce it too (SIM-006). The baseline §8.3 flag table still says "integer ≥ 0" and should be updated at the next baseline revision |
| S-13 | `analyze.py` converts every numeric cell through one helper that raises `CsvFormatError` naming the data row, step and column, and rejects empty, non-numeric and non-finite cells, ragged rows and non-UTF-8 files | Let `float()` raise | A bad file now produces `analyze: error: ...` and exit 1 instead of a traceback |

## Not decided here

No `LICENSE` file was created: the licence is the owner's choice (guide section 5). No git
remote, commit or push was made (OI-05).
