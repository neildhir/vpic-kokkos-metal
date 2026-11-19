// Periodic particle loops for Apple GPUs: the charge deposit used by
// divergence cleaning (k_accumulate_rho_p in rho_p.cc) and the kinetic-energy
// sum of the energies dump (energy_p_kernel in energy_p.cc). Each follows its
// CPU loop statement for statement. Dispatched in chunks of particles like the
// push (see metal_push.mm).

#include <metal_stdlib>
using namespace metal;

// Must match vpic_metal_rho_params in metal_push.mm (8-byte members first)
struct RhoParams {
  ulong np;       // particles
  ulong stride;   // particle (i, var) is at p[var*stride + i]
  ulong first;    // first particle of this dispatch
  float q_8V;     // species charge / (8 cell volumes)
  int   sy, sz;   // voxel strides in y and z
  int   pad;
};

// Must match vpic_metal_energy_params in metal_push.mm (8-byte members first)
struct EnergyParams {
  ulong np, stride, first;
  float qdt_2mc;  // species q dt / (2 m c)
  float msp;      // species mass
};

// Particle variables and field / interpolator layouts (kokkos_helpers.h)
constant ulong LP_DX = 0, LP_DY = 1, LP_DZ = 2, LP_UX = 3, LP_UY = 4, LP_UZ = 5, LP_W = 6;
constant ulong LP_FIELD_VARS = 16, LP_RHOF = 15;
constant ulong LP_INTERP_VARS = 18;
constant ulong LI_EX = 0, LI_DEXDY = 1, LI_DEXDZ = 2, LI_D2EXDYDZ = 3;
constant ulong LI_EY = 4, LI_DEYDZ = 5, LI_DEYDX = 6, LI_D2EYDZDX = 7;
constant ulong LI_EZ = 8, LI_DEZDX = 9, LI_DEZDY = 10, LI_D2EZDXDY = 11;

inline void add_rho(device atomic_float* f, int voxel, float value) {
  atomic_fetch_add_explicit(&f[ulong(voxel) * LP_FIELD_VARS + LP_RHOF], value, memory_order_relaxed);
}

// The eight corners of a particle's cell, as offsets from its voxel
inline int rho_corner(ushort k, int sy, int sz) {
  return ((k & 1) ? 1 : 0) + ((k & 2) ? sy : 0) + ((k & 4) ? sz : 0);
}

// Trilinear charge deposit into rhof, as k_accumulate_rho_p. Particles are
// sorted by cell between sorts, so (as in the push's deposit_in_cell) each
// SIMD group sums its lanes' weights cell by cell with simd_sum and adds one
// atomic per corner, falling back to direct atomics after MAX_CELL_PASSES
// cells. Every lane reaches the SIMD operations (uniform control flow).
kernel void accumulate_rho_p(device const float*  p     [[buffer(0)]],
                             device const int*    pidx  [[buffer(1)]],
                             device atomic_float* f     [[buffer(2)]],
                             constant RhoParams&  R     [[buffer(3)]],
                             uint   gid  [[thread_position_in_grid]],
                             ushort lane [[thread_index_in_simdgroup]]) {
  constexpr int MAX_CELL_PASSES = 4;
  const ulong i = R.first + gid;
  const ulong s = R.stride;
  const bool valid = i < R.np;
  float w[8];
  for (int k = 0; k < 8; ++k) w[k] = 0.0f;
  int v = 0;
  if (valid) {
    float w0 = p[LP_DX * s + i];
    float w1 = p[LP_DY * s + i];
    const float dz = p[LP_DZ * s + i];
    v = pidx[i];
    float w7 = p[LP_W * s + i] * R.q_8V;
    float w6 = w7 - w0 * w7;                            // q(1-dx)
    w7 = w7 + w0 * w7;                                  // q(1+dx)
    float w4 = w6 - w1 * w6, w5 = w7 - w1 * w7;         // q(1-dx)(1-dy), q(1+dx)(1-dy)
    w6 = w6 + w1 * w6; w7 = w7 + w1 * w7;               // q(1-dx)(1+dy), q(1+dx)(1+dy)
    w[0] = w4 - dz * w4; w[1] = w5 - dz * w5; w[2] = w6 - dz * w6; w[3] = w7 - dz * w7;
    w[4] = w4 + dz * w4; w[5] = w5 + dz * w5; w[6] = w6 + dz * w6; w[7] = w7 + dz * w7;
  }

  // Lanes 0..active-1 run: a grid's last SIMD group may be short
  const ushort active = ushort(simd_sum(1u));
  bool done = !valid;
  for (int pass = 0; pass < MAX_CELL_PASSES; ++pass) {
    if (simd_all(done)) return;
    const int cell = simd_min(done ? 0x7fffffff : v);
    const bool mine = !done && v == cell;
    float sum[8];
    for (int k = 0; k < 8; ++k) sum[k] = simd_sum(mine ? w[k] : 0.0f);
    for (ushort k = lane; k < 8; k += active) {   // one pass when active >= 8
      float value = sum[0];
      for (ushort m = 1; m < 8; ++m) value = (k == m) ? sum[m] : value;
      add_rho(f, cell + rho_corner(k, R.sy, R.sz), value);
    }
    done = done || mine;
  }
  if (!done)
    for (ushort k = 0; k < 8; ++k) add_rho(f, v + rho_corner(k, R.sy, R.sz), w[k]);
}

// Kinetic energy of each particle after a half step of acceleration in E, as
// energy_p_kernel, summed over each SIMD group: partial[simd group of the
// grid] = sum of the lanes' energies (in units of c^2). The host adds the
// partial sums in double. Dispatch with threadgroups that are whole multiples
// of the 32-wide SIMD group.
kernel void energy_p(device const float*   p        [[buffer(0)]],
                     device const int*     pidx     [[buffer(1)]],
                     device const float*   interp   [[buffer(2)]],
                     device float*         partial  [[buffer(3)]],
                     constant EnergyParams& E       [[buffer(4)]],
                     uint   gid  [[thread_position_in_grid]],
                     ushort lane [[thread_index_in_simdgroup]]) {
  const ulong i = E.first + gid;
  const ulong s = E.stride;
  float en = 0.0f;
  if (i < E.np) {
    const float dx = p[LP_DX * s + i];
    const float dy = p[LP_DY * s + i];
    const float dz = p[LP_DZ * s + i];
    device const float* f = interp + ulong(pidx[i]) * LP_INTERP_VARS;
    float v0 = p[LP_UX * s + i] + E.qdt_2mc * ((f[LI_EX] + dy * f[LI_DEXDY]) +
                                               dz * (f[LI_DEXDZ] + dy * f[LI_D2EXDYDZ]));
    float v1 = p[LP_UY * s + i] + E.qdt_2mc * ((f[LI_EY] + dz * f[LI_DEYDZ]) +
                                               dx * (f[LI_DEYDX] + dz * f[LI_D2EYDZDX]));
    float v2 = p[LP_UZ * s + i] + E.qdt_2mc * ((f[LI_EZ] + dx * f[LI_DEZDX]) +
                                               dy * (f[LI_DEZDY] + dx * f[LI_D2EZDXDY]));
    v0 = v0 * v0 + v1 * v1 + v2 * v2;
    en = (E.msp * p[LP_W * s + i]) * (v0 / (1.0f + sqrt(1.0f + v0)));
  }
  const float group = simd_sum(en);
  if (lane == 0) partial[gid / 32] = group;
}
