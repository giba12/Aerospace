# Test Frameworks for C++ Simulation Software

A guide for someone coming from web and data development. It covers what a test framework is, five leading options for this project, and what aerospace and defense employers expect.

---

## 1. What is a test framework?

A **test framework** is the scaffolding that lets you write small programs whose only job is to check other programs, then run them all and report what passed and what failed. You already know some: **Jest**, **Mocha**, **pytest**, **JUnit**. The C++ frameworks do the same jobs:

| Job | What it means | Jest equivalent |
|---|---|---|
| **Declare tests** | Name a check and group related checks | `test()`, `describe()` |
| **Assertions** | State what must be true; report *both* values on failure | `expect(x).toBe(y)` |
| **Fixtures** | Shared setup and teardown so each test starts clean | `beforeEach` / `afterEach` |
| **Parameterization** | Run the same test over many inputs | `test.each` |
| **Discovery and running** | Find every test and run it, so one failure doesn't stop the rest | `jest` CLI |
| **Filtering** | Run a subset by name or tag | `jest -t "sensor"` |
| **Reporting** | Human-readable output plus machine-readable output (JUnit XML) for CI | `jest-junit` |
| **Test doubles** | Substitute a fake or mock for a real dependency | `jest.fn()`, `jest.mock()` |

Most of these frameworks descend from **xUnit**: Kent Beck's SUnit for Smalltalk (1990s), then JUnit for Java, then a port in nearly every language. The xUnit family shares the same vocabulary: test case, test suite, fixture, assertion, runner.

### How C++ changes the picture

