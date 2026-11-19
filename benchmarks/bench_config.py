"""Load config.toml into typed settings; decks, cases and MPI/thread layouts."""

import tomllib
from dataclasses import MISSING, dataclass, fields
from pathlib import Path
from typing import Any, Literal

# Case fields a deck's ``args`` may name, in the order the deck takes them
CASE_ARG_FIELDS = ("nx", "ny", "nz", "nppc", "total_particles", "nstep", "sort_interval")


class ConfigError(ValueError):
    """The benchmark configuration is malformed."""


@dataclass(frozen=True)
class DeckSpec:
    """A benchmark deck and how the harness drives it."""

    name: str
    path: str  # relative to benchmarks/
    args: list[str]  # case fields passed as the deck's command-line arguments, in order
    decomposition: Literal["y", "xyz"]  # "y": ranks slice y; "xyz": topology() over all three
    nstep_multiple: int
    bulk_energy_columns: list[str]  # energy columns checked against tol_bulk


@dataclass(frozen=True)
class Case:
    """One benchmark problem: a deck and its command-line arguments.

    Exactly one of ``nppc`` (macro particles per cell, all species) and
    ``total_particles`` sets the particle count.
    """

    name: str
    deck: str
    nx: int
    ny: int
    nz: int
    nstep: int
    nppc: int | None = None
    total_particles: int | None = None
    sort_interval: int | None = None  # 0 disables sorting (decks that take it)

    @property
    def particles(self) -> int:
        """Total macro particles (all species)."""
        if self.total_particles is not None:
            return self.total_particles
        if self.nppc is None:
            raise ConfigError(f"case {self.name}: neither nppc nor total_particles is set")
        return self.nppc * self.grid_points

    @property
    def grid_points(self) -> int:
        """Number of cells, nx * ny * nz."""
        return self.nx * self.ny * self.nz

    def deck_args(self, deck: DeckSpec) -> list[str]:
        """The deck's command-line arguments for this case."""
        return [str(getattr(self, a)) for a in deck.args]

    def fits(self, ranks: int, deck: DeckSpec) -> bool:
        """Whether the deck can decompose this case over ``ranks`` MPI ranks."""
        if deck.decomposition == "xyz":
            return topology(ranks, self.nx, self.ny, self.nz) is not None
        pairs, odd = divmod(self.particles, 2)
        return not odd and self.ny % ranks == 0 and pairs % ranks == 0


def topology(ranks: int, nx: int, ny: int, nz: int) -> tuple[int, int, int] | None:
    """MPI topology the LPI deck derives from its rank count (mirrors decks/lpi_bench.deck).

    Prime factors of ``ranks``, smallest first, each go to the dimension with
    the most local cells that the factor still divides (ties: x, then y, then z).

    Returns
    -------
    tuple[int, int, int] or None
        Ranks along x, y, z, or None if the grid cannot be decomposed.

    Examples
    --------
    >>> topology(8, 24, 24, 24)
    (2, 2, 2)
    >>> topology(8, 25, 25, 25) is None
    True
    """
    topo, cells, rem, f = [1, 1, 1], (nx, ny, nz), ranks, 2
    while rem > 1:
        if rem % f:
            f += 1
            continue
        best = None
        for d in range(3):
            if cells[d] % (topo[d] * f):
                continue
            if best is None or cells[d] * topo[best] > cells[best] * topo[d]:
                best = d
        if best is None:
            return None
        topo[best] *= f
        rem //= f
    return topo[0], topo[1], topo[2]


@dataclass(frozen=True)
class RunSettings:
    """How each run is launched and repeated."""

    repeats: int
    warmup: int
    pause_s: float
    wait_idle_s: float
    timeout_s: float
    mpirun: str
    env: dict[str, str]


@dataclass(frozen=True)
class LayoutSettings:
    """Default and sweep MPI/thread layouts, and how GPU builds are recognised."""

    cpu_default: list[str]
    cpu_sweep: list[str]
    gpu_default: list[str]
    gpu_sweep: list[str]
    gpu_cmake_pattern: str


@dataclass(frozen=True)
class PreflightSettings:
    """Thresholds below which the machine counts as fit to benchmark."""

    max_load_per_core: float
    max_process_cpu_percent: float
    max_memory_fraction: float
    bytes_per_particle: float


