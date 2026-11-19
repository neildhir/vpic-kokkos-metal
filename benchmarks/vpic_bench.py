"""Benchmark labelled VPIC builds against each other on identical physics.

Compiles each case's deck with each build (decks must be compiled by the
build they run against), runs every case with every build, interleaving the
builds within each repetition, checks that every run's energies match the
reference build's, and files results.json and summary.md under
results/<timestamp>-<tag>/. See README.md.

Usage
-----
python3.12 vpic_bench.py --build cpu=../build/cpu-openmp --build metal=../build/metal \\
    --preset small --tag m4
"""

import sys

if sys.version_info < (3, 11):  # noqa: UP036 -- system python3 is 3.9; fail with a hint, not on tomllib
    sys.exit("vpic_bench.py needs Python 3.11+ (e.g. python3.12, or: uv run --no-project --python 3.12 vpic_bench.py)")

import argparse
import hashlib
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import bench_config as bc
import machine as mach
import report
import vpic_output as vo

BENCH_DIR = Path(__file__).resolve().parent
REPO_ROOT = BENCH_DIR.parent
WORK_DIR = BENCH_DIR / "work"
RESULTS_DIR = BENCH_DIR / "results"
# CMakeCache entries recorded in every build fingerprint
CMAKE_KEYS = re.compile(
    r"^(VPIC_\w+|ENABLE_\w+|USE_V4_\w+|BUILD_INTERNAL_KOKKOS|Kokkos_ENABLE_\w+|Kokkos_ARCH_\w+|"
    r"CMAKE_BUILD_TYPE|CMAKE_CXX_COMPILER|CMAKE_CXX_FLAGS|CMAKE_CXX_FLAGS_RELEASE|Kokkos_DIR)$"
)

IDLE_POLL_S = 5.0  # polling interval while waiting for other processes to finish [s]

log = logging.getLogger("vpic_bench")


def main() -> int:
    """Check the machine, compile, run, check physics, and file the results."""
    args = parse_args()
    cfg = bc.load_config(Path(args.config))
    hw = mach.machine()
    exclude = mach.own_pids()
    cases = select_cases(cfg, args)
    builds = resolve_builds(cfg, args, hw["cpu_cores"], hw["cpu_performance_cores"])
    reference = args.reference or next(iter(builds))
    if reference not in builds:
        sys.exit(f"--reference {reference!r} is not one of the builds {list(builds)}")
    repeats = args.repeats if args.repeats is not None else cfg.run.repeats
    plan_summary(cases, builds, repeats, cfg)
    if args.dry_run:
        return 0

    start = mach.conditions(cfg.preflight.max_process_cpu_percent, exclude)
    warnings = preflight(cfg, hw, start, cases, args.force)
    created = datetime.now().astimezone()
    run_id = f"{created:%Y%m%d-%H%M%S}-{args.tag}"
    out = RESULTS_DIR / f"{run_id}.incomplete"
    out.mkdir(parents=True)
    logging.getLogger().addHandler(logging.FileHandler(out / "harness.log"))
    shutil.copy(args.config, out / "config.toml")
    decks = {name: cfg.decks[name] for name in dict.fromkeys(c.deck for c in cases)}
    record: dict[str, Any] = {
        "schema": 1,
        "id": run_id,
        "created": created.isoformat(timespec="seconds"),
        "argv": sys.argv,
        "machine": hw,
        "machine_label": mach.label(hw),
        "conditions_start": start,
        "conditions_end": None,
        "forced": args.force,
        "warnings": warnings,
        "repo": repo_state(cfg.run.mpirun),
        "decks": {
            name: {
                **d.__dict__,
                "path": str((BENCH_DIR / d.path).relative_to(REPO_ROOT)),
                "sha256": sha256(BENCH_DIR / d.path),
            }
            for name, d in decks.items()
        },
        "settings": {
            "reference": reference,
            "repeats": repeats,
            "warmup": cfg.run.warmup,
            "pause_s": cfg.run.pause_s,
            "wait_idle_s": cfg.run.wait_idle_s,
            "max_process_cpu_percent": cfg.preflight.max_process_cpu_percent,
            "env": cfg.run.env,
            "mpirun": cfg.run.mpirun,
            "physics": {"tol_bulk": cfg.physics.tol_bulk, "tol_fluctuation": cfg.physics.tol_fluctuation},
        },
        "cases": {c.name: case_record(c, cfg.decks[c.deck]) for c in cases},
        "builds": {},
        "runs": [],
    }
    try:
        for label, b in builds.items():
            b["exes"] = {name: compile_deck(label, b, BENCH_DIR / d.path) for name, d in decks.items()}
            record["builds"][label] = {k: v for k, v in b.items() if k not in ("exes", "layouts")}
            record["builds"][label]["layouts"] = [bc.layout_str(lay) for lay in b["layouts"]]
        for case in cases:
            run_case(case, builds, reference, repeats, cfg, out, record, exclude)
    finally:
        record["conditions_end"] = mach.conditions(cfg.preflight.max_process_cpu_percent, exclude)
        record["summary"] = report.summarize(record)
        (out / "results.json").write_text(json.dumps(record, indent=1) + "\n")
        (out / "summary.md").write_text(report.markdown(record, record["summary"]))
    final = out.rename(RESULTS_DIR / run_id)
    print("\n" + (final / "summary.md").read_text())
    log.info("results: %s", final.relative_to(REPO_ROOT))
    ok = all(e["physics"]["passed"] and not e["failed_runs"] for pb in record["summary"].values() for e in pb.values())
    if not ok:
        log.error("PHYSICS CHECK FAILED or runs failed: see summary.md; speed-ups of failing builds are meaningless")
    return 0 if ok else 1


