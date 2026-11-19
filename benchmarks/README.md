# VPIC build benchmarks

Measures how much faster one VPIC build is than another (in particular a
Metal GPU build against the original OpenMP CPU build) on identical physics,
and refuses to call a build fast if its physics differs. Any number of
labelled build directories are treated alike; one of them is the reference.

The latest results, with plots and an explanation of each benchmark, are in
[report/README.md](report/README.md).

Standard-library Python 3.11+ only (no NumPy, no YAML, no packaging). On a
Mac whose `python3` is the system 3.9, use `python3.12` or
`uv run --no-project --python 3.12 <script>`.

## Run it

From `benchmarks/`, on mains power, with heavy apps closed:

```sh
# quick check that everything works (about 15 s)
python3.12 vpic_bench.py --build cpu=../build/cpu-openmp --build metal=../build/metal \
    --preset smoke --tag smoke

# the real measurement on a 16 GB Mac
python3.12 vpic_bench.py --build cpu=../build/cpu-openmp --build metal=../build/metal \
    --preset small --tag m4
python3.12 vpic_bench.py --build cpu=../build/cpu-openmp --build metal=../build/metal \
    --preset medium --sweep --tag m4

# the published LPI push-rate method (Tan et al. 2025, Fig. 9): a few minutes per build
python3.12 vpic_bench.py --build cpu=../build/cpu-openmp --build metal=../build/metal \
    --preset lpi-smoke --tag lpi-smoke     # seconds: checks the LPI deck works
python3.12 vpic_bench.py --build cpu=../build/cpu-openmp --build metal=../build/metal \
    --preset lpi-sweep --tag m4-lpi
```

- `--build LABEL=DIR` (repeatable): a VPIC build directory with `bin/vpic`
  and `CMakeCache.txt`. The first one is the reference unless `--reference`
  names another.
- `--preset smoke|small|medium|large|lpi-smoke|lpi-sweep` or
  `--cases 2d-small,lpi-44` (cases may use different decks).
- `--sweep`: try several layouts (ranks × threads) per case and keep the
  fastest; without it CPU builds run the default layout (8×1 on a 10-core
  M4) and GPU builds run 1 rank with one thread per performance core (1×4 on
  a base M4), since the work left on the CPU uses those threads.
  `--layouts LABEL=8x1,4x2` sets one build's layouts explicitly; `P` and `C`
  stand for the performance-core and physical-core counts (`1xP`).
- `--repeats N` overrides the configured number of measured runs.
- `--dry-run` prints the plan; `--force` runs although the preflight checks
  object (the objections are recorded in the results).

The exit status is non-zero when any run failed or any build failed the
physics check. Run the tests with `python3.12 -m unittest` (from
`benchmarks/`).

## What it does

1. **Preflight.** Refuses to start when the 1-minute load average exceeds
   0.5 × physical cores, when another process uses more than 80 % CPU, in
   Low Power Mode, or when a case's estimated memory exceeds 75 % of RAM.
   Battery power and a non-nominal thermal state are recorded as warnings.
   Before every run it checks again for busy processes (optionally waiting
   `run.wait_idle_s` for them to finish) and marks runs that started busy.
2. **Compile.** Copies `decks/harris_bench.deck` into `work/<label>/` and
   compiles it with that build's `bin/vpic`, because the library is linked
   statically and build options change struct layouts. A stamp (hashes of the
   deck, `bin/vpic` and the build's `lib*` files) skips recompiling when
   nothing changed.
3. **Run.** Per case: optional layout sweep (one run per layout), then
   `warmup` discarded runs per build, then `repeats` measured runs. Builds
   are interleaved within each repetition and the order rotates (A B, B A,
   ...) so slow drifts such as heat soak hit every build alike. Each run is
   `mpirun -np R <deck>.Darwin --tpp T nx ny nz nppc nstep` with
   `OMP_PROC_BIND=spread OMP_PLACES=threads` (VPIC ignores
   `OMP_NUM_THREADS`; threads come only from `--tpp`). GPU builds (a
   CMakeCache entry such as `VPIC_ENABLE_METAL` or `Kokkos_ENABLE_CUDA` ON)
   run 1×1.
4. **Check physics, summarise, file** into
   `results/<YYYYmmdd-HHMMSS>-<tag>/` (written as `*.incomplete` until it
   finishes): `results.json` (everything), `summary.md` (the tables),
   `config.toml` (the config used), `harness.log`, and `runs/<case>/<build>/
   <phase><rep>-<layout>/{run.log,energies}`. `python3.12 report.py
   results/<id>/results.json` regenerates `summary.md`.

## What the numbers mean

| Column | Meaning |
| --- | --- |
| Wall ms/step | VPIC's own advance-loop time (`*** Done (Xs`) / nstep. Includes the first steps (GPU warm-up, first sort) and the energy dumps; excludes initialisation. |
| Steady ms/step | The last "Since Last Update" timing table (steps nstep/2+1 … nstep), summed over all phases except `user_diagnostics` (the energy dumps), / its steps. The headline number. |
| Pushes/ns | Particle push rate: total particles (all species) × steps / `advance_p` time in that window, across all ranks; the metric of Tan et al. (2025) and Bird et al. (2021). results.json also has its inverse, `push_ns_per_particle`. |
| Sort share | `sort_particles` / steady step time. |
| Speed-up wall / step / push | Reference median / build median of the wall, steady and push times; > 1 means faster than the reference. |
| Push rate table | Pushes/ns of every build per case, ordered by deck and grid size: the LPI sweep's curve. |
| ± | (max − min) / median over the measured runs. |
| Physics | `ok`, or **FAIL** with the energy columns out of tolerance. |

The timing table is rank 0's. With several ranks it is one rank's view of a
step that all ranks run concurrently, which is what wall time per step
means. On a GPU, a phase's time is only its own if the build fences (waits
for the device) at the end of the phase; without fences kernel time shows
up in whichever later phase waits, so per-phase shares can mislead while the
step total stays right.