@dataclass(frozen=True)
class PhysicsSettings:
    """Energy-comparison tolerances (relative to each column's max |E|)."""

    tol_bulk: float
    tol_fluctuation: float


@dataclass(frozen=True)
class PublishedPoint:
    """One published GPU push rate."""

    gpu: str
    grid_points: int
    pushes_per_ns: float
    source: Literal["text", "figure"]  # stated in the text, or read off the figure by eye


@dataclass(frozen=True)
class PublishedPushRate:
    """Published push rates to compare the LPI sweep against."""

    citation: str
    points: list[PublishedPoint]


@dataclass(frozen=True)
class Config:
    """The whole benchmark configuration."""

    default_deck: str
    decks: dict[str, DeckSpec]
    run: RunSettings
    layouts: LayoutSettings
    preflight: PreflightSettings
    physics: PhysicsSettings
    cases: dict[str, Case]
    presets: dict[str, list[str]]
    published_push_rate: PublishedPushRate | None


def load_config(path: Path) -> Config:
    """Load and validate config.toml.

    Raises
    ------
    ConfigError
        On unknown or missing keys, unknown decks, bad case sizes, or presets
        naming unknown cases.
    """
    try:
        raw = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"{path}: {e}") from e
    top = {"default_deck", "decks", "run", "layouts", "preflight", "physics", "cases", "presets"}
    _check_keys(raw, top, str(path), optional={"published_push_rate"})
    decks = {name: _deck(name, spec) for name, spec in raw["decks"].items()}
    if raw["default_deck"] not in decks:
        raise ConfigError(f"default_deck {raw['default_deck']!r} is not in [decks]")
    run = dict(raw["run"])
    run["env"] = {str(k): str(v) for k, v in run.get("env", {}).items()}
    cases = {}
    for name, spec in raw["cases"].items():
        case = _build(Case, {"name": name, "deck": raw["default_deck"], **spec}, f"cases.{name}")
        _validate_case(case, decks)
        cases[name] = case
    presets = {k: list(v) for k, v in raw["presets"].items()}
    for name, members in presets.items():
        unknown = [c for c in members if c not in cases]
        if unknown:
            raise ConfigError(f"presets.{name}: unknown cases {unknown}")
    return Config(
        default_deck=raw["default_deck"],
        decks=decks,
        run=_build(RunSettings, run, "run"),
        layouts=_build(LayoutSettings, raw["layouts"], "layouts"),
        preflight=_build(PreflightSettings, raw["preflight"], "preflight"),
        physics=_build(PhysicsSettings, raw["physics"], "physics"),
        cases=cases,
        presets=presets,
        published_push_rate=_published(raw["published_push_rate"]) if "published_push_rate" in raw else None,
    )


def _deck(name: str, spec: dict[str, Any]) -> DeckSpec:
    deck = _build(DeckSpec, {"name": name, **spec}, f"decks.{name}")
    bad = [a for a in deck.args if a not in CASE_ARG_FIELDS]
    if bad:
        raise ConfigError(f"decks.{name}.args: unknown case fields {bad}; allowed {list(CASE_ARG_FIELDS)}")
    if deck.decomposition not in ("y", "xyz"):
        raise ConfigError(f"decks.{name}.decomposition must be 'y' or 'xyz'")
    return deck


def _validate_case(case: Case, decks: dict[str, DeckSpec]) -> None:
    where = f"cases.{case.name}"
    if case.deck not in decks:
        raise ConfigError(f"{where}: unknown deck {case.deck!r}")
    deck = decks[case.deck]
    if (case.nppc is None) == (case.total_particles is None):
        raise ConfigError(f"{where}: set exactly one of nppc and total_particles")
    missing = [a for a in deck.args if getattr(case, a) is None]
    if missing:
        raise ConfigError(f"{where}: deck {case.deck} needs {missing}")
    if case.nstep <= 0 or case.nstep % deck.nstep_multiple:
        raise ConfigError(f"{where}: nstep must be a positive multiple of {deck.nstep_multiple}")
    if case.sort_interval and case.nstep % (2 * case.sort_interval):
        raise ConfigError(f"{where}: nstep must be a multiple of 2 x sort_interval")
    if case.particles % 2:
        raise ConfigError(f"{where}: the particle count must be even (pairs of species)")