def parse_args() -> argparse.Namespace:
    """Command line: builds, cases, and recorded overrides."""
    p = argparse.ArgumentParser(description="Benchmark labelled VPIC builds on identical physics.")
    p.add_argument(
        "--build",
        action="append",
        required=True,
        metavar="LABEL=DIR",
        help="a VPIC build directory (with bin/vpic and CMakeCache.txt); repeatable",
    )
    p.add_argument("--preset", help="named set of cases from config.toml (smoke, small, medium, large)")
    p.add_argument("--cases", help="comma-separated case names from config.toml (instead of --preset)")
    p.add_argument("--reference", help="label of the reference build (default: the first --build)")
    p.add_argument(
        "--layouts",
        action="append",
        default=[],
        metavar="LABEL=RxT[,RxT...]",
        help="layouts to try for one build (more than one: fastest kept per case)",
    )
    p.add_argument("--sweep", action="store_true", help="sweep the config's CPU layouts for CPU builds")
    p.add_argument("--repeats", type=int, help="override config run.repeats")
    p.add_argument("--tag", default="run", help="suffix of the results folder name (letters, digits, -)")
    p.add_argument("--config", default=str(BENCH_DIR / "config.toml"))
    p.add_argument("--force", action="store_true", help="run even if the preflight checks object (recorded)")
    p.add_argument("--dry-run", action="store_true", help="print the plan and exit")
    args = p.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*", args.tag):
        p.error(f"--tag {args.tag!r}: use letters, digits and hyphens")
    if bool(args.preset) == bool(args.cases):
        p.error("give exactly one of --preset or --cases")
    return args


def select_cases(cfg: bc.Config, args: argparse.Namespace) -> list[bc.Case]:
    """The cases named by --preset or --cases."""
    names = cfg.presets.get(args.preset, None) if args.preset else args.cases.split(",")
    if names is None:
        sys.exit(f"unknown preset {args.preset!r}; config has {sorted(cfg.presets)}")
    unknown = [n for n in names if n not in cfg.cases]
    if unknown:
        sys.exit(f"unknown cases {unknown}; config has {sorted(cfg.cases)}")
    return [cfg.cases[n] for n in names]


