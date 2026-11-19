"""Shared data and style for the sensor-sim presentation builders.

Every number on a slide is read from the repository (the recorded run, docs/VALIDATION.md,
docs/requirements.csv, the test sources) so the slides cannot drift from the project.
"""
import csv
import json
import math
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Colours are fixed by role everywhere, as in the interactive demo: ink = truth,
# orange = raw sensor readings, blue = the filter's estimate.
C = dict(
    bg="#f3f5f8", surface="#ffffff", surface2="#e9edf3", ink="#0e1a2b", ink2="#46546a", ink3="#5b687c",
    line="#d3dae5", blue="#2a78d6", blue_ink="#1b5aa8", blue_soft="#cfe0f5", orange="#eb6834",
    orange_ink="#b04418", good="#16794c", good_bg="#e0f3e8", bad="#b3261e", bad_bg="#fbe8e5",
    navy="#0f1d33", navy2="#1a2d4d", navy_ink="#dbe6f5", navy_dim="#8da2c0",
)
FONT = "DejaVu Sans"


def run_data(path=None):
    path = Path(path or ROOT / "out/run.csv")
    rows = list(csv.DictReader(open(path, newline="")))
    cfg = json.load(open(str(path) + ".config.json"))
    col = lambda k: [float(r[k]) if r[k] != "" else None for r in rows]
    return dict(cfg=cfg, t=col("t_s"), true_pos=col("true_pos_m"), true_vel=col("true_vel_mps"),
                meas=col("meas_pos_m"), est=col("est_pos_m"), vel=col("est_vel_mps"), var=col("est_pos_var_m2"))


def metrics():
    return json.load(open(ROOT / "data/example-metrics.json"))


def seeds():
    """The 50 held-out seeds: (seed, raw_rmse, est_rmse, ratio, coverage)."""
    text = (ROOT / "docs/VALIDATION.md").read_text()
    out = [tuple([int(m[0])] + [float(x) for x in m[1:]]) for m in
           re.findall(r"^\| (10\d\d) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", text, re.M)]
    assert len(out) == 50, len(out)
    return out


def scenarios():
    """Exploratory scenarios from VALIDATION.md section 3: (name, flags, mean, worst, coverage, v02, v03)."""
    text = (ROOT / "docs/VALIDATION.md").read_text()
    out = []
    for m in re.finditer(r"^\| (S-[A-Z-]+) \| `([^`]+)` \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| (\*{0,2}\w+\*{0,2}) \| (\*{0,2}\w+\*{0,2}) \|",
                         text, re.M):
        n, fl, mean, worst, cov, a, b = m.groups()
        out.append((n, fl, float(mean), float(worst), float(cov), a.strip("*") == "pass", b.strip("*") == "pass"))
    assert len(out) == 5, out
    return out


def requirements():
    """Requirements per area: {prefix: (must, total)}."""
    rows = [r for r in csv.reader(open(ROOT / "docs/requirements.csv")) if r and not r[0].startswith("#")][1:]
    d = {}
    for r in rows:
        p = r[0].split("-")[0]
        m, t = d.get(p, (0, 0))
        d[p] = (m + (r[1] == "M"), t + 1)
    return d


def test_counts():
    """(C++ GoogleTest cases, Python pytest cases), counted from the sources."""
    cpp = 0
    for f in (ROOT / "tests/gtest").glob("*.cpp"):
        cpp += len(re.findall(r"^TEST(?:_F|_P)?\(", f.read_text(), re.M))
    py = None
    vpy = ROOT / ".venv/bin/python"
    if vpy.exists():
        r = subprocess.run([str(vpy), "-m", "pytest", "--collect-only", "-q"], cwd=ROOT, capture_output=True, text=True)
        m = re.search(r"(\d+) tests? collected", r.stdout)
        py = int(m[1]) if m else None
    return cpp, py


def loc():
    n = lambda pats: sum(len(p.read_text().splitlines()) for pat in pats for p in ROOT.glob(pat))
    return dict(lib=n(["src/*.cpp", "include/simulator/*.hpp"]), py=n(["python/*.py"]),
                tests=n(["tests/gtest/*.cpp", "tests/python/*.py", "tests/system/*.py"]))
