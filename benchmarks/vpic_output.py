"""Parse VPIC run output and compare runs: timings, energies, statistics.

Pure functions on text, so the tests can feed them captured VPIC output.
Standard library only.
"""

import re
import statistics
from collections.abc import Collection
from dataclasses import dataclass, field

# Phases left out of a step's time: user_diagnostics holds the harness's own
# energy dumps, which are not part of the physics step being benchmarked.
EXCLUDED_PHASES = frozenset({"user_diagnostics"})

# "Bulk" energy columns carry most of the energy and are compared tightly;
# the others ("fluctuation") start at zero and are set by noise. Each deck
# names its bulk columns in config.toml; this is the Harris deck's set, used for
# results.json files written before decks named them.
BULK_COLUMNS = frozenset({"bz", "electron", "ion"})

_FLOAT = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"
_ROW = re.compile(rf"^\s*(\w+)\s*\|\s*\d+%\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*\|")
_COMPLETED = re.compile(r"Completed step (\d+) of (\d+)")
_DONE = re.compile(rf"\*\*\* Done \(({_FLOAT})s")
_NPTOTAL = re.compile(rf"nptotal = ({_FLOAT})")
_NUM_STEP = re.compile(r"num_step = (\d+)")
_BUILD_DETAIL = re.compile(r"^# ([^:#]+?):\s*(.+?)\s*$")


@dataclass
class Phase:
    """One row of a 'Since Last Update' timing table (rank 0)."""

    seconds: float
    count: float


@dataclass
class RunLog:
    """What a VPIC run log says about the run."""

    nstep: int | None = None
    nptotal: float | None = None
    advance_s: float | None = None  # main advance loop, "*** Done (Xs"
    completed_steps: list[int] = field(default_factory=list)
    tables: list[dict[str, Phase]] = field(default_factory=list)
    build_details: dict[str, str] = field(default_factory=dict)
    normal_exit: bool = False


def parse_log(text: str) -> RunLog:
    """Parse a VPIC run log (stdout and stderr of rank 0, interleaved).

    Each "Since Last Update" header starts a new timing table; any later line
    that looks like a table row belongs to it. Rows can be interleaved with
    other output (stderr and stdout are merged), so non-row lines are skipped
    rather than ending the table.
    """
    log = RunLog()
    in_build = False
    current: dict[str, Phase] | None = None
    for line in text.splitlines():
        if "Since Last Update" in line:
            current = {}
            log.tables.append(current)
            continue
        if "Build Details" in line:
            in_build = "End" not in line
            continue
        if in_build:
            m = _BUILD_DETAIL.match(line)
            if m:
                log.build_details[m.group(1).strip()] = m.group(2)
            continue
        if current is not None:
            m = _ROW.match(line)
            if m:
                current[m.group(1)] = Phase(float(m.group(2)), float(m.group(3)))
                continue
        if m := _COMPLETED.search(line):
            log.completed_steps.append(int(m.group(1)))
            log.nstep = int(m.group(2))
        elif m := _DONE.search(line):
            log.advance_s = float(m.group(1))
        elif m := _NPTOTAL.search(line):
            log.nptotal = float(m.group(1))
        elif log.nstep is None and (m := _NUM_STEP.search(line)):
            log.nstep = int(m.group(1))
        elif line.strip() == "normal exit":
            log.normal_exit = True
    return log


@dataclass
class Metrics:
    """Per-run benchmark numbers derived from a run log."""

    wall_ms_per_step: float  # advance loop wall time / nstep
    steady_ms_per_step: float  # last status window, rank 0 phase sum / steps
    push_ns_per_particle: float  # advance_p, same window, per particle-step
    pushes_per_ns: float  # particles x steps / advance_p time, same window (= 1 / push_ns_per_particle)
    sort_share: float  # sort_particles / steady step time
    steady_steps: int
    phases_ms_per_step: dict[str, float]


def steady_window(log: RunLog) -> tuple[dict[str, Phase], int]:
    """The last timing table that covers steps, and how many steps it covers.

    VPIC prints a table at every status interval and an empty one at exit; the
    last table with a non-zero advance_p count is the steady-state window. Its
    step count is the difference of the last two "Completed step" numbers.

    Raises
    ------
    ValueError
        If the log has no such table or not enough step markers.
    """
    tables = [t for t in log.tables if t.get("advance_p", Phase(0, 0)).count > 0]
    if not tables:
        raise ValueError("no timing table with advance_p steps in the log")
    steps = log.completed_steps
    if not steps:
        raise ValueError("no 'Completed step' markers in the log")
    window = steps[-1] - (steps[-2] if len(steps) > 1 else 0)
    if window <= 0:
        raise ValueError(f"bad steady-state window from steps {steps}")
    return tables[-1], window


