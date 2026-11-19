"""Non-SysML explanatory graphics drawn on the same 100 x 75 canvas."""
from matplotlib.patches import FancyBboxPatch, Rectangle, Polygon
from common import C
from sysml import canvas, arrow, label, node
from content import CPP, PY, N_MUST


def test_strategy(ax):
    canvas(ax)
    ax.add_patch(Rectangle((0.5, 0.5), 99, 74, fc=C["surface"], ec=C["line"], lw=1.2, zorder=0))
    ax.text(3, 70, "Four layers of evidence", fontsize=14, fontweight="bold", color=C["ink"], va="center")
    layers = [
        ("Acceptance", "50 held-out seeds: does the filter help, are its error bars honest?", "#2a78d6", "#ffffff"),
        ("System", "pytest drives the real sim binary and cross-checks it against the exact-arithmetic oracle", "#5f9be4", "#ffffff"),
        ("Unit", f"{CPP} GoogleTest cases on the maths, sensor, dynamics, runner, recorder", "#a9c8ee", C["ink"]),
        ("Inspection", "automated checks of build flags, CI file, docs and the SYS-006 disclaimer", "#d7e5f6", C["ink"]),
    ]
    top, hh, gap = 64, 10.8, 1.4
    for i, (name, desc, fill, tc) in enumerate(layers):
        inset = i * 1.5
        y = top - i * (hh + gap) - hh
        ax.add_patch(FancyBboxPatch((3 + inset, y), 54 - 2 * inset, hh, boxstyle="round,pad=0,rounding_size=1.2", fc=fill, ec="none", zorder=2))
        ax.text(4.8 + inset, y + hh - 2.3, name, fontsize=13.5, fontweight="bold", color=tc, va="center", zorder=3)
        import textwrap
        ax.text(4.8 + inset, y + 3.0, "\n".join(textwrap.wrap(desc, 44 - int(2 * inset))), fontsize=10.6, color=tc, va="center", zorder=3, linespacing=1.2)
    # traceability pipeline
    ax.text(62, 70, "Every Must requirement is gated", fontsize=14, fontweight="bold", color=C["ink"], va="center")
    steps = [("Tests tag requirement IDs", 'RecordProperty("requirements", "EST-001")'),
             ("JUnit XML reports", "gtest.xml + pytest.xml"),
             ("tools/req_trace.py", "reads the registry of 70 IDs"),
             ("CI gate", "fails on unknown ID, untagged test, or a Must with no passing test")]
    y0, sh, sg = 64, 9.2, 3.0
    for i, (t, sub) in enumerate(steps):
        y = y0 - i * (sh + sg) - sh
        fc = C["good_bg"] if i == 3 else C["surface2"]
        ec = C["good"] if i == 3 else C["ink3"]
        ax.add_patch(FancyBboxPatch((62, y), 36, sh, boxstyle="round,pad=0,rounding_size=1.2", fc=fc, ec=ec, lw=1.3, zorder=2))
        ax.text(80, y + sh - 2.2, t, fontsize=11.5, fontweight="bold", ha="center", va="center", zorder=3, color=C["ink"])
        import textwrap
        ax.text(80, y + 2.6, sub if i == 0 else "\n".join(textwrap.wrap(sub, 34)), fontsize=8 if i == 0 else 9.4, ha="center", va="center", zorder=3, color=C["ink2"],
                family="DejaVu Sans Mono" if i == 0 else "DejaVu Sans", linespacing=1.15)
        if i < 3:
            arrow(ax, (80, y), (80, y - sg), lw=1.5, ms=12)
    # extras
    ax.add_patch(FancyBboxPatch((3, 3), 94, 10.5, boxstyle="round,pad=0,rounding_size=1.2", fc=C["bg"], ec=C["line"], lw=1.1, zorder=1))
    ax.text(50, 10.2, "Also run on every push", fontsize=10.5, fontweight="bold", ha="center", color=C["ink"], zorder=3)
    ax.text(50, 6, "AddressSanitizer + UBSan   ·   GCC 13 and Clang 18, warnings as errors   ·   clean-room container build   ·   30 s test budget",
            fontsize=9.8, ha="center", color=C["ink2"], zorder=3)