## The benchmark decks

Each case names its deck (`deck = "lpi"`; cases without one use
`default_deck`, the Harris deck). `[decks.<name>]` in `config.toml` gives the
deck's path, which case fields it takes as arguments, how it decomposes over
ranks, the nstep granularity it needs, and its bulk energy columns.
results.json records every case with its deck, nx, ny, nz, grid points,
particle count and deck arguments.

### Harris sheet (`harris`)

`decks/harris_bench.deck` is the Harris-sheet reconnection deck of
`build/bench/` (mass ratio 25, all field and particle dumps off, status
every nstep/2), changed so every build and layout computes the same physics:

- **Rank-count-independent loading.** VPIC's own RNG streams are seeded
  with the rank, so an 8-rank CPU run and a 1-rank GPU run would start from
  different particles. The deck instead draws every particle from a hash of
  its global pair index (splitmix64) and stratifies pairs in y, so the
  initial state is identical for any rank count. Measured: CPU 1×1, 4×1,
  8×1 and 2×4 runs agree to 1e-5 in the fluctuation energies and to every
  printed digit in the bulk energies.
- **Sorting.** Both species sort every 20 steps (the template sorted ions
  every 40), so the 20-step steady window samples the full sort cadence;
  nstep must be a multiple of 40.
- **Energies** are written to `./energies` every nstep/4 steps.

Arguments: `nx ny nz nppc nstep`, with nppc counting both species; ny and
the number of pairs (nppc·nx·ny·nz/2) must divide by the rank count, so
layouts that do not divide are skipped.

### Laser-plasma interaction (`lpi`)

`decks/lpi_bench.deck` is VPIC's own LPI benchmark, `sample/benchmark.cxx`
(Luedtke, 2021; a version of it is the benchmark of Bird et al., IEEE TPDS
2021, and of Tan, Luedtke, Taufer and Albright, SC Workshops '25). It keeps
the original physics: SI-derived code units; a 2.67 × 1.33 × 1.33 µm box
with absorbing fields and reflecting particles; a uniform electron plus
I2-ion (A = 7, Z = 14) plasma at 0.05 n_crit with T_e = 600 eV and
T_i = 150 eV; the 3D Gaussian 527 nm beam (2.5e20 W/m², 4 µm waist)
injected at x = xmin by the original Kokkos field injection; a 2-cell
reflecting vacuum layer on every face; cfl 0.98; cleaning and
synchronisation every 100 steps. Changes, and what was removed, are listed
in the deck's header. In short:

- `nx ny nz total_particles nstep sort_interval` come from the command line
  (sort_interval 0 disables sorting); the box stays fixed, so the grid sets
  the resolution.
- The MPI topology comes from the rank count (1 rank: 1×1×1; 8 ranks on an
  even cube: 2×2×2; see `bench_config.topology`, which mirrors the deck).
- Particles come from the same hash scheme as the Harris deck: every rank
  draws every pair's position and keeps the pairs in its own cells, so the
  initial state does not depend on the rank count (CPU 1×1, 8×1 and 4×2
  energies agree to 6e-7). Positions are uniform outside the vacuum layer,
  with weights that keep the density at n_e as in the original.
- The laser ramp (pulse shape 4) rises over 1000 steps (the original
  num_step) rather than over the benchmark's few steps.
- Energies every nstep/4 steps; all field, hydro, particle, restart and
  parameter-file output removed.

**The push-rate sweep.** `--preset lpi-sweep` follows Fig. 9 of Tan et al.
(2025): sorting disabled, the total particle count fixed while the grid
varies, and only the particle push timed. Here the count is 12M (about
1.2 GB) and the grids run 16³ to 128³ (4,096 to 2.1M points), including
the paper's peak points 24³, 34³ and 44³. Each run is 40 steps, so the
preset takes a few minutes per build. Published GPU values, recorded in
`config.toml` (`[published_push_rate]`) for plots:

| GPU | Peak (pushes/ns at grid points) | At ~1.9M grid points |
| --- | --- | --- |
| V100 | 4.0 at 13,824 | ~0.4 |
| A100 | 6.0 at 85,184 | ~1.3 |
| MI300A | 9.0 at 39,304 | ~7 |

The peaks are stated in the paper's text; the large-grid values are read
off Fig. 9 by eye. Bird et al. (2021), Fig. 6, shows the same V100 and A100
peaks.

**Caveats at laptop scale.** The paper's particle count, step count and
grids beyond those three points are not known here, so compare the shape
and the peak, not every point. With the box fixed, coarse grids under-resolve
the plasma: at 24³ a cell is 111 × 56 × 56 nm against a 13 nm Debye length
(the original runs 13 nm cells) and the laser gets under 5 cells per
wavelength in x; such grids heat numerically over long runs, which does not
matter over 40 steps but means these are performance runs, not physics
runs. Cells are 2:1:1 because the box is and the grids are cubes. The
2-cell vacuum layer takes a larger share of a coarse grid (42 % of the
volume at 24³), which the particle weights compensate. With 8 MPI ranks on a
small grid, particle exchange between ranks (`boundary_p`) can dominate the
step; the push rate counts `advance_p` only.

## Physics check

For every run of every build (sweep, warm-up and measured), the harness
computes, per energy column, max over the dumps of |E − E_ref| / max|E_ref|
against the reference build's first measured run, and fails a build whose
worst value exceeds:

- **1e-3** for the deck's bulk columns (Harris: bz and the electron and ion
  kinetic energies; LPI: the electron and I2 kinetic energies), and
