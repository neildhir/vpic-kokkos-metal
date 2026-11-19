# VPIC benchmark 20261118-161858-lpi-smoke

- Machine: MacBook Pro (Mac16,1) · Apple M4 · CPU 10 (4P+6E) · GPU 10-core · 16 GiB · macOS 27.2.1
- Started: 2026-11-18T16:18:58-08:00; repo `8b383248bd08` on `fix/apple-gpu-portability` (uncommitted changes)
- Deck lpi: `benchmarks/decks/lpi_bench.deck` sha256 `5731ee4338e2`
- Deck harris: `benchmarks/decks/harris_bench.deck` sha256 `93fccb8970d0`
- Cases: lpi-smoke-24, lpi-smoke-64, 2d-smoke; 2 measured runs each after 1 warm-up; builds interleaved per repetition; reference build **cpu**

Times are medians over the measured runs; ± is (max − min) / median. Speed-up is reference median over build median (> 1: faster than the reference).

| Case | Particles | Build | Layout | Wall ms/step | Steady ms/step | Pushes/ns | Sort share | Speed-up wall | Speed-up step | Speed-up push | Physics; notes |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| lpi-smoke-24 | 1e+06 | cpu | 8x1 | 78.15 ±31% | 74.82 ±11% | 0.184 | 0% | 1.00× | 1.00× | 1.00× | ok; 2/2 runs busy |
| lpi-smoke-24 | 1e+06 | metal | 1x4 | 12.28 ±41% | 7.31 ±27% | 0.191 | 0% | 6.36× | 10.24× | 1.02× | ok; 1/2 runs busy |
| lpi-smoke-64 | 1e+06 | cpu | 8x1 | 97.32 ±30% | 82.76 ±49% | 0.079 | 0% | 1.00× | 1.00× | 1.00× | ok; 2/2 runs busy |
| lpi-smoke-64 | 1e+06 | metal | 1x4 | 31.19 ±11% | 23.48 ±8% | 0.078 | 0% | 3.12× | 3.52× | 1.00× | ok; 1/2 runs busy |
| 2d-smoke | 5.24e+05 | cpu | 8x1 | 5.82 ±62% | 5.86 ±61% | 0.217 | 1% | 1.00× | 1.00× | 1.00× | ok; 2/2 runs busy |
| 2d-smoke | 5.24e+05 | metal | 1x4 | 6.92 ±4% | 6.01 ±1% | 0.144 | 3% | 0.84× | 0.97× | 0.70× | ok; 2/2 runs busy |

## Push rate

Particle pushes per ns: particles × steps / advance_p time in the steady window (all species), median over the measured runs.

| Case | Grid points | Particles | cpu | metal |
| --- | ---: | ---: | ---: | ---: |
| 2d-smoke | 16,384 | 524,288 | 0.217 | 0.144 |
| lpi-smoke-24 | 13,824 | 1,000,000 | 0.184 | 0.191 |
| lpi-smoke-64 | 262,144 | 1,000,000 | 0.079 | 0.078 |

## Physics check

Energies of every run (all layouts and repetitions) against the reference build's first measured run: max over dumps of |ΔE| / max|E_ref| per column. Tolerance 0.001 for each deck's bulk columns (lpi: electron, I2; harris: bz, electron, ion) and 0.01 for the other (fluctuation) columns. The reference row is its own run-to-run noise floor.

| Case | Build | Runs | Worst bulk | Worst fluctuation | Verdict |
| --- | --- | ---: | ---: | ---: | --- |
| lpi-smoke-24 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-smoke-24 | metal | 3 | 0.0e+00 | 6.1e-07 | ok |
| lpi-smoke-64 | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| lpi-smoke-64 | metal | 3 | 0.0e+00 | 0.0e+00 | ok |
| 2d-smoke | cpu | 3 | 0.0e+00 | 0.0e+00 | ok |
| 2d-smoke | metal | 3 | 3.8e-07 | 1.7e-05 | ok |

## Builds

| Build | Path | GPU | VPIC git | Options |
| --- | --- | --- | --- | --- |
| cpu | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/cpu-openmp` | no | 7eb2947e1274 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_AUTO_TUNING=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |
| metal | `/Users/neildhir/Projects/VPIC-METAL/vpic-kokkos-metal/build/metal` | yes | 8b383248bd08 | Kokkos COMPLEX_ALIGN, DEPRECATED_CODE_5, DEPRECATION_WARNINGS, IMPL_MDSPAN, IMPL_REF_COUNT_BRANCH_UNLIKELY, LIBDL, OPENMP, SERIAL; VPIC_ENABLE_32BIT_ATOMIC_COUNTERS=ON, VPIC_ENABLE_AUTO_TUNING=ON, VPIC_ENABLE_METAL=ON, VPIC_USE_LEGACY_PARTICLE_ARRAY=ON |

## Conditions

- Power: Battery Power; Low Power Mode: False
- Thermal state: nominal at start, nominal at end
- Load average (1/5/15 min): [2.94, 2.78, 3.7] at start, [16.22, 6.08, 4.85] at end
- Runs that started while another process used > 80.0% CPU: 10 (marked busy above; their timings are suspect)
- Warning: running on Battery Power
