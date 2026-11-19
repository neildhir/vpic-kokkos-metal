# VPIC benchmark 20261118-160429-tolerance-failcheck

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:04:29-08:00; repo `8b383248bd08` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Cases: 2d-smoke; 1 measured runs each after 0 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Push ns/particle | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-smoke | 5.24e+05 | cpu | 8x1 | 3.61 ±0% | 3.50 ±0% | 3.82 | 2% | 1.00× | 1.00× | 1.00× | ok |
| 2d-smoke | 5.24e+05 | applegpu | 8x1 | 3.47 ±0% | 3.40 ±0% | 4.06 | 1% | 1.04× | 1.03× | 0.94× | **FAIL** (ex, ey, ez, bx, by, bz, electron, ion) |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 1e-09 for bulk columns (bz, electron, ion) and 1e-09 for fluctuation columns (ex, ey, ez, bx, by). The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-smoke | cpu | 1 | 0.0e+00 | 0.0e+00 | ok |
| 2d-smoke | applegpu | 1 | 3.6e-06 | 1.2e-06 | **FAIL** (ex, ey, ez, bx, by, bz, electron, ion) |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| applegpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp-applegpu` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_DISABLE_DEVICE_FP64=ON, VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: Battery Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [4.82, 5.89, 5.5] at start, [4.82, 5.89, 5.5] at end
- Runs that started while another process used > 80.0% CPU: 0 (marked busy above; their timings are suspect)
- Warning: running on Battery Power
