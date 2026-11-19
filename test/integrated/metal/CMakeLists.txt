# Metal builds only: run small decks with every Metal check mode on. Each check
# runs the GPU code and the CPU code from the same state and aborts the run on
# a mismatch, so these tests fail if the GPU path ever disagrees with the CPU:
#   push       particles within rounding (1e-6), weights, cells and movers
#              exact, currents within 1e-4 of the largest
#   sort       same cell order and the same particles in every cell
#   rho, energy  GPU sums against a double-precision reference
#   fields     advance_b, load_interpolator, clear_jf within rounding (1e-6)
#              (enabled here)
# On the M4 these were developed on, particles and fields match bit for bit;
# the rounding allowance is for GPUs or Metal compilers that round differently.
# A failure well above 1e-6 is a real disagreement between GPU and CPU.
# The decks are the benchmark decks (benchmarks/decks): Harris reconnection
# (periodic y, conducting x walls) and VPIC's LPI deck (absorbing fields, laser
# injection, reflecting particles), on 1 and 2 ranks.

set(METAL_CHECK_ENV
    VPIC_METAL_PUSH_CHECK=1
    VPIC_METAL_SORT_CHECK=1
    VPIC_METAL_PARTICLE_LOOPS_CHECK=1
    VPIC_METAL_FIELDS=1
    VPIC_METAL_FIELDS_CHECK=1)

build_a_vpic(metal_harris ${CMAKE_SOURCE_DIR}/benchmarks/decks/harris_bench.deck)
build_a_vpic(metal_lpi ${CMAKE_SOURCE_DIR}/benchmarks/decks/lpi_bench.deck)

# name, ranks, executable, deck arguments
macro(metal_check_test name ranks exe)
  set(_dir ${CMAKE_CURRENT_BINARY_DIR}/${name})
  file(MAKE_DIRECTORY ${_dir})
  add_test(NAME ${name}
    COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} ${ranks} ${MPIEXEC_PREFLAGS}
            ${CMAKE_CURRENT_BINARY_DIR}/${exe} ${MPIEXEC_POSTFLAGS} --tpp 2 ${ARGN}
    WORKING_DIRECTORY ${_dir})
  set_tests_properties(${name} PROPERTIES ENVIRONMENT "${METAL_CHECK_ENV}")
endmacro()

# Harris args: nx ny nz nppc nstep (nstep a multiple of 40)
metal_check_test(metal_check_harris_2d 1 metal_harris 64 64 1 8 40)
metal_check_test(metal_check_harris_3d_2ranks 2 metal_harris 16 16 16 8 40)
# LPI args: nx ny nz total_particles nstep sort_interval
metal_check_test(metal_check_lpi_2ranks 2 metal_lpi 16 16 16 200000 20 4)
