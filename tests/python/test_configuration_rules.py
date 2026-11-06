"""Requirements verified by INSPECTION or DEMONSTRATION (RVCM methods I and D), as automated checks.

Be clear about what these are. They read the build files, the CI workflow, the sources and the docs
and assert that they say what each requirement needs, so that configuration cannot drift silently.
They are NOT behaviour tests. The evidence that CI really builds with both compilers, runs on every
push and passes is the CI history itself; these tests keep the configuration that produces it honest.
"""
import pathlib
import re

import pytest

import analyze

ROOT = pathlib.Path(__file__).resolve().parents[2]


def text(relative):
    return (ROOT / relative).read_text(encoding="utf-8")


def ci_step(name):
    """The text of one CI step, from its `- name:` line up to the next step or job."""
    ci = text(".github/workflows/ci.yml")
    match = re.search(rf"- name: {re.escape(name)}\n(.*?)(?=\n      - |\n  [a-z-]+:\n|\Z)", ci, re.S)
    assert match, f"no CI step named {name!r}"
    return match.group(1)


# ---- NFR-001: toolchain and warnings ----

@pytest.mark.req("NFR-001")
def test_the_build_names_its_language_standard_and_treats_warnings_as_errors():
    cmake = text("CMakeLists.txt")
    assert "cmake_minimum_required(VERSION 3.20)" in cmake
    assert "set(CMAKE_CXX_STANDARD 17)" in cmake
    for flag in ("-Wall", "-Wextra", "-Wpedantic", "-Werror"):
        assert flag in cmake
    assert re.search(r'option\(SIM_WARNINGS_AS_ERRORS "[^"]*" ON\)', cmake)


@pytest.mark.req("NFR-001")
def test_ci_builds_with_gcc_and_clang_with_warnings_as_errors_and_the_readme_names_them():
    ci = text(".github/workflows/ci.yml")
    assert "compiler: gcc-13" in ci and "compiler: clang-18" in ci
    assert "-DSIM_WARNINGS_AS_ERRORS=ON" in ci
    readme = text("README.md")
    assert "GCC 13" in readme and "Clang 18" in readme and "CMake ≥ 3.20" in readme


# ---- NFR-005: SI units, with the unit in every name ----

UNIT_SUFFIXES = ("_m", "_s", "_mps", "_mps2", "_m2", "_m2s2", "_m2ps2", "_m2ps3")
DIMENSIONLESS = {"step", "steps", "every_n_steps", "meas_every", "seed", "sensor_id", "out_path", "P",
                 "schema_version", "compiler", "source_revision"}


@pytest.mark.req("NFR-005")
def test_every_csv_column_and_sidecar_key_carries_its_unit():
    for name in analyze.EXPECTED_HEADER + analyze.REQUIRED_SIDECAR_KEYS:
        assert name in DIMENSIONLESS or name.endswith(UNIT_SUFFIXES), f"{name} has no unit suffix"


@pytest.mark.req("NFR-005")
def test_every_numeric_field_of_the_config_and_state_structs_carries_its_unit():
    field = re.compile(r"^\s+(?:double|std::u?int64_t|std::string|Mat2|Vec2)\s+(\w+)\s*[{;=]", re.M)
    names = []
    for header in ("include/simulator/config.hpp", "include/simulator/state.hpp"):
        names += field.findall(text(header))
    assert len(names) >= 15, "the field pattern stopped matching: this check would be vacuous"
    for name in names:
        assert name in DIMENSIONLESS or name.endswith(UNIT_SUFFIXES), f"{name} has no unit suffix"


# ---- SYS-005, TST-009, NFR-006, NFR-007, NFR-008: what CI is configured to do ----

@pytest.mark.req("SYS-005", "TST-011")
def test_ci_runs_the_traceability_gate_with_coverage_required():
    step = ci_step("Traceability")
    assert "tools/req_trace.py" in step and "--require-coverage" in step


@pytest.mark.req("TST-009")
def test_ci_runs_on_every_push_and_pull_request_and_runs_the_readme_commands():
    ci = text(".github/workflows/ci.yml")
    assert re.search(r"^on:\n  push:\n  pull_request:\n", ci, re.M)
    for command in ("cmake -S . -B build", "cmake --build build", "ctest --output-on-failure"):
        assert command in ci and command in text("README.md")