def resolve_builds(cfg: bc.Config, args: argparse.Namespace, cores: int, perf_cores: int) -> dict[str, dict[str, Any]]:
    """Validate the build directories and fingerprint them.

    ``cores`` and ``perf_cores`` (physical and performance cores) resolve the
    "auto", "C" and "P" layout specs.

    Raises
    ------
    SystemExit
        On a malformed --build, a duplicate label, or a directory that is not a VPIC build.
    """
    builds: dict[str, dict[str, Any]] = {}
    overrides = dict(_label_value(s, "--layouts") for s in args.layouts)
    for spec in args.build:
        label, path = _label_value(spec, "--build")
        if label in builds:
            sys.exit(f"duplicate build label {label!r}")
        bdir = Path(path).expanduser().resolve()
        if not (bdir / "bin" / "vpic").is_file() or not (bdir / "CMakeCache.txt").is_file():
            sys.exit(f"{bdir} is not a VPIC build directory (needs bin/vpic and CMakeCache.txt)")
        cache = read_cmake_cache(bdir / "CMakeCache.txt")
        gpu = any(v == "ON" and re.match(cfg.layouts.gpu_cmake_pattern, k) for k, v in cache.items())
        if label in overrides:
            specs = overrides.pop(label).split(",")
        elif gpu:
            specs = cfg.layouts.gpu_sweep if args.sweep else cfg.layouts.gpu_default
        else:
            specs = cfg.layouts.cpu_sweep if args.sweep else cfg.layouts.cpu_default
        builds[label] = {
            "path": str(bdir),
            "gpu": gpu,
            "layouts": bc.expand_layouts(specs, cores, sweep=args.sweep, perf_cores=perf_cores),
            "cmake": {k: v for k, v in cache.items() if CMAKE_KEYS.match(k)},
            "git_state": _read(bdir / "git-state.txt"),
            "libraries": {p.name: sha256(p) for p in sorted(bdir.glob("lib*")) if p.is_file()},
            "vpic_script_sha256": sha256(bdir / "bin" / "vpic"),
        }
    if overrides:
        sys.exit(f"--layouts names unknown builds {sorted(overrides)}")
    return builds


def _label_value(spec: str, flag: str) -> tuple[str, str]:
    label, sep, value = spec.partition("=")
    if not sep or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", label) or not value:
        sys.exit(f"{flag} {spec!r}: expected LABEL=VALUE")
    return label, value


def read_cmake_cache(path: Path) -> dict[str, str]:
    """CMakeCache.txt entries as {name: value}, upper-casing BOOL values."""
    out = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^([A-Za-z_][\w.+-]*):(\w+)=(.*)$", line)
        if m:
            out[m.group(1)] = m.group(3).upper() if m.group(2) == "BOOL" else m.group(3)
    return out


def case_record(case: bc.Case, deck: bc.DeckSpec) -> dict[str, Any]:
    """A case as results.json records it: its config fields plus derived sizes and its deck's bulk columns."""
    return {
        **case.__dict__,
        "particles": case.particles,
        "grid_points": case.grid_points,
        "deck_args": case.deck_args(deck),
        "bulk_energy_columns": deck.bulk_energy_columns,
    }


def plan_summary(cases: list[bc.Case], builds: dict[str, dict[str, Any]], repeats: int, cfg: bc.Config) -> None:
    """Log what will run."""
    n = 0
    for case in cases:
        for label, b in builds.items():
            valid = [lay for lay in b["layouts"] if case.fits(lay[0], cfg.decks[case.deck])]
            n += (len(valid) if len(valid) > 1 else 0) + cfg.run.warmup + repeats
    log.info(
        "cases: %s", ", ".join(f"{c.name} ({c.deck}, {c.particles:.3g} particles, {c.nstep} steps)" for c in cases)
    )
    for label, b in builds.items():
        lays = ", ".join(bc.layout_str(lay) for lay in b["layouts"])
        log.info("build %s: %s (%s), layouts %s", label, b["path"], "GPU" if b["gpu"] else "CPU", lays)
    log.info("%d runs in total", n)


