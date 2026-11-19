"""16:9 slide deck (.pptx): native, editable text and shapes; charts and SysML diagrams as images."""
import sys, tempfile, textwrap
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import ImageFont
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

sys.path.insert(0, str(Path(__file__).parent))
import charts, sysml, graphics
from common import C, ROOT, loc
from content import *

plt.rcParams["font.family"] = "DejaVu Sans"
OUT = ROOT / "presentation" / "sensor-sim-slides.pptx"
TMP = Path(tempfile.mkdtemp(prefix="deck_"))
FONT = "Calibri"
MONO = "Consolas"
_f = {}
WARN = []


def rgb(h):
    h = h.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def fits(text, size, w_in, h_in, bold=False, mono=False):
    """Conservative overflow check: measures with DejaVu (wider than Calibri)."""
    path = "/usr/share/fonts/truetype/dejavu/" + ("DejaVuSansMono.ttf" if mono else ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"))
    f = _f.setdefault((path, size), ImageFont.truetype(path, int(size * 10)))
    avail = (w_in - 0.2) * 72 * 10
    lines = 0
    for para in text.split("\n"):
        words, cur = para.split(" "), ""
        n = 1
        for w in words:
            t = (cur + " " + w).strip()
            if f.getlength(t) > avail and cur:
                n += 1
                cur = w
            else:
                cur = t
        lines += n
    need = lines * size * 1.2 / 72 + 0.1
    return need <= h_in + 0.02, need


class Deck:
    def __init__(self):
        self.prs = Presentation()
        self.prs.slide_width, self.prs.slide_height = Inches(13.333), Inches(7.5)
        self.n = 0
        self.total = 20

    def slide(self, kicker, title, dark=False, notes=""):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.n += 1
        s.background.fill.solid()
        s.background.fill.fore_color.rgb = rgb(C["navy"] if dark else C["bg"])
        s._dark = dark
        s._n = self.n
        ink = "#ffffff" if dark else C["ink"]
        band = self.rect(s, 0, 0, 13.333, 0.12, C["blue"] if dark else C["orange"])
        if kicker:
            self.text(s, 0.6, 0.28, 9, 0.35, kicker.upper(), 12, True, C["orange"] if not dark else "#7fb2ee")
        if title:
            self.text(s, 0.6, 0.58, 12.1, 0.75, title, 30, True, ink, name=f"title-{self.n}")
        self.text(s, 0.6, 7.08, 8, 0.3, "sensor-sim  ·  educational simulation, not flight software", 10, False,
                  C["navy_ink"] if dark else C["ink3"])
        self.text(s, 11.7, 7.08, 1.0, 0.3, f"{self.n}", 11, True, C["navy_ink"] if dark else C["ink3"], align=PP_ALIGN.RIGHT)
        s.notes_slide.notes_text_frame.text = notes
        return s

    def rect(self, s, x, y, w, h, fill, line=None, shape=MSO_SHAPE.RECTANGLE, lw=1.0, radius=None):
        sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        if fill:
            sh.fill.solid(); sh.fill.fore_color.rgb = rgb(fill)
        else:
            sh.fill.background()
        if line:
            sh.line.color.rgb = rgb(line); sh.line.width = Pt(lw)
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            sh.adjustments[0] = radius
        return sh

    def card(self, s, x, y, w, h, fill=None, line=None, lw=1.0):
        return self.rect(s, x, y, w, h, fill or C["surface"], line or C["line"], MSO_SHAPE.ROUNDED_RECTANGLE, lw, radius=0.04)

    def text(self, s, x, y, w, h, text, size=14, bold=False, color=None, align=PP_ALIGN.LEFT, mono=False, name=None,
             anchor=MSO_ANCHOR.TOP, spacing=None):
        color = color or (C["ink"])
        tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = Inches(0.08)
        tf.margin_top = tf.margin_bottom = Inches(0.03)
        tf.vertical_anchor = anchor
        ok, need = fits(text, size, w, h, bold, mono)
        if not ok:
            WARN.append(f"slide {getattr(s, '_n', '?')}: text needs {need:.2f}in but box is {h:.2f}in: {text[:40]!r}")
        for i, para in enumerate(text.split("\n")):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            if spacing:
                p.space_after = Pt(spacing)
            r = p.add_run()
            r.text = para
            r.font.size = Pt(size)
            r.font.bold = bold
            r.font.name = MONO if mono else FONT
            r.font.color.rgb = rgb(color)
        return tb

    def bullets(self, s, x, y, w, items, size=15, color=None, gap=0.12, dot=None):
        """Each item gets its own text box and a dot, so nothing relies on bullet formatting."""
        color = color or C["ink"]
        for t in items:
            ok, need = fits(t, size, w - 0.3, 5, False)
            h = need + 0.02
            d = self.rect(s, x + 0.03, y + 0.1, 0.11, 0.11, dot or C["orange"], shape=MSO_SHAPE.OVAL)
            self.text(s, x + 0.25, y, w - 0.25, h, t, size, False, color)
            y += h + gap
        return y

    def tile(self, s, x, y, w, h, big, small, color=None, bigsize=30):
        self.card(s, x, y, w, h)
        self.text(s, x, y + 0.08, w, h * 0.5, big, bigsize, True, color or C["blue_ink"], align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        self.text(s, x + 0.1, y + h * 0.55, w - 0.2, h * 0.42, small, 12, False, C["ink2"], align=PP_ALIGN.CENTER)

    def pic(self, s, fn, x, y, w, h, name, figsize=None, dpi=200, **kw):
        fig = plt.figure(figsize=figsize or (w, h))
        left = kw.pop("left", 0.1)
        ax = fig.add_axes([left, 0.16, 0.98 - left, 0.8])
        fn(ax, **kw) if kw else fn(ax)
        path = TMP / f"{name}.png"
        fig.savefig(path, dpi=dpi, transparent=True)
        plt.close(fig)
        s.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))

    def save(self):
        self.prs.save(OUT)