def metrics(log: RunLog) -> Metrics:
    """Benchmark numbers of one run.

    Raises
    ------
    ValueError
        If the log lacks the numbers (crashed or truncated run).
    """
    if log.advance_s is None or not log.nstep or not log.nptotal:
        raise ValueError("log lacks '*** Done', num_step or nptotal")
    table, steps = steady_window(log)
    phases = {name: 1e3 * p.seconds / steps for name, p in table.items() if name not in EXCLUDED_PHASES}
    step_ms = sum(phases.values())
    push_ms = phases.get("advance_p", 0.0)
    return Metrics(
        wall_ms_per_step=1e3 * log.advance_s / log.nstep,
        steady_ms_per_step=step_ms,
        push_ns_per_particle=1e6 * push_ms / log.nptotal,
        pushes_per_ns=push_rate(log.nptotal, steps, table["advance_p"].seconds),
        sort_share=phases.get("sort_particles", 0.0) / step_ms if step_ms else 0.0,
        steady_steps=steps,
        phases_ms_per_step=phases,
    )


def parse_energies(text: str) -> tuple[list[str], list[tuple[int, list[float]]]]:
    """Parse a VPIC energies dump: column names and (step, values) rows."""
    columns: list[str] = []
    rows: list[tuple[int, list[float]]] = []
    for line in text.splitlines():
        if line.startswith("%"):
            if line.startswith("% step"):
                columns = [c.strip('"') for c in line.split()[2:]]
            continue
        parts = line.split()
        if parts:
            rows.append((int(parts[0]), [float(x) for x in parts[1:]]))
    return columns, rows


def energy_differences(
    ref: tuple[list[str], list[tuple[int, list[float]]]],
    other: tuple[list[str], list[tuple[int, list[float]]]],
) -> dict[str, float]:
    """Per column, max over steps of |other - ref| / max over steps of |ref|.

    Raises
    ------
    ValueError
        If the two dumps have different columns or steps.
    """
    ref_cols, ref_rows = ref
    cols, rows = other
    if cols != ref_cols:
        raise ValueError(f"energy columns differ: {cols} vs {ref_cols}")
    if [s for s, _ in rows] != [s for s, _ in ref_rows]:
        raise ValueError("energy dumps cover different steps")
    out = {}
    for j, name in enumerate(cols):
        scale = max(abs(v[j]) for _, v in ref_rows) or 1.0
        out[name] = max(abs(a[j] - b[j]) for (_, a), (_, b) in zip(ref_rows, rows))
        out[name] /= scale
    return out


def push_rate(particles: float, steps: int, push_s: float) -> float:
    """Particle pushes per nanosecond: particles x steps / push time.

    Parameters
    ----------
    particles : float
        Macro particles pushed per step (all species).
    steps : int
        Steps in the timed window.
    push_s : float
        advance_p time over those steps [s].

    Returns
    -------
    float
        Pushes per ns; 0 if no push time was recorded.
    """
    return particles * steps / (push_s * 1e9) if push_s > 0 else 0.0


def tolerance(column: str, tol_bulk: float, tol_fluct: float, bulk: Collection[str]) -> float:
    """Physics-check tolerance of an energy column (``bulk``: the bulk column names)."""
    return tol_bulk if column in bulk else tol_fluct


def energy_check(diffs: dict[str, float], tol_bulk: float, tol_fluct: float, bulk: Collection[str]) -> list[str]:
    """Columns whose difference exceeds their tolerance (empty: pass).

    Parameters
    ----------
    diffs : dict[str, float]
        Output of `energy_differences`.
    tol_bulk, tol_fluct : float
        Tolerances of the bulk and fluctuation columns (see config.toml).
    bulk : Collection[str]
        Names of the bulk columns (the deck's ``bulk_energy_columns``).

    Returns
    -------
    list[str]
        Failing columns; a NaN difference fails.
    """
    return [c for c, d in diffs.items() if not d <= tolerance(c, tol_bulk, tol_fluct, bulk)]


def worst(diff_sets: list[dict[str, float]]) -> dict[str, float]:
    """Column-wise maximum over several difference sets."""
    out: dict[str, float] = {}
    for d in diff_sets:
        for k, v in d.items():
            out[k] = max(out.get(k, 0.0), v)
    return out


def stats(values: list[float]) -> dict[str, float]:
    """Median, min, max and relative spread ((max - min) / median)."""
    med = statistics.median(values)
    return {
        "median": med,
        "min": min(values),
        "max": max(values),
        "spread": (max(values) - min(values)) / med if med else 0.0,
        "n": len(values),
    }


def speedup(reference_median: float, build_median: float) -> float | None:
    """Reference time over build time (>1: the build is faster)."""
    return reference_median / build_median if build_median > 0 else None
