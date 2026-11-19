# VPIC benchmark 20261118-162340-m4-lpi

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:23:40-08:00; repo `3179ae668e54` on `fix/apple-gpu-portability`
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Cases: lpi-16, lpi-24, lpi-34, lpi-44, lpi-64, lpi-96, lpi-128; 3 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lpi-16 | 1.2e+07 | cpu | 8x1 | 31.48 ±2% | 30.60 ±5% | 0.491 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-16 | 1.2e+07 | metal | 1x4 | 21.38 ±0% | 19.26 ±1% | 0.652 | 0% | 1.47× | 1.59× | 1.33× | ok |
| lpi-24 | 1.2e+07 | cpu | 8x1 | 33.97 ±0% | 32.45 ±3% | 0.475 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-24 | 1.2e+07 | metal | 1x4 | 21.77 ±1% | 19.39 ±1% | 0.651 | 0% | 1.56× | 1.67× | 1.37× | ok |
| lpi-34 | 1.2e+07 | cpu | 8x1 | 39.82 ±23% | 40.06 ±26% | 0.409 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-34 | 1.2e+07 | metal | 1x4 | 39.10 ±2% | 37.73 ±4% | 0.328 | 0% | 1.02× | 1.06× | 0.80× | ok |
| lpi-44 | 1.2e+07 | cpu | 8x1 | 40.81 ±1% | 39.32 ±2% | 0.378 | 0% | 1.00× | 1.00× | 1.00× | ok; 1/3 runs busy |
| lpi-44 | 1.2e+07 | metal | 1x4 | 48.16 ±2% | 45.80 ±2% | 0.271 | 0% | 0.85× | 0.86× | 0.72× | ok |
| lpi-64 | 1.2e+07 | cpu | 8x1 | 62.19 ±1% | 59.08 ±5% | 0.260 | 0% | 1.00× | 1.00× | 1.00× | ok |
| lpi-64 | 1.2e+07 | metal | 1x4 | 120.91 ±2% | 114.58 ±1% | 0.110 | 0% | 0.51× | 0.52× | 0.42× | ok |
| lpi-96 | 1.2e+07 | cpu | 8x1 | 127.15 ±4% | 120.76 ±2% | 0.116 | 0% | 1.00× | 1.00× | 1.00× | ok; 1/3 runs busy |
| lpi-96 | 1.2e+07 | metal | 1x4 | 166.69 ±3% | 154.35 ±2% | 0.086 | 0% | 0.76× | 0.78× | 0.74× | ok |
| lpi-128 | 1.2e+07 | cpu | 8x1 | 176.75 ±2% | 164.33 ±2% | 0.092 | 0% | 1.00× | 1.00× | 1.00× | ok; 1/3 runs busy |
| lpi-128 | 1.2e+07 | metal | 1x4 | 245.08 ±0% | 227.45 ±0% | 0.061 | 0% | 0.72× | 0.72× | 0.67× | ok |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| lpi-16 | 4,096 | 12,000,000 | 0.491 | 0.652 |
| lpi-24 | 13,824 | 12,000,000 | 0.475 | 0.651 |
| lpi-34 | 39,304 | 12,000,000 | 0.409 | 0.328 |
| lpi-44 | 85,184 | 12,000,000 | 0.378 | 0.271 |
| lpi-64 | 262,144 | 12,000,000 | 0.260 | 0.110 |
| lpi-96 | 884,736 | 12,000,000 | 0.116 | 0.086 |
| lpi-128 | 2,097,152 | 12,000,000 | 0.092 | 0.061 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (lpi: electron, I2) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| lpi-16 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-16 | metal | 4 | 0.0e+00 | 1.0e-05 | ok |
| lpi-24 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-24 | metal | 4 | 0.0e+00 | 1.4e-06 | ok |
| lpi-34 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-34 | metal | 4 | 0.0e+00 | 4.5e-07 | ok |
| lpi-44 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-44 | metal | 4 | 0.0e+00 | 2.0e-07 | ok |
| lpi-64 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-64 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-96 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-96 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-128 | cpu | 4 | 0.0e+00 | 0.0e+00 | ok |
| lpi-128 | metal | 4 | 0.0e+00 | 0.0e+00 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: AC Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [3.79, 5.3, 4.86] at start, [7.11, 6.02, 5.25] at end
- Runs that started while another process used > 80.0% CPU: 3 (marked busy above; their timings are suspect)
