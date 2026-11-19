"""Tests of the log parsing, energy comparison, statistics and summary logic.

Fixtures in data/ are captured VPIC output: a 3D 64^3, 8x1 run of the
template Harris deck (40 steps, status every 20), and the first 20 energy
dumps of a 2D run from the default build and the VPIC_DISABLE_DEVICE_FP64
build. Run from benchmarks/: python3.12 -m unittest
"""

import math
import tempfile
import unittest
from pathlib import Path

import bench_config as bc
import report
import vpic_bench
import vpic_output as vo

DATA = Path(__file__).parent / "data"
BENCH = Path(__file__).parent.parent
LOG = (DATA / "vpic_3d64_np8x1.log").read_text()
STEADY_TABLE_S = 1.244887  # sum of the step-40 table's phases except user_diagnostics (awk)
HARRIS_BULK = ["bz", "electron", "ion"]
LPI_LOG = (DATA / "lpi_24cubed_1M_np8x1.log").read_text()


class ParseLogTest(unittest.TestCase):
    def setUp(self) -> None:
        self.log = vo.parse_log(LOG)

    def test_header_numbers(self) -> None:
        self.assertEqual(self.log.nstep, 40)
        self.assertAlmostEqual(self.log.nptotal or 0, 1.67772e7)
        self.assertAlmostEqual(self.log.advance_s or 0, 2.61454)
        self.assertEqual(self.log.completed_steps, [20, 40])
        self.assertTrue(self.log.normal_exit)
        self.assertEqual(self.log.build_details["VPIC Git Hash"], "7eb2947e12741df4931088a3ae6175adb21a6535")

    def test_tables_survive_interleaved_output(self) -> None:
        # init table, step 20, step 40, and the empty table printed at exit
        self.assertEqual(len(self.log.tables), 4)
        # the init table is split by the "Run Details" block; rows after it still count
        self.assertIn("clean_div_e", self.log.tables[0])
        self.assertIn("compute_div_b_err", self.log.tables[0])
        self.assertAlmostEqual(self.log.tables[2]["advance_p"].seconds, 0.9091)
        self.assertEqual(self.log.tables[2]["advance_p"].count, 40)
        self.assertEqual(self.log.tables[3]["advance_p"].count, 0)

    def test_metrics_use_last_window_with_steps(self) -> None:
        m = vo.metrics(self.log)
        self.assertEqual(m.steady_steps, 20)
        self.assertAlmostEqual(m.wall_ms_per_step, 1e3 * 2.61454 / 40)
        self.assertAlmostEqual(m.steady_ms_per_step, 1e3 * STEADY_TABLE_S / 20, places=3)
        self.assertAlmostEqual(m.push_ns_per_particle, 1e9 * 0.9091 / 20 / 1.67772e7, places=6)
        self.assertAlmostEqual(m.sort_share, 0.03016 / STEADY_TABLE_S, places=5)
        self.assertNotIn("user_diagnostics", m.phases_ms_per_step)

    def test_lpi_push_rate(self) -> None:
        # LPI deck, 24^3 cells, 1M particles, 20 steps at 8x1: the step-20 table covers 10 steps
        m = vo.metrics(vo.parse_log(LPI_LOG))
        self.assertEqual(m.steady_steps, 10)
        self.assertAlmostEqual(m.pushes_per_ns, 1e6 * 10 / (2.374e-2 * 1e9))
        self.assertAlmostEqual(m.pushes_per_ns * m.push_ns_per_particle, 1.0)

    def test_push_rate(self) -> None:
        self.assertAlmostEqual(vo.push_rate(12e6, 20, 0.06), 4.0)
        self.assertEqual(vo.push_rate(12e6, 20, 0.0), 0.0)

    def test_truncated_log_raises(self) -> None:
        cut = LOG[: LOG.index("*** Done")]
        with self.assertRaises(ValueError):
            vo.metrics(vo.parse_log(cut))
        with self.assertRaises(ValueError):
            vo.metrics(vo.parse_log(LOG[: LOG.index("Completed step 20")]))


class EnergyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.ref = vo.parse_energies((DATA / "energies_ref").read_text())
        self.fp32 = vo.parse_energies((DATA / "energies_fp32").read_text())

    def test_parse(self) -> None:
        cols, rows = self.ref
        self.assertEqual(cols, ["ex", "ey", "ez", "bx", "by", "bz", "electron", "ion"])
        self.assertEqual([s for s, _ in rows], list(range(21)))
        self.assertEqual(rows[0][1][5], 2.488889e3)

    def test_identical_runs_differ_by_zero(self) -> None:
        d = vo.energy_differences(self.ref, self.ref)
        self.assertEqual(set(d.values()), {0.0})
        self.assertEqual(vo.energy_check(d, 1e-3, 1e-2, HARRIS_BULK), [])

    def test_float_build_within_tolerance(self) -> None:
        d = vo.energy_differences(self.ref, self.fp32)
        self.assertGreater(max(d.values()), 0)
        self.assertEqual(vo.energy_check(d, 1e-3, 1e-2, HARRIS_BULK), [])

    def test_perturbed_column_fails(self) -> None:
        cols, rows = self.ref
        bad = (cols, [(s, v[:6] + [v[6] * 1.01] + v[7:]) for s, v in rows])  # electron energy +1 %
        d = vo.energy_differences(self.ref, bad)
        self.assertAlmostEqual(d["electron"], 0.01, places=3)
        self.assertEqual(vo.energy_check(d, 1e-3, 1e-2, HARRIS_BULK), ["electron"])

    def test_nan_fails(self) -> None:
        self.assertEqual(vo.energy_check({"ex": math.nan, "bz": 0.0}, 1e-3, 1e-2, HARRIS_BULK), ["ex"])

    def test_nan_after_first_step_propagates(self) -> None:
        cols, rows = self.ref
        bad = (cols, rows[:-1] + [(rows[-1][0], [math.nan] + rows[-1][1][1:])])  # ex is NaN at the last dump
        d = vo.energy_differences(self.ref, bad)
        self.assertTrue(math.isnan(d["ex"]))
        self.assertEqual(vo.energy_check(d, 1e-3, 1e-2, HARRIS_BULK), ["ex"])

    def test_worst_keeps_nan(self) -> None:
        w = vo.worst([{"ex": 0.1}, {"ex": math.nan}, {"ex": 0.2}])
        self.assertTrue(math.isnan(w["ex"]))
        self.assertEqual(vo.worst([{"ex": 0.1}, {"ex": 0.3}]), {"ex": 0.3})

    def test_ragged_row_raises_value_error(self) -> None:
        cols, rows = self.ref
        with self.assertRaises(ValueError):
            vo.energy_differences(self.ref, (cols, rows[:-1] + [(rows[-1][0], rows[-1][1][:3])]))

    def test_mismatched_dumps_raise(self) -> None:
        cols, rows = self.ref
        with self.assertRaises(ValueError):
            vo.energy_differences(self.ref, (cols, rows[:-1]))
        with self.assertRaises(ValueError):
            vo.energy_differences(self.ref, (cols[::-1], rows))


class StatsTest(unittest.TestCase):
    def test_stats_and_speedup(self) -> None:
        s = vo.stats([10.0, 12.0, 11.0])
        self.assertEqual((s["median"], s["min"], s["max"], s["n"]), (11.0, 10.0, 12.0, 3))
        self.assertAlmostEqual(s["spread"], 2 / 11)
        self.assertEqual(vo.speedup(100.0, 25.0), 4.0)
        self.assertIsNone(vo.speedup(100.0, 0.0))


