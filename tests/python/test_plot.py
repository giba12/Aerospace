"""ANA-003: the plot is produced and labelled. Needs matplotlib (pinned in python/requirements.txt)."""
import math
import struct

import pytest

import analyze

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _rows(n=30):
    """A small run in the CSV's own text form. The estimate is empty for the first 3 rows."""
    rows = []
    for k in range(n):
        has_est = k >= 3
        rows.append({
            "step": str(k), "t_s": str(0.1 * k), "true_pos_m": str(1.0 * k), "true_vel_mps": "10",
            "meas_pos_m": str(1.0 * k + 0.5) if k % 5 == 0 else "",
            "est_pos_m": str(1.0 * k + 0.2) if has_est else "", "est_vel_mps": "9.5" if has_est else "",
            "est_pos_var_m2": "4" if has_est else "", "est_vel_var_m2s2": "9" if has_est else ""})
    return rows


@pytest.mark.req("ANA-003")
def test_every_panel_has_labelled_axes_with_units_and_a_legend():
    fig = analyze.make_figure(_rows(), side={"seed": 42, "sigma_m": 5.0, "meas_every": 5, "dt_s": 0.1})
    pos, err, vel = fig.axes
    assert pos.get_ylabel() == "position (m)"
    assert err.get_ylabel() == "position error (m)"
    assert vel.get_ylabel() == "velocity (m/s)"
    assert vel.get_xlabel() == "time (s)"
    labels = lambda ax: [t.get_text() for t in ax.get_legend().get_texts()]
    assert labels(pos) == ["truth", "filter estimate", "sensor readings"]
    assert "estimate error" in labels(err) and "raw reading error" in labels(err)
    assert labels(vel) == ["true velocity", "estimated velocity"]
    assert "seed 42" in fig._suptitle.get_text()


@pytest.mark.req("ANA-003")
def test_the_plot_is_written_as_a_real_png(tmp_path):
    path = tmp_path / "plot.png"
    analyze.write_plot(path, _rows())
    data = path.read_bytes()
    assert data.startswith(PNG_SIGNATURE)
    width, height = struct.unpack(">II", data[16:24])   # the IHDR chunk
    assert width >= 800 and height >= 800
    assert len(data) > 20_000   # an empty canvas compresses to a few kilobytes


@pytest.mark.req("ANA-003")
def test_rows_before_the_estimator_starts_become_gaps_not_errors():
    fig = analyze.make_figure(_rows())
    est_line = next(l for l in fig.axes[0].lines if l.get_label() == "filter estimate")
    ys = list(est_line.get_ydata())
    assert all(math.isnan(y) for y in ys[:3]) and not any(math.isnan(y) for y in ys[3:])