@pytest.mark.req("NFR-006")
def test_ci_enforces_the_thirty_second_budget_on_the_normal_build():
    step = ci_step("Time budget")
    assert "tools/check_budget.py" in step and "--limit 30" in step


@pytest.mark.req("NFR-007")
def test_a_sanitizer_build_exists_and_ci_runs_it():
    cmake = text("CMakeLists.txt")
    assert "SIM_SANITIZE" in cmake and "-fsanitize=address,undefined" in cmake
    assert "-fno-sanitize-recover=all" in cmake      # a finding must abort, never just print
    assert "-DSIM_SANITIZE=ON" in text(".github/workflows/ci.yml")


@pytest.mark.req("NFR-008")
def test_a_coverage_report_exists_and_ci_uploads_it_without_gating_on_it():
    cmake, ci = text("CMakeLists.txt"), text(".github/workflows/ci.yml")
    assert "SIM_COVERAGE" in cmake and "--coverage" in cmake and "add_custom_target(coverage" in cmake
    assert "--target coverage" in ci and "name: coverage" in ci
    assert "--fail-under" not in cmake + ci          # NFR-008: a goal reported, not a gate


# ---- NFR-009: pinned dependencies ----

@pytest.mark.req("NFR-009")
def test_every_python_dependency_is_pinned_to_an_exact_version():
    lines = [l.strip() for l in text("python/requirements.txt").splitlines() if l.strip() and not l.startswith("#")]
    assert lines
    for line in lines:
        assert re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9_.+-]*", line), f"not pinned exactly: {line}"
    names = {l.split("==")[0].lower() for l in lines}
    assert {"pytest", "matplotlib", "gcovr"} <= names
    assert "pip install -r python/requirements.txt" in text(".github/workflows/ci.yml")


@pytest.mark.req("NFR-009")
def test_the_test_framework_download_is_pinned_by_content_hash():
    cmake = text("tests/gtest/CMakeLists.txt")
    assert re.search(r"URL_HASH SHA256=[0-9a-f]{64}", cmake)
    assert re.search(r"/v\d+\.\d+\.\d+\.tar\.gz", cmake)   # a release, not a branch


# ---- TST-002, TST-004, TST-008: how the tests are wired ----

@pytest.mark.req("TST-002")
def test_no_test_framework_is_named_outside_tests():
    banned = re.compile(r"gtest|GTest|googletest|catch2|doctest", re.I)
    files = [ROOT / "CMakeLists.txt"] + list((ROOT / "src").glob("*")) + list((ROOT / "include").rglob("*"))
    for path in files:
        if path.is_file():
            assert not banned.search(path.read_text()), f"{path} names a test framework"


@pytest.mark.req("TST-004")
def test_ctest_is_set_up_to_write_junit_for_both_runners():
    assert "--junitxml=${CMAKE_BINARY_DIR}/test-reports/pytest.xml" in text("tests/CMakeLists.txt")
    assert "--gtest_output=xml:${CMAKE_BINARY_DIR}/test-reports/gtest.xml" in text("tests/gtest/CMakeLists.txt")


@pytest.mark.req("TST-008")
def test_every_system_test_file_drives_the_built_program_and_ctest_supplies_it():
    drivers = ("run_sim", "sim_bin")
    for path in (ROOT / "tests" / "system").glob("test_*.py"):
        assert any(d in path.read_text() for d in drivers), f"{path.name} never runs the sim binary"
    assert "SIM_BIN=$<TARGET_FILE:sim>" in text("tests/CMakeLists.txt")


# ---- SYS-001: the clean-room container ----

@pytest.mark.req("SYS-001", "NFR-009")
def test_the_dockerfile_pins_its_base_image_by_digest():
    assert re.search(r"^FROM \S+@sha256:[0-9a-f]{64}$", text("Dockerfile"), re.M)


