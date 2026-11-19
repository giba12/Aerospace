#!/usr/bin/env python3
"""Build demo/index.html: fill demo/src.html with data taken from the repository itself.

The page shows the recorded reference run (out/run.csv or data/), the 50 held-out seeds in
docs/VALIDATION.md, and the requirement-to-test links found by scanning tests/. Nothing is
typed in by hand, so the page cannot drift from the repository without a rebuild.

    python3 tools/build_demo.py [--run out/run.csv]
"""
import argparse
import csv
import json
import math
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def recorded_run(path):
    rows = list(csv.DictReader(open(path, newline="")))
    cfg = json.load(open(str(path) + ".config.json"))
    f = lambda s: None if s == "" else float(s)
    meas = [f(r["meas_pos_m"]) for r in rows]
    est = [round(float(r["est_pos_m"]), 6) for r in rows]
    vel = [round(float(r["est_vel_mps"]), 6) for r in rows]
    var = [round(float(r["est_pos_var_m2"]), 6) for r in rows]
    # Only the readings and the estimate are stored; truth is rebuilt from the settings.
    return {"config": {k: cfg[k] for k in ("steps", "dt_s", "x0_m", "v0_mps", "accel_mps2",
                                           "meas_every", "sigma_m", "seed", "est_q_m2ps3",
                                           "est_r_m2", "est_p0_pos_m2", "est_p0_vel_m2ps2", "compiler")},
            "meas": [None if m is None else round(m, 6) for m in meas],
            "est": est, "vel": vel, "var": var}


def seeds():
    text = (ROOT / "docs/VALIDATION.md").read_text()
    out = []
    for m in re.finditer(r"^\| (10\d\d) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \|$", text, re.M):
        out.append([int(m[1]), float(m[2]), float(m[3]), float(m[4]), float(m[5])])
    assert len(out) == 50, len(out)
    return out


def requirements():
    reg = {}
    for line in (ROOT / "docs/requirements.csv").read_text().splitlines():
        if line.startswith("#") or line.startswith("id,"):
            continue
        rid, pri, method, level = next(csv.reader([line]))
        reg[rid] = {"pri": pri, "method": method}
    for line in (ROOT / "docs/requirements.md").read_text().splitlines():
        m = re.match(r"^\| ([A-Z]{2,4}-\d{3}) \| ([MSC]) \| (.*?) \| (.*?) \|$", line)
        if m and m[1] in reg:
            reg[m[1]]["text"] = m[3]
    # Requirements the scope document does not word are worded in the baseline (bold IDs).
    for line in (ROOT / "docs/systems-engineering-baseline.md").read_text().splitlines():
        m = re.match(r"^\| \*\*([A-Z]{2,4}-\d{3})\*\* \| [MSC] \| (.*?) \|", line)
        if m and m[1] in reg and not reg[m[1]].get("text"):
            text = re.sub(r"\s*\*\((?:Parent|Child)[^)]*\)\*", "", m[2])
            reg[m[1]]["text"] = text.replace("**", "").replace("`", "").strip()
    # Last resort: the verification matrix's one-line note for that requirement.
    for line in (ROOT / "docs/systems-engineering-baseline.md").read_text().splitlines():
        m = re.match(r"^\| ([A-Z]{2,4}-\d{3}) \| [MSC] \| [^|]*\| [^|]*\| ([^|]+) \|$", line)
        if m and m[1] in reg and not reg[m[1]].get("text"):
            note = m[2].replace("`", "").strip()
            reg[m[1]]["text"] = note[:1].upper() + note[1:] + "."
    tests = defaultdict(list)
    for p in sorted((ROOT / "tests").rglob("*")):
        if p.suffix not in (".cpp", ".py"):
            continue
        src = p.read_text()
        rel = p.relative_to(ROOT).as_posix()
        if p.suffix == ".cpp":
            for m in re.finditer(r'TEST(?:_F)?\((\w+),\s*(\w+)\)\s*\{\s*RecordProperty\("requirements",\s*"([^"]+)"', src):
                for rid in m[3].split(","):
                    tests[rid.strip()].append([rel, f"{m[1]}.{m[2]}"])
        else:
            for m in re.finditer(r'((?:@pytest\.mark\.req\([^)]*\)\s*)+)(?:@[^\n]*\n\s*)*def (test_\w+)', src):
                for rid in re.findall(r'"([A-Z]{2,4}-\d{3})"', m[1]):
                    tests[rid].append([rel, m[2]])
    for rid, r in reg.items():
        r["tests"] = tests.get(rid, [])
        r.setdefault("text", "")
    return reg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default=str(ROOT / "out/run.csv"))
    args = ap.parse_args()
    data = {"run": recorded_run(args.run), "seeds": seeds(), "reqs": requirements()}
    src = (ROOT / "demo/src.html").read_text()
    blob = json.dumps(data, separators=(",", ":")).replace("</", "<\\/")
    engine = (ROOT / "demo/engine.js").read_text()
    page = src.replace("/*__ENGINE__*/", engine).replace("/*__DATA__*/null", blob)
    (ROOT / "demo/index.html").write_text(page)
    n = sum(1 for r in data["reqs"].values() if r["tests"])
    print(f"demo/index.html written; {n}/{len(data['reqs'])} requirements have a linked test")


if __name__ == "__main__":
    main()
