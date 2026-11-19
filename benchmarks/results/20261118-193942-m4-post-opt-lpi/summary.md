# VPIC benchmark 20261118-193942-m4-post-opt-lpi

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T19:39:42-08:00; repo `91468073c439` on `fix/apple-gpu-portability`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: lpi-16, lpi-24, lpi-34, lpi-44, lpi-64, lpi-96, lpi-128; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lpi-16 | 1.2e+07 | cpu | 8x1 | 31.58 ±12% | 30.07 ±7% | 0.517 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-16 | 1.2e+07 | metal | 1x4 | 19.22 ±5% | 18.34 ±1% | 0.687 | 0% | 1.64× | 1.64× | 1.33× | ok |
| lpi-24 | 1.2e+07 | cpu | 8x1 | 35.74 ±7% | 33.53 ±10% | 0.482 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-24 | 1.2e+07 | metal | 1x4 | 19.30 ±1% | 18.37 ±1% | 0.689 | 0% | 1.85× | 1.82× | 1.43× | ok |
| lpi-34 | 1.2e+07 | cpu | 8x1 | 36.98 ±3% | 35.55 ±3% | 0.419 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-34 | 1.2e+07 | metal | 1x4 | 38.16 ±0% | 37.24 ±2% | 0.332 | 0% | 0.97× | 0.95× | 0.79× | ok |
| lpi-44 | 1.2e+07 | cpu | 8x1 | 40.45 ±3% | 38.40 ±4% | 0.406 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-44 | 1.2e+07 | metal | 1x4 | 47.58 ±2% | 45.05 ±2% | 0.275 | 0% | 0.85× | 0.85× | 0.68× | ok |
| lpi-64 | 1.2e+07 | cpu | 8x1 | 59.29 ±9% | 57.25 ±6% | 0.261 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-64 | 1.2e+07 | metal | 1x4 | 116.11 ±0% | 112.74 ±0% | 0.110 | 0% | 0.51× | 0.51× | 0.42× | ok |
| lpi-96 | 1.2e+07 | cpu | 8x1 | 125.64 ±4% | 118.45 ±6% | 0.119 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-96 | 1.2e+07 | metal | 1x4 | 153.62 ±2% | 148.13 ±1% | 0.089 | 0% | 0.82× | 0.80× | 0.74× | ok |
| lpi-128 | 1.2e+07 | cpu | 8x1 | 172.16 ±3% | 160.82 ±1% | 0.092 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-128 | 1.2e+07 | metal | 1x4 | 232.48 ±0% | 225.17 ±1% | 0.061 | 0% | 0.74× | 0.71× | 0.66× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| lpi-16 | 4,096 | 12,000,000 | 0.517 | 0.687 |
| lpi-24 | 13,824 | 12,000,000 | 0.482 | 0.689 |
| lpi-34 | 39,304 | 12,000,000 | 0.419 | 0.332 |
| lpi-44 | 85,184 | 12,000,000 | 0.406 | 0.275 |
| lpi-64 | 262,144 | 12,000,000 | 0.261 | 0.110 |
| lpi-96 | 884,736 | 12,000,000 | 0.119 | 0.089 |
| lpi-128 | 2,097,152 | 12,000,000 | 0.092 | 0.061 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| lpi-16 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-16 | metal | 4 | 0.0e+00 | 5.5e-06 | ok |
| lpi-24 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-24 | metal | 4 | 0.0e+00 | 1.4e-06 | ok |
| lpi-34 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-34 | metal | 4 | 0.0e+00 | 2.7e-07 | ok |
| lpi-44 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-44 | metal | 4 | 0.0e+00 | 1.7e-07 | ok |
| lpi-64 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-64 | metal | 4 | 0.0e+00 | 2.3e-07 | ok |
| lpi-96 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-96 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-128 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-128 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 91468073c439 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | 91468073c439 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_SORT_ORDER=auto, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON, VPIC_METAL_SOURCES_SHA256=2cf967a97a7e9c148b1c7cc83bd5e5efb15c4b2ab3fb06e8bb0abc24b5b18ff0 |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [3.83, 3.42, 2.81] at start, [5.37, 4.79, 3.57] at end
- Runs that started while another process used > 80.0% CPU: 0 (marked busy above; their timings are suspect)
