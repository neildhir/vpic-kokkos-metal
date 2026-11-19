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
// push from the same state and abort on a mismatch beyond rounding (slow; for
// validation; tolerances in advance_p_metal_checked).
bool vpic_metal_push_check_enabled();

// Drop the GPU's wrappers of VPIC's arrays. Wrappers are made once per array
// (wrapping costs about as much as the push) and reused, so call this before
// any wrapped array (particles, movers, fields, interpolators, neighbors) is
// freed or re-created; otherwise a new array at the same address and size
// would be reached through the stale wrapper. Does nothing before first use.
void vpic_metal_forget_arrays();

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

// True if VPIC_METAL_SORT_CHECK=1: compare every GPU sort with the CPU sort
// and abort on a mismatch.
bool vpic_metal_sort_check_enabled();

// Sort the particles. Aborts the run on failure.
void vpic_metal_sort_particles(const vpic_metal_sort_args& args);

// Periodic particle loops on the GPU: the charge deposit of divergence
// cleaning and the kinetic energy of the energies dump. Both follow their CPU
// loops (k_accumulate_rho_p, energy_p_kernel) statement for statement.
struct vpic_metal_rho_args {
  const float* particles;          // particle (i, var) at particles[var*stride + i]
  size_t       particle_stride;
  size_t       particle_capacity;  // rows allocated
  const int*   particles_i;
  size_t       np;
  float*       fields;             // 16 floats per voxel; rhof is added to
  size_t       nvoxels;
  float        q_8V;               // species charge / (8 cell volumes)
  int          sy, sz;             // voxel strides
};

struct vpic_metal_energy_args {
  const float* particles;
  size_t       particle_stride;
  size_t       particle_capacity;
  const int*   particles_i;
  size_t       np;
  const float* interpolators;      // 18 floats per voxel
  size_t       nvoxels;
  float        qdt_2mc, msp;
};

// True unless VPIC_METAL_PARTICLE_LOOPS=0, which runs both loops on the CPU.
bool vpic_metal_particle_loops_enabled();

// True if VPIC_METAL_PARTICLE_LOOPS_CHECK=1: compare each GPU loop with the
// CPU loop from the same state (slow; for validation).
bool vpic_metal_particle_loops_check_enabled();

// Add the species' charge density to rhof. Aborts the run on failure.
void vpic_metal_accumulate_rho_p(const vpic_metal_rho_args& args);

// The species' kinetic energy, as energy_p_kernel returns it (local to this
// rank, in units of c^2; the caller does the MPI sum). Summed per SIMD group
// in float, then in double on the host. Aborts the run on failure.
double vpic_metal_energy_p(const vpic_metal_energy_args& args);

// Field kernels on the GPU: advance_b, load_interpolator and clear_jf. Each
// follows its Kokkos loop statement for statement and matches it bit for bit
// (Apple GPUs flush denormals to zero, the only difference). Off by default:
// on a base M4 (about 100 GB/s for CPU and GPU alike) the CPU already runs
// them at the memory limit, and in 2D its caches hold much of the field
// array, so the GPU versions gained 3% per step at LPI 128^3 and lost 2-5%
// on Harris. Chips whose GPU has more bandwidth than the CPU can use (M-series
// Pro and Max) may differ; enable them with VPIC_METAL_FIELDS=1 to measure.
struct vpic_metal_field_args {
  float*       fields;          // 16 floats per voxel
  float*       interpolators;   // 18 floats per voxel (load_interpolator only)
  size_t       nvoxels;         // voxels in both arrays
  int          nx, ny, nz;
  float        px, py, pz;      // advance_b only: frac * c dt / dx (0 in a collapsed dimension)
};

// True if VPIC_METAL_FIELDS=1 (default: the CPU runs these field kernels).
bool vpic_metal_fields_enabled();

// True if VPIC_METAL_FIELDS_CHECK=1: run each field kernel on the CPU and the
// GPU from the same state and abort unless the results match bit for bit.
bool vpic_metal_fields_check_enabled();

void vpic_metal_advance_b(const vpic_metal_field_args& args);
void vpic_metal_load_interpolator(const vpic_metal_field_args& args);
void vpic_metal_clear_jf(const vpic_metal_field_args& args);

// Compact currents. Between begin and end, the Metal push adds currents to a
// compact GPU array (4 floats per voxel) instead of the 64-byte field records,
// which cuts the push's memory traffic. advance() opens the window around its
// species loop in place of clear_jf; end stores the currents into the fields
// (add false) or adds them (add true, for check mode, which also flushes with
// add after each checked push). Pushes outside the window write the fields.
// True unless VPIC_METAL_COMPACT_J=0. advance() uses compact currents only
// below METAL_COMPACT_J_MAX_PPC particles per voxel (see advance.cc).
bool vpic_metal_compact_currents_enabled();
void vpic_metal_begin_compact_currents(size_t nvoxels);
void vpic_metal_flush_compact_currents(float* fields, size_t nvoxels, bool add);
void vpic_metal_end_compact_currents(float* fields, size_t nvoxels, bool add);

#endif // _vpic_metal_push_h_
