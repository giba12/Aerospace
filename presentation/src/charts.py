"""Charts, drawn into a caller-supplied matplotlib Axes (so they are vector in the PDF)."""
import math
from common import C, FONT, run_data, seeds, scenarios, requirements, metrics


def _style(ax, fs):
    ax.set_facecolor(C["surface"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(C["line"])
    ax.tick_params(colors=C["ink2"], labelsize=fs, length=3)
    ax.grid(True, color=C["line"], lw=0.7, alpha=0.8)
    ax.set_axisbelow(True)


def error_chart(ax, fs=13):
    d = run_data()
    t = d["t"]
    meas_t = [x for x, m in zip(t, d["meas"]) if m is not None]
    meas_e = [m - p for m, p in zip(d["meas"], d["true_pos"]) if m is not None]
    est_e = [e - p for e, p in zip(d["est"], d["true_pos"])]
    two_sig = [2 * math.sqrt(v) for v in d["var"]]
    _style(ax, fs)
    ax.fill_between(t, [-s for s in two_sig], two_sig, color=C["blue_soft"], lw=0, label="filter's own ±2σ error bars")
    ax.scatter(meas_t, meas_e, s=11, color=C["orange"], zorder=3, label="raw sensor readings")
    ax.plot(t, est_e, color=C["blue"], lw=1.8, zorder=4, label="filter estimate")
    ax.axhline(0, color=C["ink"], lw=1)
    ax.set_xlabel("time (s)", fontsize=fs, color=C["ink2"])
    ax.set_ylabel("position error (m)", fontsize=fs, color=C["ink2"])
    ax.set_xlim(0, 100)
    ax.set_ylim(-15, 18)
    leg = ax.legend(loc="upper right", fontsize=fs - 1.5, frameon=True, framealpha=0.95, edgecolor=C["line"], ncol=1)
    for h in leg.legend_handles:
        try:
            h.set_sizes([30])
        except AttributeError:
            pass


def velocity_chart(ax, fs=13):
    d = run_data()
    _style(ax, fs)
    ax.plot(d["t"], d["true_vel"], color=C["ink"], lw=2, label="true velocity (never measured)")
    ax.plot(d["t"], d["vel"], color=C["blue"], lw=1.8, label="filter's estimate")
    ax.axvspan(0, 5, color=C["surface2"], zorder=0)
    ax.text(2.5, 1.2, "warm-up", ha="center", fontsize=fs - 2, color=C["ink3"])
    ax.set_xlabel("time (s)", fontsize=fs, color=C["ink2"])
    ax.set_ylabel("velocity (m/s)", fontsize=fs, color=C["ink2"])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 12.5)
    ax.legend(loc="lower right", fontsize=fs - 1.5, frameon=True, framealpha=0.95, edgecolor=C["line"])


def ratio_chart(ax, fs=13):
    s = seeds()
    _style(ax, fs)
    xs = [r[0] for r in s]
    ys = [r[3] for r in s]
    ax.axhline(0.75, color=C["bad"], lw=1.8, ls="--")
    ax.text(1001, 0.775, "required: ≤ 0.75 on every seed", color=C["bad"], fontsize=fs - 1.5, va="bottom")
    ax.vlines(xs, 0, ys, color=C["blue_soft"], lw=3)
    ax.scatter(xs, ys, s=26, color=C["blue"], zorder=3)
    w = max(s, key=lambda r: r[3])
    ax.annotate(f"worst: {w[3]:.3f}\n(seed {w[0]})", (w[0], w[3]), xytext=(w[0] + 4, 0.60),
                fontsize=fs - 2, color=C["ink2"], arrowprops=dict(arrowstyle="-", color=C["ink3"], lw=0.8))
    ax.set_ylim(0, 0.9)
    ax.set_xlim(999, 1052)
    ax.set_xlabel("held-out seed", fontsize=fs, color=C["ink2"])
    ax.set_ylabel("RMSE ratio\n(estimate ÷ raw)  lower = better", fontsize=fs - 1, color=C["ink2"])


def coverage_chart(ax, fs=13):
    s = seeds()
    _style(ax, fs)
    xs = [r[0] for r in s]
    ys = [r[4] for r in s]
    ax.axhline(0.90, color=C["bad"], lw=1.8, ls="--")
    ax.text(1001, 0.893, "required: ≥ 0.90 pooled", color=C["bad"], fontsize=fs - 1.5, va="top")
    ax.axhline(0.95, color=C["ink3"], lw=1.2, ls=":")
    ax.text(1051.5, 0.953, "perfect filter ≈ 0.95", color=C["ink3"], fontsize=fs - 2.5, ha="right", va="bottom")
    ax.vlines(xs, 0.85, ys, color=C["blue_soft"], lw=3)
    ax.scatter(xs, ys, s=26, color=C["blue"], zorder=3)
    ax.set_ylim(0.85, 1.03)
    ax.set_xlim(999, 1052)
    ax.set_xlabel("held-out seed", fontsize=fs, color=C["ink2"])
    ax.set_ylabel("share of errors inside\nthe filter's own ±2σ", fontsize=fs - 1, color=C["ink2"])


NICE = {"S-ACCEL-SMALL": "accel 0.1 m/s²", "S-ACCEL-LARGE": "accel 0.5 m/s²", "S-HIGH-NOISE": "noise 20 m",
        "S-SPARSE": "reading every 5 s", "S-WRONG-R": "filter told R wrong"}


def scenario_charts(ax_ratio, ax_cov, fs=13):
    sc = scenarios()
    held = seeds()
    ref_ratio = sum(r[3] for r in held) / len(held)
    ref_cov = 9807 / 10050
    rows = [("reference (held-out)", ref_ratio, ref_cov, True, True)] + \
           [(NICE[n], mean, cov, a, b) for n, _f, mean, _w, cov, a, b in sc]
    names = [r[0] for r in rows][::-1]
    for ax, idx, ok_i, limit, lab, better in ((ax_ratio, 1, 3, 0.75, "mean RMSE ratio (lower = better)", None),
                                              (ax_cov, 2, 4, 0.90, "share inside ±2σ (higher = better)", None)):
        _style(ax, fs)
        ax.grid(axis="y", visible=False)
        vals = [r[idx] for r in rows][::-1]
        oks = [r[ok_i] for r in rows][::-1]
        ax.barh(names, vals, color=[C["blue"] if o else C["bad"] for o in oks], height=0.62)
        ax.axvline(limit, color=C["ink"], lw=1.5, ls="--")
        for i, (v, o) in enumerate(zip(vals, oks)):
            ax.text(v + 0.015, i, f"{v:.2f}" + ("" if o else "  ✗"), va="center", fontsize=fs - 1,
                    color=C["ink"] if o else C["bad"], fontweight="normal" if o else "bold")
        ax.set_xlabel(lab, fontsize=fs - 1, color=C["ink2"])
        ax.set_xlim(0, 1.35 if idx == 1 else 1.15)
    ax_ratio.text(0.75, len(rows) - 0.4, "limit 0.75", fontsize=fs - 3, ha="center", color=C["ink"])
    ax_cov.text(0.90, len(rows) - 0.4, "limit 0.90", fontsize=fs - 3, ha="center", color=C["ink"])
    ax_cov.set_yticklabels([])


def requirements_chart(ax, fs=13):
    d = requirements()
    names = {"SYS": "System", "SEN": "Sensor", "EST": "Estimator", "SIM": "Dynamics", "RUN": "Runner", "OUT": "Output",
             "ANA": "Analysis", "CFG": "Config", "TST": "Testing", "NFR": "Non-functional", "DOC": "Docs"}
    items = sorted(d.items(), key=lambda kv: kv[1][1])
    _style(ax, fs)
    ax.grid(axis="y", visible=False)
    ys = range(len(items))
    ax.barh(list(ys), [m for _, (m, t) in items], color=C["blue"], height=0.62, label="Must")
    ax.barh(list(ys), [t - m for _, (m, t) in items], left=[m for _, (m, t) in items], color=C["blue_soft"],
            height=0.62, label="Should / Could")
    ax.set_yticks(list(ys))
    ax.set_yticklabels([names[k] for k, _ in items], fontsize=fs)
    for y, (_, (m, t)) in zip(ys, items):
        ax.text(t + 0.2, y, str(t), va="center", fontsize=fs - 1, color=C["ink2"])
    ax.set_xlim(0, 15)
    ax.set_xlabel("requirements", fontsize=fs - 1, color=C["ink2"])
    ax.legend(loc="lower right", fontsize=fs - 2, frameon=False)
