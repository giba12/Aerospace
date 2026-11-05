#!/usr/bin/env python3
"""Run `sim` over a set of random seeds and summarise how the filter performs (VAL-02, VAL-03).

  VAL-02  does the estimator help?   estimate RMSE <= 0.75 x raw-reading RMSE on EVERY seed (EST-008)
  VAL-03  is it honest about its own uncertainty?   pooled +/-2 sigma coverage >= 0.90 (EST-012)

The seeds come from seed_sets.py: `held-out` for acceptance, `tuning` for anything exploratory
(TST-012). The thresholds are the baseline's and are defined once, here; the acceptance tests import
them. Standard library only.

    python python/ensemble.py --sim build/sim --seeds held-out --markdown report.md
    python python/ensemble.py --sim build/sim --seeds tuning --label "reading every 50 steps" -- --meas-every 50

Everything after `--` is passed to `sim` unchanged. The exit code is 1 if VAL-02 or VAL-03 fails.
"""
import argparse
import datetime
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import analyze
import seed_sets

MAX_RATIO = 0.75     # EST-008 / VAL-02
MIN_COVERAGE = 0.90  # EST-012 / VAL-03
SEED_SETS = {"held-out": seed_sets.HELD_OUT_SEEDS, "tuning": seed_sets.TUNING_SEEDS}


def run_ensemble(sim_bin, seeds, flags=()):
    """Run `sim` once per seed with `flags` and return a list of per-seed dicts.

    Each dict has the seed, the analysis metrics (see analyze.compute_metrics) and the ratio of the
    estimate's RMSE to the raw readings' RMSE. Raises RuntimeError if a run fails. Returns also,
    as the second value, the sidecar of the first run (for the report's build information).
    """
    results, first_sidecar = [], None
    with tempfile.TemporaryDirectory() as work:
        for seed in seeds:
            csv_path = Path(work) / "run.csv"
            done = subprocess.run([str(sim_bin), *flags, "--seed", str(seed), "--out", str(csv_path)],
                                  capture_output=True, text=True)
            if done.returncode != 0:
                raise RuntimeError(f"seed {seed}: sim exited {done.returncode}: {done.stderr.strip()}")
            metrics = analyze.compute_metrics(analyze.read_rows(csv_path))
            if first_sidecar is None:
                first_sidecar = analyze.read_sidecar(str(csv_path))
            raw = metrics["rmse_meas_pos_m"]
            results.append({"seed": seed, **metrics,
                            "ratio": metrics["rmse_est_pos_m"] / raw if raw > 0 else None})
    return results, first_sidecar


def summarize(results, max_ratio=MAX_RATIO, min_coverage=MIN_COVERAGE):
    """Reduce per-seed results to the VAL-02 and VAL-03 verdicts.

    Coverage is POOLED: total errors inside the bars divided by total errors, not the average of
    the per-seed fractions (the two differ when seeds have different numbers of readings).
    """
    ratios = [r["ratio"] for r in results]
    if any(x is None for x in ratios):
        raise ValueError("a seed has a raw RMSE of 0 (exact sensor): the ratio is undefined")
    worst = max(results, key=lambda r: r["ratio"])
    inside = sum(r["n_within_2sigma"] for r in results)
    total = sum(r["n_measurements"] for r in results)
    return {
        "n_seeds": len(results),
        "ratio_min": min(ratios), "ratio_mean": sum(ratios) / len(ratios), "ratio_max": max(ratios),
        "worst_seed": worst["seed"],
        "seeds_over_limit": [r["seed"] for r in results if r["ratio"] > max_ratio],
        "pooled_inside": inside, "pooled_total": total, "pooled_coverage": inside / total,
        "coverage_per_seed_min": min(r["frac_pos_within_2sigma"] for r in results),
        "coverage_per_seed_max": max(r["frac_pos_within_2sigma"] for r in results),
        "max_ratio": max_ratio, "min_coverage": min_coverage,
        "val02_pass": all(x <= max_ratio for x in ratios),
        "val03_pass": inside / total >= min_coverage,
    }