def _published(raw: dict[str, Any]) -> PublishedPushRate:
    _check_keys(raw, {"citation", "points"}, "published_push_rate")
    points = [_build(PublishedPoint, p, f"published_push_rate.points[{i}]") for i, p in enumerate(raw["points"])]
    for p in points:
        if p.source not in ("text", "figure"):
            raise ConfigError(f"published_push_rate: source {p.source!r} must be 'text' or 'figure'")
    return PublishedPushRate(citation=raw["citation"], points=points)


def _check_keys(data: dict[str, Any], expected: set[str], where: str, optional: set[str] | None = None) -> None:
    optional = optional or set()
    unknown, missing = set(data) - expected - optional, expected - set(data)
    if unknown or missing:
        raise ConfigError(f"{where}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")


def _build(cls: Any, data: dict[str, Any], where: str) -> Any:
    required = {f.name for f in fields(cls) if f.default is MISSING and f.default_factory is MISSING}
    _check_keys(data, required, where, optional={f.name for f in fields(cls)} - required)
    return cls(**data)


def parse_layout(spec: str) -> tuple[int, int]:
    """Parse "<ranks>x<threads>", e.g. "8x1".

    Raises
    ------
    ConfigError
        If the spec is not two positive integers joined by "x".
    """
    try:
        ranks, tpp = (int(v) for v in spec.lower().split("x"))
    except ValueError as e:
        raise ConfigError(f"layout {spec!r}: expected <ranks>x<threads>, e.g. 8x1") from e
    if ranks < 1 or tpp < 1:
        raise ConfigError(f"layout {spec!r}: ranks and threads must be positive")
    return ranks, tpp


def layout_str(layout: tuple[int, int]) -> str:
    """Format a layout as "<ranks>x<threads>"."""
    return f"{layout[0]}x{layout[1]}"


def expand_layouts(specs: list[str], cores: int, sweep: bool, perf_cores: int | None = None) -> list[tuple[int, int]]:
    """Expand layout specs, resolving "auto", "P" and "C" for this machine.

    Parameters
    ----------
    specs : list[str]
        Layout specs ("8x1"), "auto", or specs using "P" (performance cores)
        or "C" (all physical cores) for a count, e.g. "1xP".
    cores : int
        Physical CPU cores.
    sweep : bool
        Whether "auto" means the sweep set (else the single default layout:
        the largest power of two <= cores, one thread per rank).
    perf_cores : int or None
        Performance cores, needed by specs that use "P".

    Returns
    -------
    list[tuple[int, int]]
        Distinct (ranks, threads) layouts in order.

    Raises
    ------
    ConfigError
        If a spec is malformed, or uses "P" without ``perf_cores``.

    Examples
    --------
    >>> expand_layouts(["auto"], 10, sweep=False)
    [(8, 1)]
    >>> expand_layouts(["auto"], 10, sweep=True)
    [(1, 10), (2, 5), (4, 2), (8, 1)]
    >>> expand_layouts(["1x1", "1xP", "1xC"], 10, sweep=True, perf_cores=4)
    [(1, 1), (1, 4), (1, 10)]
    """
    out: list[tuple[int, int]] = []
    for spec in specs:
        if spec != "auto":
            if "P" in spec and perf_cores is None:
                raise ConfigError(f"layout {spec!r}: the performance-core count is unknown")
            candidates = [parse_layout(spec.replace("P", str(perf_cores)).replace("C", str(cores)))]
        elif not sweep:
            candidates = [(_pow2_floor(cores), 1)]
        else:
            # all cores busy: N ranks x cores//N threads, plus N x 1 where that uses at least half the cores
            candidates = []
            n = 1
            while n <= cores:
                candidates += [(n, cores // n)] + ([(n, 1)] if 2 * n >= cores else [])
                n *= 2
        for c in candidates:
            if c not in out:
                out.append(c)
    return out


def _pow2_floor(n: int) -> int:
    p = 1
    while p * 2 <= n:
        p *= 2
    return p
