"""NFR-006: the 30 s test-time budget is checked by tools/check_budget.py."""
import pytest

import check_budget


def _junit(tmp_path, name, times):
    cases = "".join(f'<testcase classname="S" name="t{i}" time="{t}"/>' for i, t in enumerate(times))
    path = tmp_path / name
    path.write_text(f"<testsuite>{cases}</testsuite>")
    return str(path)


@pytest.mark.req("NFR-006")
def test_a_suite_inside_the_budget_passes_and_one_over_it_fails(tmp_path, capsys):
    ok = _junit(tmp_path, "ok.xml", [10.0, 12.5])
    assert check_budget.main(["--junit", ok]) == 0
    assert "22.5 s" in capsys.readouterr().out
    slow = _junit(tmp_path, "slow.xml", [20.0, 10.5])
    assert check_budget.main(["--junit", slow]) == 1
    assert "over the time budget" in capsys.readouterr().err


@pytest.mark.req("NFR-006")
def test_times_from_several_junit_files_are_added(tmp_path):
    a, b = _junit(tmp_path, "a.xml", [16.0]), _junit(tmp_path, "b.xml", [16.0])
    assert check_budget.main(["--junit", a]) == 0
    assert check_budget.main(["--junit", a, b]) == 1   # 32 s together, 16 s each


@pytest.mark.req("NFR-006")
def test_an_unreadable_or_empty_report_fails_instead_of_passing(tmp_path):
    assert check_budget.main(["--junit", str(tmp_path / "nope.xml")]) == 1
    bad = tmp_path / "bad.xml"
    bad.write_text("<not xml")
    assert check_budget.main(["--junit", str(bad)]) == 1
    assert check_budget.main(["--junit", _junit(tmp_path, "empty.xml", [])]) == 1  # 0 tests: proves nothing