def preflight(cfg: bc.Config, hw: dict[str, Any], cond: dict[str, Any], cases: list[bc.Case], force: bool) -> list[str]:
    """Refuse to benchmark a busy, throttled or too-small machine; return warnings.

    Raises
    ------
    SystemExit
        On the first refusal, unless ``force`` (then the refusals become warnings).
    """
    refusals, warnings = [], []
    load_limit = cfg.preflight.max_load_per_core * hw["cpu_cores"]
    if cond["load_average"][0] > load_limit:
        refusals.append(f"1-minute load average {cond['load_average'][0]:.1f} exceeds {load_limit:.1f}")
    for p in cond["busy_processes"]:
        refusals.append(f"process {p['command']} (pid {p['pid']}) uses {p['cpu_percent']:.0f}% CPU")
    if cond["low_power_mode"]:
        refusals.append("Low Power Mode is on")
    mem_limit = cfg.preflight.max_memory_fraction * hw["memory_gib"] * 2**30
    for c in cases:
        need = c.particles * cfg.preflight.bytes_per_particle
        if need > mem_limit:
            refusals.append(f"case {c.name} needs ~{need / 2**30:.1f} GiB, over {mem_limit / 2**30:.1f} GiB")
    if shutil.which(cfg.run.mpirun) is None:
        sys.exit(f"{cfg.run.mpirun} not found")
    if cond["power_source"] != "AC Power":
        warnings.append(f"running on {cond['power_source']}")
    if cond["thermal_state"] != "nominal":
        warnings.append(f"thermal state is {cond['thermal_state']} at start")
    if refusals and not force:
        sys.exit("machine not fit to benchmark (pass --force to override):\n  " + "\n  ".join(refusals))
    warnings += [f"forced past: {r}" for r in refusals]
    for w in warnings:
        log.warning("warning: %s", w)
    return warnings


def compile_deck(label: str, build: dict[str, Any], deck: Path) -> Path:
    """Compile a deck with this build into work/<label>/, unless already compiled from the same inputs.

    Raises
    ------
    SystemExit
        If the compile fails.
    """
    wdir = WORK_DIR / label
    wdir.mkdir(parents=True, exist_ok=True)
    exe = wdir / f"{deck.name}.{platform.system()}"
    stamp = {
        "deck_sha256": sha256(deck),
        "build": build["path"],
        "libraries": build["libraries"],
        "vpic_script_sha256": build["vpic_script_sha256"],
    }
    stamp_file = wdir / f"{deck.stem}.stamp.json"
    if exe.is_file() and stamp_file.is_file() and json.loads(stamp_file.read_text()) == stamp:
        log.info("build %s: %s already compiled from the same deck and build", label, deck.name)
    else:
        log.info("build %s: compiling %s", label, deck.name)
        stamp_file.unlink(missing_ok=True)
        exe.unlink(missing_ok=True)
        shutil.copy(deck, wdir / deck.name)
        with open(wdir / f"{deck.stem}.compile.log", "w") as f:
            rc = subprocess.run(
                [str(Path(build["path"]) / "bin" / "vpic"), deck.name],
                cwd=wdir,
                stdout=f,
                stderr=subprocess.STDOUT,
                check=False,
            ).returncode
        if rc != 0 or not exe.is_file():
            sys.exit(f"compiling {deck.name} with {label} failed; see {wdir / f'{deck.stem}.compile.log'}")
        stamp_file.write_text(json.dumps(stamp, indent=1) + "\n")
    build.setdefault("exe_sha256", {})[deck.stem] = sha256(exe)
    return exe


