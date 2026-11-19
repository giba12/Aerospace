"""SysML 1.x diagrams drawn with matplotlib patches into a 100 x 75 data-coordinate canvas.

Notation used: bdd (block definition: composition = filled diamond), ibd (parts, proxy ports, item
flows), req (containment, <<verify>>, <<satisfy>>), act (actions, decisions, initial/final nodes),
stm (states, transitions with trigger [guard] / effect). Text sizes are chosen for a canvas shown
about 10 inches wide.
"""
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon, Circle, FancyArrowPatch, Arc
from common import C, FONT

NAVY, FILL, DASH = C["ink"], "#ffffff", (0, (4, 3))
W, H = 100, 75


def canvas(ax):
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ax.axis("off")


def frame(ax, kind, title):
    ax.add_patch(Rectangle((0.5, 0.5), W - 1, H - 1, fc=C["surface"], ec=NAVY, lw=1.6, zorder=0))
    label = f"{kind} {title}"
    wtab = 1.3 + 0.88 * len(label)
    ax.add_patch(Polygon([(0.5, H - 0.5), (0.5 + wtab, H - 0.5), (0.5 + wtab, H - 4.2), (0.5 + wtab - 2, H - 5.6),
                          (0.5, H - 5.6)], fc=C["surface2"], ec=NAVY, lw=1.2, zorder=1))
    ax.text(1.6, H - 3.0, label, fontsize=12, fontweight="bold", color=NAVY, va="center", zorder=2)


def box(ax, x, y, w, h, name, stereo=None, lines=(), fs=13, fill=FILL, ec=NAVY, lw=1.5, bold=True, namec=NAVY, z=2,
        dashed=False):
    """A block-like box: optional <<stereotype>>, bold name, then compartment lines."""
    ax.add_patch(Rectangle((x, y), w, h, fc=fill, ec=ec, lw=lw, zorder=z, ls=DASH if dashed else "-"))
    top = y + h - 1.0
    if stereo:
        ax.text(x + w / 2, top - 0.5, f"«{stereo}»", ha="center", va="center", fontsize=fs - 3, style="italic",
                color=C["ink2"], zorder=z + 1)
        top -= 2.0
    ax.text(x + w / 2, top - 1.1 if not lines else top - 1.1, name, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", color=namec, zorder=z + 1)
    if lines:
        ly = top - 2.7
        ax.plot([x, x + w], [ly, ly], color=ec, lw=1, zorder=z + 1)
        for i, s in enumerate(lines):
            ax.text(x + 1.0, ly - 1.5 - i * 2.0, s, ha="left", va="center", fontsize=fs - 3, color=C["ink2"],
                    zorder=z + 1, family="DejaVu Sans Mono")


def node(ax, x, y, w, h, text, fs=11.5, fill=FILL, ec=NAVY, lw=1.4, r=1.6, z=2, color=NAVY, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0,rounding_size={r}", fc=fill, ec=ec, lw=lw, zorder=z))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, color=color, zorder=z + 1,
            fontweight=weight, linespacing=1.15)


def arrow(ax, p0, p1, style="-|>", ls="-", color=NAVY, lw=1.5, ms=14, rad=0.0, z=3, shrinkA=0, shrinkB=0):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=ms, ls=ls, color=color, lw=lw,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z, shrinkA=shrinkA, shrinkB=shrinkB))


def line(ax, pts, color=NAVY, lw=1.5, ls="-", z=3):
    ax.plot([p[0] for p in pts], [p[1] for p in pts], color=color, lw=lw, ls=ls, zorder=z, solid_capstyle="butt")


def polyline_arrow(ax, pts, **kw):
    """Straight segments with the arrowhead on the last one."""
    if len(pts) > 2:
        line(ax, pts[:-1], color=kw.get("color", NAVY), lw=kw.get("lw", 1.5), ls=kw.get("ls", "-"))
    arrow(ax, pts[-2], pts[-1], **kw)


def label(ax, x, y, s, fs=10.5, color=C["ink2"], ha="center", va="center", bg=True, weight="normal", style="normal", z=6):
    kw = dict(boxstyle="round,pad=0.15", fc=C["surface"], ec="none", alpha=0.92) if bg else None
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, color=color, zorder=z, fontweight=weight, style=style, bbox=kw,
            linespacing=1.15)


