// Field kernels for Apple GPUs: the magnetic field half advance (advance_b.cc),
// the interpolator load (interpolator_array.cc) and the current clear
// (sfa.cc's clear_jf_kokkos). Each follows its Kokkos loop statement for
// statement. Every thread writes only its own voxel's values and reads values
// no thread writes, so there are no races and results match the CPU exactly.

#include <metal_stdlib>
using namespace metal;

// Must match vpic_metal_field_params in metal_push.mm
struct FieldParams {
  int   nx, ny, nz;
  float px, py, pz;   // advance_b: frac * c dt / dx (0 in a collapsed dimension)
};

// VOXEL(x,y,z, nx,ny,nz) of grid.h
inline ulong voxel(int x, int y, int z, constant FieldParams& G) {
  return ulong(x) + ulong(G.nx + 2) * (ulong(y) + ulong(G.ny + 2) * ulong(z));
}

// advance_b_kokkos: the main loop over x, y, z in [1, n] updates cbx, cby and
// cbz; the left-over loops update cbx on the x = nx+1 face, cby on y = ny+1
// and cbz on z = nz+1. One dispatch over [1, nx+1] x [1, ny+1] x [1, nz+1]
// covers them all (threads on the extra edges and corner do nothing).
kernel void advance_b(device float* f [[buffer(0)]],
                      constant FieldParams& G [[buffer(1)]],
                      uint3 gid [[thread_position_in_grid]]) {
  const int x = int(gid.x) + 1, y = int(gid.y) + 1, z = int(gid.z) + 1;
  const bool in_x = x <= G.nx, in_y = y <= G.ny, in_z = z <= G.nz;
  device float* f0 = f + voxel(x, y, z, G) * FIELD_VARS;
  device const float* fx = f + voxel(x + 1, y, z, G) * FIELD_VARS;
  device const float* fy = f + voxel(x, y + 1, z, G) * FIELD_VARS;
  device const float* fz = f + voxel(x, y, z + 1, G) * FIELD_VARS;
  const float px = G.px, py = G.py, pz = G.pz;
  if (in_y && in_z && (in_x || x == G.nx + 1))   // main loop, or left-over bx
    f0[F_CBX] -= ( py*( fy[F_EZ]-f0[F_EZ] ) - pz*( fz[F_EY]-f0[F_EY] ) );
  if (in_x && in_z && (in_y || y == G.ny + 1))   // main loop, or left-over by
    f0[F_CBY] -= ( pz*( fz[F_EX]-f0[F_EX] ) - px*( fx[F_EZ]-f0[F_EZ] ) );
  if (in_x && in_y && (in_z || z == G.nz + 1))   // main loop, or left-over bz
    f0[F_CBZ] -= ( px*( fx[F_EY]-f0[F_EY] ) - py*( fy[F_EX]-f0[F_EX] ) );
}