1. **Tests are compiled.** Your tests become a separate executable that links against your code, which is why TST-001 puts all the logic in a library. There's no `node_modules` magic: the build system (CMake) must be told how to build and link the tests.
2. **No reflection or decorators.** Python can find functions named `test_*` at runtime, but C++ can't inspect itself that way. Every C++ framework therefore uses **macros** (`TEST(...)`, `TEST_CASE(...)`) that expand into code which registers the test in a global list before `main()` runs.
3. **A crash kills everything.** A bad pointer (segfault) terminates the whole test process, not just one test. CTest mitigates this by running each discovered test in its own process.
4. **Floating point needs tolerances.** `0.1 * 3 == 0.3` is false in C++ just as in JavaScript. Every numeric check in this project uses a tolerance: absolute (±1e-9 m), relative (±0.01%) or ULP-based (within a few representable doubles).
5. **Build integration matters as much as syntax.** How the framework is fetched, linked and registered with **CTest** (CMake's test runner) decides whether swapping it is easy. CTest is the layer that lets us swap frameworks (requirements TST-003).

---

## 2. The five frameworks

The first four are C++ unit-test frameworks, and any one of them can sit behind our `SIM_TEST_FRAMEWORK` switch. The fifth, **pytest**, tests the system from the outside. It stays in place whatever C++ framework is chosen, and it is the one closest to your existing experience.

Every example tests the same requirement, **SIM-003** (constant-velocity propagation matches the analytic solution), so you can compare them side by side. `sim::propagate` and `sim::TrueState` are the planned project APIs.

### 2.1 GoogleTest (with GoogleMock)

**What it is:** Google's C++ testing framework, open-sourced in 2008 (BSD-3 license). It is the most widely used C++ test framework and the one most often named in job postings. GoogleMock, its mocking library, ships in the same repository.

```cpp
#include <gtest/gtest.h>
#include "simulator/dynamics.hpp"

TEST(Dynamics, ConstantVelocityMatchesAnalytic) {
    RecordProperty("requirements", "SIM-003");      // appears in the XML report
    sim::TrueState s{/*t_s=*/0.0, /*position_m=*/0.0, /*velocity_mps=*/10.0};
    for (int k = 1; k <= 1000; ++k) s = sim::propagate(s, 0.1, k);
    EXPECT_NEAR(s.position_m, 1000.0, 1e-9);
    EXPECT_NEAR(s.velocity_mps, 10.0, 1e-12);
}
```

**What it does**
- `TEST(Suite, Name)` for plain tests. `TEST_F` for fixture classes, with setup in `SetUp()` and a fresh object for every test.
- Two assertion levels. `EXPECT_*` records the failure and continues. `ASSERT_*` stops the current test.
- Floating-point checks: `EXPECT_NEAR` (absolute tolerance) and `EXPECT_DOUBLE_EQ` (within 4 ULPs).
- Value-parameterized tests (`TEST_P`) and type-parameterized tests.
- **Death tests**, which check that code aborts as expected. Useful for testing guard conditions.
- GoogleMock: `MOCK_METHOD` generates fake implementations of an interface, with expectations such as "called once with these arguments".
- XML output: `--gtest_output=xml:report.xml`. CMake integration: `gtest_discover_tests()`.

**Why it's designed this way**
- Google's C++ style historically banned exceptions, so a failing `ASSERT_*` can't throw. It **returns** from the current function instead. That's why `ASSERT_*` works only in functions that return `void`, and why the non-fatal `EXPECT_*` exists: you see *all* the failures in one run.
- It follows xUnit closely (fixture classes, suites) so developers coming from JUnit feel at home.

**Strengths:** industry default, excellent documentation, the best built-in mocking, runs tests in parallel and shuffled (`--gtest_shuffle`) to catch order dependencies.
**Weaknesses:** more boilerplate than Catch2/doctest, fixture classes feel heavy for small tests, and recent releases require C++17.
**Where you'll see it:** almost everywhere modern C++ is written, including defense contractors' newer ground-software and simulation codebases.

### 2.2 Catch2

**What it is:** an open-source framework started by Phil Nash in 2010 (Boost Software License). It was famous for being a single header. Version 3 became a normal compiled library to speed up builds. It's popular for readable tests with little boilerplate.

```cpp
#include <catch2/catch_test_macros.hpp>
#include <catch2/matchers/catch_matchers_floating_point.hpp>
#include "simulator/dynamics.hpp"
using Catch::Matchers::WithinAbs;

TEST_CASE("constant velocity matches analytic solution", "[dynamics][SIM-003]") {
    sim::TrueState s{0.0, 0.0, 10.0};
    for (int k = 1; k <= 1000; ++k) s = sim::propagate(s, 0.1, k);
    REQUIRE_THAT(s.position_m, WithinAbs(1000.0, 1e-9));
}

TEST_CASE("sensor behaviour", "[sensor]") {
    sim::TrueState truth{2.0, 50.0, 10.0};                 // re-run fresh for EACH section
    SECTION("zero noise returns exact position [SEN-003]") { /* ... */ }
    SECTION("timestamp copied from truth [SEN-005]")       { /* ... */ }
}
```

**What it does**
- Tests are named with free-text strings and **tags** (`[sensor][SEN-003]`). You filter by tag from the command line, which makes requirement IDs easy to carry.
- `REQUIRE` (stop) and `CHECK` (continue). **Expression decomposition**: `REQUIRE(a == b)` prints the actual values of `a` and `b` on failure without needing special macros.
- **SECTIONs**: the setup code at the top of a `TEST_CASE` runs again from scratch for each section. You get fixture-like isolation without writing a class.
- Floating-point matchers: `WithinAbs`, `WithinRel`, `WithinULP`.
- Data generators (`GENERATE`), BDD-style macros (`SCENARIO` / `GIVEN` / `WHEN` / `THEN`) and built-in micro-benchmarking.
- Reporters: console, JUnit, XML, TAP, SonarQube. CMake integration: `catch_discover_tests()`.

**Why it's designed this way:** its author wanted tests to read like specifications, with less ceremony than xUnit. Sections replace fixture classes, and expression decomposition replaces dozens of `ASSERT_EQ`/`ASSERT_LT` variants.
**Strengths:** very readable, flexible tagging, the BDD style reads well next to requirements.
**Weaknesses:** no built-in mocking (pair it with a library such as trompeloeil). Sections are powerful but can confuse people at first.
**Where you'll see it:** open-source projects, game and simulation companies, and teams that value readable tests.

### 2.3 doctest

**What it is:** a lightweight framework by Viktor Kirilov (MIT license), inspired by Catch. It's a single header, and it's designed to compile and run *extremely* fast.

```cpp
#include <doctest/doctest.h>
#include "simulator/dynamics.hpp"

TEST_CASE("constant velocity matches analytic solution"
          * doctest::description("SIM-003") * doctest::test_suite("dynamics")) {
    sim::TrueState s{0.0, 0.0, 10.0};
    for (int k = 1; k <= 1000; ++k) s = sim::propagate(s, 0.1, k);
    CHECK(s.position_m == doctest::Approx(1000.0).epsilon(1e-12));
}
```

**What it does:** its syntax is nearly the same as Catch2's (`TEST_CASE`, `CHECK`/`REQUIRE`, `SUBCASE` in place of `SECTION`, `doctest::Approx`), with decorators for metadata, a JUnit reporter and `doctest_discover_tests()` for CMake.
**Why it's designed this way:** its headline feature is that tests can live **inside production source files**, next to the code they test (like Rust's `#[test]` or Python doctests). Defining `DOCTEST_CONFIG_DISABLE` strips them out of the release build completely. Keeping that zero-cost removal cheap required a tiny, fast header.
**Strengths:** fastest compile times of the group; easy migration from Catch2.
**Weaknesses:** smaller community and ecosystem; no mocking; fewer advanced features (generators, benchmarks).
**Where you'll see it:** performance-sensitive codebases and libraries that want in-source tests.
**Role in our project:** a good third adapter, because moving from Catch2 to doctest is almost mechanical, which shows how well the seam holds.

