"""System tests for the ensemble tool: it runs the real `sim` and its exit code means something."""
import json
import subprocess
import sys

import pytest

import ensemble


def _tool(sim_bin, *args):
    return subprocess.run([sys.executable, ensemble.__file__, "--sim", sim_bin, *args],
                          capture_output=True, text=True)


@pytest.mark.req("SYS-004", "EST-008")
def test_the_report_and_summary_files_agree_with_the_per_seed_runs(sim_bin, tmp_path):
    done = _tool(sim_bin, "--seeds", "tuning", "--max-seeds", "6",
                 "--markdown", tmp_path / "r.md", "--json", tmp_path / "s.json")
    assert done.returncode == 0, done.stderr
    summary = json.loads((tmp_path / "s.json").read_text())
    results, _ = ensemble.run_ensemble(sim_bin, ensemble.SEED_SETS["tuning"][:6])
    assert summary == json.loads(json.dumps(ensemble.summarize(results)))
    text = (tmp_path / "r.md").read_text()
    assert "VAL-02" in text and "VAL-03" in text and "PASS" in text and "`tuning`" in text
    assert "partial: the first 6 of 200" in text    # a short run can never pass for the full set


@pytest.mark.req("SYS-004", "EST-012")
def test_the_exit_code_is_1_and_the_report_says_FAIL_when_the_filter_is_mismatched(sim_bin, tmp_path):
    # True acceleration the constant-velocity filter does not model: it stops helping.
    done = _tool(sim_bin, "--seeds", "tuning", "--max-seeds", "6", "--markdown", tmp_path / "r.md",
                 "--", "--accel", "0.5")
    assert done.returncode == 1
    text = (tmp_path / "r.md").read_text()
    assert "**FAIL**" in text and "--accel 0.5" in text and "Seeds over the ratio limit" in text


@pytest.mark.req("SYS-004")
def test_a_failing_sim_run_is_reported_not_swallowed(sim_bin):
    done = _tool(sim_bin, "--seeds", "tuning", "--max-seeds", "2", "--", "--dt", "0")
    assert done.returncode == 1 and "ensemble: error" in done.stderr


@pytest.mark.req("SYS-004")
def test_a_nonsense_seed_count_is_refused(sim_bin):
    for bad in ("0", "-1", "201"):
        done = _tool(sim_bin, "--seeds", "tuning", "--max-seeds", bad)
        assert done.returncode == 1 and "--max-seeds" in done.stderr
