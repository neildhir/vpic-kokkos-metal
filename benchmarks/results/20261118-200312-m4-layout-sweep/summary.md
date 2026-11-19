# VPIC benchmark 20261118-200312-m4-layout-sweep

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T20:03:12-08:00; repo `a7ae75fc705d` on `feat/metal-field-solve`
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: 2d-small, 3d-small, lpi-sorted-64, lpi-sorted-128; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2d-small | 2.62e+07 | cpu | 8x1 | 97.57 ±1% | 94.55 ±2% | 0.368 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 2d-small | 2.62e+07 | metal | 1x4 | 42.39 ±3% | 40.53 ±2% | 0.967 | 7% | 2.30× | 2.33× | 2.63× | ok |
| 3d-small | 1.68e+07 | cpu | 8x1 | 64.64 ±1% | 61.49 ±1% | 0.374 | 4% | 1.00× | 1.00× | 1.00× | ok |
| 3d-small | 1.68e+07 | metal | 1x4 | 25.68 ±0% | 24.90 ±0% | 0.866 | 8% | 2.52× | 2.47× | 2.31× | ok |
| lpi-sorted-64 | 1.2e+07 | cpu | 8x1 | 40.57 ±1% | 38.50 ±2% | 0.427 | 4% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-64 | 1.2e+07 | metal | 1x4 | 19.19 ±0% | 15.49 ±1% | 1.077 | 9% | 2.11× | 2.48× | 2.52× | ok |
| lpi-sorted-128 | 1.2e+07 | cpu | 8x1 | 95.44 ±1% | 90.27 ±2% | 0.205 | 2% | 1.00× | 1.00× | 1.00× | ok |
| lpi-sorted-128 | 1.2e+07 | metal | 1x4 | 48.78 ±1% | 42.63 ±1% | 0.583 | 4% | 1.96× | 2.12× | 2.84× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| 2d-small | 262,144 | 26,214,400 | 0.368 | 0.967 |
| 3d-small | 262,144 | 16,777,216 | 0.374 | 0.866 |
| lpi-sorted-64 | 262,144 | 12,000,000 | 0.427 | 1.077 |
| lpi-sorted-128 | 2,097,152 | 12,000,000 | 0.205 | 0.583 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (harris: bz, electron, ion; lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| 2d-small | cpu | 8 | 0.0e+00 | 4.2e-07 | ok |
| 2d-small | metal | 7 | 0.0e+00 | 4.2e-07 | ok |
| 3d-small | cpu | 8 | 3.8e-07 | 6.3e-06 | ok |
| 3d-small | metal | 7 | 3.8e-07 | 6.3e-06 | ok |
| lpi-sorted-64 | cpu | 8 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-64 | metal | 7 | 0.0e+00 | 2.3e-07 | ok |
| lpi-sorted-128 | cpu | 8 | 0.0e+00 | 0.0e+00 | ok |
| lpi-sorted-128 | metal | 7 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | afe2086b5af3 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | afe2086b5af3 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON, VPIC_METAL_SOURCES_SHA256=2cf967a97a7e9c148b1c7cc83bd5e5efb15c4b2ab3fb06e8bb0abc24b5b18ff0 |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [2.9, 2.45, 2.75] at start, [7.25, 5.02, 3.81] at end
- Runs that started while another process used > 80.0% CPU: 0 (marked busy above; their timings are suspect)
