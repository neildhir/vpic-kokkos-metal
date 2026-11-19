# VPIC benchmark 20261118-165025-m4-gpu-sort

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:50:25-08:00; repo `c95c8d672a98` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: 2d-small, 3d-small, lpi-sorted-24, lpi-sorted-44, lpi-sorted-64, lpi-sorted-128; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-small | 2.62e+07 | cpu | 8x1 | 98.78 ±2% | 95.72 ±1% | 0.366 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 2d-small | 2.62e+07 | metal | 1x4 | 56.65 ±5% | 52.07 ±3% | 0.839 | 6% | 1.74× | 1.84× | 2.29× | ok |
| 3d-small | 1.68e+07 | cpu | 8x1 | 65.82 ±6% | 64.62 ±8% | 0.366 | 5% | 1.00× | 1.00× | 1.00× | ok |
| 3d-small | 1.68e+07 | metal | 1x4 | 30.90 ±0% | 28.62 ±0% | 0.780 | 7% | 2.13× | 2.26× | 2.13× | ok |
| lpi-sorted-24 | 1.2e+07 | cpu | 8x1 | 31.08 ±6% | 29.34 ±9% | 0.550 | 6% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-24 | 1.2e+07 | metal | 1x4 | 16.04 ±1% | 12.22 ±0% | 1.199 | 10% | 1.94× | 2.40× | 2.18× | ok |
| lpi-sorted-44 | 1.2e+07 | cpu | 8x1 | 33.04 ±4% | 30.87 ±10% | 0.496 | 5% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-44 | 1.2e+07 | metal | 1x4 | 18.24 ±1% | 13.55 ±1% | 1.105 | 9% | 1.81× | 2.28× | 2.23× | ok |
| lpi-sorted-64 | 1.2e+07 | cpu | 8x1 | 40.42 ±1% | 38.08 ±2% | 0.428 | 4% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-64 | 1.2e+07 | metal | 1x4 | 21.61 ±1% | 16.61 ±1% | 1.011 | 8% | 1.87× | 2.29× | 2.36× | ok |
| lpi-sorted-128 | 1.2e+07 | cpu | 8x1 | 95.22 ±4% | 89.42 ±1% | 0.207 | 2% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-128 | 1.2e+07 | metal | 1x4 | 55.27 ±3% | 46.77 ±3% | 0.570 | 4% | 1.72× | 1.91× | 2.75× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| 2d-small | 262,144 | 26,214,400 | 0.366 | 0.839 |
| 3d-small | 262,144 | 16,777,216 | 0.366 | 0.780 |
| lpi-sorted-24 | 13,824 | 12,000,000 | 0.550 | 1.199 |
| lpi-sorted-44 | 85,184 | 12,000,000 | 0.496 | 1.105 |
| lpi-sorted-64 | 262,144 | 12,000,000 | 0.428 | 1.011 |
| lpi-sorted-128 | 2,097,152 | 12,000,000 | 0.207 | 0.570 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (harris: bz, electron, ion; lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 2d-small | metal | 4 | 0.0e+00 | 4.2e-07 | ok |
| 3d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 3d-small | metal | 4 | 3.8e-07 | 7.5e-06 | ok |
| lpi-sorted-24 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-24 | metal | 4 | 0.0e+00 | 1.4e-06 | ok |
| lpi-sorted-44 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-44 | metal | 4 | 0.0e+00 | 1.6e-07 | ok |
| lpi-sorted-64 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-64 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | c95c8d672a98 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [2.67, 3.52, 4.07] at start, [6.52, 4.66, 4.44] at end
- Runs that started while another process used > 80.0% CPU: 0 (marked busy above; their timings are suspect)
