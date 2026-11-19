# VPIC benchmark 20261118-193618-m4-post-opt-sorted

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T19:36:18-08:00; repo `91468073c439` on `fix/apple-gpu-portability`
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: 2d-small, 3d-small, lpi-sorted-24, lpi-sorted-44, lpi-sorted-64, lpi-sorted-128; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-small | 2.62e+07 | cpu | 8x1 | 100.34 ±2% | 98.13 ±2% | 0.356 | 3% | 1.00× | 1.00× | 1.00× | ok |
| 2d-small | 2.62e+07 | metal | 1x4 | 42.25 ±3% | 39.86 ±3% | 0.972 | 7% | 2.37× | 2.46× | 2.73× | ok |
| 3d-small | 1.68e+07 | cpu | 8x1 | 62.46 ±0% | 60.49 ±2% | 0.377 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 3d-small | 1.68e+07 | metal | 1x4 | 25.74 ±2% | 24.96 ±2% | 0.863 | 8% | 2.43× | 2.42× | 2.29× | ok |
| lpi-sorted-24 | 1.2e+07 | cpu | 8x1 | 29.45 ±2% | 27.40 ±2% | 0.581 | 6% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-24 | 1.2e+07 | metal | 1x4 | 13.82 ±4% | 11.43 ±5% | 1.304 | 11% | 2.13× | 2.40× | 2.24× | ok |
| lpi-sorted-44 | 1.2e+07 | cpu | 8x1 | 31.56 ±9% | 29.54 ±11% | 0.516 | 5% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-44 | 1.2e+07 | metal | 1x4 | 16.12 ±0% | 12.66 ±1% | 1.196 | 9% | 1.96× | 2.33× | 2.32× | ok |
| lpi-sorted-64 | 1.2e+07 | cpu | 8x1 | 39.31 ±1% | 37.39 ±3% | 0.432 | 4% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-64 | 1.2e+07 | metal | 1x4 | 19.09 ±1% | 15.50 ±1% | 1.077 | 9% | 2.06× | 2.41× | 2.49× | ok |
| lpi-sorted-128 | 1.2e+07 | cpu | 8x1 | 96.20 ±5% | 93.31 ±9% | 0.197 | 2% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-128 | 1.2e+07 | metal | 1x4 | 50.02 ±2% | 44.36 ±4% | 0.569 | 4% | 1.92× | 2.10× | 2.88× | ok; 1/3 runs busy |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| 2d-small | 262,144 | 26,214,400 | 0.356 | 0.972 |
| 3d-small | 262,144 | 16,777,216 | 0.377 | 0.863 |
| lpi-sorted-24 | 13,824 | 12,000,000 | 0.581 | 1.304 |
| lpi-sorted-44 | 85,184 | 12,000,000 | 0.516 | 1.196 |
| lpi-sorted-64 | 262,144 | 12,000,000 | 0.432 | 1.077 |
| lpi-sorted-128 | 2,097,152 | 12,000,000 | 0.197 | 0.569 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (harris: bz, electron, ion; lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 2d-small | metal | 4 | 0.0e+00 | 7.8e-07 | ok |
| 3d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 3d-small | metal | 4 | 3.8e-07 | 7.6e-06 | ok |
| lpi-sorted-24 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-24 | metal | 4 | 0.0e+00 | 1.4e-06 | ok |
| lpi-sorted-44 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-44 | metal | 4 | 0.0e+00 | 2.0e-07 | ok |
| lpi-sorted-64 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-64 | metal | 4 | 0.0e+00 | 2.3e-07 | ok |
| lpi-sorted-128 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 3e0d11e5c6f2 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | 3e0d11e5c6f2 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON, VPIC_METAL_SOURCES_SHA256=2cf967a97a7e9c148b1c7cc83bd5e5efb15c4b2ab3fb06e8bb0abc24b5b18ff0 |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [2.02, 2.16, 2.27] at start, [5.5, 3.45, 2.76] at end
- Runs that started while another process used > 80.0% CPU: 1 (marked busy above; their timings are suspect)