def diamond(ax, x, y, hw, hh, fill=NAVY, ec=NAVY, z=3):
    ax.add_patch(Polygon([(x - hw, y), (x, y + hh), (x + hw, y), (x, y - hh)], fc=fill, ec=ec, lw=1.4, zorder=z))


def comp_end(ax, x, y, direction):
    """Filled composition diamond whose tip touches (x, y), opening toward `direction` ('down' or 'right')."""
    a, b = 1.1, 1.7
    if direction == "down":
        pts = [(x, y), (x - a, y - b / 2), (x, y - b), (x + a, y - b / 2)]
    else:
        pts = [(x, y), (x + b / 2, y + a), (x + b, y), (x + b / 2, y - a)]
    ax.add_patch(Polygon(pts, fc=NAVY, ec=NAVY, lw=1, zorder=4))


# --------------------------------------------------------------------------------------------- bdd
def bdd(ax, counts):
    canvas(ax)
    frame(ax, "bdd", "[package] sensor-sim  »  System structure")
    box(ax, 33, 57, 34, 9.5, "Sensor-Sim", "system", fs=14, fill=C["blue_soft"])
    cols = [
        (1.5, "simcore", "C++17 library", [("Dynamics", "propagate()"), ("NoisySensor", "observe()"),
                                           ("KalmanEstimator", "predict()  update()"), ("Runner", "run()"),
                                           ("CsvRecorder", "write_row()  commit()"), ("Cli", "cli_main()")]),
        (35, "Analysis tools", "Python 3.12", [("analyze.py", "metrics, plot"), ("kalman_oracle.py", "exact re-check"),
                                               ("ensemble.py", "50-seed validation"), ("seed_sets.py", "tuning ≠ held-out")]),
        (68.5, "Verification", "tests + CI", [("GoogleTest", f"{counts[0]} C++ tests"), ("pytest", f"{counts[1]} Python tests"),
                                              ("req_trace.py", "requirement gate"), ("CI (GitHub)", "gcc · clang · container")]),
    ]
    for x, name, st, kids in cols:
        w, py, ph = 30, 45.5, 8
        box(ax, x, py, w, ph, name, st, fs=13, fill="#eef3fa")
        polyline_arrow(ax, [(50, 57), (50, 54.5), (x + w / 2, 54.5), (x + w / 2, py + ph)], style="-", lw=1.5)
        comp_end(ax, 50, 57, "down")
        sx = x + 2.2
        step, bh = 6.4, 5.4
        for i, (kn, kop) in enumerate(kids):
            ky = py - 1.4 - (i + 1) * step + (step - bh)
            box(ax, x + 5, ky, w - 5, bh, "", None, fs=12, fill=FILL, lw=1.3)
            ax.text(x + 5 + (w - 5) / 2, ky + 3.6, kn, ha="center", va="center", fontsize=11.5, fontweight="bold", zorder=5)
            ax.text(x + 5 + (w - 5) / 2, ky + 1.3, kop, ha="center", va="center", fontsize=9, color=C["ink2"], zorder=5)
            line(ax, [(sx, ky + bh / 2), (x + 5, ky + bh / 2)], lw=1.3)
            last = ky + bh / 2
        line(ax, [(sx, py - 1.7), (sx, last)], lw=1.3)
        comp_end(ax, sx, py, "down")
    ax.text(50, 2.4, "Filled diamond = composition (the part cannot exist without the whole).  "
                     "Under each part: its key operations.", ha="center", fontsize=9.6, color=C["ink2"])


