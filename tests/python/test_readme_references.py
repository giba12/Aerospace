"""The README's pointers to files must point at files that exist (DOC-001, VAL-07)."""
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
README = (ROOT / "README.md").read_text(encoding="utf-8")


@pytest.mark.req("DOC-001")
def test_every_path_in_the_repository_layout_table_exists():
    table = README.split("## Repository layout", 1)[1].split("\n## ", 1)[0]
    paths = []
    for row in table.splitlines():
        if row.startswith("| `"):
            first_cell = row.split("|")[1]
            paths += re.findall(r"`([^`]+)`", first_cell)
    assert len(paths) >= 8, "the layout table parse found too little: this check would be vacuous"
    for path in paths:
        assert (ROOT / path).exists(), f"the README layout lists {path}, which does not exist"


@pytest.mark.req("DOC-001")
def test_every_relative_link_and_image_in_the_readme_resolves():
    targets = [t for t in re.findall(r"\]\(([^)]+)\)", README) if not t.startswith(("http", "#"))]
    assert len(targets) >= 4
    for target in targets:
        assert (ROOT / target.split("#")[0]).exists(), f"the README links to {target}, which does not exist"


# ---- numbers the README quotes, tied to the data they come from (VAL-07) ----

def _readme_text():
    return " ".join(README.split())


@pytest.mark.req("DOC-001")
def test_a_perfect_filter_scores_about_95_percent():
    """C-59: the share of a Gaussian inside two standard deviations."""
    import math
    inside = math.erf(2 / math.sqrt(2))
    assert round(100 * inside) == 95
    assert "A perfect filter scores about 95 %." in _readme_text()


@pytest.mark.req("DOC-001")
def test_the_registry_has_as_many_must_requirements_as_the_readme_says():
    import csv
    lines = [l for l in (ROOT / "docs" / "requirements.csv").read_text().splitlines() if not l.startswith("#")]
    musts = sum(1 for row in csv.DictReader(lines) if row["priority"] == "M")
    assert f"All {musts} Must requirements have a passing test" in _readme_text()


@pytest.mark.req("DOC-001", "SYS-004")
def test_the_readmes_acceleration_figures_match_the_validation_record():
    """C-77: the README's figures for the filter under acceleration are the ones recorded in VALIDATION.md."""
    record = (ROOT / "docs" / "VALIDATION.md").read_text(encoding="utf-8")
    cells = {}
    for name in ("S-ACCEL-SMALL", "S-ACCEL-LARGE"):
        row = next(l for l in record.splitlines() if l.startswith(f"| {name} |"))
        parts = [c.strip() for c in row.strip("|").split("|")]
        cells[name] = (parts[2], round(100 * float(parts[4])))   # mean ratio, pooled coverage in percent
    readme = _readme_text()
    small, large = cells["S-ACCEL-SMALL"], cells["S-ACCEL-LARGE"]
    assert f"(RMSE ratio {small[0]}, error-bar coverage {small[1]} %)" in readme
    assert f"(ratio {large[0]})" in readme and f"only {large[1]} % of the time" in readme