### 2.4 Boost.Test

**What it is:** the test framework in the **Boost** C++ libraries, in use since the early 2000s (Boost Software License). Many older and large codebases already depend on Boost, so they use Boost.Test.

```cpp
#define BOOST_TEST_MODULE simulator_tests
#include <boost/test/included/unit_test.hpp>   // header-only variant
#include "simulator/dynamics.hpp"
namespace utf = boost::unit_test;

BOOST_AUTO_TEST_CASE(constant_velocity_matches_analytic,
                     * utf::description("SIM-003") * utf::tolerance(1e-12)) {
    sim::TrueState s{0.0, 0.0, 10.0};
    for (int k = 1; k <= 1000; ++k) s = sim::propagate(s, 0.1, k);
    BOOST_TEST(s.position_m == 1000.0);          // uses the relative tolerance above
}
```

**What it does**
- Test suites (`BOOST_AUTO_TEST_SUITE`), fixtures (`BOOST_FIXTURE_TEST_CASE`) and global fixtures.
- Three assertion levels: `WARN`, `CHECK` and `REQUIRE`.
- Floating-point tolerance as a *decorator* on the test case. It is **relative**, and the older `BOOST_CHECK_CLOSE` takes a *percentage*, a classic trap.
- Data-driven tests (`BOOST_DATA_TEST_CASE`) that combine datasets.
- Log formats including `--log_format=JUNIT`. It can be used header-only, as a static library or as a shared library.

**Why it's designed this way:** it grew up inside Boost's scientific and generic-programming community, which explains the careful attention to floating-point comparison and the three severity levels.
**Strengths:** mature, feature-rich, strong numeric comparisons, no extra dependency if you already use Boost.
**Weaknesses:** Boost is a large dependency; slower compiles; CMake has no built-in automatic test discovery for it (you register tests with `add_test` yourself); the documentation is dense.
**Where you'll see it:** long-lived defense, finance and scientific codebases. Knowing it signals that you can work in legacy environments, which is a real asset in aerospace.

### 2.5 pytest (system and analysis tests)

**What it is:** the dominant Python test framework (MIT license). In this project it tests the **Python analysis code** and runs **black-box system tests**: it launches the compiled `sim` binary and checks what comes out.

```python
# tests/system/test_reference_scenario.py
import subprocess
import pytest
from analyze import load_run, rmse

@pytest.mark.parametrize("seed", [1, 42, 1234])
def test_estimate_beats_raw_measurements(sim_binary, tmp_path, seed):
    """EST-008"""
    out = tmp_path / "run.csv"
    subprocess.run([sim_binary, "--seed", str(seed), "--out", str(out)], check=True)
    run = load_run(out)
    measured = run[run.meas_pos_m.notna()]
    assert rmse(measured.est_pos_m, measured.true_pos_m) < rmse(measured.meas_pos_m, measured.true_pos_m)
```

**What it does:** plain `assert`. pytest rewrites assertions so failures show the values, like Catch2's expression decomposition. Fixtures use **dependency injection**: name a fixture as a function argument (`tmp_path`, `sim_binary`) and pytest supplies it. It also offers `@pytest.mark.parametrize`, `pytest.approx`, a large plugin ecosystem (coverage, parallel runs) and `--junitxml`.
**Why it's designed this way:** Python *does* have runtime introspection, so pytest needs no registration macros or classes. Plain functions and plain `assert` are enough.
**Strengths:** you probably know it already, it's fast to write, and it's ideal for end-to-end and data-validation tests.
**Role in our project:** these tests are the **stable safety net**. The system tests exercise the binary through its command-line and CSV contract, so they don't change at all when you swap the C++ framework. That lets you confirm a swap didn't break behavior.
**Where you'll see it:** test-engineering and integration roles, where Python often drives hardware-in-the-loop rigs, simulators and ground-system test harnesses.

---

## 3. Side-by-side comparison