# --------------------------------------------------------------------------------------------- ibd
def ibd(ax):
    canvas(ax)
    frame(ax, "ibd", "[block] Sensor-Sim  »  Data flow (what each part may see)")
    ax.add_patch(FancyBboxPatch((1.5, 25), 97, 42, boxstyle="round,pad=0,rounding_size=1", fc="#f7f9fc", ec=C["ink3"], lw=1.2, ls=DASH, zorder=1))
    ax.text(3, 65, "simcore", fontsize=11.5, style="italic", color=C["ink2"], va="center")
    P = dict(dyn=(3, 50, 20, 11), sen=(3, 30, 20, 11), run=(38, 36, 24, 20), est=(77, 36, 20, 20), rec=(38, 27.5, 24, 6))
    box(ax, *P["dyn"], "Dynamics", "part", fs=12.5)
    box(ax, *P["sen"], "NoisySensor", "part", fs=12.5)
    box(ax, 38, 38, 24, 22, "Runner", "part", fs=14, fill=C["blue_soft"])
    box(ax, 77, 38, 20, 22, "KalmanEstimator", "part", fs=11.2)
    box(ax, 38, 26.5, 24, 8, "CsvRecorder", "part", fs=12)
    # Dynamics -> Runner
    arrow(ax, (23, 56), (38, 56), lw=1.6)
    label(ax, 30.5, 58.8, "TrueState", 10.5)
    # Runner -> Sensor (truth, const) and Sensor -> Runner (Measurement?)
    arrow(ax, (38, 47), (23, 38.5), lw=1.6)
    label(ax, 30.3, 46.6, "TrueState\n(const)", 10)
    arrow(ax, (23, 33.5), (38, 41.5), lw=1.6)
    label(ax, 32.5, 33.6, "Measurement?", 10)
    # Runner <-> Estimator
    arrow(ax, (62, 57), (77, 57), lw=1.6, color=C["bad"], ls=DASH)
    label(ax, 69.5, 59.6, "TrueState", 10.5, color=C["bad"])
    ax.text(69.5, 57, "✗", color=C["bad"], fontsize=17, fontweight="bold", ha="center", va="center", zorder=7,
            bbox=dict(boxstyle="circle,pad=0.1", fc=C["surface"], ec="none"))
    arrow(ax, (62, 51), (77, 51), lw=1.6)
    label(ax, 69.5, 53.4, "Measurement", 10.5)
    arrow(ax, (77, 44), (62, 44), lw=1.6)
    label(ax, 69.5, 46.4, "Estimate", 10.5)
    # Runner -> Recorder
    arrow(ax, (50, 38), (50, 34.5), lw=1.6)
    label(ax, 56, 36.2, "row", 10)
    # SYS-002 note
    ax.add_patch(FancyBboxPatch((66, 28), 31.5, 7.4, boxstyle="round,pad=0,rounding_size=0.8", fc=C["bad_bg"], ec=C["bad"], lw=1.1, zorder=2))
    ax.text(81.7, 31.7, "SYS-002: ground truth never reaches\nthe estimator. Enforced at compile\ntime (static_assert).",
            fontsize=9.2, color=C["bad"], ha="center", va="center", zorder=3, linespacing=1.2)
    # external files and tools
    box(ax, 3, 6, 20, 11, "run.csv", "file", ["+ run.csv.config.json"], fs=12.5, fill="#fff7e6")
    box(ax, 36, 11, 26, 9, "analyze.py", "python", fs=12.5)
    box(ax, 36, 2.8, 26, 7, "kalman_oracle.py", "python", fs=11.5)
    box(ax, 75, 11, 23, 9, "metrics.json\nplot.png", "file", fs=11, fill="#fff7e6", bold=False)
    box(ax, 75, 2.8, 23, 7, "PASS / FAIL", "cross-check", fs=11, fill=C["good_bg"], ec=C["good"], namec=C["good"])
    polyline_arrow(ax, [(50, 26.5), (50, 22), (13, 22), (13, 17.2)], lw=1.6)
    arrow(ax, (23, 12.5), (36, 15.5), lw=1.6)
    arrow(ax, (23, 9.5), (36, 6.5), lw=1.6)
    arrow(ax, (62, 15.5), (75, 15.5), lw=1.6)
    arrow(ax, (62, 6.3), (75, 6.3), lw=1.6)
    label(ax, 29.5, 17.4, "reads", 9.5)
    label(ax, 68.5, 17.4, "writes", 9.5)
    label(ax, 68.5, 8.2, "agrees?", 9.5)
    label(ax, 31, 23.4, "written by CsvRecorder", 9.5)


