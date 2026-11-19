# Running VPIC on Apple Silicon Macs

This fork of VPIC-Kokkos can use the GPU of an Apple Silicon Mac through Metal. It is meant for small and medium
runs on a laptop or desktop Mac, the kind that would otherwise wait in a cluster queue.

On a base M4 MacBook Pro, the Metal build runs the reconnection and laser-plasma benchmarks 2.1 to 2.5 times faster
per step than the same code on all of the Mac's CPU cores. The full results are in
[benchmarks/report/README.md](benchmarks/report/README.md).

## What runs where

VPIC's Kokkos code runs on the CPU as usual. Hand-written Metal kernels run four particle loops on the GPU, working
directly on the same memory, since Apple Silicon shares memory between CPU and GPU:

| On the GPU | On the CPU |
| --- | --- |
| Particle push and current deposit | Field solve (unless `VPIC_METAL_FIELDS=1`, see below) |
| Particle sort | Particle boundary exchange and MPI |
| Charge deposit for divergence cleaning | Diagnostics, dumps and checkpoints |
| Particle energy sum for the energies output | Your deck's own code |

## Requirements

- **A Mac with an M1 chip or newer.** The GPU code needs float atomics, which Apple GPUs have from the M1
  generation on (Metal GPU family Apple7); the code checks this at start-up.
- **macOS 15 or newer.** The GPU code sets Metal compiler options that macOS 15 introduced.
- **Xcode command line tools.** Install them with `xcode-select --install`.
- **Homebrew packages:** CMake, Open MPI and the OpenMP runtime.

```sh
brew install cmake open-mpi libomp
```

So far this has been tested on one machine only: a MacBook Pro with a base M4 chip, on macOS 27.2. Other M-series
chips and macOS versions should work, but have not been tried. If you run it on another Mac, the `ctest` result and
the benchmark numbers would be very welcome.

## Build

```sh
git clone --recursive https://github.com/neildhir/vpic-kokkos-metal.git
cd vpic-kokkos-metal
mkdir build && cd build
../arch/AppleSilicon-Metal
make -j 8
```

The build takes several minutes, mostly for Kokkos. `arch/AppleSilicon-CPU` builds the same code without Metal, which
is useful for comparing results or speed. If you cloned without `--recursive`, run `git submodule update --init`
first.

Check the build with the test suite:

```sh
ctest
```

All 23 tests should pass. The three `metal_check_*` tests run small decks with every check mode on, so they fail if
the GPU ever disagrees with the CPU code.

## Run a deck

Compile your deck with the build's `vpic` script, then run the executable it writes:

```sh
./bin/vpic my_problem.deck
OMP_PROC_BIND=spread OMP_PLACES=threads mpirun -np 1 ./my_problem.deck.Darwin --tpp 4
```

- **Use one MPI rank.** The GPU does the heavy particle work, and one rank owns all of it.
- **Set `--tpp` to the number of performance cores.** That is 4 on a base M4. Find it with
  `sysctl -n hw.perflevel0.physicalcpu`. VPIC ignores `OMP_NUM_THREADS`; threads come from `--tpp`.
- **Sort particles regularly.** The GPU push is much faster when particles are sorted by cell. Every 20 steps is a
  good default. Without sorting, the GPU build is slower than the CPU build on all but the smallest grids.
- **Leave memory headroom.** CPU and GPU share the Mac's memory. Allow about 100 bytes per macro particle plus the
  fields, and keep the total under about three quarters of the Mac's memory.

## Checking results

Metal runs are not bitwise repeatable. The GPU adds currents with atomics whose order changes from run to run, and
the GPU sort orders particles within a cell differently each time. Results drift from the CPU build the same way two
multithreaded CPU runs drift from each other.

To check the GPU against the CPU, set one or more check modes. Each runs the GPU code and the CPU code from the same
state every step, and stops the run with an error if they disagree beyond rounding:

| Variable | Checks |
| --- | --- |
| `VPIC_METAL_PUSH_CHECK=1` | Particles, cells and movers, and the currents within 1e-4 of the largest |
| `VPIC_METAL_SORT_CHECK=1` | The same cell order and the same particles in every cell |
| `VPIC_METAL_PARTICLE_LOOPS_CHECK=1` | The charge deposit and energy sum against a double-precision sum |
| `VPIC_METAL_FIELDS_CHECK=1` | The GPU field kernels, when they are enabled |

Check modes are slow. Use them on a short run of a new deck, not for production runs.

## Settings

All settings are environment variables, read when the run starts:

| Variable | Default | Effect |
| --- | --- | --- |
| `VPIC_METAL_PUSH` | on | `0` runs the particle push on the CPU instead |
| `VPIC_METAL_SORT` | on | `0` sorts on the CPU instead |
| `VPIC_METAL_PARTICLE_LOOPS` | on | `0` runs the charge deposit and energy sum on the CPU instead |
| `VPIC_METAL_FIELDS` | off | `1` runs the magnetic field update, interpolator load and current clear on the GPU |
| `VPIC_METAL_PROFILE` | off | `1` prints the GPU time of every kernel call, and totals at exit |
| `VPIC_METAL_CHUNK` | 16777216 | Particles per GPU command buffer; lower it if macOS reports a GPU timeout |
| `VPIC_METAL_FAST_MATH` | off | `1` uses fast GPU maths; results then differ from the CPU, for experiments only |
| `VPIC_METAL_THREADS` | 256 | Threads per threadgroup for particle kernels; 64 to 1024 are within 2% on an M4 |

The GPU field kernels are off by default because on a base M4 they are no faster than the CPU. The field solve is
limited by memory bandwidth, which the CPU and GPU share. On a Pro, Max or Ultra chip, whose GPU has much more
bandwidth than its CPU can use, they may help. Try a short run with and without `VPIC_METAL_FIELDS=1`.

## Profiling

`VPIC_METAL_PROFILE=1` prints, for every GPU call, its GPU time, and for the push also the host time spent encoding,
waiting for the GPU to start and waking after it finishes. At exit it prints totals, and at start-up the most threads
per threadgroup each kernel allows (below 1024 would mean its register use limits the GPU's parallelism).

Instruments' Metal System Trace shows the GPU timeline. Every VPIC command buffer is labelled with its kernel
(`vpic push`, `vpic sort scatter` and so on):

```sh
xcrun xctrace record --template 'Metal System Trace' --output run.trace --env OMP_PROC_BIND=spread \
    --env OMP_PLACES=threads --launch -- ./my_problem.deck.Darwin --tpp 4
```

Run the deck directly, without `mpirun`, so that Instruments can follow it. Tracing slows the run somewhat, so take
timings from runs without it.

## Known limits

- **One GPU per Mac.** Several MPI ranks on one Mac share the same GPU. That works and is tested, but only one rank
  per Mac has been benchmarked and tuned.
- **32-bit particle counters.** Apple GPUs have no 64-bit atomics, so this build counts particles with 32-bit
  integers. That caps each rank at about 4 billion particles, far beyond a Mac's memory.
- **Standard sort order only.** The GPU sort implements VPIC's standard order, which is also the faster one on Apple
  GPUs. A build with `VPIC_SORT_ORDER=strided` sorts on the CPU.
- **Very small numbers.** Apple GPUs flush float values below about 1.2e-38 to zero, where the CPU keeps them. Decks in
  VPIC's usual normalised units never get near that. A deck that gives particle charges in SI units can: in
  `sample/beam_plas` the push's charge term is about 1e-30, and up to 5% of its tiny thermal ion current is lost on
  the GPU. The push prints a warning at a species' first push when its charges are that small.

## How it was validated

Every GPU kernel was run against the CPU code with all check modes on, on a base M4 MacBook Pro:

- **The benchmark decks.** Harris reconnection in 2D and 3D on 1 to 4 ranks, with periodic and conducting
  boundaries. VPIC's laser-plasma deck on 1 to 3 ranks, with absorbing fields, laser injection and reflecting
  particles. These also run as the `metal_check_*` tests.
- **The sample decks in `sample/`.** Each was run for 10 steps. The GPU matched the CPU on `harris`,
  `Weibel/Weibel.cxx`, `generic` (2 ranks), `RFB_SIERRA.cxx` (16 million particles) and
  `lpi_head_single_new_diag_for_Bird-GC.cxx`. `beam_plas` differs in its currents, for the reason above.
- **VPIC's own tests.** The particle tests for acceleration, cyclotron motion and current deposition, and the
  checkpoint-and-restart test, all pass with the GPU push.

The other sample decks do not run on a Mac with either build, so they say nothing about the GPU code. Six no longer
compile against the current VPIC. `dipole`, `shapes` and `template` crash at start-up, `waveguide` and
`bench/fdtd_scaling` stop with errors, and `cygnus` is killed by the system. `cygnus_close_up` needs 32 ranks, and
`NEW_DUMP_EXAMPLE_DECK` stops in VPIC's memory query, which does not support macOS.

## Troubleshooting

- **`libomp not found` from the arch script.** Install it with `brew install libomp`.
- **`compiling the Metal kernels failed`.** The kernels are compiled when the run starts. This usually means an
  edited `.metal` file has an error; the message gives its line in the combined kernel source.
- **A GPU timeout or `command buffer failed` error.** macOS stops GPU work that runs too long. Lower
  `VPIC_METAL_CHUNK`, for example to 4194304.
- **A deck still runs old code after rebuilding.** Decks link VPIC statically, so recompile the deck with `./bin/vpic`
  after every rebuild.