// load_interpolator_array_kokkos: one interpolator per voxel, x, y, z in [1, n]
kernel void load_interpolator(device float*        interp [[buffer(0)]],
                              device const float*  f      [[buffer(1)]],
                              constant FieldParams& G     [[buffer(2)]],
                              uint3 gid [[thread_position_in_grid]]) {
  const int x = int(gid.x) + 1, y = int(gid.y) + 1, z = int(gid.z) + 1;
  if (x > G.nx || y > G.ny || z > G.nz) return;
  const float fourth = 0.25;
  const float one_half = 0.5;   // "half" in the CPU code; a type name in Metal
  device float* pi = interp + voxel(x, y, z, G) * INTERP_VARS;
  device const float* pf0  = f + voxel(x,     y,     z,     G) * FIELD_VARS;
  device const float* pfx  = f + voxel(x + 1, y,     z,     G) * FIELD_VARS;
  device const float* pfy  = f + voxel(x,     y + 1, z,     G) * FIELD_VARS;
  device const float* pfz  = f + voxel(x,     y,     z + 1, G) * FIELD_VARS;
  device const float* pfyz = f + voxel(x,     y + 1, z + 1, G) * FIELD_VARS;
  device const float* pfzx = f + voxel(x + 1, y,     z + 1, G) * FIELD_VARS;
  device const float* pfxy = f + voxel(x + 1, y + 1, z,     G) * FIELD_VARS;
  float w0, w1, w2, w3;

  w0 = pf0[F_EX]; w1 = pfy[F_EX]; w2 = pfz[F_EX]; w3 = pfyz[F_EX];
  pi[EX]       = fourth*( (w3 + w0) + (w1 + w2) );
  pi[DEXDY]    = fourth*( (w3 - w0) + (w1 - w2) );
  pi[DEXDZ]    = fourth*( (w3 - w0) - (w1 - w2) );
  pi[D2EXDYDZ] = fourth*( (w3 + w0) - (w1 + w2) );

  w0 = pf0[F_EY]; w1 = pfz[F_EY]; w2 = pfx[F_EY]; w3 = pfzx[F_EY];
  pi[EY]       = fourth*( (w3 + w0) + (w1 + w2) );
  pi[DEYDZ]    = fourth*( (w3 - w0) + (w1 - w2) );
  pi[DEYDX]    = fourth*( (w3 - w0) - (w1 - w2) );
  pi[D2EYDZDX] = fourth*( (w3 + w0) - (w1 + w2) );

  w0 = pf0[F_EZ]; w1 = pfx[F_EZ]; w2 = pfy[F_EZ]; w3 = pfxy[F_EZ];
  pi[EZ]       = fourth*( (w3 + w0) + (w1 + w2) );
  pi[DEZDX]    = fourth*( (w3 - w0) + (w1 - w2) );
  pi[DEZDY]    = fourth*( (w3 - w0) - (w1 - w2) );
  pi[D2EZDXDY] = fourth*( (w3 + w0) - (w1 + w2) );

  w0 = pf0[F_CBX]; w1 = pfx[F_CBX];
  pi[CBX]    = one_half*( w1 + w0 );
  pi[DCBXDX] = one_half*( w1 - w0 );

  w0 = pf0[F_CBY]; w1 = pfy[F_CBY];
  pi[CBY]    = one_half*( w1 + w0 );
  pi[DCBYDY] = one_half*( w1 - w0 );

  w0 = pf0[F_CBZ]; w1 = pfz[F_CBZ];
  pi[CBZ]    = one_half*( w1 + w0 );
  pi[DCBZDZ] = one_half*( w1 - w0 );
}

// clear_jf_kokkos: zero jfx, jfy, jfz in every voxel
kernel void clear_jf(device float* f [[buffer(0)]],
                     constant uint& nv [[buffer(1)]],
                     uint v [[thread_position_in_grid]]) {
  if (v >= nv) return;
  device float* f0 = f + ulong(v) * FIELD_VARS;
  f0[F_JFX] = 0;
  f0[F_JFY] = 0;
  f0[F_JFZ] = 0;
}

// Compact currents (see add_current in advance_p.metal): move each voxel's
// jx, jy, jz from the compact array into its field record, storing them
// (P[1] = 0: the step's first currents, replacing clear_jf) or adding them
// (P[1] = 1), and zero the compact array for the next step.
kernel void unload_currents(device float* f    [[buffer(0)]],
                            device float* jacc [[buffer(1)]],
                            constant uint* P   [[buffer(2)]],
                            uint v [[thread_position_in_grid]]) {
  if (v >= P[0]) return;
  device float* f0 = f + ulong(v) * FIELD_VARS;
  device float* j0 = jacc + ulong(v) * 4;
  if (P[1]) {
    f0[F_JFX] += j0[0];
    f0[F_JFY] += j0[1];
    f0[F_JFZ] += j0[2];
  } else {
    f0[F_JFX] = j0[0];
    f0[F_JFY] = j0[1];
    f0[F_JFZ] = j0[2];
  }
  j0[0] = 0;
  j0[1] = 0;
  j0[2] = 0;
}