def to_markdown(summary, results, label, seeds_name, flags, sidecar, of_total=None, per_seed=True):
    """A human-readable record of one ensemble run. `of_total` is the size of the whole seed set
    when only its first seeds were run, so a partial run can never pass for a full one."""
    s = summary
    partial = f" (**partial: the first {s['n_seeds']} of {of_total}**)" if of_total else ""
    verdict = lambda ok: "PASS" if ok else "**FAIL**"
    lines = [
        f"### {label}",
        "",
        f"- Seeds: `{seeds_name}`{partial} ({s['n_seeds']} seeds, {results[0]['seed']} to {results[-1]['seed']})",
        f"- `sim` flags: `{' '.join(flags) if flags else '(defaults: the reference scenario)'}`",
        f"- Build: {sidecar['compiler']}, source revision `{sidecar['source_revision']}`",
        f"- Run on {datetime.date.today().isoformat()}",
        "",
        "| Check | Requirement | Result | Measured | Limit |",
        "|---|---|---|---|---|",
        f"| VAL-02: estimate beats the raw readings on every seed | EST-008 | {verdict(s['val02_pass'])} "
        f"| worst ratio {s['ratio_max']:.3f} (seed {s['worst_seed']}); best {s['ratio_min']:.3f}, "
        f"mean {s['ratio_mean']:.3f} | at most {s['max_ratio']} |",
        f"| VAL-03: the error bars are honest (pooled +/-2 sigma coverage) | EST-012 | {verdict(s['val03_pass'])} "
        f"| {s['pooled_coverage']:.4f} ({s['pooled_inside']} of {s['pooled_total']}); per seed "
        f"{s['coverage_per_seed_min']:.3f} to {s['coverage_per_seed_max']:.3f} | at least {s['min_coverage']} |",
        "",
    ]
    over = s["seeds_over_limit"]
    if over:
        shown = ", ".join(map(str, over[:10])) + (f", ... ({len(over)} of {s['n_seeds']} in all)" if len(over) > 10 else "")
        lines += [f"Seeds over the ratio limit: {shown}", ""]
    if not per_seed:
        return "\n".join(lines)
    lines += ["<details><summary>Per-seed results</summary>", "",
              "| Seed | Raw RMSE (m) | Estimate RMSE (m) | Ratio | Coverage |", "|---|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['seed']} | {r['rmse_meas_pos_m']:.3f} | {r['rmse_est_pos_m']:.3f} "
                     f"| {r['ratio']:.3f} | {r['frac_pos_within_2sigma']:.3f} |")
    return "\n".join(lines + ["", "</details>", ""])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sim", required=True, help="path to the built `sim` executable")
    parser.add_argument("--seeds", choices=sorted(SEED_SETS), default="held-out")
    parser.add_argument("--max-seeds", type=int, metavar="N",
                        help="run only the first N seeds of the set (quick checks; the report says so)")
    parser.add_argument("--summary-only", action="store_true", help="omit the per-seed table from the report")
    parser.add_argument("--label", default=None, help="heading for the report")
    parser.add_argument("--json", metavar="PATH", help="also write the summary as JSON")
    parser.add_argument("--markdown", metavar="PATH", help="write the report here instead of stdout")
    parser.add_argument("flags", nargs=argparse.REMAINDER, help="after `--`: flags passed to sim")
    args = parser.parse_args(argv)
    flags = args.flags[1:] if args.flags[:1] == ["--"] else args.flags
    seeds = SEED_SETS[args.seeds]
    if args.max_seeds is not None and not 1 <= args.max_seeds <= len(seeds):
        print(f"ensemble: error: --max-seeds must be between 1 and {len(seeds)}", file=sys.stderr)
        return 1
    chosen = seeds[:args.max_seeds] if args.max_seeds else seeds
    try:
        results, sidecar = run_ensemble(args.sim, chosen, flags)
        summary = summarize(results)
    except (RuntimeError, ValueError, OSError, analyze.CsvFormatError) as e:
        print(f"ensemble: error: {e}", file=sys.stderr)
        return 1
    label = args.label or f"Ensemble on the {args.seeds} seeds"
    report = to_markdown(summary, results, label, args.seeds, flags, sidecar,
                         of_total=len(seeds) if len(chosen) < len(seeds) else None,
                         per_seed=not args.summary_only)
    if args.markdown:
        Path(args.markdown).write_text(report, encoding="utf-8")
    else:
        print(report)
    if args.json:
        Path(args.json).write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return 0 if summary["val02_pass"] and summary["val03_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