# --------------------------------------------------------------------------------------------- req
def req(ax):
    canvas(ax)
    frame(ax, "req", "[package] Requirements  »  Parent, child, and the test that proves it")
    cw, gap = 22.8, 1.9
    xs = [1.9 + i * (cw + gap) for i in range(4)]

    def rbox(x, y, w, h, rid, text, fs=10):
        ax.add_patch(Rectangle((x, y), w, h, fc=FILL, ec=NAVY, lw=1.5, zorder=2))
        ax.text(x + w / 2, y + h - 1.4, "«requirement»", ha="center", va="center", fontsize=8.5, style="italic", color=C["ink2"], zorder=3)
        ax.text(x + w / 2, y + h - 3.6, rid, ha="center", va="center", fontsize=11.5, fontweight="bold", zorder=3)
        ax.text(x + w / 2, y + (h - 5) / 2, text, ha="center", va="center", fontsize=fs, zorder=3, color=NAVY, linespacing=1.2)

    # parents (row 1) and children (row 2)
    py, ph, cy, chh = 55.5, 11, 33.5, 15.5
    rbox(xs[0], py, cw, ph, "SYS-002", "The estimator uses\nmeasurements only;\ntruth is for evaluation")
    rbox(xs[1], py, 2 * cw + gap, ph, "SYS-004", "Quantify performance against the raw sensor\nand against the estimator's own uncertainty")
    rbox(xs[3], py, cw, ph, "SYS-006", "All docs say: educational\nsimulation, no flight\nqualification claimed")
    rbox(xs[0], cy, cw, chh, "EST-002", "The estimator's update\ninterface cannot take\nground truth\n(compile-time check)")
    rbox(xs[1], cy, cw, chh, "EST-008", "RMSE(estimate) ≤ 0.75 ×\nRMSE(raw), on EVERY\nheld-out seed")
    rbox(xs[2], cy, cw, chh, "EST-012", "≥ 90 % of position errors\ninside the filter's own\n±2σ, pooled over seeds")
    rbox(xs[3], cy, cw, chh, "DOC-001", "README has purpose,\ndata flow, limits and\nthe SYS-006 statement")
    # containment lines with the crossed-circle end at the parent
    def contain(px_, py_, cx_, cy_):
        line(ax, [(px_, py_), (px_, (py_ + cy_) / 2), (cx_, (py_ + cy_) / 2), (cx_, cy_)], lw=1.4)
        ax.add_patch(Circle((px_, py_ - 1.3), 1.3, fc=FILL, ec=NAVY, lw=1.3, zorder=5))
        ax.plot([px_ - 0.75, px_ + 0.75], [py_ - 1.3, py_ - 1.3], color=NAVY, lw=1.1, zorder=6)
        ax.plot([px_, px_], [py_ - 2.05, py_ - 0.55], color=NAVY, lw=1.1, zorder=6)
    contain(xs[0] + cw / 2, py, xs[0] + cw / 2, cy + chh)
    mid = xs[1] + cw + gap / 2
    contain(mid, py, xs[1] + cw / 2, cy + chh)
    contain(mid, py, xs[2] + cw / 2, cy + chh)
    contain(xs[3] + cw / 2, py, xs[3] + cw / 2, cy + chh)
    # test cases (row 3) with <<verify>> arrows up
    ty, th = 9, 17
    def tbox(x, text, result, ok=True):
        ax.add_patch(Rectangle((x, ty), cw, th, fc=C["good_bg"], ec=C["good"], lw=1.5, zorder=2))
        ax.text(x + cw / 2, ty + th - 1.4, "«testCase»", ha="center", va="center", fontsize=8.5, style="italic", color=C["ink2"], zorder=3)
        ax.text(x + cw / 2, ty + th - 8.0, text, ha="center", va="center", fontsize=9.3, zorder=3, linespacing=1.2)
        ax.text(x + cw / 2, ty + 2.3, result, ha="center", va="center", fontsize=9.8, fontweight="bold", color=C["good"], zorder=3)
    tbox(xs[0], "Interfaces.\nEstimatorCannotAccept\nTruth\n(static_assert)", "✓ compiles = passes")
    tbox(xs[1], "50 held-out seeds\n(1001–1050), real sim\nrun once per seed", "✓ worst ratio 0.561")
    tbox(xs[2], "same 50 seeds,\npooled 10,050\nreadings", "✓ coverage 0.976")
    tbox(xs[3], "automated inspection\nof every document\n(test_configuration_rules)", "✓ passes in CI")
    for x in xs:
        arrow(ax, (x + cw / 2, ty + th), (x + cw / 2, cy), ls=DASH, lw=1.4, color=C["good"], ms=13)
        label(ax, x + cw / 2 + 0.3, 28.2, "«verify»", 9.5, color=C["good"], style="italic")
    # satisfy: KalmanEstimator -> EST-002 is shown on the left margin as text, legend at the bottom
    ax.text(50, 3.6, "SYS-005: CI fails the build if any of the 61 Must requirements loses its passing test.   "
                     "⊕ = containment, dashed arrow = verify", ha="center", fontsize=9.4, color=C["ink2"])