@pytest.mark.req("SYS-001")
def test_the_dockerfile_follows_the_readme_steps_and_runs_the_whole_test_suite():
    docker = text("Dockerfile")
    for step in ("pip install --no-cache-dir -r python/requirements.txt", "cmake -S . -B build -G Ninja",
                 "cmake --build build", "ctest --output-on-failure"):
        assert step in docker, f"the Dockerfile does not run: {step}"
    assert "ARG RUN_TESTS=1" in docker, "the tests must run by default"
    for step in ("./build/sim", "python/analyze.py", "python/kalman_oracle.py"):
        assert step in docker, f"the container's default run lacks: {step}"
    readme = text("README.md")
    assert "docker build -t sensor-sim ." in readme and "podman build -t sensor-sim ." in readme
    # rootless Podman cannot write to the mounted directory without this flag (found by running it)
    assert "--userns=keep-id" in readme and "--userns=keep-id" in docker


@pytest.mark.req("SYS-001")
def test_the_image_runs_as_a_non_root_user_and_holds_no_secrets_or_local_state():
    docker = text("Dockerfile")
    assert re.search(r"^USER ubuntu$", docker, re.M), "the image must not run as root"
    for line in docker.splitlines():
        if re.match(r"\s*(ENV|ARG)\b", line):
            assert not re.search(r"KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL", line, re.I), f"secret-like name: {line}"
    ignored = text(".dockerignore").split()
    for entry in (".git", ".venv", "build", ".claude"):
        assert entry in ignored, f".dockerignore must exclude {entry}"


@pytest.mark.req("SYS-001")
def test_ci_builds_and_runs_the_container_on_every_push():
    ci = text(".github/workflows/ci.yml")
    assert "docker build -t sensor-sim ." in ci
    assert 'docker run --rm --user "$(id -u):$(id -g)"' in ci


# ---- SYS-006, DOC-001: the documentation says what this is ----

DISCLAIMED_DOCS = ["README.md", "docs/architecture.md", "docs/VALIDATION.md", "docs/EVIDENCE.md", "docs/FILE_MAP.md",
                   "docs/M1_REPORT.md", "docs/M2_REPORT.md", "docs/M3_WORKSHEET.md",
                   "docs/ARCHITECTURE_REPORT.md", "docs/CODE_REPORT.md"]
OVERCLAIM = re.compile(r"flight[- ]qualif|operational fidelity|(real|operational) sensor fusion", re.I)
NEGATION = re.compile(r"\b(not|no|never|nor|without)\b|n't", re.I)


@pytest.mark.req("SYS-006")
def test_each_document_says_it_is_an_educational_simulation():
    for doc in DISCLAIMED_DOCS:
        assert re.search(r"educational simulation", text(doc), re.I), f"{doc} lacks the SYS-006 statement"


@pytest.mark.req("SYS-006")
def test_no_document_claims_qualification_or_operational_fidelity_except_to_deny_it():
    # A sentence often wraps over several lines, so the denial is looked for in the whole paragraph.
    # The requirement documents are exempt: they define and discuss SYS-006 itself, and name these
    # claims in "out of scope" lists where the denial is the heading, not a word in the sentence.
    requirement_docs = {"requirements.md", "requirements-explained.md", "systems-engineering-baseline.md",
                        "test-frameworks.md", "CONTINUATION_GUIDE.md"}
    scanned = [ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md")) + sorted((ROOT / "docs").glob("*/*.md"))
    for path in [p for p in scanned if p.name not in requirement_docs]:
        for paragraph in re.split(r"\n\s*\n", path.read_text()):
            match = OVERCLAIM.search(paragraph)
            if match:
                assert NEGATION.search(paragraph), f"{path.name} may overclaim: ...{paragraph[:120].strip()}"


@pytest.mark.req("DOC-001", "SYS-006")
def test_the_readme_has_every_section_the_requirement_lists():
    readme = text("README.md")
    headings = re.findall(r"^## (.+)$", readme, re.M)
    for required in ("What this project demonstrates",   # purpose
                     "Data flow", "Units and assumptions", "Build, test, run, analyze",
                     "Expected output",                  # sample output
                     "Limitations", "Next steps"):
        assert required in headings, f"README has no '## {required}' section"
    for command in ("cmake -S . -B build", "cmake --build build", "ctest --output-on-failure",
                    "./build/sim", "python/analyze.py"):
        assert command in readme
    assert "educational simulation" in readme[:600]      # the SYS-006 statement, at the top
