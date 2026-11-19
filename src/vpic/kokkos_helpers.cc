#include "kokkos_helpers.h"

// Helper functions, like printing etc

void print_accumulator(k_accumulators_t& f, int n)
{
#ifdef VPIC_DISABLE_DEVICE_FP64
    // Device printf would pass floats as doubles: print a host copy instead
    auto h = Kokkos::create_mirror_view_and_copy(Kokkos::HostSpace(), f);
    printf("size of accumulator is %ld\n", h.size() );
    for (int z = 0; z < n; z++)
        for (int zz = 0; zz < ACCUMULATOR_VAR_COUNT; zz++)
            printf("accum %d has %d %f %f %f %f \n", 0, zz,
                   h(0, zz, 0), h(0, zz, 1), h(0, zz, 2), h(0, zz, 3));
#else

    printf("size of accumulator is %ld\n", f.size() );

    Kokkos::parallel_for("field printer", Kokkos::RangePolicy <
            Kokkos::DefaultExecutionSpace > (0, 1), KOKKOS_LAMBDA (int i)
            {

            for (int z = 0; z < n; z++)
            {
                for (int zz = 0; zz < ACCUMULATOR_VAR_COUNT; zz++)
                {
                    printf("accum %d has %d %f %f %f %f \n", i, zz,
                        f(i, zz, 0),
                        f(i, zz, 1),
                        f(i, zz, 2),
                        f(i, zz, 3)
                      );
                }
            }
    });
#endif
}
void print_particles_d(
        k_particles_t particles,
        size_t np
        )
{
    printf("Particle printer from 0 to %zu \n", np);
#ifdef VPIC_DISABLE_DEVICE_FP64
    // Device printf would pass floats as doubles: print a host copy instead
    auto h = Kokkos::create_mirror_view_and_copy(Kokkos::HostSpace(), particles);
    for (size_t z = 0; z < np; z++)
        printf("accum part %zu has %f %f %f %f %f %f \n", z,
               h(z, particle_var::dx), h(z, particle_var::dy), h(z, particle_var::dz),
               h(z, particle_var::ux), h(z, particle_var::uy), h(z, particle_var::uz));
#else
    Kokkos::parallel_for("particle printer", Kokkos::RangePolicy <
            Kokkos::DefaultExecutionSpace > (0, 1), KOKKOS_LAMBDA (int i)
    {
        for (size_t z = 0; z < np; z++)
        {
            printf("accum part %zu has %f %f %f %f %f %f \n", z,
                    particles(z, particle_var::dx),
                    particles(z, particle_var::dy),
                    particles(z, particle_var::dz),
                    particles(z, particle_var::ux),
                    particles(z, particle_var::uy),
                    particles(z, particle_var::uz)
                  );
        }
    });
#endif
}