# --------------------------------------------------------------------------------------------- act
def act(ax):
    canvas(ax)
    frame(ax, "act", "[activity] Runner.run(config, sensor, estimator, recorder)")
    cx = 27
    def n(x, y, w, h, text, fs=10.8, **kw):
        node(ax, x - w / 2, y - h / 2, w, h, text, fs=fs, **kw)
    # initial
    ax.add_patch(Circle((cx, 68), 1.3, fc=NAVY, ec=NAVY, zorder=3))
    arrow(ax, (cx, 66.7), (cx, 64.2))
    n(cx, 61.5, 38, 5, "validate config;  truth ← initial state")
    arrow(ax, (cx, 59), (cx, 55.4))
    # loop decision
    diamond(ax, cx, 52.5, 11, 3.0, fill=FILL)
    ax.text(cx, 52.5, "k ≤ steps ?", ha="center", va="center", fontsize=10.5, zorder=5)
    arrow(ax, (cx, 49.5), (cx, 46.3))
    label(ax, cx + 2, 48, "yes", 9.5)
    # exit
    arrow(ax, (cx + 11, 52.5), (66, 52.5))
    label(ax, cx + 16, 54, "no", 9.5)
    n(77.5, 52.5, 20, 5, "recorder.commit()\n(atomic rename)", fs=10)
    arrow(ax, (77.5, 50), (77.5, 46.5))
    ax.add_patch(Circle((77.5, 45), 1.5, fc=FILL, ec=NAVY, lw=1.5, zorder=3))
    ax.add_patch(Circle((77.5, 45), 0.8, fc=NAVY, ec=NAVY, zorder=4))
    # k>0 ?
    diamond(ax, cx, 43.5, 8, 2.9, fill=FILL)
    ax.text(cx, 43.5, "k > 0 ?", ha="center", va="center", fontsize=10.5, zorder=5)
    arrow(ax, (cx + 8, 43.5), (45, 43.5))
    label(ax, cx + 10.5, 45, "yes", 9.5)
    n(55, 43.5, 20, 5, "truth ← propagate\n(explicit Euler)", fs=10)
    polyline_arrow(ax, [(55, 41), (55, 38.2), (cx, 38.2)], style="-")
    arrow(ax, (cx, 40.6), (cx, 36.2))
    label(ax, cx + 2, 39.2, "no", 9.5)
    n(cx, 33.6, 42, 5, "meas ← sensor.observe(truth, k)\n(a reading every M steps, else none)", fs=10)
    arrow(ax, (cx, 31.1), (cx, 28.4))
    # initialized?
    diamond(ax, cx, 25.5, 11, 3.0, fill=FILL)
    ax.text(cx, 25.5, "initialized ?", ha="center", va="center", fontsize=10.5, zorder=5)
    # no branch (left)
    polyline_arrow(ax, [(cx - 11, 25.5), (14, 25.5), (14, 21.4)])
    label(ax, 19, 27, "no", 9.5)
    n(14, 18.6, 20, 5.6, "if meas:\nest ← initialize(meas)\n(no predict, EST-009)", fs=9.4)
    # yes branch (right)
    polyline_arrow(ax, [(cx + 11, 25.5), (55, 25.5), (55, 21.6)])
    label(ax, cx + 14.5, 27, "yes", 9.5)
    n(55, 19, 20, 5, "est ← predict(dt)", fs=10.5)
    arrow(ax, (55, 16.5), (55, 13.9))
    diamond(ax, 55, 11.2, 7, 2.7, fill=FILL)
    ax.text(55, 11.2, "meas ?", ha="center", va="center", fontsize=10.5, zorder=5)
    arrow(ax, (62, 11.2), (73, 11.2))
    label(ax, 66.5, 12.7, "yes", 9.5)
    n(83, 11.2, 20, 5, "est ← update(meas)", fs=10.5)
    # merge to write_row
    n(33.5, 4.4, 57, 4.8, "recorder.write_row(k, truth, meas, est)", fs=10.8, fill=C["blue_soft"])
    arrow(ax, (14, 15.8), (14, 6.8))
    arrow(ax, (55, 8.5), (55, 6.8))
    label(ax, 57.2, 7.6, "no", 9.5)
    polyline_arrow(ax, [(83, 8.7), (83, 4.4), (62, 4.4)])
    polyline_arrow(ax, [(5, 4.4), (2.4, 4.4), (2.4, 52.5), (cx - 11, 52.5)], style="-|>", ms=12)
    ax.text(2.4, 30, "k ← k + 1", fontsize=9.3, rotation=90, ha="center", va="center", color=C["ink2"], zorder=6,
            bbox=dict(boxstyle="round,pad=0.15", fc=C["surface"], ec="none"))
    ax.text(93, 65.5, "Only `meas`, never\n`truth`, is passed\nto the estimator\n(SYS-002).", fontsize=9, ha="right",
            va="top", color=C["bad"], linespacing=1.2)


