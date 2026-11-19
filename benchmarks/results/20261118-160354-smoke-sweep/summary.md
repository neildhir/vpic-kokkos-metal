# VPIC benchmark 20261118-160354-smoke-sweep

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:03:54-08:00; repo `8b383248bd08` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Cases: 2d-smoke, 3d-smoke; 2 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Push ns/particle | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-smoke | 5.24e+05 | cpu | 8x1 | 4.60 ±11% | 4.27 ±9% | 4.18 | 1% | 1.00× | 1.00× | 1.00× | ok; 2/2 runs busy |
| 2d-smoke | 5.24e+05 | applegpu | 8x1 | 4.16 ±7% | 3.94 ±0% | 3.81 | 1% | 1.11× | 1.08× | 1.10× | ok; 1/2 runs busy |
| 3d-smoke | 1.05e+06 | cpu | 8x1 | 8.59 ±53% | 6.24 ±2% | 3.38 | 2% | 1.00× | 1.00× | 1.00× | ok; 1/2 runs busy |
| 3d-smoke | 1.05e+06 | applegpu | 8x1 | 8.58 ±47% | 10.66 ±77% | 3.51 | 2% | 1.00× | 0.59× | 0.96× | ok; 2/2 runs busy |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for bulk columns (bz, electron, ion) and 0.01 for fluctuation columns (ex, ey, ez, bx, by). The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-smoke | cpu | 7 | 3.8e-07 | 2.7e-05 | ok |
| 2d-smoke | applegpu | 7 | 3.6e-06 | 2.4e-05 | ok |
| 3d-smoke | cpu | 7 | 3.8e-07 | 1.1e-05 | ok |
| 3d-smoke | applegpu | 7 | 5.6e-06 | 9.1e-06 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| applegpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp-applegpu` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_DISABLE_DEVICE_FP64=ON, VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: Battery Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [4.74, 5.94, 5.5] at start, [5.99, 6.16, 5.59] at end
- Runs that started while another process used > 80.0% CPU: 17 (marked busy above; their timings are suspect)
- Warning: running on Battery Power
