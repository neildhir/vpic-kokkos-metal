"""Plot a benchmark results folder as standalone SVG figures (standard library only).

Usage (from benchmarks/)::

    python3.12 plots.py results/<id> [results/<id> ...]

Each results folder gains a ``plots/`` directory with:

- ``step_and_push.svg``: for the Harris (whole-step) cases, steady time per step
  and particle-push time per particle for every build, side by side.
- ``push_rate_vs_grid.svg``: for the laser-plasma (LPI) sweep, particle pushes
  per nanosecond against grid size for every build, with the published GPU
  values from the config copy in the folder (``[published_push_rate]``).

The figures follow the light/dark colour scheme of the viewer, carry a hover
tooltip on every mark, and keep the legend below the axes. The numbers behind
them are in the folder's ``summary.md``.
"""

from __future__ import annotations

import json
import logging
import math
import sys
import tomllib
from dataclasses import dataclass
from html import escape
from pathlib import Path
from typing import Any

log = logging.getLogger("plots")

# Layout of a figure, in SVG pixels
FIG_WIDTH = 880
PANEL_HEIGHT = 300
MARGIN_TOP = 64  # title and subtitle
MARGIN_LEFT = 92  # y-axis labels
MARGIN_RIGHT = 28
AXIS_BAND = 46  # x-axis tick labels and title
LEGEND_ROW = 26
END_LABEL_ROOM = 72  # right of a line chart, for the direct labels at the line ends
CHAR_WIDTH = 7  # rough width of a 12 px label character, for legend wrapping
PANEL_GAP = 72
FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

# Bars and markers (see the dataviz mark specs: thin marks, 2 px gaps, 8 px markers)
BAR_THICKNESS = 14
BAR_GAP = 2
GROUP_GAP = 18
BAR_RADIUS = 4
LABEL_ROOM = 1.35  # bar axes extend this far past the longest whisker, for the speed-up labels
MARKER_RADIUS = 4.5
LINE_WIDTH = 2

# Light and dark tokens. Categorical slots 1-2 validated with validate_palette.js
# (light on #fcfcfb, dark on #1a1a19): all checks pass.
STYLE = f"""
.root {{ font-family: {FONT}; }}
.surface {{ fill: #fcfcfb; }}
.ink {{ fill: #0b0b0b; }}
.ink2 {{ fill: #52514e; }}
.muted {{ fill: #898781; }}
.grid {{ stroke: #e1e0d9; stroke-width: 1; }}
.axis {{ stroke: #c3c2b7; stroke-width: 1; }}
.whisker {{ stroke: #52514e; stroke-width: 1.5; }}
.ref {{ fill: none; stroke: #52514e; stroke-width: 1.5; }}
.s0 {{ fill: #2a78d6; stroke: #2a78d6; }}
.s1 {{ fill: #eb6834; stroke: #eb6834; }}
path.line, line.line {{ fill: none; stroke-width: {LINE_WIDTH}; }}  /* beats .sN in both modes */
.ring {{ stroke: #fcfcfb; stroke-width: 2; }}
@media (prefers-color-scheme: dark) {{
  .surface {{ fill: #1a1a19; }}
  .ink {{ fill: #f0efec; }}
  .ink2 {{ fill: #c3c2b7; }}
  .grid {{ stroke: #2c2c2a; }}
  .axis {{ stroke: #383835; }}
  .whisker, .ref {{ stroke: #c3c2b7; }}
  .s0 {{ fill: #3987e5; stroke: #3987e5; }}
  .s1 {{ fill: #d95926; stroke: #d95926; }}
  .ring {{ stroke: #1a1a19; }}
}}
"""

MAX_SERIES = 2  # validated categorical slots; more builds need another palette check


class PlotError(Exception):
    """A results folder that cannot be plotted."""


@dataclass(frozen=True)
class Series:
    """One build's medians and ranges for a metric, in case order."""

    build: str
    label: str
    slot: int
    medians: list[float]
    lows: list[float]
    highs: list[float]


@dataclass(frozen=True)
class PublishedPoint:
    """A published particle-push rate (see config.toml, ``[published_push_rate]``)."""

    gpu: str
    grid_points: float
    pushes_per_ns: float
    source: str