# --------------------------------------------------------------------------------------------- stm
def stm(ax):
    canvas(ax)
    frame(ax, "stm", "[state machine] KalmanEstimator")
    ax.add_patch(Circle((9, 60), 1.4, fc=NAVY, ec=NAVY, zorder=3))
    arrow(ax, (9, 58.6), (9, 55.6))
    node(ax, 1.5, 40, 24, 15.5, "Uninitialized", fs=13, weight="bold", r=2.5)
    ax.text(13.5, 43.6, "initialized = false\nno belief yet", ha="center", va="center", fontsize=9.5, color=C["ink2"], zorder=5, linespacing=1.2)
    ax.add_patch(FancyBboxPatch((38, 17), 60, 51, boxstyle="round,pad=0,rounding_size=2.5", fc="#f7f9fc", ec=NAVY, lw=1.6, zorder=1))
    ax.text(68, 65, "Initialized", ha="center", va="center", fontsize=13, fontweight="bold", zorder=3)
    ax.plot([38.3, 97.7], [62.4, 62.4], color=NAVY, lw=1, zorder=2)
    node(ax, 41, 30, 21, 14, "Predicted", fs=12.5, weight="bold", r=2.5, fill="#fdeee7", ec=C["orange_ink"])
    ax.text(51.5, 33.4, "doubt P grows", ha="center", va="center", fontsize=9.6, color=C["ink2"], zorder=5)
    node(ax, 76, 30, 20, 14, "Corrected", fs=12.5, weight="bold", r=2.5, fill=C["blue_soft"], ec=C["blue_ink"])
    ax.text(86, 33.4, "doubt P shrinks", ha="center", va="center", fontsize=9.6, color=C["ink2"], zorder=5)
    arrow(ax, (25.5, 47.5), (38, 47.5), lw=1.6)
    label(ax, 31.6, 53.4, "initialize(\nfirst reading)\n/ x ← [z, 0]\n  P ← diag(p0)", 9.2)
    ax.add_patch(Circle((86, 56), 1.2, fc=NAVY, ec=NAVY, zorder=3))
    arrow(ax, (86, 54.8), (86, 44.2), lw=1.4)
    arrow(ax, (62, 40), (76, 40), lw=1.6)
    label(ax, 69, 47.2, "update(z)\n[z.t ≥ last reading]\n/ Joseph-form fix", 9.2)
    arrow(ax, (76, 34), (62, 34), lw=1.6)
    label(ax, 69, 26.5, "predict(dt)  [dt > 0]\n/ x ← F x ;  P ← F P Fᵀ + Q", 9.2)
    arrow(ax, (55, 44), (47.5, 44), lw=1.5, rad=-1.6, ms=12)
    label(ax, 51.5, 51.2, "predict(dt)\n(many steps with\nno reading)", 9.2)
    ax.add_patch(FancyBboxPatch((1.5, 2.5), 97, 11.5, boxstyle="round,pad=0,rounding_size=1", fc=C["bad_bg"], ec=C["bad"], lw=1.1, zorder=2))
    ax.text(3.5, 11.6, "Refused events (state left unchanged, error raised):", fontsize=10.2, fontweight="bold", color=C["bad"], va="center", zorder=3)
    ax.text(3.5, 6.6, "•  predict() or update() before initialize()  →  logic_error\n"
                      "•  initialize() called twice  →  logic_error\n"
                      "•  update() with a reading older than the last accepted one (EST-013)  →  invalid_argument",
            fontsize=9.6, color=NAVY, va="center", zorder=3, linespacing=1.35)