class ConfigTest(unittest.TestCase):
    def test_shipped_config_loads(self) -> None:
        cfg = bc.load_config(BENCH / "config.toml")
        for preset in ("smoke", "small", "medium", "large"):
            self.assertIn(preset, cfg.presets)
        self.assertEqual(cfg.cases["2d-small"].particles, 512 * 512 * 100)

    def test_unknown_key_fails(self) -> None:
        text = (BENCH / "config.toml").read_text().replace("repeats = 3", "repeat = 3")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "c.toml"
            p.write_text(text)
            with self.assertRaises(bc.ConfigError):
                bc.load_config(p)

    def test_layouts(self) -> None:
        self.assertEqual(bc.parse_layout("8x1"), (8, 1))
        for bad in ("8", "0x1", "ax2"):
            with self.assertRaises(bc.ConfigError):
                bc.parse_layout(bad)
        self.assertEqual(bc.expand_layouts(["auto"], 10, sweep=False), [(8, 1)])
        self.assertEqual(bc.expand_layouts(["auto", "8x1"], 10, sweep=True), [(1, 10), (2, 5), (4, 2), (8, 1)])
        self.assertEqual(bc.expand_layouts(["auto"], 16, sweep=False), [(16, 1)])

    def test_layouts_with_core_counts(self) -> None:
        self.assertEqual(bc.expand_layouts(["1xP"], 10, sweep=False, perf_cores=4), [(1, 4)])
        self.assertEqual(
            bc.expand_layouts(["1x1", "1xP", "1xC"], 10, sweep=True, perf_cores=4), [(1, 1), (1, 4), (1, 10)]
        )
        self.assertEqual(bc.expand_layouts(["1xP", "1x4"], 10, sweep=False, perf_cores=4), [(1, 4)])
        with self.assertRaises(bc.ConfigError):
            bc.expand_layouts(["1xP"], 10, sweep=False)

    def test_case_fits(self) -> None:
        cfg = bc.load_config(BENCH / "config.toml")
        c = bc.Case("t", deck="harris", nx=128, ny=128, nz=1, nppc=32, nstep=40)
        self.assertTrue(c.fits(8, cfg.decks["harris"]))
        self.assertFalse(c.fits(3, cfg.decks["harris"]))  # ny not divisible
        self.assertEqual(c.deck_args(cfg.decks["harris"]), ["128", "128", "1", "32", "40"])

    def test_lpi_case_args_and_fits(self) -> None:
        cfg = bc.load_config(BENCH / "config.toml")
        lpi = cfg.decks["lpi"]
        c = cfg.cases["lpi-34"]
        self.assertEqual(c.deck_args(lpi), ["34", "34", "34", "12000000", "40", "0"])
        self.assertEqual((c.particles, c.grid_points), (12_000_000, 39_304))
        self.assertTrue(c.fits(8, lpi))  # 2x2x2 of 17^3
        self.assertFalse(c.fits(3, lpi))
        # every point of the sweep has the same particle count and sorting off
        sweep = [cfg.cases[n] for n in cfg.presets["lpi-sweep"]]
        self.assertEqual({(s.particles, s.sort_interval) for s in sweep}, {(12_000_000, 0)})
        self.assertTrue({13_824, 39_304, 85_184} <= {s.grid_points for s in sweep})

    def test_topology_mirrors_deck(self) -> None:
        self.assertEqual(bc.topology(1, 24, 24, 24), (1, 1, 1))
        self.assertEqual(bc.topology(8, 24, 24, 24), (2, 2, 2))
        self.assertEqual(bc.topology(4, 34, 34, 34), (2, 2, 1))
        self.assertEqual(bc.topology(2, 200, 100, 100), (2, 1, 1))
        self.assertEqual(bc.topology(6, 24, 24, 24), (2, 3, 1))
        self.assertIsNone(bc.topology(8, 25, 25, 25))

    def test_case_validation(self) -> None:
        base = (BENCH / "config.toml").read_text()
        bad_edits = [
            # LPI case without its sort interval
            ("total_particles = 1000000\nnstep = 20\nsort_interval = 0", "total_particles = 1000000\nnstep = 20"),
            # both particle counts
            ("nx = 128\nny = 128\nnz = 1\nnppc = 32", "nx = 128\nny = 128\nnz = 1\nnppc = 32\ntotal_particles = 4"),
            # unknown deck
            ('deck = "lpi"\nnx = 24', 'deck = "nope"\nnx = 24'),
            # published point with an unknown source
            ('source = "figure"', 'source = "guess"'),
        ]
        for old, new in bad_edits:
            self.assertIn(old, base)
            with tempfile.TemporaryDirectory() as d:
                p = Path(d) / "c.toml"
                p.write_text(base.replace(old, new, 1))
                with self.assertRaises(bc.ConfigError, msg=new):
                    bc.load_config(p)

    def test_published_push_rate(self) -> None:
        pub = bc.load_config(BENCH / "config.toml").published_push_rate
        assert pub is not None
        self.assertIn("10.1145/3731599.3767493", pub.citation)
        text = {(p.gpu, p.grid_points, p.pushes_per_ns) for p in pub.points if p.source == "text"}
        self.assertEqual(text, {("V100", 13824, 4.0), ("A100", 85184, 6.0), ("MI300A", 39304, 9.0)})
        self.assertEqual(sum(p.source == "figure" for p in pub.points), 3)


