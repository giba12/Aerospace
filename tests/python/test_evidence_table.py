"""The claim-to-evidence table (docs/EVIDENCE.md) is checked, so it cannot quietly rot (VAL-07).

What a test can verify about a table of claims: that each quoted claim is still in the README, that no README
paragraph or bullet lacks a row, and that every piece of evidence a row cites actually exists and is the kind
it says. It cannot verify that a cited test really proves the claim; the Caveat column and review do that.
"""
import csv
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
STRENGTHS = {"T", "C", "R", "I", "X"}


def _collapse(text):
    """Whitespace collapsed to single spaces, and the '> ' prefix of block quotes removed."""
    text = re.sub(r"(?m)^>\s?", "", text)
    return " ".join(text.split())


README = (ROOT / "README.md").read_text(encoding="utf-8")
README_FLAT = _collapse(README)


def _rows():
    rows = []
    for line in (ROOT / "docs" / "EVIDENCE.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"\| C-\d+ \|", line):
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            assert len(cells) == 5, f"a row must have 5 cells: {line[:80]}"
            rows.append({"id": cells[0], "claim": cells[1], "evidence": cells[2],
                         "strength": cells[3].split(), "caveat": cells[4]})
    return rows


def _items(evidence):
    """Split an evidence cell into (kind, value) pairs."""
    out = []
    for part in evidence.split(" ; "):
        kind, _, value = part.strip().partition(":")
        out.append((kind, value.strip()))
    return out


def _registry():
    lines = [l for l in (ROOT / "docs" / "requirements.csv").read_text().splitlines() if not l.startswith("#")]
    return {row["id"] for row in csv.DictReader(lines)}


def _defines_test(path, name):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".cpp":
        suite, _, case = name.partition(".")
        return re.search(rf"TEST\(\s*{re.escape(suite)}\s*,\s*{re.escape(case)}\s*\)", text) is not None
    return re.search(rf"^def {re.escape(name)}\b", text, re.M) is not None


@pytest.mark.req("DOC-001", "SYS-006")
def test_the_table_has_rows_with_unique_ids_and_a_known_strength_for_each():
    rows = _rows()
    assert len(rows) >= 50, "the table parse found too few rows: this check would be vacuous"
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "duplicate claim IDs"
    for r in rows:
        assert r["strength"] and set(r["strength"]) <= STRENGTHS, f"{r['id']}: strength must use {sorted(STRENGTHS)}"


@pytest.mark.req("DOC-001", "SYS-006")
def test_every_quoted_claim_is_still_in_the_readme_word_for_word():
    for r in _rows():
        assert _collapse(r["claim"]) in README_FLAT, f"{r['id']} quotes text that is not in the README: {r['claim'][:70]}"


@pytest.mark.req("DOC-001", "SYS-006")
def test_every_piece_of_evidence_exists_and_is_the_kind_the_row_says():
    registry = _registry()
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for r in _rows():
        items = _items(r["evidence"])
        kinds = {kind for kind, _ in items}
        assert kinds <= {"test", "file", "req", "ci", "obs"}, f"{r['id']}: unknown evidence kind {kinds}"
        for kind, value in items:
            assert value, f"{r['id']}: empty {kind}: item"
            if kind == "test":
                path, _, name = value.partition("::")
                assert (ROOT / path).is_file(), f"{r['id']}: no such test file {path}"
                assert _defines_test(ROOT / path, name), f"{r['id']}: {path} defines no test {name}"
            elif kind == "file":
                assert (ROOT / value).exists(), f"{r['id']}: no such file {value}"
            elif kind == "req":
                assert value in registry, f"{r['id']}: unknown requirement {value}"
            elif kind == "ci":
                job, _, step = value.partition("/")
                assert re.search(rf"^  {re.escape(job)}:", ci, re.M), f"{r['id']}: no CI job {job}"
                if step:
                    assert f"- name: {step}" in ci, f"{r['id']}: no CI step {step}"
        # a row may not claim a kind of evidence it does not cite
        if "T" in r["strength"]:
            assert "test" in kinds, f"{r['id']}: strength T needs a test: item"
        if "C" in r["strength"]:
            assert "ci" in kinds, f"{r['id']}: strength C needs a ci: item"
        if "R" in r["strength"]:
            assert "obs" in kinds, f"{r['id']}: strength R needs an obs: item"
        if "I" in r["strength"]:
            assert kinds & {"file", "test"}, f"{r['id']}: strength I needs a file: item"


def _prose_blocks():
    """The README's paragraphs, list items, tables and block quotes. Code blocks, headings and images are not claims."""
    text = re.sub(r"```.*?```", "\n\n", README, flags=re.S)
    blocks = []
    for chunk in re.split(r"\n\s*\n", text):
        chunk = chunk.strip("\n")
        if not chunk.strip() or chunk.lstrip().startswith(("#", "![")):
            continue
        # a bulleted list is one claim set per bullet
        parts = re.split(r"(?m)^(?=- )", chunk) if chunk.lstrip().startswith("- ") else [chunk]
        blocks += [p for p in parts if p.strip()]
    return blocks


@pytest.mark.req("DOC-001", "SYS-006")
def test_every_readme_paragraph_and_bullet_has_a_row():
    quotes = [_collapse(r["claim"]) for r in _rows()]
    blocks = _prose_blocks()
    assert len(blocks) >= 30, "the README parse found too few blocks: this check would be vacuous"
    missing = [_collapse(b)[:80] for b in blocks if not any(q in _collapse(b) for q in quotes)]
    assert not missing, "README text with no row in docs/EVIDENCE.md:\n  " + "\n  ".join(missing)


@pytest.mark.req("SYS-006", "DOC-001")
def test_the_table_states_the_sys_006_disclaimer_and_admits_what_it_does_not_support():
    evidence = (ROOT / "docs" / "EVIDENCE.md").read_text(encoding="utf-8")
    assert "educational simulation" in evidence[:600]
    assert "## What this repository does not support" in evidence
    assert "## What this review changed in the README" in evidence
