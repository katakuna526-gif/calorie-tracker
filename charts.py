"""Chart drawing for the progress bars and the weight trend.

These functions only call create_line / create_rectangle / create_oval / create_text on a
canvas, so they work on a real Tk Canvas and on the recording canvas used in tests (which
can render a picture, so the charts can be looked at without a screen).

Design rules followed: thin marks (2 px line, bars at most 24 px thick), recessive solid
hairline grid, text in neutral ink (never in the series colour), one direct label on the
latest value instead of a number on every point, and one colour for one series.
Progress bars use no red/green judgement: going over a target is shown by the bar passing
a target tick, and the numbers say the rest.
"""

import math
from datetime import timedelta
from typing import List, Optional, Sequence, Tuple

SURFACE = "#ffffff"
INK = "#0b0b0b"          # primary text
INK_2 = "#52514e"        # secondary text, target tick
GRID = "#e5e7eb"         # hairline grid, one step off the surface
SERIES = "#2a78d6"       # categorical slot 1 (same blue as "consumed" in the Stats chart)
TRACK = "#cde2fb"        # lighter step of the same blue ramp, behind a progress fill

FONT = "TkDefaultFont"
MAX_BAR_THICKNESS = 24
OVERFLOW_CAP = 1.5       # a progress bar stops growing at 150% of its target


def est_width(text: str, size_pt: float = 9) -> float:
    """Rough pixel width of text. Used only to keep labels inside the canvas."""
    return len(text) * size_pt * (96 / 72) * 0.55


def nice_ticks(lo: float, hi: float, target_count: int = 5) -> Tuple[List[float], int]:
    """Round axis ticks covering [lo, hi]. Returns (ticks, decimals to show)."""
    span = hi - lo
    if span <= 0:
        span = max(abs(hi), 1.0) * 0.1
        lo, hi = lo - span / 2, hi + span / 2
    raw = span / max(target_count - 1, 1)
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw - 1e-12)
    first = math.floor(lo / step + 1e-9) * step
    last = math.ceil(hi / step - 1e-9) * step
    count = int(round((last - first) / step)) + 1
    ticks = [round(first + i * step, 10) for i in range(count)]
    decimals = next((d for d in range(4) if abs(step * 10 ** d - round(step * 10 ** d)) < 1e-9), 3)
    return ticks, decimals


def bar_geometry(fraction: float, x0: float, x1: float) -> dict:
    """Pixel positions for one progress bar.

    The track fills x0..x1. At or under 100% the target is the right end of the track. Over 100%
    the track is rescaled (up to 150%) so the fill visibly passes a target tick.
    """
    fraction = max(fraction, 0.0)
    axis_max = max(1.0, min(fraction, OVERFLOW_CAP))
    scale = (x1 - x0) / axis_max
    return {
        "fill_x1": x0 + min(fraction, axis_max) * scale,
        "tick_x": x0 + scale if axis_max > 1.0 else None,
    }


def draw_progress_rows(canvas, width: float, rows: Sequence[dict], row_height: int = 28,
                       label_width: int = 78, value_width: int = 170) -> int:
    """Rows of {label, fraction, value_text}. Returns the height used."""
    canvas.delete("all")
    x0, x1 = label_width, max(width - value_width, label_width + 40)
    thickness = min(12, MAX_BAR_THICKNESS)
    for i, row in enumerate(rows):
        mid = 4 + i * row_height + row_height / 2
        top, bottom = mid - thickness / 2, mid + thickness / 2
        canvas.create_text(4, mid, text=row["label"], anchor="w", fill=INK_2, font=(FONT, 9))
        canvas.create_rectangle(x0, top, x1, bottom, fill=TRACK, outline="")
        geo = bar_geometry(row["fraction"], x0, x1)
        if geo["fill_x1"] > x0:
            canvas.create_rectangle(x0, top, geo["fill_x1"], bottom, fill=SERIES, outline="")
        if geo["tick_x"] is not None:
            canvas.create_line(geo["tick_x"], top - 3, geo["tick_x"], bottom + 3, fill=INK_2, width=2)
        canvas.create_text(width - 4, mid, text=row["value_text"], anchor="e", fill=INK, font=(FONT, 9))
    return 8 + len(rows) * row_height


def _format_tick(value: float, decimals: int) -> str:
    return f"{value:,.{decimals}f}"


def draw_weight_chart(canvas, width: float, height: float,
                      points: Sequence[Tuple[object, float]],
                      empty_text: str = "No weigh-ins yet. Log your weight to see a chart.",
                      unit: str = "kg") -> None:
    """Line chart of (date, kg) points, oldest first. One series, so no legend; the latest value is labelled."""
    canvas.delete("all")
    if not points:
        canvas.create_text(width / 2, height / 2, text=empty_text, fill=INK_2, font=(FONT, 10))
        return

    left, right, top, bottom = 52, 78, 16, height - 30
    plot_w, plot_h = width - left - right, bottom - top
    values = [kg for _, kg in points]
    lo, hi = min(values), max(values)
    pad = max(1.0, (hi - lo) * 0.15)
    ticks, decimals = nice_ticks(lo - pad, hi + pad)
    y_min, y_max = ticks[0], ticks[-1]

    def y_of(value):
        return bottom - (value - y_min) / (y_max - y_min) * plot_h

    for tick in ticks:                                   # recessive solid hairlines
        y = y_of(tick)
        canvas.create_line(left, y, width - right, y, fill=GRID, width=1)
        canvas.create_text(left - 8, y, text=_format_tick(tick, decimals), anchor="e", fill=INK_2, font=(FONT, 8))

    first_day, last_day = points[0][0], points[-1][0]
    span = (last_day - first_day).days

    def x_of(day):
        return left + ((day - first_day).days / span if span else 0.5) * plot_w

    # Date labels land on whole-day steps so the spacing is even.
    step_days = max(1, math.ceil(span / 4)) if span else 1
    label_days = [first_day + timedelta(days=i) for i in range(0, span + 1, step_days)] if span else [first_day]
    for day in label_days:
        canvas.create_text(x_of(day), bottom + 8, text=day.strftime("%d %b"), anchor="n", fill=INK_2, font=(FONT, 8))

    if len(points) > 1:
        coords = [c for day, kg in points for c in (x_of(day), y_of(kg))]
        canvas.create_line(*coords, fill=SERIES, width=2, joinstyle="round", capstyle="round")

    marked = points if len(points) <= 40 else points[-1:]    # dense data: only the latest gets a marker
    radius = 5
    for day, kg in marked:
        x, y = x_of(day), y_of(kg)
        canvas.create_oval(x - radius, y - radius, x + radius, y + radius, fill=SERIES, outline=SURFACE, width=2)

    last_x, last_y = x_of(last_day), y_of(points[-1][1])
    label = f"{points[-1][1]:.1f} {unit}"
    if last_x + 10 + est_width(label, 10) <= width - 2:
        canvas.create_text(last_x + 10, last_y, text=label, anchor="w", fill=INK, font=(FONT, 10, "bold"))
    else:                                                    # no room to the right: put it above-left
        canvas.create_text(last_x - 6, last_y - 10, text=label, anchor="se", fill=INK, font=(FONT, 10, "bold"))
    if len(points) == 1:
        canvas.create_text(width / 2, top + 4, text="Log one more weigh-in to see a line.",
                           anchor="n", fill=INK_2, font=(FONT, 9))