def main(argv: list[str]) -> int:
    """Plot every results folder named on the command line.

    Returns
    -------
    int
        Process exit status (0 when every folder was plotted).
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if not argv:
        log.error("usage: python3.12 plots.py results/<id> [results/<id> ...]")
        return 2
    status = 0
    for arg in argv:
        try:
            for path in plot_results(Path(arg)):
                log.info("wrote %s", path)
        except PlotError as e:
            log.error("%s: %s", arg, e)
            status = 1
    return status


def plot_results(folder: Path) -> list[Path]:
    """Write the figures for one results folder and return their paths.

    Raises
    ------
    PlotError
        If the folder has no readable results.json or no plottable cases.
    """
    try:
        results = json.loads((folder / "results.json").read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise PlotError(f"cannot read results.json: {e}") from e
    builds = list(results.get("builds", {}))
    if not builds:
        raise PlotError("no builds in results.json")
    if len(builds) > MAX_SERIES:
        raise PlotError(f"{len(builds)} builds; the palette is validated for {MAX_SERIES}")
    subtitle = f"{results.get('machine_label', '')} · {results.get('id', folder.name)}"
    out_dir = folder / "plots"
    out_dir.mkdir(exist_ok=True)
    written = []
    harris = [c for c in results["cases"].values() if not _is_lpi(c)]
    lpi = sorted((c for c in results["cases"].values() if _is_lpi(c)), key=_grid_points)
    if harris:
        svg = step_and_push_figure(results, harris, builds, subtitle)
        written.append(_write(out_dir / "step_and_push.svg", svg))
    if lpi:
        published = load_published(folder / "config.toml")
        svg = push_rate_figure(results, lpi, builds, published, subtitle)
        written.append(_write(out_dir / "push_rate_vs_grid.svg", svg))
    if not written:
        raise PlotError("no cases to plot")
    return written


def step_and_push_figure(results: dict[str, Any], cases: list[dict[str, Any]], builds: list[str], subtitle: str) -> str:
    """Two bar panels: steady ms per step, and push ns per particle, per case and build.

    Separate panels rather than two y-scales, since the units differ.
    """
    names = [c["name"] for c in cases]
    step = [_series(results, names, b, i, "steady_ms_per_step") for i, b in enumerate(builds)]
    push = [_series(results, names, b, i, "push_ns_per_particle") for i, b in enumerate(builds)]
    group = len(builds) * (BAR_THICKNESS + BAR_GAP) + GROUP_GAP
    plot_h = group * len(names)
    panel_w = (FIG_WIDTH - MARGIN_LEFT - MARGIN_RIGHT - PANEL_GAP) // 2
    height = MARGIN_TOP + plot_h + AXIS_BAND + LEGEND_ROW * 2
    parts = _header("Reconnection deck: CPU build vs Metal GPU build", subtitle, height)
    x0 = MARGIN_LEFT
    parts += _bar_panel(step, names, x0, MARGIN_TOP, panel_w, plot_h, "Steady time per step [ms]", "ms", True)
    x1 = MARGIN_LEFT + panel_w + PANEL_GAP
    parts += _bar_panel(push, names, x1, MARGIN_TOP, panel_w, plot_h, "Particle push [ns per particle]", "ns", False)
    parts += _legend([(s.label, s.slot, "bar") for s in step], MARGIN_TOP + plot_h + AXIS_BAND + 8)
    return _finish(parts)


def push_rate_figure(
    results: dict[str, Any],
    cases: list[dict[str, Any]],
    builds: list[str],
    published: list[PublishedPoint],
    subtitle: str,
) -> str:
    """Log-log lines of particle pushes per ns against grid points, with published GPU points."""
    names = [c["name"] for c in cases]
    grid = [float(_grid_points(c)) for c in cases]
    series = []
    for i, b in enumerate(builds):
        ns = _series(results, names, b, i, "push_ns_per_particle")
        # pushes per ns = 1 / (ns per particle push); the fastest run has the smallest time
        series.append(
            Series(
                ns.build,
                ns.label,
                ns.slot,
                [1 / v for v in ns.medians],
                [1 / v for v in ns.highs],
                [1 / v for v in ns.lows],
            )
        )
    xs = grid + [p.grid_points for p in published]
    ys = [v for s in series for v in s.lows + s.highs] + [p.pushes_per_ns for p in published]
    xscale = _LogScale(min(xs) / 1.5, max(xs) * 1.5, MARGIN_LEFT, FIG_WIDTH - MARGIN_RIGHT - END_LABEL_ROOM)
    plot_h = PANEL_HEIGHT
    yscale = _LogScale(min(ys) / 1.5, max(ys) * 1.5, MARGIN_TOP + plot_h, MARGIN_TOP)
    height = MARGIN_TOP + plot_h + AXIS_BAND + LEGEND_ROW * 2
    parts = _header("Laser-plasma benchmark: particle push rate vs grid size", subtitle, height)
    parts += _log_grid(xscale, yscale, MARGIN_TOP, MARGIN_TOP + plot_h, "Grid points", "Particle pushes per ns")
    for s in series:
        pts = [(xscale(x), yscale(y)) for x, y in zip(grid, s.medians, strict=True)]
        path = " ".join(f"{'M' if k == 0 else 'L'}{x:.1f},{y:.1f}" for k, (x, y) in enumerate(pts))
        parts.append(f'<path class="line s{s.slot}" d="{path}"/>')
        for (x, y), lo, hi, g, m in zip(pts, s.lows, s.highs, grid, s.medians, strict=True):
            parts.append(
                f'<line class="whisker" x1="{x:.1f}" x2="{x:.1f}" y1="{yscale(lo):.1f}" y2="{yscale(hi):.1f}"/>'
            )
            tip = f"{s.label}: {m:.3g} pushes/ns at {g:,.0f} grid points (range {lo:.3g}-{hi:.3g})"
            parts.append(_marker(x, y, s.slot, tip))
        end_x, end_y = pts[-1]
        parts.append(_text(end_x + 8, end_y + 4, s.build, "ink2", size=11))
    for p in published:
        x, y = xscale(p.grid_points), yscale(p.pushes_per_ns)
        approx = "≈" if p.source == "figure" else ""
        tip = f"{p.gpu} (published): {approx}{p.pushes_per_ns:g} pushes/ns at {p.grid_points:,.0f} grid points"
        parts.append(
            f'<circle class="ref" cx="{x:.1f}" cy="{y:.1f}" r="{MARKER_RADIUS}"><title>{escape(tip)}</title></circle>'
        )
        parts.append(_text(x + 8, y + 4, f"{p.gpu} {approx}".strip(), "ink2", size=11))
    items = [(s.label, s.slot, "line") for s in series]
    if published:
        items.append(
            ("Published GPUs, Tan et al. 2025: larger problem, for scale only (≈: read off the figure)", -1, "ref")
        )
    parts += _legend(items, MARGIN_TOP + plot_h + AXIS_BAND + 8)
    return _finish(parts)


def load_published(config_path: Path) -> list[PublishedPoint]:
    """Read ``[published_push_rate]`` points from a results folder's config copy (empty if absent).

    Raises
    ------
    PlotError
        If the section exists but a point is malformed.
    """
    try:
        raw = tomllib.loads(config_path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        log.warning("%s: unreadable; plotting without published values", config_path)
        return []
    section = raw.get("published_push_rate")
    if section is None:
        return []
    try:
        return [
            PublishedPoint(str(p["gpu"]), float(p["grid_points"]), float(p["pushes_per_ns"]), str(p["source"]))
            for p in section["points"]
        ]
    except (KeyError, TypeError, ValueError) as e:
        raise PlotError(f"{config_path}: malformed [published_push_rate]: {e}") from e


# Helpers below: data access, then SVG building blocks.


def _is_lpi(case: dict[str, Any]) -> bool:
    return "lpi" in str(case.get("deck", "")).lower() or case["name"].startswith("lpi")


def _grid_points(case: dict[str, Any]) -> int:
    return int(case["nx"]) * int(case["ny"]) * int(case["nz"])


def _series(results: dict[str, Any], names: list[str], build: str, slot: int, metric: str) -> Series:
    meds, lows, highs, layout = [], [], [], ""
    for name in names:
        try:
            entry = results["summary"][name][build]
            stats = entry["stats"][metric]
        except KeyError as e:
            raise PlotError(f"case {name}, build {build}: no {metric} ({e})") from e
        layout = entry.get("layout", layout)
        meds.append(stats["median"])
        lows.append(stats["min"])
        highs.append(stats["max"])
    kind = "GPU" if results["builds"][build].get("gpu") else "CPU"
    return Series(build, f"{build} ({kind}, {layout.replace('x', '×')} ranks×threads)", slot, meds, lows, highs)


def _bar_panel(
    series: list[Series], names: list[str], x0: int, y0: int, w: int, h: int, title: str, unit: str, show_names: bool
) -> list[str]:
    top = max(v for s in series for v in s.highs) * LABEL_ROOM
    scale = _LinScale(0.0, top, x0, x0 + w)
    parts = []
    for t in _nice_ticks(0.0, top):
        x = scale(t)
        parts.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{y0}" y2="{y0 + h}"/>')
        parts.append(_text(x, y0 + h + 16, f"{t:g}", "muted", anchor="middle", size=11))
    parts.append(f'<line class="axis" x1="{x0}" x2="{x0}" y1="{y0}" y2="{y0 + h}"/>')
    parts.append(_text(x0 + w / 2, y0 + h + 36, title, "ink2", anchor="middle", size=12))
    group = len(series) * (BAR_THICKNESS + BAR_GAP) + GROUP_GAP
    for c, name in enumerate(names):
        gy = y0 + c * group + GROUP_GAP / 2
        if show_names:
            mid = gy + len(series) * (BAR_THICKNESS + BAR_GAP) / 2
            parts.append(_text(x0 - 10, mid + 4, name, "ink", anchor="end", size=12))
        for k, s in enumerate(series):
            y = gy + k * (BAR_THICKNESS + BAR_GAP)
            v, lo, hi = s.medians[c], s.lows[c], s.highs[c]
            tip = f"{name} · {s.label}: {v:.4g} {unit} (range {lo:.4g}-{hi:.4g})"
            parts.append(_bar(scale(0), scale(v), y, s.slot, tip))
            mid = y + BAR_THICKNESS / 2
            parts.append(
                f'<line class="whisker" x1="{scale(lo):.1f}" x2="{scale(hi):.1f}" y1="{mid:.1f}" y2="{mid:.1f}"/>'
            )
            if k > 0:
                parts.append(
                    _text(scale(max(v, hi)) + 6, mid + 4, _speedup_label(series[0].medians[c] / v), "ink2", size=11)
                )
    return parts


def _speedup_label(ratio: float) -> str:
    """Describe reference time / this time as faster or slower than the reference build."""
    return f"{ratio:.2f}× faster" if ratio >= 1 else f"{1 / ratio:.2f}× slower"


def _bar(x_start: float, x_end: float, y: float, slot: int, tip: str) -> str:
    """A horizontal bar anchored at the baseline with a 4 px rounded data end."""
    length = max(x_end - x_start, 0.0)
    r = min(BAR_RADIUS, length / 2, BAR_THICKNESS / 2)
    t = BAR_THICKNESS
    d = (
        f"M{x_start:.1f},{y:.1f} H{x_start + length - r:.1f} "
        f"Q{x_start + length:.1f},{y:.1f} {x_start + length:.1f},{y + r:.1f} "
        f"V{y + t - r:.1f} Q{x_start + length:.1f},{y + t:.1f} {x_start + length - r:.1f},{y + t:.1f} "
        f"H{x_start:.1f} Z"
    )
    return f'<path class="s{slot}" stroke="none" d="{d}"><title>{escape(tip)}</title></path>'


def _marker(x: float, y: float, slot: int, tip: str) -> str:
    return f'<circle class="s{slot} ring" cx="{x:.1f}" cy="{y:.1f}" r="{MARKER_RADIUS}"><title>{escape(tip)}</title></circle>'


def _log_grid(xs: _LogScale, ys: _LogScale, top: int, bottom: int, xtitle: str, ytitle: str) -> list[str]:
    parts = []
    for t in xs.ticks():
        x = xs(t)
        parts.append(f'<line class="grid" x1="{x:.1f}" x2="{x:.1f}" y1="{top}" y2="{bottom}"/>')
        parts.append(_text(x, bottom + 16, _fmt_count(t), "muted", anchor="middle", size=11))
    for t in ys.ticks():
        y = ys(t)
        parts.append(f'<line class="grid" x1="{xs.lo_px}" x2="{xs.hi_px}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(_text(xs.lo_px - 8, y + 4, f"{t:g}", "muted", anchor="end", size=11))
    parts.append(f'<line class="axis" x1="{xs.lo_px}" x2="{xs.hi_px}" y1="{bottom}" y2="{bottom}"/>')
    parts.append(
        _text((xs.lo_px + xs.hi_px) / 2, bottom + 36, xtitle + " (log scale)", "ink2", anchor="middle", size=12)
    )
    mid = (top + bottom) / 2
    parts.append(
        f'<text class="ink2" font-size="12" text-anchor="middle" transform="translate({xs.lo_px - 62},{mid}) rotate(-90)">'
        f"{escape(ytitle)} (log scale)</text>"
    )
    return parts


def _legend(items: list[tuple[str, int, str]], y: float) -> list[str]:
    """One legend row below the axes: (label, slot or -1 for the reference style, mark kind)."""
    parts, x = [], MARGIN_LEFT
    for label, slot, kind in items:
        width = 24 + CHAR_WIDTH * len(label)
        if x > MARGIN_LEFT and x + width > FIG_WIDTH - MARGIN_RIGHT:
            x, y = MARGIN_LEFT, y + LEGEND_ROW
        if kind == "bar":
            parts.append(f'<rect class="s{slot}" stroke="none" x="{x}" y="{y + 2}" width="14" height="10" rx="2"/>')
        elif kind == "line":
            parts.append(f'<line class="line s{slot}" x1="{x}" x2="{x + 16}" y1="{y + 7}" y2="{y + 7}"/>')
            parts.append(f'<circle class="s{slot}" cx="{x + 8}" cy="{y + 7}" r="{MARKER_RADIUS}"/>')
        else:
            parts.append(f'<circle class="ref" cx="{x + 8}" cy="{y + 7}" r="{MARKER_RADIUS}"/>')
        parts.append(_text(x + 24, y + 11, label, "ink", size=12))
        x += width + 24
    return parts


def _header(title: str, subtitle: str, height: int) -> list[str]:
    return [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" class="root" width="{FIG_WIDTH}" height="{height}" '
            f'viewBox="0 0 {FIG_WIDTH} {height}" role="img" aria-label="{escape(title)}">'
        ),
        f"<title>{escape(title)}</title>",
        f"<style>{STYLE}</style>",
        f'<rect class="surface" x="0" y="0" width="{FIG_WIDTH}" height="{height}"/>',
        _text(MARGIN_LEFT, 26, title, "ink", size=16, weight=600),
        _text(MARGIN_LEFT, 46, subtitle, "ink2", size=12),
    ]


def _finish(parts: list[str]) -> str:
    return "\n".join(parts + ["</svg>"]) + "\n"


def _text(x: float, y: float, s: str, cls: str, anchor: str = "start", size: int = 12, weight: int = 400) -> str:
    return (
        f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}">{escape(s)}</text>'
    )


def _write(path: Path, svg: str) -> Path:
    path.write_text(svg)
    return path


def _fmt_count(v: float) -> str:
    if v >= 1e6:
        return f"{v / 1e6:g}M"
    if v >= 1e3:
        return f"{v / 1e3:g}k"
    return f"{v:g}"


def _nice_ticks(lo: float, hi: float, target: int = 5) -> list[float]:
    """Round tick values covering [lo, hi], about ``target`` of them."""
    raw = (hi - lo) / target
    mag = 10 ** math.floor(math.log10(raw))
    step = min((m * mag for m in (1, 2, 2.5, 5, 10)), key=lambda st: abs(st - raw))
    first = math.ceil(lo / step) * step
    return [round(first + k * step, 10) for k in range(int((hi - first) / step) + 1)]


class _LinScale:
    def __init__(self, lo: float, hi: float, lo_px: float, hi_px: float) -> None:
        self.lo, self.hi, self.lo_px, self.hi_px = lo, hi, lo_px, hi_px

    def __call__(self, v: float) -> float:
        return self.lo_px + (v - self.lo) / (self.hi - self.lo) * (self.hi_px - self.lo_px)


class _LogScale:
    def __init__(self, lo: float, hi: float, lo_px: float, hi_px: float) -> None:
        self.lo, self.hi, self.lo_px, self.hi_px = math.log10(lo), math.log10(hi), lo_px, hi_px

    def __call__(self, v: float) -> float:
        return self.lo_px + (math.log10(v) - self.lo) / (self.hi - self.lo) * (self.hi_px - self.lo_px)

    def ticks(self) -> list[float]:
        """1, 2 and 5 times each power of ten inside the range (decades only if that is too dense)."""
        out = []
        for e in range(math.floor(self.lo), math.ceil(self.hi) + 1):
            for m in (1, 2, 5):
                v = m * 10.0**e
                if self.lo <= math.log10(v) <= self.hi:
                    out.append(v)
        return out if len(out) <= 12 else [v for v in out if math.isclose(math.log10(v) % 1, 0, abs_tol=1e-9)]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