- **1e-2** for the other, fluctuation columns (the field energies; in the
  LPI deck they hold the injected laser and plasma noise, and start at
  zero).

Why these values: VPIC computes in float32 on every backend, so builds
differ only in summation order (atomics, reductions, domain boundaries) and
in compiler contraction (FMA, Metal fast math). Measured on the M4: CPU
layouts agree to 1e-5 (fluctuation) and to the printed digits (bulk); the
`VPIC_DISABLE_DEVICE_FP64` build, which also sums the energies themselves in
float, differs by up to 4e-5 (bulk). A GPU without float64 sums energies
over 1e4–1e7 cells and particles in float32 (eps 6e-8), and its reordered
current deposition is amplified by the chaotic particle dynamics in the
noise-level fields. The tolerances leave 10–100× headroom over that, while a
real defect (lost particles, a wrong deposit, a wrong field update) moves
these energies by a percent or more. They are not fine enough to catch an
error that changes the energy by less than 0.1 %. The reference's own row
in the physics table is its run-to-run noise floor. Tolerances live in
`config.toml` (`[physics]`).

## Adding a build or a case

- **A build:** configure and build it anywhere, then pass
  `--build LABEL=DIR`. Nothing else is needed; it is compiled against the
  deck on first use. A GPU build whose CMake switch the pattern in
  `config.toml` (`layouts.gpu_cmake_pattern`) does not recognise can be
  given its layout with `--layouts LABEL=1xP`.
- **A case:** add a `[cases.<name>]` table to `config.toml` and,
  optionally, list it in a `[presets]` entry. A Harris case gives nx, ny, nz,
  nppc and nstep (a multiple of 40; ny and the pair count divisible by the
  rank counts you will use). An LPI case gives `deck = "lpi"`, nx, ny, nz,
  total_particles, nstep (a multiple of 4) and sort_interval; the grid must
  split over the rank count (even cubes are safe for 8 ranks). A changed
  case is a different benchmark: give it a new name rather than editing one
  with results.
- **A deck:** add `decks/<name>.deck` and a `[decks.<name>]` table. The deck
  must print `nptotal = <total particles>` and VPIC's status timing tables,
  write `./energies`, and give the same initial state for any rank count
  (see the hash loading in either deck), or the physics check will fail it.
- **Bigger Macs:** the `large` preset (210M and 268M particles) needs about
  20–26 GB; the memory guard refuses it on smaller machines. Larger cases
  scale the same way (memory ≈ 96 bytes per particle).

## Files

| File | Holds / does |
| --- | --- |
| `vpic_bench.py` | the command: preflight, compile, run, physics check, filing |
| `config.toml` | cases, presets, repeats, layouts, thresholds, tolerances |
| `bench_config.py` | loads and validates `config.toml`; layouts |
| `vpic_output.py` | parses VPIC logs and energies; statistics |
| `report.py` | per-case summary and `summary.md` |
| `machine.py` | hardware fingerprint and run conditions (from firm3d_metal) |
| `decks/harris_bench.deck` | Harris-sheet reconnection problem |
| `decks/lpi_bench.deck` | VPIC's laser-plasma interaction benchmark, adapted |
| `tests/` | unit tests on captured VPIC output |
| `work/` | compiled decks (ignored by git) |
| `results/` | one folder per benchmark run |

Every `results.json` fingerprints the run: chip, core and GPU counts,
memory, macOS version and build; repo commit, branch and dirty state; the
deck's SHA-256; per build its path, selected CMakeCache options,
`git-state.txt`, library and executable hashes, and the "Build Details"
VPIC prints at start-up; the settings, commands and per-run conditions.