def run_case(
    case: bc.Case,
    builds: dict[str, dict[str, Any]],
    reference: str,
    repeats: int,
    cfg: bc.Config,
    out: Path,
    record: dict[str, Any],
    exclude: set[int],
) -> None:
    """Sweep layouts, warm up, then measure with builds interleaved per repetition."""
    labels = list(builds)
    best: dict[str, tuple[int, int]] = {}
    for label in labels:
        valid = [lay for lay in builds[label]["layouts"] if case.fits(lay[0], cfg.decks[case.deck])]
        if not valid:
            record["warnings"].append(f"{case.name}: the deck cannot decompose it over any layout of {label}; skipped")
            continue
        if len(valid) > 1:
            sweep = [one_run(case, label, builds[label], lay, "sweep", 0, cfg, out, record, exclude) for lay in valid]
            timed = [(r["metrics"]["steady_ms_per_step"], r["layout"]) for r in sweep if is_good(r)]
            if not timed:
                continue
            best[label] = bc.parse_layout(min(timed)[1])
            log.info("%s %s: fastest layout %s", case.name, label, bc.layout_str(best[label]))
        else:
            best[label] = valid[0]
    for label in [lab for lab in labels if lab in best]:
        for w in range(cfg.run.warmup):
            one_run(case, label, builds[label], best[label], "warmup", w, cfg, out, record, exclude)
    for rep in range(repeats):
        order = labels[rep % len(labels) :] + labels[: rep % len(labels)]  # rotate who goes first
        for label in [lab for lab in order if lab in best]:
            one_run(case, label, builds[label], best[label], "measure", rep, cfg, out, record, exclude)
    compare_energies(case, reference, record, out)


def one_run(
    case: bc.Case,
    label: str,
    build: dict[str, Any],
    layout: tuple[int, int],
    phase: str,
    rep: int,
    cfg: bc.Config,
    out: Path,
    record: dict[str, Any],
    exclude: set[int],
) -> dict[str, Any]:
    """Run the deck once and append its record (timings, or the error) to ``record['runs']``."""
    ranks, tpp = layout
    rel = Path("runs") / case.name / label / f"{phase}{rep}-{bc.layout_str(layout)}"
    rdir = out / rel
    rdir.mkdir(parents=True)
    busy = wait_for_idle(cfg, exclude)
    exe = str(build["exes"][case.deck])
    cmd = [cfg.run.mpirun, "-np", str(ranks), exe, "--tpp", str(tpp), *case.deck_args(cfg.decks[case.deck])]
    env = {**os.environ, **cfg.run.env}
    run: dict[str, Any] = {
        "case": case.name,
        "build": label,
        "layout": bc.layout_str(layout),
        "phase": phase,
        "rep": rep,
        "dir": str(rel),
        "command": cmd,
        "load_before": round(os.getloadavg()[0], 2),
        "busy_before": [p.__dict__ for p in busy],
        "error": None,
        "metrics": None,
    }
    t0 = time.monotonic()
    try:
        with open(rdir / "run.log", "w") as f:
            proc = subprocess.run(
                cmd, cwd=rdir, env=env, stdout=f, stderr=subprocess.STDOUT, timeout=cfg.run.timeout_s, check=False
            )
        run["returncode"] = proc.returncode
    except subprocess.TimeoutExpired:
        run["error"] = f"timed out after {cfg.run.timeout_s} s"
    run["elapsed_s"] = round(time.monotonic() - t0, 3)
    parsed = vo.parse_log((rdir / "run.log").read_text(errors="replace"))
    if run["error"] is None and (run.get("returncode") or not parsed.normal_exit):
        run["error"] = f"exit code {run.get('returncode')}; see {rel / 'run.log'}"
    if run["error"] is None:
        try:
            m = vo.metrics(parsed)
            run["metrics"] = m.__dict__
        except ValueError as e:
            run["error"] = f"unparseable log: {e}"
    # VPIC prints nptotal with 6 significant digits
    if run["error"] is None and (
        parsed.nptotal is None or abs(parsed.nptotal / case.particles - 1) > 1e-5 or parsed.nstep != case.nstep
    ):
        run["error"] = f"log reports {parsed.nptotal} particles / {parsed.nstep} steps, not the case's"
    if "vpic_git_hash" not in record["builds"][label] and parsed.build_details:
        record["builds"][label]["vpic_git_hash"] = parsed.build_details.get("VPIC Git Hash", "?")
        record["builds"][label]["build_details"] = parsed.build_details
    record["runs"].append(run)
    if run["error"]:
        log.error("%s %s %s %s: %s", case.name, label, run["layout"], phase, run["error"])
    else:
        log.info(
            "%-12s %-14s %-5s %-8s steady %8.2f ms/step  wall %8.2f ms/step  push %.3f /ns%s",
            case.name,
            label,
            run["layout"],
            f"{phase}{rep}",
            run["metrics"]["steady_ms_per_step"],
            run["metrics"]["wall_ms_per_step"],
            run["metrics"]["pushes_per_ns"],
            "  (busy: " + ", ".join(p.command.split()[0] for p in busy) + ")" if busy else "",
        )
    if cfg.run.pause_s:
        time.sleep(cfg.run.pause_s)
    return run


