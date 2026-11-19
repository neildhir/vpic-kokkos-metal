"""Summarise run records into per-case, per-build numbers and a Markdown table.

Pure functions on the result record that vpic_bench.py writes, so a summary
can be regenerated from any results.json (``python3 report.py <results.json>``).
"""

import json
import sys
from pathlib import Path
from typing import Any

import vpic_output as vo

TIMING_KEYS = ("wall_ms_per_step", "steady_ms_per_step", "push_ns_per_particle", "sort_share", "pushes_per_ns")
SPEEDUP_KEYS = TIMING_KEYS[:3]  # times, where speed-up = reference / build


def summarize(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per case and build: timing statistics, speed-ups and the physics check.

    Parameters
    ----------
    record : dict[str, Any]
        The results.json record: ``runs``, ``builds`` (in order), ``cases``,
        ``settings.reference`` and ``settings.physics``.

    Returns
    -------
    dict[str, dict[str, Any]]
        ``summary[case][build]`` with ``layout``, a ``stats`` dict per timing
        key over the measured runs, ``speedup`` (reference median over build
        median, per timing key except sort_share) and ``physics``.
    """
    ref = record["settings"]["reference"]
    tol = record["settings"]["physics"]
    out: dict[str, dict[str, Any]] = {}
    for case in record["cases"]:
        per_build: dict[str, Any] = {}
        for label in record["builds"]:
            runs = [r for r in record["runs"] if r["case"] == case and r["build"] == label]
            measured = [r for r in runs if r["phase"] == "measure" and r.get("metrics")]
            entry: dict[str, Any] = {
                "layout": measured[0]["layout"] if measured else None,
                "failed_runs": sum(1 for r in runs if r.get("error")),
                "busy_runs": sum(1 for r in measured if r.get("busy_before")),
                "stats": _stats(measured),
                "physics": _physics(runs, tol["tol_bulk"], tol["tol_fluctuation"], bulk_columns(record, case)),
            }
            per_build[label] = entry
        ref_stats = per_build.get(ref, {}).get("stats", {})
        for entry in per_build.values():
            entry["speedup"] = {
                k: vo.speedup(ref_stats[k]["median"], entry["stats"][k]["median"])
                for k in SPEEDUP_KEYS
                if ref_stats and entry["stats"]
            }
        out[case] = per_build
    return out


def bulk_columns(record: dict[str, Any], case: str) -> list[str]:
    """The case's bulk energy columns (the Harris set for records that predate per-deck columns)."""
    return record["cases"][case].get("bulk_energy_columns", sorted(vo.BULK_COLUMNS))


def _stats(measured: list[dict[str, Any]]) -> dict[str, Any]:
    """Statistics per timing key over the measured runs (keys missing from older records skipped)."""
    if not measured:
        return {}
    keys = [k for k in TIMING_KEYS if all(k in r["metrics"] for r in measured)]
    return {k: vo.stats([r["metrics"][k] for r in measured]) for k in keys}


def _physics(runs: list[dict[str, Any]], tol_bulk: float, tol_fluct: float, bulk: list[str]) -> dict[str, Any]:
    """Worst energy difference of a build's runs against the reference, and the verdict."""
    diffs = [r["energy_diff"] for r in runs if r.get("energy_diff")]
    problems = [r["energy_error"] for r in runs if r.get("energy_error")]
    if not diffs:
        return {"compared": 0, "worst": {}, "failing": [], "problems": problems, "passed": False}
    worst = vo.worst(diffs)
    failing = vo.energy_check(worst, tol_bulk, tol_fluct, bulk)
    return {
        "compared": len(diffs),
        "worst": worst,
        "failing": failing,
        "problems": problems,
        "passed": not failing and not problems,
    }


def markdown(record: dict[str, Any], summary: dict[str, dict[str, Any]]) -> str:
    """The results as a Markdown page: headline table, physics check, fingerprints."""
    s = record["settings"]
    repo = record["repo"]
    lines = [
        f"# VPIC benchmark {record['id']}",
        "",
        f"- Machine: {record['machine_label']}",
        f"- Started: {record['created']}; repo `{repo['commit'][:12]}` on `{repo['branch']}`"
        + (" (uncommitted changes)" if repo["dirty"] else ""),
        *[f"- Deck {name}: `{d['path']}` sha256 `{d['sha256'][:12]}`" for name, d in _decks(record).items()],
        (
            f"- Cases: {', '.join(record['cases'])}; {s['repeats']} measured runs each after {s['warmup']} warm-up; "
            f"builds interleaved per repetition; reference build **{s['reference']}**"
        ),
        "",
        (
            "Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median "
            "over build median (> 1: faster than the reference)."
        ),
        "",
        (
            "| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share "
            "| Speed-up wall | Speed-up step | Speed-up push | Physics; notes |"
        ),
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for case, per_build in summary.items():
        particles = record["cases"][case]["particles"]
        for label, e in per_build.items():
            st, sp = e["stats"], e["speedup"]
            if not st:
                lines.append(f"| {case} | {particles:.3g} | {label} | – | failed | | | | | | | |")
                continue
            lines.append(
                f"| {case} | {particles:.3g} | {label} | {e['layout']} "
                f"| {_ms(st['wall_ms_per_step'])} | {_ms(st['steady_ms_per_step'])} "
                f"| {_rate(st)} | {100 * st['sort_share']['median']:.0f}% "
                f"| {_x(sp.get('wall_ms_per_step'))} | {_x(sp.get('steady_ms_per_step'))} | {_x(sp.get('push_ns_per_particle'))} "
                f"| {_verdict(e['physics'])}{_busy(e, len(measured_of(record, case, label)))} |"
            )
    lines += _push_rate_section(record, summary) + _physics_section(record, summary)
    lines += _builds_section(record) + _conditions_section(record)
    return "\n".join(lines) + "\n"


def _decks(record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Decks of the run (records that predate several decks have one, under "deck")."""
    return record.get("decks") or {"harris": record["deck"]}


def _rate(st: dict[str, Any]) -> str:
    """Median pushes per ns (derived from ns/particle for records that predate the metric)."""
    if "pushes_per_ns" in st:
        return f"{st['pushes_per_ns']['median']:.3f}"
    return f"{1 / st['push_ns_per_particle']['median']:.3f}"


def _push_rate_section(record: dict[str, Any], summary: dict[str, dict[str, Any]]) -> list[str]:
    """Pushes per ns of every build, by case in order of grid size (the LPI sweep's curve)."""
    labels = list(record["builds"])
    lines = [
        "",
        "## Push rate",
        "",
        (
            "Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), "
            "median over the measured runs."
        ),
        "",
        "| Case | Grid points | Particles | " + " | ".join(labels) + " |",
        "| --- | ---: | ---: | " + " | ".join("---:" for _ in labels) + " |",
    ]
    cases = sorted(summary, key=lambda c: (record["cases"][c].get("deck", ""), _grid_points(record["cases"][c])))
    for case in cases:
        c = record["cases"][case]
        rates = [_rate(summary[case][lab]["stats"]) if summary[case][lab]["stats"] else "–" for lab in labels]
        lines.append(f"| {case} | {_grid_points(c):,} | {c['particles']:,} | " + " | ".join(rates) + " |")
    return lines


def _grid_points(case: dict[str, Any]) -> int:
    return case["nx"] * case["ny"] * case["nz"]


def measured_of(record: dict[str, Any], case: str, label: str) -> list[dict[str, Any]]:
    """The measured runs of one case and build."""
    return [r for r in record["runs"] if r["case"] == case and r["build"] == label and r["phase"] == "measure"]


def _busy(entry: dict[str, Any], n: int) -> str:
    return f"; {entry['busy_runs']}/{n} runs busy" if entry["busy_runs"] else ""


def _ms(st: dict[str, float]) -> str:
    return f"{st['median']:.2f} ±{100 * st['spread']:.0f}%"


def _x(v: float | None) -> str:
    return "–" if v is None else f"{v:.2f}×"


def _verdict(p: dict[str, Any]) -> str:
    if p["passed"]:
        return "ok"
    if p["problems"] or not p["compared"]:
        return "**FAIL** (no comparable energies)"
    return f"**FAIL** ({', '.join(p['failing'])})"


def _physics_section(record: dict[str, Any], summary: dict[str, dict[str, Any]]) -> list[str]:
    tol = record["settings"]["physics"]
    by_deck = {c.get("deck", "harris"): bulk_columns(record, name) for name, c in record["cases"].items()}
    bulk_text = "; ".join(f"{d}: {', '.join(cols)}" for d, cols in by_deck.items())
    lines = [
        "",
        "## Physics check",
        "",
        (
            "Energies of every run (all layouts and repetitions) against the reference build's first measured run: "
            f"max over dumps of |ΔE| / max|E_ref| per column. Tolerance {tol['tol_bulk']:g} for each deck's bulk "
            f"columns ({bulk_text}) and {tol['tol_fluctuation']:g} for the other (fluctuation) columns. "
            "The reference row is its own run-to-run noise floor."
        ),
        "",
        "| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for case, per_build in summary.items():
        for label, e in per_build.items():
            w, cols = e["physics"]["worst"], bulk_columns(record, case)
            bulk = max((v for k, v in w.items() if k in cols), default=float("nan"))
            fluct = max((v for k, v in w.items() if k not in cols), default=float("nan"))
            lines.append(
                f"| {case} | {label} | {e['physics']['compared']} | {bulk:.1e} | {fluct:.1e} "
                f"| {_verdict(e['physics'])} |"
            )
    return lines


def _builds_section(record: dict[str, Any]) -> list[str]:
    lines = ["", "## Builds", "", "| Build | Path | GPU | VPIC git | Options |", "| --- | --- | --- | --- | --- |"]
    for label, b in record["builds"].items():
        opts = ", ".join(f"{k}={v}" for k, v in b["cmake"].items() if k.startswith("VPIC_") and v not in ("OFF",))
        backends = ", ".join(
            k.removeprefix("Kokkos_ENABLE_")
            for k, v in b["cmake"].items()
            if k.startswith("Kokkos_ENABLE_") and v == "ON"
        )
        lines.append(
            f"| {label} | `{b['path']}` | {'yes' if b['gpu'] else 'no'} | {b.get('vpic_git_hash', '?')[:12]} "
            f"| Kokkos {backends}; {opts} |"
        )
    return lines


def _conditions_section(record: dict[str, Any]) -> list[str]:
    start, end = record["conditions_start"], record.get("conditions_end") or {}
    busy_runs = sum(1 for r in record["runs"] if r.get("busy_before"))
    lines = [
        "",
        "## Conditions",
        "",
        f"- Power: {start['power_source']}; Low Power Mode: {start['low_power_mode']}",
        f"- Thermal state: {start['thermal_state']} at start, {end.get('thermal_state', '?')} at end",
        f"- Load average (1/5/15 min): {start['load_average']} at start, {end.get('load_average', '?')} at end",
        (
            f"- Runs that started while another process used > {record['settings']['max_process_cpu_percent']}% CPU: "
            f"{busy_runs} (marked busy above; their timings are suspect)"
        ),
    ]
    lines += [f"- Warning: {w}" for w in record.get("warnings", [])]
    return lines


def main() -> None:
    """Regenerate summary.md from a results.json."""
    path = Path(sys.argv[1])
    record = json.loads(path.read_text())
    path.with_name("summary.md").write_text(markdown(record, summarize(record)))


if __name__ == "__main__":
    main()
