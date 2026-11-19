# VPIC benchmark 20261118-162848-m4-harris-small

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:28:48-08:00; repo `3179ae668e54` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Cases: 2d-small, 3d-small; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-small | 2.62e+07 | cpu | 8x1 | 98.62 ±2% | 95.45 ±4% | 0.360 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 2d-small | 2.62e+07 | metal | 1x4 | 56.71 ±4% | 53.83 ±6% | 0.836 | 10% | 1.74× | 1.77× | 2.32× | ok |
| 3d-small | 1.68e+07 | cpu | 8x1 | 65.05 ±2% | 63.02 ±5% | 0.358 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 3d-small | 1.68e+07 | metal | 1x4 | 35.88 ±1% | 29.67 ±4% | 0.778 | 10% | 1.81× | 2.12× | 2.17× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| 2d-small | 262,144 | 26,214,400 | 0.360 | 0.836 |
| 3d-small | 262,144 | 16,777,216 | 0.358 | 0.778 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (harris: bz, electron, ion) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 2d-small | metal | 4 | 0.0e+00 | 4.2e-07 | ok |
| 3d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 3d-small | metal | 4 | 3.8e-07 | 9.2e-06 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [3.91, 5.33, 5.05] at start, [5.34, 5.43, 5.11] at end
- Runs that started while another process used > 80.0% CPU: 0 (marked busy above; their timings are suspect)
