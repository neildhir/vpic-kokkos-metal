if(VPIC_USE_LEGACY_PARTICLE_ARRAY)
add_executable(rho_p ./rho_p.cc)
target_link_libraries(rho_p vpic Kokkos::kokkos)
add_test(NAME rho_p COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} 1 ${MPIEXEC_PREFLAGS} ./rho_p)
if(VPIC_ENABLE_METAL)
  # Metal builds deposit charge on the GPU, which sums in a different order
  # from the CPU and legacy deposits; with 10^6 particles in one cell their
  # float sums differ by ~3e-4, more than this test's 1e-4. In check mode the
  # GPU deposit must match a double-precision sum (within 1e-5 of the largest
  # deposit, or the run aborts) and the CPU deposit's result is kept, so the
  # test still compares the CPU deposit with the legacy one, as written.
  set_tests_properties(rho_p PROPERTIES ENVIRONMENT "VPIC_METAL_PARTICLE_LOOPS_CHECK=1")
endif()
add_executable(hydro_p ./hydro_p.cc)
target_link_libraries(hydro_p vpic Kokkos::kokkos)
add_test(NAME hydro_p COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} 1 ${MPIEXEC_PREFLAGS} ./hydro_p)
endif(VPIC_USE_LEGACY_PARTICLE_ARRAY)

add_executable(field_comm field_comm.cpp)
target_link_libraries(field_comm vpic Kokkos::kokkos)
add_test(NAME field_comm_1x1x1 COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} 1  ${MPIEXEC_PREFLAGS} ./field_comm ${MPIEXEC_POSTFLAGS} 1 1 1 --kokkos-num-threads=1 --kokkos-map-device-id-by=mpi_rank)
add_test(NAME field_comm_2x2x2 COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} 8  --oversubscribe ${MPIEXEC_PREFLAGS} ./field_comm ${MPIEXEC_POSTFLAGS} 2 2 2 --kokkos-num-threads=1 --kokkos-map-device-id-by=mpi_rank)
add_test(NAME field_comm_3x3x3 COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} 27 --oversubscribe ${MPIEXEC_PREFLAGS} ./field_comm ${MPIEXEC_POSTFLAGS} 3 3 3 --kokkos-num-threads=1 --kokkos-map-device-id-by=mpi_rank)

add_executable(field_local_bc field_local_bc.cpp)
target_link_libraries(field_local_bc vpic Kokkos::kokkos)
add_test(NAME field_local_bc COMMAND ${MPIEXEC} ${MPIEXEC_NUMPROC_FLAG} 8 --oversubscribe ${MPIEXEC_PREFLAGS} ./field_local_bc ${MPIEXEC_POSTFLAGS} 2 2 2 --kokkos-num-threads=1 --kokkos-map-device-id-by=mpi_rank)