def wait_for_idle(cfg: bc.Config, exclude: set[int]) -> list[mach.BusyProcess]:
    """Wait up to run.wait_idle_s for other busy processes to finish; return those still busy."""
    deadline = time.monotonic() + cfg.run.wait_idle_s
    busy = mach.busy_processes(cfg.preflight.max_process_cpu_percent, exclude)
    if busy and cfg.run.wait_idle_s > 0:
        log.info("waiting up to %.0f s for: %s", cfg.run.wait_idle_s, ", ".join(p.command[:60] for p in busy))
    while busy and time.monotonic() < deadline:
        time.sleep(IDLE_POLL_S)
        busy = mach.busy_processes(cfg.preflight.max_process_cpu_percent, exclude)
    return busy


def is_good(run: dict[str, Any]) -> bool:
    """True if the run finished without error and has timings."""
    return not run.get("error") and bool(run.get("metrics"))


def compare_energies(case: bc.Case, reference: str, record: dict[str, Any], out: Path) -> None:
    """Attach to every run of the case its energy difference from the reference's first measured run.

    A run whose energies (or the reference's) cannot be read or compared gets ``energy_error`` instead;
    nothing here stops the remaining cases.
    """
    runs = [r for r in record["runs"] if r["case"] == case.name and not r["error"]]
    ref = next((r for r in runs if r["build"] == reference and r["phase"] == "measure"), None)
    if ref is None:
        record["warnings"].append(f"{case.name}: reference {reference} has no successful measured run")
        return
    try:
        ref_e = vo.parse_energies((out / ref["dir"] / "energies").read_text())
    except (OSError, ValueError) as e:
        for r in runs:
            r["energy_error"] = f"reference energies unreadable: {e}"
        record["warnings"].append(f"{case.name}: reference {reference} energies unreadable: {e}")
        return
    for r in runs:
        path = out / r["dir"] / "energies"
        try:
            r["energy_diff"] = vo.energy_differences(ref_e, vo.parse_energies(path.read_text()))
        except (OSError, ValueError) as e:
            r["energy_error"] = str(e)


def repo_state(mpirun: str) -> dict[str, Any]:
    """Commit, branch and dirty state (tracked files) of the VPIC checkout, and the MPI version."""

    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=REPO_ROOT, capture_output=True, text=True, check=False).stdout.strip()

    return {
        "commit": git("rev-parse", "HEAD"),
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(git("status", "--porcelain", "--untracked-files=no")),
        "mpirun_version": subprocess.run(
            [mpirun, "--version"], capture_output=True, text=True, check=False
        ).stdout.split("\n")[0],
    }


def sha256(path: Path) -> str:
    """SHA-256 of a file's contents."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> str | None:
    return path.read_text().strip() if path.is_file() else None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
