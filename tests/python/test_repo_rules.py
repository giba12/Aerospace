"""Inspection-type requirements turned into automated checks."""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.req("TST-006")
def test_test_support_includes_no_framework_headers():
    banned = re.compile(r'#\s*include\s*[<"](gtest|gmock|catch2|doctest|boost/test)')
    for path in (ROOT / "tests" / "support").rglob("*"):
        if path.is_file():
            assert not banned.search(path.read_text()), f"{path} includes a test-framework header"


@pytest.mark.req("NFR-003")
def test_simcore_uses_no_hidden_randomness_or_clock():
    banned = re.compile(r"\b(rand|srand|time)\s*\(|std::random_device")
    for path in list((ROOT / "src").glob("*.cpp")) + list((ROOT / "include").rglob("*.hpp")):
        assert not banned.search(path.read_text()), f"{path} uses a hidden source of randomness or time"


@pytest.mark.req("TST-001")
def test_main_makes_one_call_into_simcore():
    text = (ROOT / "src" / "main.cpp").read_text()
    assert text.count("sim::cli_main(") == 1
    assert "validate" not in text and "Estimator" not in text
