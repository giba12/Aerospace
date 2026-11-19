"""LinkedIn document: a 4:5 portrait PDF carousel (1080 x 1350 px per page), all vector."""
import sys, textwrap
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle

sys.path.insert(0, str(Path(__file__).parent))
import charts, sysml, graphics
from common import C, ROOT
from content import *

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["pdf.fonttype"] = 42
PW, PH, UW, UH = 10.8, 13.5, 108, 135
TOTAL = 16
OUT = ROOT / "presentation" / "sensor-sim-linkedin-carousel.pdf"


class Page:
    def __init__(self, n, kicker, title, dark=False):
        self.dark, self.n = dark, n
        self.bg = C["navy"] if dark else C["bg"]
        self.ink = "#ffffff" if dark else C["ink"]
        self.ink2 = C["navy_ink"] if dark else C["ink2"]
        self.fig = plt.figure(figsize=(PW, PH))
        self.fig.patch.set_facecolor(self.bg)
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, UW); self.ax.set_ylim(0, UH); self.ax.axis("off")
        self.ax.add_patch(Rectangle((0, 130.5), UW, 4.5, fc=C["orange"] if not dark else C["blue"], ec="none"))
        y = 125
        if kicker:
            self.ax.text(7, y, kicker.upper(), fontsize=16, fontweight="bold", color=C["orange"] if not dark else "#7fb2ee", va="center")
        self.y = y - 4
        if title:
            self.y = self.para(7, y - 3, title, 35, 94, weight="bold", color=self.ink, lh=1.18)
        self.ax.text(7, 5, "sensor-sim  ·  educational simulation, not flight software", fontsize=12.5, color=self.ink2, va="center")
        self.ax.text(101, 5, f"{n} / {TOTAL}" + ("   →" if n < TOTAL else ""), fontsize=14, color=self.ink2, ha="right", va="center", fontweight="bold")

    def para(self, x, ytop, text, size, width, weight="normal", color=None, lh=1.38, family=None, ha="left"):
        color = color or self.ink
        cpl = max(8, int(width / 10 * 72 / (size * 0.60)))
        lines = []
        for chunk in text.split("\n"):
            lines += textwrap.wrap(chunk, cpl) or [""]
        step = size * lh / 72 * 10
        y = ytop
        for ln in lines:
            self.ax.text(x if ha == "left" else x + width / 2, y - step / 2, ln, fontsize=size, color=color, fontweight=weight,
                         va="center", ha=ha, family=family or "DejaVu Sans")
            y -= step
        return y

    def card(self, x, y, w, h, fc=None, ec=None, lw=1.4, r=1.8):
        self.ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fc or C["surface"],
                                         ec=ec or C["line"], lw=lw, zorder=1))

    def sub(self, x, y, w, h):
        a = self.fig.add_axes([x / UW, y / UH, w / UW, h / UH])
        return a

    def tile(self, x, y, w, h, big, small, color=None, bigsize=40):
        self.card(x, y, w, h)
        self.ax.text(x + w / 2, y + h * 0.66, big, fontsize=bigsize, fontweight="bold", color=color or C["blue_ink"], ha="center", va="center")
        self.para(x + 1.5, y + h * 0.40, small, 15, w - 3, color=C["ink2"], ha="center", lh=1.25)

    def diagram(self, fn, caption, size=19):
        d = self.fig.add_axes([2.2 / UW, 31 / UH, 103.6 / UW, 77.7 / UH])
        fn(d)
        self.para(7, 28.5, caption, size, 94, color=self.ink, lh=1.32)


def save(pdf, p):
    import os
    if os.environ.get("PREVIEW_DIR"):
        p.fig.savefig(f"{os.environ['PREVIEW_DIR']}/c{p.n:02d}.png", dpi=50, facecolor=p.bg)
    pdf.savefig(p.fig, facecolor=p.bg)
    plt.close(p.fig)