class SummaryTest(unittest.TestCase):
    """report.summarize on a synthetic record: one case, a CPU reference and a faster GPU."""

    def record(self, gpu_diff: float) -> dict:
        def run(build: str, rep: int, steady: float, diff: float) -> dict:
            metrics = {
                "wall_ms_per_step": steady * 1.1,
                "steady_ms_per_step": steady,
                "push_ns_per_particle": steady / 10,
                "sort_share": 0.1,
            }
            return {
                "case": "c",
                "build": build,
                "phase": "measure",
                "rep": rep,
                "layout": "8x1",
                "metrics": metrics,
                "error": None,
                "energy_diff": {"bz": diff, "ex": diff},
            }

        runs = [run("cpu", i, s, 0.0) for i, s in enumerate((100.0, 104.0, 98.0))]
        runs += [run("gpu", i, s, gpu_diff) for i, s in enumerate((20.0, 25.0, 21.0))]
        return {
            "settings": {"reference": "cpu", "physics": {"tol_bulk": 1e-3, "tol_fluctuation": 1e-2}},
            "cases": {"c": {"particles": 1000}},
            "builds": {"cpu": {}, "gpu": {}},
            "runs": runs,
        }

    def test_speedup_and_pass(self) -> None:
        s = report.summarize(self.record(1e-5))["c"]
        self.assertEqual(s["cpu"]["speedup"]["steady_ms_per_step"], 1.0)
        self.assertAlmostEqual(s["gpu"]["speedup"]["steady_ms_per_step"], 100.0 / 21.0)
        self.assertAlmostEqual(s["gpu"]["speedup"]["push_ns_per_particle"], 100.0 / 21.0)
        self.assertTrue(s["gpu"]["physics"]["passed"])

    def test_physics_failure_flagged(self) -> None:
        p = report.summarize(self.record(5e-3))["c"]["gpu"]["physics"]
        self.assertFalse(p["passed"])
        self.assertEqual(p["failing"], ["bz"])  # 5e-3 exceeds the bulk but not the fluctuation tolerance

    def test_bulk_columns_come_from_the_case(self) -> None:
        rec = self.record(5e-3)
        rec["cases"]["c"]["bulk_energy_columns"] = ["electron", "I2"]  # LPI: bz is a fluctuation column
        self.assertTrue(report.summarize(rec)["c"]["gpu"]["physics"]["passed"])

    def test_push_rate_stats_and_markdown(self) -> None:
        rec = self.record(1e-5)
        for r in rec["runs"]:
            r["metrics"]["pushes_per_ns"] = 1 / r["metrics"]["push_ns_per_particle"]
        rec["cases"]["c"].update({"deck": "lpi", "nx": 24, "ny": 24, "nz": 24})
        summary = report.summarize(rec)
        self.assertAlmostEqual(summary["c"]["gpu"]["stats"]["pushes_per_ns"]["median"], 10 / 21.0)
        rec.update(
            id="x",
            created="now",
            machine_label="m",
            repo={"commit": "abc", "branch": "b", "dirty": False},
            decks={"lpi": {"path": "benchmarks/decks/lpi_bench.deck", "sha256": "0" * 64}},
            conditions_start={
                "power_source": "AC",
                "low_power_mode": False,
                "thermal_state": "nominal",
                "load_average": [1, 1, 1],
            },
        )
        rec["settings"].update(repeats=3, warmup=1, max_process_cpu_percent=80)
        rec["builds"] = {
            "cpu": {"path": "p", "gpu": False, "cmake": {}},
            "gpu": {"path": "q", "gpu": True, "cmake": {}},
        }
        md = report.markdown(rec, summary)
        self.assertIn("## Push rate", md)
        self.assertIn("| c | 13,824 | 1,000 | 0.100 | 0.476 |", md)


class CompareEnergiesTest(unittest.TestCase):
    def test_missing_reference_energies_are_recorded_not_raised(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "ref").mkdir()  # no energies file
            (out / "gpu").mkdir()
            (out / "gpu" / "energies").write_text((DATA / "energies_ref").read_text())
            runs = [
                {"case": "c", "build": "cpu", "phase": "measure", "dir": "ref", "error": None},
                {"case": "c", "build": "metal", "phase": "measure", "dir": "gpu", "error": None},
            ]
            record: dict = {"runs": runs, "warnings": []}
            case = bc.Case("c", deck="harris", nx=8, ny=8, nz=1, nppc=2, nstep=40)
            vpic_bench.compare_energies(case, "cpu", record, out)
            self.assertTrue(all("energy_error" in r for r in runs))
            self.assertEqual(len(record["warnings"]), 1)

    def test_is_good_rejects_runs_with_errors(self) -> None:
        self.assertTrue(vpic_bench.is_good({"error": None, "metrics": {"steady_ms_per_step": 1.0}}))
        bad_count = {"error": "log reports 1 particles", "metrics": {"steady_ms_per_step": 1.0}}
        self.assertFalse(vpic_bench.is_good(bad_count))
        self.assertFalse(vpic_bench.is_good({"error": None, "metrics": None}))


if __name__ == "__main__":
    unittest.main()
