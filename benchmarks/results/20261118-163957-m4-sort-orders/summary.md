# VPIC benchmark 20261118-163957-m4-sort-orders

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:39:57-08:00; repo `c95c8d672a98` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: 2d-small, 3d-small, lpi-sorted-24, lpi-sorted-44, lpi-sorted-64, lpi-sorted-128, lpi-24, lpi-44, lpi-64, lpi-128; 2 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-small | 2.62e+07 | cpu | 8x1 | 100.35 ±3% | 96.44 ±3% | 0.360 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 2d-small | 2.62e+07 | metal | 1x4 | 67.54 ±6% | 66.92 ±12% | 0.607 | 8% | 1.49× | 1.44× | 1.69× | ok |
| 2d-small | 2.62e+07 | strided | 1x4 | 130.36 ±1% | 125.10 ±2% | 0.289 | 9% | 0.77× | 0.77× | 0.80× | ok |
| 3d-small | 1.68e+07 | cpu | 8x1 | 62.98 ±1% | 60.11 ±1% | 0.377 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 3d-small | 1.68e+07 | metal | 1x4 | 40.44 ±1% | 35.03 ±1% | 0.633 | 9% | 1.56× | 1.72× | 1.68× | ok |
| 3d-small | 1.68e+07 | strided | 1x4 | 57.13 ±1% | 53.02 ±1% | 0.428 | 14% | 1.10× | 1.13× | 1.13× | ok |
| lpi-sorted-24 | 1.2e+07 | cpu | 8x1 | 29.95 ±2% | 28.65 ±2% | 0.585 | 5% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-24 | 1.2e+07 | metal | 1x4 | 22.40 ±0% | 16.97 ±1% | 0.902 | 16% | 1.34× | 1.69× | 1.54× | ok |
| lpi-sorted-24 | 1.2e+07 | strided | 1x4 | 26.79 ±2% | 23.67 ±3% | 0.662 | 19% | 1.12× | 1.21× | 1.13× | ok |
| lpi-sorted-44 | 1.2e+07 | cpu | 8x1 | 38.45 ±26% | 35.11 ±18% | 0.454 | 5% | 1.00× | 1.00× | 1.00× | ok; 1/2 runs busy |
| lpi-sorted-44 | 1.2e+07 | metal | 1x4 | 22.11 ±3% | 17.23 ±1% | 0.894 | 13% | 1.74× | 2.04× | 1.98× | ok |
| lpi-sorted-44 | 1.2e+07 | strided | 1x4 | 42.68 ±23% | 39.23 ±25% | 0.395 | 16% | 0.90× | 0.90× | 0.86× | ok |
| lpi-sorted-64 | 1.2e+07 | cpu | 8x1 | 44.79 ±1% | 44.23 ±3% | 0.384 | 4% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-64 | 1.2e+07 | metal | 1x4 | 25.64 ±12% | 19.87 ±2% | 0.857 | 12% | 1.75× | 2.23× | 2.23× | ok |
| lpi-sorted-64 | 1.2e+07 | strided | 1x4 | 52.08 ±1% | 48.22 ±9% | 0.311 | 11% | 0.86× | 0.92× | 0.81× | ok |
| lpi-sorted-128 | 1.2e+07 | cpu | 8x1 | 100.64 ±5% | 95.78 ±5% | 0.199 | 2% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-128 | 1.2e+07 | metal | 1x4 | 57.23 ±1% | 48.64 ±0% | 0.536 | 4% | 1.76× | 1.97× | 2.69× | ok |
| lpi-sorted-128 | 1.2e+07 | strided | 1x4 | 93.91 ±5% | 85.13 ±8% | 0.224 | 5% | 1.07× | 1.13× | 1.12× | ok |
| lpi-24 | 1.2e+07 | cpu | 8x1 | 35.81 ±1% | 34.40 ±4% | 0.434 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-24 | 1.2e+07 | metal | 1x4 | 21.61 ±0% | 19.25 ±0% | 0.658 | 0% | 1.66× | 1.79× | 1.52× | ok |
| lpi-24 | 1.2e+07 | strided | 1x4 | 21.59 ±1% | 19.30 ±1% | 0.657 | 0% | 1.66× | 1.78× | 1.52× | ok |
| lpi-44 | 1.2e+07 | cpu | 8x1 | 41.85 ±5% | 39.93 ±3% | 0.377 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-44 | 1.2e+07 | metal | 1x4 | 47.45 ±3% | 44.99 ±1% | 0.276 | 0% | 0.88× | 0.89× | 0.73× | ok |
| lpi-44 | 1.2e+07 | strided | 1x4 | 47.52 ±2% | 45.22 ±4% | 0.275 | 0% | 0.88× | 0.88× | 0.73× | ok |
| lpi-64 | 1.2e+07 | cpu | 8x1 | 65.02 ±7% | 60.83 ±11% | 0.248 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-64 | 1.2e+07 | metal | 1x4 | 120.29 ±0% | 113.65 ±1% | 0.110 | 0% | 0.54× | 0.54× | 0.45× | ok |
| lpi-64 | 1.2e+07 | strided | 1x4 | 119.94 ±1% | 112.98 ±1% | 0.111 | 0% | 0.54× | 0.54× | 0.45× | ok |
| lpi-128 | 1.2e+07 | cpu | 8x1 | 173.67 ±1% | 164.15 ±0% | 0.091 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-128 | 1.2e+07 | metal | 1x4 | 248.85 ±0% | 232.28 ±0% | 0.059 | 0% | 0.70× | 0.71× | 0.65× | ok |
| lpi-128 | 1.2e+07 | strided | 1x4 | 248.79 ±0% | 233.73 ±0% | 0.059 | 0% | 0.70× | 0.70× | 0.65× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal | strided |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2d-small | 262,144 | 26,214,400 | 0.360 | 0.607 | 0.289 |
| 3d-small | 262,144 | 16,777,216 | 0.377 | 0.633 | 0.428 |
| lpi-sorted-24 | 13,824 | 12,000,000 | 0.585 | 0.902 | 0.662 |
| lpi-24 | 13,824 | 12,000,000 | 0.434 | 0.658 | 0.657 |
| lpi-sorted-44 | 85,184 | 12,000,000 | 0.454 | 0.894 | 0.395 |
| lpi-44 | 85,184 | 12,000,000 | 0.377 | 0.276 | 0.275 |
| lpi-sorted-64 | 262,144 | 12,000,000 | 0.384 | 0.857 | 0.311 |
| lpi-64 | 262,144 | 12,000,000 | 0.248 | 0.110 | 0.111 |
| lpi-sorted-128 | 2,097,152 | 12,000,000 | 0.199 | 0.536 | 0.224 |
| lpi-128 | 2,097,152 | 12,000,000 | 0.091 | 0.059 | 0.059 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (harris: bz, electron, ion; lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-small | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| 2d-small | metal | 3 | 0.0e+00 | 4.2e-07 | ok |
| 2d-small | strided | 3 | 0.0e+00 | 4.2e-07 | ok |
| 3d-small | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| 3d-small | metal | 3 | 3.8e-07 | 9.0e-06 | ok |
| 3d-small | strided | 3 | 3.8e-07 | 5.4e-06 | ok |
| lpi-sorted-24 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-24 | metal | 3 | 0.0e+00 | 1.4e-06 | ok |
| lpi-sorted-24 | strided | 3 | 0.0e+00 | 2.1e-06 | ok |
| lpi-sorted-44 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-44 | metal | 3 | 0.0e+00 | 1.6e-07 | ok |
| lpi-sorted-44 | strided | 3 | 0.0e+00 | 1.7e-07 | ok |
| lpi-sorted-64 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-64 | metal | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-64 | strided | 3 | 0.0e+00 | 8.6e-08 | ok |
| lpi-sorted-128 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | metal | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | strided | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-24 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-24 | metal | 3 | 0.0e+00 | 1.4e-06 | ok |
| lpi-24 | strided | 3 | 0.0e+00 | 1.4e-06 | ok |
| lpi-44 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-44 | metal | 3 | 0.0e+00 | 2.0e-07 | ok |
| lpi-44 | strided | 3 | 0.0e+00 | 2.0e-07 | ok |
| lpi-64 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-64 | metal | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-64 | strided | 3 | 0.0e+00 | 2.3e-07 | ok |
| lpi-128 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-128 | metal | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-128 | strided | 3 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | c95c8d672a98 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| strided | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal-strided` | yes | c95c8d672a98 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=strided, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [2.53, 3.98, 4.43] at start, [4.26, 4.42, 4.52] at end
- Runs that started while another process used > 80.0% CPU: 3 (marked busy above; their timings are suspect)