def build():
    pdf = PdfPages(OUT)
    pdf.infodict().update(Title="sensor-sim: estimating what a sensor can't see", Subject="Project walkthrough",
                          Keywords="Kalman filter, C++17, SysML, systems engineering, testing")

    # 1 -------------------------------------------------------------- title
    p = Page(1, "Project walkthrough", None, dark=True)
    p.para(7, 118, "Estimating what a sensor can't see", 50, 94, weight="bold", color="#ffffff", lh=1.12)
    p.para(7, 88, "A sensor and Kalman-filter simulator, built with systems-engineering rigor: requirements, SysML models, "
                  "and tests that prove the claims.", 22, 90, color=C["navy_ink"], lh=1.35)
    p.card(7, 41, 45, 30, fc=C["navy2"], ec=C["navy2"])
    p.card(56, 41, 45, 30, fc=C["navy2"], ec=C["navy2"])
    p.ax.text(29.5, 62, f"{M['rmse_meas_pos_m']:.2f} m → {M['rmse_est_pos_m']:.2f} m", fontsize=26, fontweight="bold", color="#ffffff", ha="center", va="center")
    p.para(9.5, 56, "position error: raw sensor readings vs the filter's estimate", 15.5, 40, color=C["navy_ink"], ha="center", lh=1.25)
    p.ax.text(78.5, 62, f"{M['rmse_est_vel_mps'] if False else 1.20:.2f} m/s", fontsize=26, fontweight="bold", color="#ffffff", ha="center", va="center")
    p.para(58.5, 56, "velocity error, for a quantity the sensor never measures", 15.5, 40, color=C["navy_ink"], ha="center", lh=1.25)
    p.ax.text(7, 33, "C++17   ·   Python   ·   SysML   ·   GoogleTest   ·   CI", fontsize=17, color="#7fb2ee", va="center", fontweight="bold")
    p.para(7, 24, DISCLAIMER, 14, 94, color=C["navy_dim"])
    save(pdf, p)

    # 2 -------------------------------------------------------------- problem
    p = Page(2, "The problem", "Noisy readings, hidden state")
    pts = ["A 1-D object moves at 10 m/s.",
           "A simulated sensor reports its position every 0.5 s, with 5 m of Gaussian noise.",
           "The estimator sees only those readings, never the truth.",
           "The job: recover position and velocity, and say how wrong the answer might be."]
    y = p.y - 2
    for t in pts:
        p.ax.add_patch(plt.Circle((9.5, y - 1.6), 0.9, color=C["orange"], zorder=3))
        y = p.para(12, y, t, 23, 88, lh=1.32) - 2.4
    # pipeline
    base = 40
    boxes = [("Truth", "position, velocity", C["ink"], "#ffffff"), ("Sensor", "+5 m noise, seeded", C["orange"], "#ffffff"),
             ("Kalman filter", "estimate + doubt", C["blue"], "#ffffff"), ("Compare", "estimate vs truth", C["good"], "#ffffff")]
    bw, g = 20.5, 4.5
    for i, (a, b, fc, tc) in enumerate(boxes):
        x = 7 + i * (bw + g)
        p.ax.add_patch(FancyBboxPatch((x, base), bw, 17, boxstyle="round,pad=0,rounding_size=1.6", fc=fc, ec="none", zorder=2))
        p.ax.text(x + bw / 2, base + 11, a, fontsize=17, fontweight="bold", color=tc, ha="center", va="center", zorder=3)
        p.para(x + 1, base + 7.2, b, 12.5, bw - 2, color=tc, ha="center", lh=1.15)
        if i < 3:
            p.ax.annotate("", xy=(x + bw + g - 0.4, base + 8.5), xytext=(x + bw + 0.4, base + 8.5), arrowprops=dict(arrowstyle="-|>", color=C["ink"], lw=2))
    p.ax.annotate("", xy=(7 + 3 * (bw + g) + bw / 2, base - 1.2), xytext=(7 + bw / 2, base - 1.2),
                  arrowprops=dict(arrowstyle="-|>", color=C["bad"], lw=2.2, ls="--", connectionstyle="arc3,rad=0.0"))
    p.ax.text(54, base - 5.5, "Truth reaches the comparison only. Never the filter.", fontsize=16, color=C["bad"], ha="center", va="center", fontweight="bold")
    p.card(7, 11, 94, 15, fc=C["surface2"], ec=C["line"])
    p.para(10, 24.2, "Why it matters: a filter that quietly peeks at the truth would look brilliant and prove nothing. "
                     "The design makes peeking impossible.", 17.5, 88, lh=1.3)
    save(pdf, p)

    # 3 -------------------------------------------------------------- how it works
    p = Page(3, "The idea", "Two steps, repeated")
    T = p.y - 2
    specs = [("1  Predict", C["orange_ink"], "x ← F x\nP ← F P Fᵀ + Q", 11, 36,
              "Move the guess forward by dt using constant velocity. The doubt P grows, because time passes with no new information."),
             ("2  Update", C["blue_ink"], "K = P Hᵀ / (H P Hᵀ + R)\nx ← x + K (z − H x)\nP ← (I − KH) P (I − KH)ᵀ + K R Kᵀ", 17, 44,
              "A reading z arrives. Pull the guess toward it by the gain K, which weighs the reading against the doubt. P shrinks.")]
    top = T
    for hd, col, eq, eqh, ch, expl in specs:
        p.card(7, top - ch, 94, ch, ec=col, lw=2.2)
        p.ax.text(11, top - 5, hd, fontsize=26, fontweight="bold", color=col, va="center")
        p.card(11, top - 9.5 - eqh, 86, eqh, fc=C["surface2"], ec="none", r=1.2)
        p.ax.text(14, top - 9.5 - eqh / 2, eq, fontsize=17, family="DejaVu Sans Mono", color=C["ink"], va="center", linespacing=1.5)
        p.para(11, top - 12.5 - eqh, expl, 17, 86, color=C["ink2"], lh=1.3)
        top -= ch + 4
    p.para(7, top + 1, "State x = [position, velocity]. The sensor reads position only; velocity is inferred from how positions change. "
                       "The Joseph-form update keeps P symmetric and non-negative.", 15, 94, color=C["ink2"], lh=1.3)
    save(pdf, p)

    # 4 -------------------------------------------------------------- result
    p = Page(4, "Result", "5.46 m of noise down to 2.32 m")
    a = p.sub(13, 61, 87, 49); charts.error_chart(a, fs=12)
    p.tile(7, 34, 29, 22, f"{M['improvement_ratio']:.2f}", "RMSE ratio, estimate ÷ raw")
    p.tile(39, 34, 29, 22, f"{M['frac_pos_within_2sigma']*100:.0f} %", "of errors inside the filter's own ±2σ", bigsize=36)
    p.tile(71, 34, 30, 22, f"{M['n_measurements']}", "readings, seed 42 (one run, one seed)", bigsize=36)
    p.para(7, 30, "Orange dots are raw readings, wandering up to ±15 m. The blue line is the estimate, hugging zero inside the shaded "
                  "error bars the filter reports about itself.", 17, 94, color=C["ink2"], lh=1.3)
    save(pdf, p)

    # 5 -------------------------------------------------------------- velocity
    p = Page(5, "Result", "It recovers a speed the sensor never measures")
    a = p.sub(13, 59, 87, 45); charts.velocity_chart(a, fs=12)
    p.tile(7, 33, 45, 21, "1.20 m/s", "velocity RMSE over the whole run", bigsize=34)
    p.tile(56, 33, 45, 21, "≈ 5 s", "to settle within about 1 m/s of the true 10 m/s", bigsize=34)
    p.para(7, 29, "Position readings only, yet the filter infers velocity from how those readings change.", 18, 94, color=C["ink2"], lh=1.3)
    save(pdf, p)

    # 6 -------------------------------------------------------------- 50 seeds
    p = Page(6, "Validation", "Not one lucky seed: 50 held-out seeds")
    a = p.sub(15, 75, 85, 28); charts.ratio_chart(a, fs=11)
    b = p.sub(15, 41, 85, 28); charts.coverage_chart(b, fs=11)
    p.para(7, 31, f"Worst ratio {RATIO_WORST:.3f} against a required 0.75. Pooled coverage {COV_POOLED*100:.1f} % against a required 90 % "
                  "(a perfect filter scores about 95 %).", 17.5, 94, lh=1.3)
    p.para(7, 20, "The seeds were never used to tune anything, and a test checks that they stay disjoint from the tuning set.", 15.5, 94, color=C["ink2"], lh=1.3)
    save(pdf, p)

    # 7 -------------------------------------------------------------- limits
    p = Page(7, "Limits, reported honestly", "Where the filter breaks")
    a = p.sub(21, 66, 36, 44); b = p.sub(63, 66, 36, 44)
    charts.scenario_charts(a, b, fs=11)
    p.para(7, 58, "Red bars miss the acceptance limit.", 18, 94, weight="bold", lh=1.3)
    y = 52
    for t in ["Accelerating truth (0.5 m/s²): the constant-velocity model is wrong, so the filter is no better than raw readings.",
              "Wrong noise setting (R = 1, true 25): the estimate still helps, but its error bars lie. Only 35 % of errors fall inside.",
              "A reading every 5 s: coverage stays honest, but there is little to average (ratio 0.81)."]:
        p.ax.add_patch(plt.Circle((9.5, y - 1.5), 0.8, color=C["bad"], zorder=3))
        y = p.para(12, y, t, 16.5, 88, lh=1.28) - 1.8
    p.para(7, 14, "Measured on 200 tuning seeds (docs/VALIDATION.md).", 14, 94, color=C["ink2"])
    save(pdf, p)

    # 8 -------------------------------------------------------------- design
    p = Page(8, "Architecture and design", "Six design choices that carry the weight")
    cw, ch = 45.5, 26.5
    T = p.y - 2
    for i, (h, t) in enumerate(DESIGN):
        x = 7 + (i % 2) * (cw + 3)
        y = T - (i // 2) * (ch + 2.5) - ch
        p.card(x, y, cw, ch)
        p.ax.add_patch(Rectangle((x, y + ch - 1.3), cw, 1.3, fc=C["blue"], ec="none", zorder=2))
        p.para(x + 2.2, y + ch - 3, h, 18.5, cw - 4, weight="bold", color=C["blue_ink"], lh=1.2)
        p.para(x + 2.2, y + ch - 10.2, t, 14.6, cw - 4, color=C["ink2"], lh=1.27)
    p.para(7, 21, "Layout: include/simulator + src (the simcore library, all logic), python/ (analysis), tests/ (C++ and pytest), "
                  "docs/ (requirements, baseline).", 14, 94, color=C["ink2"], lh=1.25)
    save(pdf, p)

    # 9..12 SysML ------------------------------------------------------ diagrams
    p = Page(9, "SysML · block definition diagram", "System structure")
    p.diagram(lambda ax: sysml.bdd(ax, (CPP, PY)), "Three blocks make up the system: the C++17 simcore library, Python analysis tools, and the verification "
                                                 "layer. Each part has one job and a small set of operations.")
    save(pdf, p)
    p = Page(10, "SysML · internal block diagram", "Data flow, with a firewall")
    p.diagram(sysml.ibd, "The Runner hands the sensor the truth and the estimator only the measurement. The red dashed flow is "
                         "the one that must not exist: the compiler enforces it.")
    save(pdf, p)
    p = Page(11, "SysML · state machine", "How the estimator behaves")
    p.diagram(sysml.stm, "Predict grows the doubt, update shrinks it. Out-of-order or non-finite readings are refused and "
                         "leave the state untouched (a test compares against an untouched twin).")
    save(pdf, p)
    p = Page(12, "SysML · requirements diagram", "From requirement to proof")
    p.diagram(sysml.req, f"{N_REQ} requirements, {N_MUST} of them Must. Every Must is verified by at least one test, and CI fails the "
                         "build if one loses its test.")
    save(pdf, p)

    # 13 ------------------------------------------------------------ test strategy
    p = Page(13, "Testing", "How the claims get proved")
    p.diagram(graphics.test_strategy, f"{N_TESTS} automated tests across four layers. Each test names the requirement it verifies, "
                                       "and a script checks the citations.")
    save(pdf, p)

    # 14 ------------------------------------------------------------ test cases
    p = Page(14, "Test cases", "Four tests worth reading")
    cw, ch = 45.5, 46.5
    T = p.y - 2
    for i, (reqs, name, given, expect, why) in enumerate(TESTCASES[:4]):
        x = 7 + (i % 2) * (cw + 3)
        y = T - (i // 2) * (ch + 2.5) - ch
        p.card(x, y, cw, ch)
        p.ax.add_patch(FancyBboxPatch((x + 2, y + ch - 6.0), 25, 3.8, boxstyle="round,pad=0,rounding_size=1", fc=C["blue_soft"], ec="none", zorder=2))
        p.ax.text(x + 14.5, y + ch - 4.1, reqs, fontsize=10, fontweight="bold", color=C["blue_ink"], ha="center", va="center", zorder=3)
        ty = y + ch - 7.2
        for ln in name.split("\n"):
            p.ax.text(x + 2, ty - 1.1, ln, fontsize=11, fontweight="bold", family="DejaVu Sans Mono", va="center")
            ty -= 2.7
        ty = p.para(x + 2, ty - 0.6, given, 13.2, cw - 4, color=C["ink2"], lh=1.22)
        ty = p.para(x + 2, ty - 0.8, expect, 13.2, cw - 4, color=C["good"], weight="bold", lh=1.22)
        p.para(x + 2, ty - 0.8, why, 12.8, cw - 4, color=C["ink"], lh=1.22)
    save(pdf, p)

    # 15 ------------------------------------------------------------ numbers + stack
    p = Page(15, "By the numbers", "Evidence and tech stack")
    T = p.y - 2
    for i, (big, small) in enumerate(KEY_NUMBERS):
        p.tile(7 + (i % 2) * 48, T - (i // 2) * 23 - 21, 46, 21, big, small, bigsize=36)
    p.ax.text(7, 59, "Tech stack", fontsize=24, fontweight="bold", color=C["ink"], va="center")
    cw = 22
    for i, (grp, items) in enumerate(STACK):
        x = 7 + i * (cw + 2)
        p.card(x, 13, cw, 41)
        p.ax.text(x + 2, 50, grp.upper(), fontsize=12.5, fontweight="bold", color=C["orange_ink"], va="center")
        y = 46
        for it in items:
            y = p.para(x + 2, y, it, 14.5, cw - 3.5, weight="bold", color=C["blue_ink"], lh=1.2) - 2.6
    save(pdf, p)

    # 16 ------------------------------------------------------------ close
    p = Page(16, "Takeaways", None, dark=True)
    p.para(7, 118, "What this project is really about", 40, 94, weight="bold", color="#ffffff", lh=1.15)
    y = 92
    for h, t in [("Make claims checkable.", "Every number here comes from a recorded run, a test, or a CI job. A test even fails if the README drifts."),
                 ("Model before you build.", "SysML structure, flow, behaviour and requirements, then code that follows them."),
                 ("Report the failures.", "Accelerating targets and mis-set noise are in the validation record, not hidden.")]:
        p.ax.add_patch(plt.Circle((9.5, y - 2.2), 1.1, color=C["orange"]))
        p.ax.text(13, y - 2.2, h, fontsize=23, fontweight="bold", color="#ffffff", va="center")
        y = p.para(13, y - 6.5, t, 17.5, 86, color=C["navy_ink"], lh=1.32) - 5
    p.card(7, 13, 94, 18, fc=C["navy2"], ec=C["navy2"])
    p.para(10, 28.5, "Next: scenario records (VAL-05/06/08), tagging the baseline, and a model that handles accelerating targets. "
                     "Questions or feedback are welcome in the comments.", 16.5, 88, color="#ffffff", lh=1.32)
    save(pdf, p)
    pdf.close()
    print("wrote", OUT)


if __name__ == "__main__":
    build()