def diagram_slide(d, kicker, title, fn, notes_title, bullets, notes):
    s = d.slide(kicker, title, notes=notes)
    h = 5.7
    w = h * 4 / 3
    fig = plt.figure(figsize=(10, 7.5))
    ax = fig.add_axes([0, 0, 1, 1])
    fn(ax)
    path = TMP / f"dia{d.n}.png"
    fig.savefig(path, dpi=200)
    plt.close(fig)
    s.shapes.add_picture(str(path), Inches(0.5), Inches(1.3), Inches(w), Inches(h))
    x = 0.5 + w + 0.35
    d.text(s, x, 1.3, 13.333 - x - 0.5, 0.4, notes_title, 15, True, C["orange_ink"])
    d.bullets(s, x, 1.8, 13.333 - x - 0.5, bullets, 14, gap=0.14)
    return s


def build():
    d = Deck()

    # 1 title
    s = d.slide("Project walkthrough", None, dark=True, notes="Opening: a sensor and Kalman-filter simulator built with systems-engineering rigor. "
                "The headline: 5.46 m of raw noise becomes 2.32 m, and velocity, which the sensor never measures, is recovered to 1.2 m/s.")
    d.text(s, 0.6, 1.1, 12.0, 1.8, "Estimating what a sensor can't see", 48, True, "#ffffff")
    d.text(s, 0.6, 2.95, 10.5, 1.0, "A sensor and Kalman-filter simulator built with systems-engineering rigor: requirements, SysML models, "
           "and tests that prove the claims.", 20, False, C["navy_ink"])
    for i, (big, small) in enumerate([(f"{M['rmse_meas_pos_m']:.2f} m → {M['rmse_est_pos_m']:.2f} m", "position error: raw sensor readings vs the filter's estimate"),
                                      ("1.20 m/s", "velocity error, for a quantity the sensor never measures"),
                                      (f"{COV_POOLED*100:.1f} %", "of true positions inside the filter's own ±2σ (50 held-out seeds)")]):
        x = 0.6 + i * 4.1
        d.card(s, x, 4.3, 3.9, 1.7, C["navy2"], C["navy2"])
        d.text(s, x, 4.4, 3.9, 0.8, big, 28, True, "#ffffff", align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        d.text(s, x + 0.15, 5.2, 3.6, 0.75, small, 13, False, C["navy_ink"], align=PP_ALIGN.CENTER)
    d.text(s, 0.6, 6.35, 12, 0.4, "C++17   ·   Python   ·   SysML   ·   GoogleTest   ·   CI", 16, True, "#7fb2ee")
    d.text(s, 0.6, 6.7, 12, 0.35, DISCLAIMER, 11, False, C["navy_dim"])

    # 2 problem
    s = d.slide("The problem", "Noisy readings, hidden state", notes="Set up the problem. Emphasise that the estimator never sees the truth; "
                "the comparison against truth is the only place truth is used.")
    d.bullets(s, 0.6, 1.5, 6.2, ["A 1-D object moves at 10 m/s.",
                                 "A simulated sensor reports its position every 0.5 s, with 5 m of Gaussian noise.",
                                 "The estimator sees only those readings, never the truth.",
                                 "The job: recover position and velocity, and say how wrong the answer might be."], 18, gap=0.22)
    boxes = [("Truth", "position, velocity", C["ink"]), ("Sensor", "+5 m noise, seeded", C["orange"]),
             ("Kalman filter", "estimate + doubt", C["blue"]), ("Compare", "estimate vs truth", C["good"])]
    for i, (a, b, fc) in enumerate(boxes):
        x, y = 7.3, 1.5 + i * 1.05
        sh = d.rect(s, x, y, 3.2, 0.8, fc, None, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.12)
        d.text(s, x, y + 0.02, 3.2, 0.42, a, 16, True, "#ffffff", align=PP_ALIGN.CENTER)
        d.text(s, x, y + 0.42, 3.2, 0.34, b, 12, False, "#ffffff", align=PP_ALIGN.CENTER)
        if i < 3:
            d.text(s, x + 1.4, y + 0.72, 0.4, 0.4, "↓", 14, True, C["ink"], align=PP_ALIGN.CENTER)
    d.text(s, 10.65, 1.5, 2.2, 3.2, "Truth is used only to score the result. Never as an input to the filter.", 14, True, C["bad"])
    d.card(s, 0.6, 5.75, 12.1, 1.0, C["surface2"])
    d.text(s, 0.8, 5.85, 11.7, 0.85, "Why it matters: a filter that quietly peeks at the truth would look brilliant and prove nothing. "
           "The design makes peeking impossible.", 16, False, C["ink"])

    # 3 kalman
    s = d.slide("The idea", "Two steps, repeated", notes="Predict then update. P is the filter's doubt. Joseph form keeps P symmetric and non-negative.")
    for i, (hd, col, eq, expl) in enumerate([
        ("1  Predict", C["orange_ink"], "x ← F x\nP ← F P Fᵀ + Q", "Move the guess forward by dt using constant velocity. The doubt P grows, because time passes with no new information."),
        ("2  Update", C["blue_ink"], "K = P Hᵀ / (H P Hᵀ + R)\nx ← x + K (z − H x)\nP ← (I−KH) P (I−KH)ᵀ + K R Kᵀ", "A reading z arrives. Pull the guess toward it by the gain K, which weighs the reading against the doubt. P shrinks.")]):
        x = 0.6 + i * 6.15
        d.card(s, x, 1.5, 5.95, 4.3, None, col, 2)
        d.text(s, x + 0.2, 1.6, 5, 0.5, hd, 24, True, col)
        d.card(s, x + 0.25, 2.25, 5.45, 1.5, C["surface2"], C["surface2"])
        d.text(s, x + 0.35, 2.3, 5.3, 1.4, eq, 15, False, C["ink"], mono=True, anchor=MSO_ANCHOR.MIDDLE)
        d.text(s, x + 0.2, 3.95, 5.55, 1.7, expl, 15, False, C["ink2"])
    d.text(s, 0.6, 6.05, 12.1, 0.9, "State x = [position, velocity]. The sensor reads position only; velocity is inferred from how positions change. "
           "Defaults: process noise q = 0.1, assumed sensor variance R = 25.", 14, False, C["ink2"])

    # 4 result
    s = d.slide("Result", "5.46 m of noise down to 2.32 m", notes="One seed (42), 201 readings. Orange dots are raw errors, blue is the estimate's error, "
                "shaded band is the filter's own ±2σ. 94% of errors fall inside it.")
    d.pic(s, charts.error_chart, 0.5, 1.4, 8.6, 4.9, "err", fs=11)
    for i, (b, t, bs) in enumerate([(f"{M['improvement_ratio']:.2f}", "RMSE ratio, estimate ÷ raw", 34), (f"{M['frac_pos_within_2sigma']*100:.0f} %", "of errors inside the filter's own ±2σ", 34),
                                    (f"{M['n_measurements']}", "readings, seed 42 (one run, one seed)", 34)]):
        d.tile(s, 9.4, 1.4 + i * 1.7, 3.35, 1.55, b, t, bigsize=bs)
    d.text(s, 0.6, 6.35, 12.1, 0.6, "Orange dots are raw readings, wandering up to ±15 m. The blue line is the estimate, hugging zero inside the shaded error bars the filter reports about itself.", 14, False, C["ink2"])

    # 5 velocity
    s = d.slide("Result", "It recovers a speed the sensor never measures", notes="The sensor reads position only. Velocity RMSE is 1.20 m/s over the whole run, "
                "and the estimate sits within about 1 m/s of the true 10 m/s from roughly 5 s on.")
    d.pic(s, charts.velocity_chart, 0.5, 1.4, 8.6, 4.9, "vel", fs=11)
    d.tile(s, 9.4, 1.4, 3.35, 1.7, "1.20 m/s", "velocity RMSE over the whole run", bigsize=30)
    d.tile(s, 9.4, 3.3, 3.35, 1.7, "≈ 5 s", "to settle within about 1 m/s of the true 10 m/s", bigsize=30)
    d.text(s, 9.4, 5.2, 3.35, 1.1, "Position readings only. Velocity is inferred from how they change.", 14, False, C["ink2"])

    # 6 seeds
    s = d.slide("Validation", "Not one lucky seed: 50 held-out seeds", notes="Seeds 1001–1050 were never used to tune anything; a test checks disjointness from the tuning set. "
                f"Worst ratio {RATIO_WORST:.3f} (seed 1026) against a limit of 0.75; pooled coverage {COV_POOLED:.3f} against 0.90.")
    d.pic(s, charts.ratio_chart, 0.5, 1.35, 6.1, 3.9, "ratio", fs=10.5, left=0.16)
    d.pic(s, charts.coverage_chart, 6.75, 1.35, 6.1, 3.9, "cov", fs=10.5, left=0.16)
    d.tile(s, 0.6, 5.4, 3.9, 1.5, f"{RATIO_WORST:.3f}", "worst RMSE ratio, against a required ≤ 0.75", bigsize=30)
    d.tile(s, 4.7, 5.4, 3.9, 1.5, f"{COV_POOLED*100:.1f} %", "pooled coverage, against a required ≥ 90 %", bigsize=30)
    d.text(s, 8.8, 5.4, 4.0, 1.5, "Seeds were never used to tune anything, and a test checks that they stay disjoint from the tuning set. A perfect filter scores about 95 %.", 13, False, C["ink2"])

    # 7 limits
    s = d.slide("Limits, reported honestly", "Where the filter breaks", notes="Exploratory scenarios on the 200 tuning seeds, from docs/VALIDATION.md. "
                "These are report-only; the acceptance tests cover the reference scenario.")
    fig, axs = plt.subplots(1, 2, figsize=(8.0, 4.4), gridspec_kw=dict(width_ratios=[1.35, 1], wspace=0.08))
    charts.scenario_charts(axs[0], axs[1], fs=10.5)
    fig.subplots_adjust(left=0.22, right=0.98, bottom=0.17, top=0.95)
    p = TMP / "scen.png"
    fig.savefig(p, dpi=200, transparent=True)
    plt.close(fig)
    s.shapes.add_picture(str(p), Inches(0.5), Inches(1.4), Inches(8.0), Inches(4.4))
    d.text(s, 8.8, 1.4, 4.0, 0.4, "Red bars miss the limit", 16, True, C["bad"])
    d.bullets(s, 8.8, 1.9, 4.0, ["Accelerating truth (0.5 m/s²): the constant-velocity model is wrong, so the filter is no better than raw readings.",
                                 "Wrong noise setting (R = 1, true 25): the estimate helps, but its error bars lie. Only 35 % of errors fall inside.",
                                 "A reading every 5 s: coverage stays honest, but there is little to average (ratio 0.81)."], 13, dot=C["bad"])
    d.text(s, 0.6, 6.1, 12, 0.6, "Reference row is the 50 held-out seeds; the other rows are the 200 tuning seeds. Dashed line = acceptance limit.", 12, False, C["ink3"])

    # 8 architecture
    s = d.slide("Architecture", "A pipeline with a truth firewall", notes="Walk left to right. The core library does all the logic; main.cpp makes one call. "
                "Python tools only read files the core wrote. Tests and CI wrap the whole thing.")
    st = loc()
    stages = [("CLI", "14 flags, units shown,\nexit codes 0/1/2", C["surface2"]), ("simcore (C++17)", "Dynamics · NoisySensor ·\nKalmanEstimator · Runner ·\nCsvRecorder", C["blue_soft"]),
              ("run.csv + sidecar", "17-digit values, units in\nevery column, seed and\nbuild recorded", "#fff7e6"), ("Python analysis", "analyze.py · kalman_oracle.py\n· ensemble.py", C["surface2"]),
              ("Outputs", "metrics.json · plot.png ·\nPASS/FAIL cross-check", C["good_bg"])]
    w, g = 2.25, 0.2
    for i, (a, b, fc) in enumerate(stages):
        x = 0.6 + i * (w + g)
        d.card(s, x, 1.55, w, 2.0, fc, C["ink3"])
        d.text(s, x, 1.62, w, 0.45, a, 14, True, C["ink"], align=PP_ALIGN.CENTER)
        d.text(s, x, 2.15, w, 1.35, b, 11.5, False, C["ink2"], align=PP_ALIGN.CENTER)
        if i < 4:
            d.text(s, x + w - 0.05, 2.3, 0.3, 0.4, "→", 18, True, C["ink"], align=PP_ALIGN.CENTER)
    d.card(s, 0.6, 3.8, 12.1, 0.75, C["surface"], C["good"], 1.5)
    d.text(s, 0.75, 3.88, 11.8, 0.6, "Tests + CI wrap everything: GoogleTest and pytest, the exact-arithmetic oracle, sanitizers, coverage, and a container build on every push.", 13, False, C["ink"])
    d.bullets(s, 0.6, 4.85, 5.9, ["include/simulator + src/: the simcore library holds all logic; main.cpp is one call into it.",
                                  "python/: analysis tools that only read what the core wrote.",
                                  "tests/: framework-neutral support, a GoogleTest adapter, pytest system tests."], 13.5, gap=0.1)
    d.bullets(s, 6.9, 4.85, 5.8, [f"{st['lib']:,} lines of library code, {st['py']:,} of Python tooling, {st['tests']:,} of tests.",
                                  "The Runner follows the call order fixed in the baseline (section 7.4).",
                                  "Design of record: systems-engineering baseline; docs/architecture.md logs 57 design decisions."], 13.5, gap=0.1)

    # 9 design principles
    s = d.slide("Design", "Six design choices that carry the weight", notes="Each card is a decision that shows up in the code and is guarded by a test.")
    cw, ch = 3.95, 2.55
    for i, (h, t) in enumerate(DESIGN):
        x = 0.6 + (i % 3) * (cw + 0.12)
        y = 1.5 + (i // 3) * (ch + 0.15)
        d.card(s, x, y, cw, ch)
        d.rect(s, x, y + 0.02, cw, 0.07, C["blue"])
        d.text(s, x + 0.1, y + 0.15, cw - 0.2, 0.45, h, 17, True, C["blue_ink"])
        d.text(s, x + 0.1, y + 0.65, cw - 0.2, ch - 0.7, t, 13, False, C["ink2"])

    # 10 decisions table
    s = d.slide("Design", "Decisions, alternatives, reasons", notes="A sample of the 57 decisions recorded in docs/architecture.md. Each one lists what was rejected and why.")
    rows = [("Decision", "Alternative rejected", "Why"),
            ("Euler: position uses the OLD velocity", "Semi-implicit Euler, RK4", "Baseline fixes 5995.0 m and the error bound a·t·dt/2. A mutation test confirmed the tests catch the swap."),
            ("Draw a standard normal, multiply by σ", "Construct N(0, σ²) directly", "σ = 0 is exact with no special case; the same seed gives the same pattern, scaled."),
            ("Filter maths as two pure functions", "Maths inside the class", "A hand-picked starting belief can be tested; the Python oracle mirrors the same two functions."),
            ("Oracle in 60-digit decimals", "Port in double precision", "A double-precision oracle was itself wrong after 100,000 steps with no reading. An oracle must beat what it checks."),
            ("Disjoint tuning (200) and held-out (50) seeds", "One seed list", "Makes 'works on unseen data' mechanically checkable."),
            ("Container build runs the whole test suite", "Build only", "An image that exists is an image whose tests passed.")]
    tbl = s.shapes.add_table(len(rows), 3, Inches(0.6), Inches(1.5), Inches(12.1), Inches(5.2)).table
    for ci, wdt in enumerate([3.6, 2.8, 5.7]):
        tbl.columns[ci].width = Inches(wdt)
    for ri, row in enumerate(rows):
        tbl.rows[ri].height = Inches(0.5 if ri == 0 else 0.78)
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.fill.solid()
            cell.fill.fore_color.rgb = rgb(C["navy"] if ri == 0 else (C["surface"] if ri % 2 else C["surface2"]))
            cell.margin_left = cell.margin_right = Inches(0.1)
            tf = cell.text_frame
            tf.word_wrap = True
            r = tf.paragraphs[0].add_run()
            r.text = val
            r.font.size = Pt(14 if ri == 0 else 12.5)
            r.font.bold = (ri == 0 or ci == 0)
            r.font.name = FONT
            r.font.color.rgb = rgb("#ffffff" if ri == 0 else C["ink"])
            ok, need = fits(val, 14 if ri == 0 else 12.5, tbl.columns[ci].width / 914400, 0.78, ci == 0)
            if not ok:
                WARN.append(f"table cell r{ri}c{ci} needs {need:.2f}in: {val[:30]!r}")

    # 11-15 SysML
    diagram_slide(d, "SysML · block definition diagram", "System structure", lambda ax: sysml.bdd(ax, (CPP, PY)), "What it shows",
                  ["Three blocks make up the system: the simcore C++17 library, the Python analysis tools, and the verification layer.",
                   "Filled diamonds are composition: the parts exist only inside the whole.",
                   "Each part lists its key operations. The estimator exposes predict() and update(), and nothing takes ground truth."],
                  "BDD: structure. simcore has six parts, each with one job. The analysis tools only read files. Verification is a first-class block, not an afterthought.")
    diagram_slide(d, "SysML · internal block diagram", "Data flow, with a firewall", sysml.ibd, "What it shows",
                  ["The Runner hands the sensor the truth and the estimator only the measurement.",
                   "The red dashed flow is the one that must not exist (SYS-002). A static_assert enforces it at compile time.",
                   "Files cross the boundary: the CSV and sidecar feed analyze.py and the oracle."],
                  "IBD: parts and the item flows between them. The red crossed flow is a requirement made visible.")
    diagram_slide(d, "SysML · activity diagram", "The Runner loop", sysml.act, "What it shows",
                  ["One loop over steps 0…N produces N+1 rows.",
                   "Truth advances first; the sensor decides whether a reading is due.",
                   "The estimator is initialized on the first reading with no predict step (EST-009), then predicts every step and updates when a reading exists.",
                   "The recorder commits with an atomic rename at the end."],
                  "Activity: Runner.run. This mirrors src/runner.cpp line for line, including the call order of baseline section 7.4.")
    diagram_slide(d, "SysML · state machine", "How the estimator behaves", sysml.stm, "What it shows",
                  ["Uninitialized until the first reading arrives.",
                   "Inside Initialized, predict grows the doubt and update shrinks it.",
                   "Illegal events are refused and leave the state untouched. A test compares against an untouched twin to prove it.",
                   "Out-of-order readings are rejected (EST-013)."],
                  "State machine: KalmanEstimator. Predicted and Corrected are the two substates; errors raise exceptions without mutating state.")
    diagram_slide(d, "SysML · requirements diagram", "From requirement to proof", sysml.req, "What it shows",
                  [f"{N_REQ} requirements, {N_MUST} of them Must.",
                   "Parents contain children; each child is verified by a named test case.",
                   "The results come from real runs: worst ratio 0.561, coverage 0.976.",
                   "CI fails the build if any Must loses its passing test (SYS-005)."],
                  "Requirements diagram: containment and verify relationships for four of the most important requirements.")

    # 16 test strategy
    diagram_slide(d, "Testing", "How the claims get proved", graphics.test_strategy, "What it shows",
                  [f"{N_TESTS} automated tests: {CPP} GoogleTest cases and {PY} pytest cases.",
                   "Each test names the requirement it verifies; a script checks the citations.",
                   "Acceptance runs the real binary on 50 unseen seeds.",
                   "The test framework is isolated behind an adapter, so it could be swapped."],
                  "Four layers of evidence, and the traceability gate that keeps them honest.")

    # 17 test cases
    s = d.slide("Test cases", "Six tests worth reading", notes="Pick two or three to walk through live. The oracle sabotage test is a good talking point: a check that cannot fail proves nothing.")
    cw, ch = 3.95, 2.78
    for i, (reqs, name, given, expect, why) in enumerate(TESTCASES):
        x = 0.6 + (i % 3) * (cw + 0.12)
        y = 1.4 + (i // 3) * (ch + 0.1)
        d.card(s, x, y, cw, ch)
        d.text(s, x + 0.08, y + 0.04, cw - 0.2, 0.3, reqs, 10.5, True, C["blue_ink"])
        d.text(s, x + 0.08, y + 0.3, cw - 0.2, 0.5, name.replace("\n", ""), 9.5, True, C["ink"], mono=True)
        d.text(s, x + 0.08, y + 0.76, cw - 0.2, 0.8, given, 11, False, C["ink2"])
        d.text(s, x + 0.08, y + 1.5, cw - 0.2, 0.72, expect, 11, True, C["good"])
        d.text(s, x + 0.08, y + 2.2, cw - 0.2, 0.55, why, 11, False, C["ink"])

    # 18 evidence
    s = d.slide("By the numbers", "Evidence", notes="Coverage was 94.0% locally and 94.5% on CI on 2026-11-05, with exception edges excluded from branch coverage. Line coverage is reported, never a gate.")
    d.pic(s, charts.requirements_chart, 0.5, 1.4, 6.3, 4.6, "reqs", fs=11, left=0.24)
    d.text(s, 0.6, 6.05, 6.2, 0.5, "Requirements per area, Must in dark blue", 12, False, C["ink3"])
    for i, (big, small) in enumerate(KEY_NUMBERS):
        d.tile(s, 7.2 + (i % 2) * 2.85, 1.4 + (i // 2) * 1.85, 2.7, 1.7, big, small, bigsize=30)
    d.bullets(s, 7.2, 5.2, 5.5, ["Passes under AddressSanitizer and UBSan.", "GCC 13 and Clang 18, warnings as errors.",
                                  "Whole suite inside a 30 s budget (CI: 5 to 14 s)."], 13, gap=0.06)

    # 19 tech stack
    s = d.slide("Tech stack", "What it is built with, and why", notes="Every dependency is pinned. GoogleTest is fetched by SHA-256; the container base image is pinned by digest.")
    why = {"Core": "C++17 with warnings as errors on two compilers; CMake + Ninja for a fast, reproducible build.",
           "Analysis": "Python 3.12 for the metrics, plots and the exact-arithmetic oracle (stdlib decimal); matplotlib for figures.",
           "Quality": "GoogleTest for unit tests, pytest for black-box system tests, sanitizers and gcovr for depth.",
           "Delivery": "GitHub Actions on every push; a Dockerfile that builds, tests and runs in a clean room."}
    cw = 2.95
    for i, (grp, items) in enumerate(STACK):
        x = 0.6 + i * (cw + 0.1)
        d.card(s, x, 1.5, cw, 4.0)
        d.text(s, x + 0.1, 1.6, cw - 0.2, 0.4, grp.upper(), 13, True, C["orange_ink"])
        y = 2.1
        for it in items:
            d.text(s, x + 0.1, y, cw - 0.2, 0.4, it, 15, True, C["blue_ink"])
            y += 0.5
        d.text(s, x + 0.1, 3.7, cw - 0.2, 1.7, why[grp], 13, False, C["ink2"])
    d.text(s, 0.6, 5.85, 12.1, 0.6, "Deliberately small: no framework beyond the test runner, and the analysis uses the standard library wherever it can.", 13, False, C["ink2"])

    # 20 close
    s = d.slide("Takeaways", None, dark=True, notes="Close on the three habits. Invite questions.")
    d.text(s, 0.6, 0.8, 12, 0.9, "What this project is really about", 40, True, "#ffffff")
    y = 2.1
    for h, t in [("Make claims checkable.", "Every number here comes from a recorded run, a test, or a CI job. A test even fails if the README drifts."),
                 ("Model before you build.", "SysML structure, flow, behaviour and requirements, then code that follows them."),
                 ("Report the failures.", "Accelerating targets and mis-set noise are in the validation record, not hidden.")]:
        d.rect(s, 0.65, y + 0.1, 0.18, 0.18, C["orange"], shape=MSO_SHAPE.OVAL)
        d.text(s, 1.0, y - 0.05, 11, 0.5, h, 22, True, "#ffffff")
        d.text(s, 1.0, y + 0.45, 11.3, 0.7, t, 16, False, C["navy_ink"])
        y += 1.45
    d.card(s, 0.6, 6.0, 12.1, 0.85, C["navy2"], C["navy2"])
    d.text(s, 0.75, 6.07, 11.8, 0.75, "Next: scenario records (VAL-05/06/08), tagging the baseline, and a model that handles accelerating targets.", 14, False, "#ffffff")

    d.save()
    print("wrote", OUT, "slides:", d.n)
    for w in WARN:
        print("FIT WARNING:", w)


if __name__ == "__main__":
    build()
