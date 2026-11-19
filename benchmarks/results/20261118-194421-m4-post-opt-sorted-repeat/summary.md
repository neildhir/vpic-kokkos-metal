# VPIC benchmark 20261118-194421-m4-post-opt-sorted-repeat

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T19:44:21-08:00; repo `91468073c439` on `fix/apple-gpu-portability`
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: 2d-small, 3d-small, lpi-sorted-24, lpi-sorted-44, lpi-sorted-64, lpi-sorted-128; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-small | 2.62e+07 | cpu | 8x1 | 97.93 ±2% | 95.88 ±3% | 0.362 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 2d-small | 2.62e+07 | metal | 1x4 | 41.39 ±0% | 39.76 ±0% | 0.971 | 7% | 2.37× | 2.41× | 2.68× | ok |
| 3d-small | 1.68e+07 | cpu | 8x1 | 63.07 ±0% | 60.43 ±3% | 0.370 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 3d-small | 1.68e+07 | metal | 1x4 | 25.55 ±1% | 24.78 ±0% | 0.867 | 8% | 2.47× | 2.44× | 2.34× | ok |
| lpi-sorted-24 | 1.2e+07 | cpu | 8x1 | 30.29 ±2% | 28.08 ±4% | 0.555 | 6% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-24 | 1.2e+07 | metal | 1x4 | 13.73 ±1% | 11.28 ±2% | 1.315 | 11% | 2.21× | 2.49× | 2.37× | ok |
| lpi-sorted-44 | 1.2e+07 | cpu | 8x1 | 32.82 ±2% | 31.34 ±7% | 0.514 | 5% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-44 | 1.2e+07 | metal | 1x4 | 16.07 ±1% | 12.59 ±1% | 1.199 | 9% | 2.04× | 2.49× | 2.33× | ok |
| lpi-sorted-64 | 1.2e+07 | cpu | 8x1 | 41.01 ±4% | 38.27 ±4% | 0.413 | 5% | 1.00× | 1.00× | 1.00× | ok; 1/3 runs busy |
| lpi-sorted-64 | 1.2e+07 | metal | 1x4 | 19.16 ±1% | 15.35 ±2% | 1.084 | 9% | 2.14× | 2.49× | 2.62× | ok; 2/3 runs busy |
| lpi-sorted-128 | 1.2e+07 | cpu | 8x1 | 95.05 ±4% | 90.03 ±3% | 0.205 | 2% | 1.00× | 1.00× | 1.00× | ok; 1/3 runs busy |
| lpi-sorted-128 | 1.2e+07 | metal | 1x4 | 48.44 ±0% | 42.66 ±2% | 0.585 | 4% | 1.96× | 2.11× | 2.86× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| 2d-small | 262,144 | 26,214,400 | 0.362 | 0.971 |
| 3d-small | 262,144 | 16,777,216 | 0.370 | 0.867 |
| lpi-sorted-24 | 13,824 | 12,000,000 | 0.555 | 1.315 |
| lpi-sorted-44 | 85,184 | 12,000,000 | 0.514 | 1.199 |
| lpi-sorted-64 | 262,144 | 12,000,000 | 0.413 | 1.084 |
| lpi-sorted-128 | 2,097,152 | 12,000,000 | 0.205 | 0.585 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (harris: bz, electron, ion; lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 2d-small | metal | 4 | 0.0e+00 | 4.2e-07 | ok |
| 3d-small | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| 3d-small | metal | 4 | 3.8e-07 | 7.1e-06 | ok |
| lpi-sorted-24 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-24 | metal | 4 | 0.0e+00 | 2.1e-06 | ok |
| lpi-sorted-44 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-44 | metal | 4 | 0.0e+00 | 1.7e-07 | ok |
| lpi-sorted-64 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-64 | metal | 4 | 0.0e+00 | 8.6e-08 | ok |
| lpi-sorted-128 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 91468073c439 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | 91468073c439 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON, VPIC_METAL_SOURCES_SHA256=2cf967a97a7e9c148b1c7cc83bd5e5efb15c4b2ab3fb06e8bb0abc24b5b18ff0 |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [3.47, 4.36, 3.48] at start, [6.67, 5.22, 3.94] at end
- Runs that started while another process used > 80.0% CPU: 4 (marked busy above; their timings are suspect)
