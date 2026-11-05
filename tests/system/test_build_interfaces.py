"""Build and test-runner interfaces, checked against the real build (TST-002, TST-003, TST-004, NFR-003).

These need the built binaries, so they run through ctest (which sets SIM_BIN), like the other system tests.
"""
import pathlib
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

import req_trace

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def build_dir(sim_bin):
    return pathlib.Path(sim_bin).parent


def _gtest_names(build_dir):
    binary = build_dir / "tests" / "gtest" / "sim_gtest_tests"
    out = subprocess.run([str(binary), "--gtest_list_tests"], capture_output=True, text=True, check=True).stdout
    names, suite = [], None
    for line in out.splitlines():
        if not line.startswith(" "):
            suite = line.split("#")[0].strip().rstrip(".")
        elif line.strip():
            names.append(f"{suite}.{line.split('#')[0].strip()}")
    return binary, names


def _generator(build_dir):
    """The CMake generator of the real build, so this test needs no tool the build itself does not.
    (Naming none made CMake default to Makefiles and fail in a container that has only Ninja.)"""
    match = re.search(r"^CMAKE_GENERATOR:INTERNAL=(.+)$", (build_dir / "CMakeCache.txt").read_text(), re.M)
    assert match, "CMakeCache.txt names no generator"
    return match.group(1)


@pytest.mark.req("TST-002")
def test_an_unknown_test_framework_is_refused_at_configure_time(build_dir, tmp_path):
    done = subprocess.run(["cmake", "-S", str(ROOT), "-B", str(tmp_path / "b"), "-G", _generator(build_dir),
                           "-DSIM_TEST_FRAMEWORK=bogus"], capture_output=True, text=True)
    assert done.returncode != 0
    assert "SIM_TEST_FRAMEWORK='bogus' has no adapter in tests/bogus/" in done.stderr


@pytest.mark.req("TST-003")
def test_ctest_lists_every_cpp_test_and_both_wrapper_tests(build_dir):
    _, gtest_names = _gtest_names(build_dir)
    assert len(gtest_names) >= 40, "could not list the C++ tests"
    listing = subprocess.run(["ctest", "-N", "--test-dir", str(build_dir)], capture_output=True, text=True)
    assert listing.returncode == 0, listing.stderr
    listed = set(re.findall(r"Test\s+#\d+: (\S+)", listing.stdout))
    missing = [n for n in gtest_names if n not in listed]
    assert not missing, f"ctest -N does not list: {missing[:5]}"
    assert {"system.pytest", "junit.gtest"} <= listed


@pytest.mark.req("TST-004")
def test_the_cpp_test_binary_writes_junit_that_parses_and_carries_requirement_tags(build_dir, tmp_path):
    binary, _ = _gtest_names(build_dir)
    out = tmp_path / "gtest.xml"
    done = subprocess.run([str(binary), f"--gtest_output=xml:{out}"], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout[-500:]
    tests = req_trace.load_tests([str(out)])
    assert len(tests) >= 40
    assert all(ids for _, ids, _ in tests), "a C++ test cites no requirement"
    assert all(passed for _, _, passed in tests)


@pytest.mark.req("TST-004")
def test_pytest_writes_junit_that_parses(tmp_path):
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "test_tiny.py").write_text("def test_ok():\n    assert True\n")
    out = tmp_path / "pytest.xml"
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", str(tmp_path),
                           f"--junitxml={out}", str(tmp_path / "test_tiny.py")], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout[-500:]
    assert len(list(ET.parse(out).getroot().iter("testcase"))) == 1
    assert len(req_trace.load_tests([str(out)])) == 1


# Writable global or static data in the compiled library. There are exactly two and both are constants:
# the flag table (built once, never changed) and the CSV header pointer. Anything else is hidden state.
ALLOWED_WRITABLE_DATA = {"sim::(anonymous namespace)::flags()::table", "sim::kCsvHeader"}
# Compiler- and tool-generated entries that are read-only metadata or instrumentation, not program state.
TOOLING_SYMBOLS = re.compile(
    r"^(typeinfo|typeinfo name|vtable|VTT) for |^(__gcov|__asan|___asan|__odr_asan|__ubsan|\.Lubsan|__sancov|guard variable)")


@pytest.mark.req("NFR-003")
def test_the_compiled_library_holds_no_writable_global_state(build_dir):
    nm = shutil.which("nm")
    assert nm, "nm (part of the compiler toolchain) is required for this check"
    out = subprocess.run([nm, "-C", "--defined-only", str(build_dir / "libsimcore.a")],
                         capture_output=True, text=True, check=True).stdout
    found = set()
    for line in out.splitlines():
        match = re.match(r"^[0-9a-f]+ ([bBdD]) (.+)$", line)
        if match and not TOOLING_SYMBOLS.match(match.group(2)):
            found.add(match.group(2))
    assert found == ALLOWED_WRITABLE_DATA, f"unexpected writable data: {sorted(found - ALLOWED_WRITABLE_DATA)}"