| | GoogleTest | Catch2 | doctest | Boost.Test | pytest |
|---|---|---|---|---|---|
| License | BSD-3 | BSL-1.0 | MIT | BSL-1.0 | MIT |
| Style | xUnit, fixture classes | Spec-style, SECTIONs, BDD | Catch-like, in-source option | xUnit, suites, decorators | Plain functions |
| Stop vs continue | `ASSERT_` / `EXPECT_` | `REQUIRE` / `CHECK` | `REQUIRE` / `CHECK` | `REQUIRE` / `CHECK` / `WARN` | `assert` (stops) |
| Float tolerance | `EXPECT_NEAR`, `DOUBLE_EQ` | `WithinAbs/Rel/ULP` | `Approx` | `tolerance()` (relative) | `pytest.approx` |
| Parameterized | `TEST_P` | `GENERATE` | templates / loops | `BOOST_DATA_TEST_CASE` | `parametrize` |
| Mocking | GoogleMock built in | external (trompeloeil) | external | external | `unittest.mock` |
| Requirement tagging | `RecordProperty` | tags `[SIM-003]` | `description`, `test_suite` | `description`, `label` | markers / docstrings |
| JUnit XML | yes | yes | yes | yes | yes |
| CTest discovery | `gtest_discover_tests` | `catch_discover_tests` | `doctest_discover_tests` | manual `add_test` | `add_test` wrapper, or run directly |
| Compile cost | medium | medium (v3) | very low | high | n/a |

**Why swapping is easy:** every framework can (1) register with CTest and (2) emit JUnit XML. Those two shared interfaces are exactly what TST-003 and TST-004 depend on. Everything above that layer is framework-specific syntax, confined to thin adapter files.

---

## 4. What aerospace and defense employers expect

Open-source frameworks are only part of it. Safety-critical aerospace work adds requirements that general web development doesn't have.

### 4.1 Requirements-based testing and traceability
In avionics and many defense programs, **every test must trace to a written requirement, and every requirement must trace to at least one test.** This is two-way traceability. Auditors check it. It's why this project gives requirements IDs and tags tests with them (TST-005). Being able to say *"I built a traceability matrix from my JUnit reports"* is a strong interview point for a junior candidate.

### 4.2 Standards you'll hear about
- **DO-178C**: the certification standard for software in civil aircraft, also widely applied on military aircraft programs. Software is assigned a level from A (catastrophic failure effect) to E (no effect). The level determines how much verification is required.
- **DO-330**: rules for *qualifying tools*. If a test tool's output is trusted without manual checking, the tool itself must be qualified.
- **MIL-STD-882E**: the DoD standard for system safety.
- **NASA NPR 7150.2**: NASA's software engineering requirements, relevant to space programs.
- **Coding standards:** MISRA C++, AUTOSAR C++14, and JSF AV C++ (written for the F-35) are enforced by static-analysis tools.

You aren't expected to know these in depth for a junior role. Recognizing them, and knowing *why* they exist, sets you apart.

### 4.3 Structural coverage
Coverage measures which code the tests actually executed.
- **Statement coverage**: was every line run?
- **Decision (branch) coverage**: did every `if` go both ways?
- **MC/DC** (modified condition/decision coverage): was each condition inside a decision shown to independently change the outcome? DO-178C Level A requires it.

Open-source tools: **gcov / gcovr / lcov** for statement and branch coverage. Recent compilers have added MC/DC instrumentation: Clang 18 (`-fcoverage-mcdc`) and GCC 14 (`-fcondition-coverage`).

### 4.4 Commercial tools used on certified programs
On certified flight software you'll often find commercial suites instead of, or alongside, GoogleTest: **VectorCAST** (Vector), the **LDRA tool suite**, **Parasoft C/C++test** and **Rapita RVS**. They generate unit-test harnesses, measure coverage up to MC/DC on the target hardware, manage traceability and come with qualification kits for DO-330. They're licensed and expensive, so you won't use them here. The underlying concepts (tests traced to requirements, coverage, reproducible harnesses) are the same ones this project practices. For embedded C/C++, **CppUTest** and **Unity/Ceedling** are the common open-source choices.

### 4.5 The test levels you'll hear in interviews
| Level | Meaning | In this project |
|---|---|---|
| Unit | One component in isolation | GoogleTest/Catch2 tests of sensor, estimator, dynamics |
| Integration | Components working together | Runner sequencing test with fakes (RUN-001) |
| System | Whole program through its external interface | pytest driving the `sim` binary |
| **SIL**: software-in-the-loop | Flight or ground software tested against a *simulated* environment | This project *is* a miniature SIL: the estimator is the "software", and the simulator plus sensor are the "environment" |
| **HIL**: hardware-in-the-loop | Real hardware with simulated inputs | Out of scope; worth being able to define |
| **Monte Carlo** | Many randomized runs to measure performance statistically | The parameterized-seed pytest above is a tiny version (Extension 4 in the guide) |
| Regression | Proving old behavior still works after changes | CI on every push |

### 4.6 Skills to be able to show in this project
1. Tests traced to written requirements.
2. Deterministic tests of randomized code (fixed seeds plus statistical bounds).
3. Correct floating-point comparisons.
4. CMake + CTest + CI producing JUnit reports.
5. Coverage reports, sanitizers and warning-free builds.
6. Clean separation of testable logic from I/O, including dependency injection and fakes.
