# VPIC benchmark 20261118-160205-smoke

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:02:05-08:00; repo `8b383248bd08` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Cases: 2d-smoke, 3d-smoke; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Push ns/particle | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-smoke | 5.24e+05 | cpu | 8x1 | 3.66 ±4% | 3.53 ±4% | 3.94 | 1% | 1.00× | 1.00× | 1.00× | ok |
| 2d-smoke | 5.24e+05 | applegpu | 8x1 | 3.71 ±4% | 3.69 ±7% | 3.28 | 1% | 0.99× | 0.96× | 1.20× | ok |
| 3d-smoke | 1.05e+06 | cpu | 8x1 | 10.43 ±24% | 8.83 ±84% | 3.86 | 3% | 1.00× | 1.00× | 1.00× | ok; 2/3 runs busy |
| 3d-smoke | 1.05e+06 | applegpu | 8x1 | 7.90 ±47% | 9.36 ±47% | 3.50 | 1% | 1.32× | 0.94× | 1.10× | ok; 3/3 runs busy |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for bulk columns (bz, electron, ion) and 0.01 for fluctuation columns (ex, ey, ez, bx, by). The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-smoke | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 2d-smoke | applegpu | 4 | 3.6e-06 | 1.2e-06 | ok |
| 3d-smoke | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 3d-smoke | applegpu | 4 | 5.6e-06 | 2.6e-06 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| applegpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp-applegpu` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_DISABLE_DEVICE_FP64=ON, VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: Battery Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [4.43, 5.94, 5.41] at start, [6.11, 6.22, 5.52] at end
- Runs that started while another process used > ?% CPU: 5 (marked "busy" above; their timings are suspect)
- Warning: running on Battery Power
