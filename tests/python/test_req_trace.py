"""Unit tests for tools/req_trace.py (TST-011 verification: a fixture with a missing/unknown ID)."""
import textwrap

import pytest

import req_trace as trace_tool  # tools/req_trace.py; imported by name via pytest.ini pythonpath

REGISTRY = textwrap.dedent("""\
    # comment line
    id,priority,method,level
    "AAA-001",M,"T","U"
    "AAA-002",M,"T","U"
    "AAA-003",S,"T","U"
""")


def _write(tmp_path, junit_cases):
    reg = tmp_path / "reg.csv"
    reg.write_text(REGISTRY)
    xml = tmp_path / "r.xml"
    xml.write_text(f"<testsuites><testsuite>{junit_cases}</testsuite></testsuites>")
    return reg, xml


def _run(tmp_path, cases, *extra):
    reg, xml = _write(tmp_path, cases)
    return trace_tool.main(["--requirements", str(reg), "--junit", str(xml), *extra])


@pytest.mark.req("TST-011")
def test_all_musts_covered_passes_even_with_gate_on(tmp_path):
    cases = ('<testcase classname="S" name="a" requirements="AAA-001"/>'
             '<testcase classname="S" name="b" requirements="AAA-002"/>')
    assert _run(tmp_path, cases, "--require-coverage") == 0


@pytest.mark.req("TST-011")
def test_uncovered_must_fails_only_when_gate_is_on(tmp_path):
    cases = '<testcase classname="S" name="a" requirements="AAA-001"/>'  # AAA-002 has no test
    assert _run(tmp_path, cases) == 0
    assert _run(tmp_path, cases, "--require-coverage") == 1


@pytest.mark.req("TST-011", "TST-005")
def test_unknown_id_and_orphan_test_always_fail(tmp_path):
    assert _run(tmp_path, '<testcase classname="S" name="a" requirements="ZZZ-999"/>') == 1
    assert _run(tmp_path, '<testcase classname="S" name="a"/>') == 1


@pytest.mark.req("TST-011")
def test_failed_test_does_not_count_as_coverage(tmp_path):
    cases = ('<testcase classname="S" name="a" requirements="AAA-001"><failure/></testcase>'
             '<testcase classname="S" name="b" requirements="AAA-002"/>')
    assert _run(tmp_path, cases, "--require-coverage") == 1


@pytest.mark.req("TST-011")
def test_pytest_style_property_child_is_read(tmp_path):
    cases = ('<testcase classname="S" name="a"><properties>'
             '<property name="requirements" value="AAA-001,AAA-002"/></properties></testcase>')
    assert _run(tmp_path, cases, "--require-coverage") == 0
