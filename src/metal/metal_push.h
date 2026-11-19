#ifndef _vpic_metal_push_h_
#define _vpic_metal_push_h_

// Particle push on an Apple GPU through Metal (built with VPIC_ENABLE_METAL).
//
// The GPU works on VPIC's own arrays in place: Apple GPUs share memory with
// the CPU, so each array is wrapped as a Metal buffer once and reused. The
// arrays must therefore stay allocated (and must not move) for the run.
// This interface uses plain pointers so that the Objective-C++ side needs no
// Kokkos headers.
//
// Runs are not bitwise repeatable: currents are added with GPU atomics in an
// order that varies from run to run, and the GPU sort orders particles within
// a cell differently each time. The differences start at roundoff and grow, as
// between multithreaded CPU runs. Compare results with tolerances, or use the
// check modes (VPIC_METAL_PUSH_CHECK, VPIC_METAL_SORT_CHECK), which compare
// each GPU step with the CPU code from the same state.

#include <cstddef>
#include <cstdint>

struct vpic_metal_push_args {
  float*         particles;        // particle (i, var) at particles[var*stride + i]
  size_t         particle_stride;
  size_t         particle_capacity;  // rows allocated, for the buffer extent
  int*           particles_i;
  size_t         np;
  const float*   interpolators;    // 18 floats per voxel
  float*         fields;           // 16 floats per voxel; jfx, jfy, jfz are added to
  size_t         nvoxels;
  const int64_t* neighbors;        // 6 per voxel; nullptr before VPIC builds the table
  float*         movers;           // 3 floats per mover
  size_t*        movers_i;
  float*         copies;           // 7 floats per mover
  int*           copies_i;
  size_t         max_nm;
  float qdt_2mc, cdt_dx, cdt_dy, cdt_dz, qsp, cx, cy, cz;
  int nx, ny, nz;
  int64_t rangel, rangeh;
};

// True unless the environment sets VPIC_METAL_PUSH=0, which runs the CPU push
// in a Metal build (for A/B comparisons in one binary).
bool vpic_metal_push_enabled();

// True if VPIC_METAL_PUSH_CHECK=1: compare every Metal push against the CPU
// push from the same state (slow; for validation).
bool vpic_metal_push_check_enabled();

// Push all np particles. Returns the number of particles on the mover list.
// On failure (no GPU, kernel error, mover list overflow) prints the reason and
// aborts the run.
size_t vpic_metal_advance_p(const vpic_metal_push_args& args);

// Particle sort on the GPU: particles grouped by cell, cells in increasing
// order (VPIC's StandardSortOrder), sorted in place.
struct vpic_metal_sort_args {
  float* particles;          // particle (i, var) at particles[var*stride + i]
  size_t particle_stride;
  size_t particle_capacity;  // rows allocated
  int*   particles_i;        // cell of each particle
  size_t np;
  size_t ncells;             // cell indices are in [0, ncells)
};

// True unless VPIC_METAL_SORT=0, which sorts on the CPU in a Metal build.
bool vpic_metal_sort_enabled();

// True if VPIC_METAL_SORT_CHECK=1: compare every GPU sort with the CPU sort.
bool vpic_metal_sort_check_enabled();

// Sort the particles. Aborts the run on failure.
void vpic_metal_sort_particles(const vpic_metal_sort_args& args);

#endif // _vpic_metal_push_h_
