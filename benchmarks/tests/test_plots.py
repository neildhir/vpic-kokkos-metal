"""Tests of plots.py on a synthetic results folder. Run from benchmarks/: python3.12 -m unittest"""

import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import plots

SVG = "{http://www.w3.org/2000/svg}"

PUBLISHED_TOML = """
[published_push_rate]
citation = "test"

[[published_push_rate.points]]
gpu = "V100"
grid_points = 13824
pushes_per_ns = 4.0
source = "text"

[[published_push_rate.points]]
gpu = "A100"
grid_points = 1900000
pushes_per_ns = 1.3
source = "figure"
"""


def _stats(median: float, lo: float, hi: float) -> dict[str, float]:
    return {"median": median, "min": lo, "max": hi, "spread": (hi - lo) / median, "n": 3}


def _entry(layout: str, step_ms: float, push_ns: float) -> dict[str, Any]:
    return {
        "layout": layout,
        "stats": {
            "steady_ms_per_step": _stats(step_ms, 0.9 * step_ms, 1.1 * step_ms),
            "push_ns_per_particle": _stats(push_ns, 0.95 * push_ns, 1.05 * push_ns),
        },
    }


def _results(builds: list[str]) -> dict[str, Any]:
    cases = {
        "2d-small": {"name": "2d-small", "nx": 512, "ny": 512, "nz": 1},
        "lpi-24": {"name": "lpi-24", "deck": "lpi", "nx": 24, "ny": 24, "nz": 24},
        "lpi-64": {"name": "lpi-64", "deck": "lpi", "nx": 64, "ny": 64, "nz": 64},
    }
    timing = {"cpu": ("8x1", 100.0, 4.0), "metal": ("1x4", 50.0, 2.0), "third": ("1x1", 70.0, 3.0)}
    return {
        "id": "test",
        "machine_label": "test machine",
        "builds": {b: {"gpu": b != "cpu"} for b in builds},
        "cases": cases,
        "summary": {name: {b: _entry(*timing[b]) for b in builds} for name in cases},
    }


class PlotResultsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        (self.folder / "config.toml").write_text(PUBLISHED_TOML)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _plot(self, builds: list[str]) -> dict[str, ET.Element]:
        (self.folder / "results.json").write_text(json.dumps(_results(builds)))
        return {p.name: ET.parse(p).getroot() for p in plots.plot_results(self.folder)}

    def test_writes_one_figure_per_deck_as_valid_svg(self) -> None:
        figures = self._plot(["cpu", "metal"])
        self.assertEqual(sorted(figures), ["push_rate_vs_grid.svg", "step_and_push.svg"])

    def test_push_rate_figure_marks(self) -> None:
        root = self._plot(["cpu", "metal"])["push_rate_vs_grid.svg"]
        circles = root.findall(f"{SVG}circle")
        refs = [c for c in circles if c.get("class") == "ref" and c.find(f"{SVG}title") is not None]
        series = [c for c in circles if "ring" in (c.get("class") or "")]
        self.assertEqual(len(refs), 2)  # one per published point
        self.assertEqual(len(series), 4)  # 2 builds x 2 LPI cases
        tips = [c.findtext(f"{SVG}title") or "" for c in series]
        # 2 ns per particle push is 0.5 pushes per ns; 4 ns is 0.25
        self.assertTrue(any(t.startswith("metal") and "0.5 pushes/ns" in t for t in tips), tips)
        self.assertTrue(any(t.startswith("cpu") and "0.25 pushes/ns" in t for t in tips), tips)
        ref_tips = [c.findtext(f"{SVG}title") or "" for c in refs]
        self.assertIn("≈1.3", " ".join(ref_tips))  # read off the figure, so marked approximate

    def test_bar_figure_labels_speedup_against_first_build(self) -> None:
        root = self._plot(["cpu", "metal"])["step_and_push.svg"]
        texts = [t.text or "" for t in root.iter(f"{SVG}text")]
        self.assertIn("2.00× faster", texts)  # 100 ms -> 50 ms, and 4 ns -> 2 ns

    def test_refuses_more_builds_than_validated_colours(self) -> None:
        with self.assertRaises(plots.PlotError):
            self._plot(["cpu", "metal", "third"])


class HelpersTest(unittest.TestCase):
    def test_speedup_label(self) -> None:
        self.assertEqual(plots._speedup_label(2.0), "2.00× faster")
        self.assertEqual(plots._speedup_label(0.5), "2.00× slower")

    def test_nice_ticks_cover_range(self) -> None:
        ticks = plots._nice_ticks(0.0, 13.5)
        self.assertEqual(ticks[0], 0.0)
        self.assertGreaterEqual(len(ticks), 4)
        self.assertLessEqual(ticks[-1], 13.5)

    def test_published_section_optional_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "config.toml"
            p.write_text('deck = "x"\n')
            self.assertEqual(plots.load_published(p), [])
            p.write_text('[published_push_rate]\npoints = [{ gpu = "V100" }]\n')
            with self.assertRaises(plots.PlotError):
                plots.load_published(p)


if __name__ == "__main__":
    unittest.main()
