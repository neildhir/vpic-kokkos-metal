// Particle push for Apple GPUs: a Metal translation of advance_p_kokkos_gpu
// (src/species_advance/standard/advance_p.cc) and move_p_kokkos
// (src/species_advance/species_advance.h). The arithmetic follows those
// functions statement by statement so that results match the CPU push to
// roundoff. CMake embeds this file in the library; it is compiled at run time.

#include <metal_stdlib>
using namespace metal;

// Array layouts (FIELD_VARS, JFX, EX, PDX, ...) are in layout.metal

// Must match vpic_metal_push_params in metal_push.mm (8-byte members first)
struct PushParams {
  ulong np;               // particles in the species
  ulong stride;           // particle (i, var) is at p[var*stride + i]
  ulong max_nm;           // capacity of the mover list
  ulong first;            // first particle handled by this dispatch
  long  rangel, rangeh;   // range of local voxel ids in the neighbor table
  float qdt_2mc, cdt_dx, cdt_dy, cdt_dz, qsp, cx, cy, cz;
  int   nx, ny, nz;
  int   has_neighbors;  // 0 before VPIC has built the neighbor table
};

inline int voxel(int x, int y, int z, int nx, int ny) {
  return x + (nx + 2) * (y + (ny + 2) * z);
}

inline void add_current(device atomic_float* f, int v, ulong comp, float value) {
  atomic_fetch_add_explicit(&f[ulong(v) * FIELD_VARS + comp], value,
                            memory_order_relaxed);
}

// Charge-conserving current of one streak on the 12 edges of its cell, in the
// order jx (4 edges), jy (4), jz (4), already scaled by cx, cy, cz.
// mid: streak midpoint, disp: streak displacement, q: charge weight,
// v5: the q*dx*dy*dz/3 correction term.
struct EdgeCurrents { float j[12]; };

inline EdgeCurrents edge_currents(float3 mid, float3 disp, float q, float v5,
                                  constant PushParams& P) {
  EdgeCurrents e;
  float v0, v1, v2, v3, v4;

#define ACCUMULATE_J(X, Y, Z)                                               \
  v4  = q * disp.X;      /* q ux                                */          \
  v1  = v4 * mid.Y;      /* q ux dy                             */          \
  v0  = v4 - v1;         /* q ux (1-dy)                         */          \
  v1 += v4;              /* q ux (1+dy)                         */          \
  v4  = 1.0f + mid.Z;    /* 1+dz                                */          \
  v2  = v0 * v4;         /* q ux (1-dy)(1+dz)                   */          \
  v3  = v1 * v4;         /* q ux (1+dy)(1+dz)                   */          \
  v4  = 1.0f - mid.Z;    /* 1-dz                                */          \
  v0 *= v4;              /* q ux (1-dy)(1-dz)                   */          \
  v1 *= v4;              /* q ux (1+dy)(1-dz)                   */          \
  v0 += v5;              /* q ux [ (1-dy)(1-dz) + uy*uz/3 ]     */          \
  v1 -= v5;              /* q ux [ (1+dy)(1-dz) - uy*uz/3 ]     */          \
  v2 -= v5;              /* q ux [ (1-dy)(1+dz) - uy*uz/3 ]     */          \
  v3 += v5;              /* q ux [ (1+dy)(1+dz) + uy*uz/3 ]     */

  ACCUMULATE_J(x, y, z);
  e.j[0] = P.cx * v0; e.j[1] = P.cx * v1; e.j[2]  = P.cx * v2; e.j[3]  = P.cx * v3;
  ACCUMULATE_J(y, z, x);
  e.j[4] = P.cy * v0; e.j[5] = P.cy * v1; e.j[6]  = P.cy * v2; e.j[7]  = P.cy * v3;
  ACCUMULATE_J(z, x, y);
  e.j[8] = P.cz * v0; e.j[9] = P.cz * v1; e.j[10] = P.cz * v2; e.j[11] = P.cz * v3;
#undef ACCUMULATE_J
  return e;
}

// Add a cell's edge currents to the field array
inline void scatter_currents(device atomic_float* f, int ii, thread const EdgeCurrents& e,
                             constant PushParams& P) {
  int iii = ii;
  const int zi = iii / ((P.nx + 2) * (P.ny + 2));
  iii -= zi * (P.nx + 2) * (P.ny + 2);
  const int yi = iii / (P.nx + 2);
  const int xi = iii - yi * (P.nx + 2);
  const int ax  = voxel(xi + 1, yi,     zi,     P.nx, P.ny);
  const int ay  = voxel(xi,     yi + 1, zi,     P.nx, P.ny);
  const int az  = voxel(xi,     yi,     zi + 1, P.nx, P.ny);
  const int ayz = voxel(xi,     yi + 1, zi + 1, P.nx, P.ny);
  const int azx = voxel(xi + 1, yi,     zi + 1, P.nx, P.ny);
  const int axy = voxel(xi + 1, yi + 1, zi,     P.nx, P.ny);
  add_current(f, ii,  JFX, e.j[0]);
  add_current(f, ay,  JFX, e.j[1]);
  add_current(f, az,  JFX, e.j[2]);
  add_current(f, ayz, JFX, e.j[3]);
  add_current(f, ii,  JFY, e.j[4]);
  add_current(f, az,  JFY, e.j[5]);
  add_current(f, ax,  JFY, e.j[6]);
  add_current(f, azx, JFY, e.j[7]);
  add_current(f, ii,  JFZ, e.j[8]);
  add_current(f, ax,  JFZ, e.j[9]);
  add_current(f, ay,  JFZ, e.j[10]);
  add_current(f, axy, JFZ, e.j[11]);
}

// Performance experiments (VPIC_METAL_DEFINES, see metal_push.mm); none is
// defined in normal runs, and results with any of them are not physical:
//   VPIC_EXP_SKIP_INCELL_DEPOSIT  no current from particles that stay in their cell
//   VPIC_EXP_SKIP_MOVE_DEPOSIT    no current from move_p (cell crossers)
//   VPIC_EXP_MOVE_PLAIN_ADD       move_p adds current without atomics (racy)
//   VPIC_EXP_COUNT_CROSSERS       count particles that leave their cell (counters[3])
//   VPIC_EXP_NO_FOLD              crossers' first streak deposited by move_p, not the reduction
//   VPIC_EXP_SERIAL_ATOMICS       one lane adds a cell's 12 edge currents (previous scheme)
inline void scatter_move_currents(device atomic_float* f, int ii, thread const EdgeCurrents& e,
                                  constant PushParams& P) {
#if defined(VPIC_EXP_SKIP_MOVE_DEPOSIT)
  return;
#elif defined(VPIC_EXP_MOVE_PLAIN_ADD)
  device float* g = reinterpret_cast<device float*>(f);
  int iii = ii;
  const int zi = iii / ((P.nx + 2) * (P.ny + 2));
  iii -= zi * (P.nx + 2) * (P.ny + 2);
  const int yi = iii / (P.nx + 2);
  const int xi = iii - yi * (P.nx + 2);
  const int v[12] = {ii, voxel(xi, yi + 1, zi, P.nx, P.ny), voxel(xi, yi, zi + 1, P.nx, P.ny),
                     voxel(xi, yi + 1, zi + 1, P.nx, P.ny), ii, voxel(xi, yi, zi + 1, P.nx, P.ny),
                     voxel(xi + 1, yi, zi, P.nx, P.ny), voxel(xi + 1, yi, zi + 1, P.nx, P.ny), ii,
                     voxel(xi + 1, yi, zi, P.nx, P.ny), voxel(xi, yi + 1, zi, P.nx, P.ny),
                     voxel(xi + 1, yi + 1, zi, P.nx, P.ny)};
  for (int k = 0; k < 12; ++k) g[ulong(v[k]) * FIELD_VARS + JFX + ulong(k / 4)] += e.j[k];
#else
  scatter_currents(f, ii, e, P);
#endif
}

// One streak of a particle's track inside its current cell: the body of
// move_p_kokkos's loop up to the deposit, statement for statement. Returns the
// streak's edge currents, advances pos and disp, and sets axis (3: the track
// ends in this cell) and dir (the face direction along axis, if axis < 3).
inline EdgeCurrents streak(thread float3& pos, thread float3& disp, float q,
                           thread int& axis, thread float& dir, constant PushParams& P) {
  float3 s_mid  = pos;
  float3 s_disp = disp;
  const float3 s_dir = select(float3(-1.0f), float3(1.0f), s_disp > 0.0f);

  // Twice the fractional distance to each potential face intersection
  const float v0 = (s_disp.x == 0) ? 3.4e38f : (s_dir.x - s_mid.x) / s_disp.x;
  const float v1 = (s_disp.y == 0) ? 3.4e38f : (s_dir.y - s_mid.y) / s_disp.y;
  const float v2 = (s_disp.z == 0) ? 3.4e38f : (s_dir.z - s_mid.z) / s_disp.z;

  // Fractional length and axis of this streak (axis 3: end of the track)
  float v3 = 2;
  axis = 3;
  if (v0 < v3) { v3 = v0; axis = 0; }
  if (v1 < v3) { v3 = v1; axis = 1; }
  if (v2 < v3) { v3 = v2; axis = 2; }
  v3 *= 0.5f;

  s_disp *= v3;
  s_mid  += s_disp;
  const float v5 = q * s_disp.x * s_disp.y * s_disp.z * (1.f / 3.f);
  const EdgeCurrents e = edge_currents(s_mid, s_disp, q, v5, P);

  disp -= s_disp;                 // Remaining displacement
  pos  += s_disp + s_disp;        // New particle offset
  dir = axis < 3 ? s_dir[axis] : 0.0f;
  return e;
}

// Continue a cell crosser's move (move_p_kokkos) after a streak in cell ii
// that ended on a face (axis < 3) or at the end of the track (axis 3): cross
// into the next cell and move streak by streak, depositing current, until the
// track ends. Returns true if the particle hit a boundary this rank cannot
// handle and must go on the mover list; disp then holds the remaining
// displacement. q is the particle's charge weight (qsp * w).
inline bool move_p_continue(device float* p, device int* pidx, ulong i, float q,
                            thread float3& pos, thread float3& disp, int ii, int axis, float dir,
                            device atomic_float* f, device const long* neighbors,
                            device atomic_uint* counters, constant PushParams& P) {
  const ulong s = P.stride;
  bool keep = false;
  while (axis < 3) {
    // Put the particle exactly on the face it reached
    pos[axis] = dir;
    const int face = axis + (dir > 0 ? 3 : 0);
    if (!P.has_neighbors) {
      // No neighbor table yet (a push during deck initialisation): flag it
      // for the host, which aborts, and leave the particle on the face
      atomic_store_explicit(&counters[2], 1u, memory_order_relaxed);
      break;
    }
    const long neighbor = neighbors[6 * long(ii) + face];

    if (neighbor == REFLECT_PARTICLES) {
      // Reflect the momentum and the remaining displacement, keep moving
      p[(PUX + ulong(axis)) * s + i] = -p[(PUX + ulong(axis)) * s + i];
      disp[axis] = -disp[axis];
    } else if (neighbor < P.rangel || neighbor > P.rangeh) {
      // A boundary this rank cannot handle: record the face hit
      ii = 8 * ii + face;
      keep = true;
      break;
    } else {
      // Crossed into a local voxel: change coordinates and keep moving
      ii = int(neighbor - P.rangel);
      pos[axis] = -dir;
    }

    const EdgeCurrents e = streak(pos, disp, q, axis, dir, P);
    scatter_move_currents(f, ii, e, P);
  }

  p[PDX * s + i] = pos.x;
  p[PDY * s + i] = pos.y;
  p[PDZ * s + i] = pos.z;
  pidx[i] = ii;
  return keep;
}

// The whole move of a cell crosser, from its first streak (used by the
// VPIC_EXP_NO_FOLD experiment; normally the first streak goes into the
// in-cell reduction and the kernel calls move_p_continue).
inline bool move_p(device float* p, device int* pidx, ulong i,
                   thread float3& disp, device atomic_float* f,
                   device const long* neighbors, device atomic_uint* counters,
                   constant PushParams& P) {
  const ulong s = P.stride;
  const float q = P.qsp * p[PW * s + i];
  float3 pos = float3(p[PDX * s + i], p[PDY * s + i], p[PDZ * s + i]);
  const int ii = pidx[i];
  int axis;
  float dir;
  const EdgeCurrents e = streak(pos, disp, q, axis, dir, P);
  scatter_move_currents(f, ii, e, P);
  return move_p_continue(p, pidx, i, q, pos, disp, ii, axis, dir, f, neighbors, counters, P);
}

// Add one of a cell's 12 edge currents (index k in EdgeCurrents order) to
// the field array. In VPIC's voxel numbering the neighbours used by
// scatter_currents are fixed offsets: +1 in x, +(nx+2) in y, +(nx+2)(ny+2) in z.
inline void add_edge_current(device atomic_float* f, int ii, int k, float value,
                             constant PushParams& P) {
  const int sy = P.nx + 2, sz = (P.nx + 2) * (P.ny + 2);
  int off;
  switch (k) {   // jx: ii, ay, az, ayz; jy: ii, az, ax, azx; jz: ii, ax, ay, axy
    case 1:  off = sy;      break;
    case 2:  off = sz;      break;
    case 3:  off = sy + sz; break;
    case 5:  off = sz;      break;
    case 6:  off = 1;       break;
    case 7:  off = sz + 1;  break;
    case 9:  off = 1;       break;
    case 10: off = sy;      break;
    case 11: off = sy + 1;  break;
    default: off = 0;       break;   // 0, 4, 8: the cell itself
  }
  add_current(f, ii + off, JFX + ulong(k / 4), value);
}

// Add the currents of the streaks that lie in each lane's own cell: in-cell
// particles, and the first streak of cell crossers. Particles are sorted by
// cell, so a SIMD group's lanes span only a few cells: cell by cell, sum the
// lanes' currents with simd_sum, which leaves the sums in every lane, and let
// lanes 0-11 add one edge each (lanes cover several edges in a short group).
// That is 12 atomics per cell instead of 12 per particle, issued as one SIMD
// instruction rather than 12 in a row from one lane. On an M4 the in-cell
// atomics are still about half the push time; issuing them in parallel saved
// 9-12% of it, and folding crossers' first streaks in another 1-2%. After
// MAX_CELL_PASSES cells (unsorted particles) the remaining lanes add directly.
//
// Every lane of the SIMD group must call this (uniform control flow), with
// take_part false for lanes that have nothing to add. SIMD-group operations
// inside divergent branches or loops are not reliable: the compiler may
// evaluate them over the whole group.
inline void deposit_in_cell(device atomic_float* f, int ii, thread const EdgeCurrents& e,
                            bool take_part, ushort lane, constant PushParams& P) {
  constexpr int MAX_CELL_PASSES = 4;
  // Lanes 0..active-1 run: a grid's last SIMD group may have fewer than 12
  const ushort active = ushort(simd_sum(1u));
  bool done = !take_part;
  for (int pass = 0; pass < MAX_CELL_PASSES; ++pass) {
    if (simd_all(done)) return;
    const int cell = simd_min(done ? 0x7fffffff : ii);
    const bool mine = !done && ii == cell;
    EdgeCurrents sum;
    for (int k = 0; k < 12; ++k) sum.j[k] = simd_sum(mine ? e.j[k] : 0.0f);
#if defined(VPIC_EXP_SERIAL_ATOMICS)
    // Previous scheme, for A/B experiments: one lane adds all 12 edges
    const ushort first = simd_min(mine ? lane : ushort(0xffff));
    if (lane == first) scatter_currents(f, cell, sum, P);
#else
    for (ushort k = lane; k < 12; k += active) {   // one pass when active >= 12
      float v = sum.j[0];
      for (ushort m = 1; m < 12; ++m) v = (k == m) ? sum.j[m] : v;
      add_edge_current(f, cell, k, v, P);
    }
#endif
    done = done || mine;
  }
  if (!done) scatter_currents(f, ii, e, P);
}

kernel void advance_p(device float*         p         [[buffer(0)]],
                      device int*           pidx      [[buffer(1)]],
                      device const float*   interp    [[buffer(2)]],
                      device atomic_float*  f         [[buffer(3)]],
                      device const long*    neighbors [[buffer(4)]],
                      device float*         movers    [[buffer(5)]],
                      device ulong*         movers_i  [[buffer(6)]],
                      device float*         copies    [[buffer(7)]],
                      device int*           copies_i  [[buffer(8)]],
                      device atomic_uint*   counters  [[buffer(9)]],  // [0] movers, [1] overflow, [2] no neighbors
                      constant PushParams&  P         [[buffer(10)]],
                      uint gid [[thread_position_in_grid]],
                      ushort lane [[thread_index_in_simdgroup]]) {
  const ulong i = P.first + gid;
  const ulong s = P.stride;
  constexpr float one = 1.0f, one_third = 1.0f / 3.0f, two_fifteenths = 2.0f / 15.0f;

  // No early returns before deposit_in_cell: every lane must reach it
  const bool valid = i < P.np;
  bool inbnds = false;
  bool folded = false;   // a crosser whose first streak is in e
  int ii = 0;
  float3 pos_move = float3(0.0f);
  float q_move = 0.0f;
  int axis_move = 3;
  float dir_move = 0.0f;
  EdgeCurrents e;
  for (int k = 0; k < 12; ++k) e.j[k] = 0.0f;
  float3 disp = float3(0.0f);

  if (valid) {
    float dx = p[PDX * s + i];                     // Load position
    float dy = p[PDY * s + i];
    float dz = p[PDZ * s + i];
    ii = pidx[i];
    device const float* fi = interp + ulong(ii) * INTERP_VARS;

    const float hax = P.qdt_2mc * ((fi[EX] + dy * fi[DEXDY]) +
                                   dz * (fi[DEXDZ] + dy * fi[D2EXDYDZ]));
    const float hay = P.qdt_2mc * ((fi[EY] + dz * fi[DEYDZ]) +
                                   dx * (fi[DEYDX] + dz * fi[D2EYDZDX]));
    const float haz = P.qdt_2mc * ((fi[EZ] + dx * fi[DEZDX]) +
                                   dy * (fi[DEZDY] + dx * fi[D2EZDXDY]));
    const float cbx = fi[CBX] + dx * fi[DCBXDX];     // Interpolate B
    const float cby = fi[CBY] + dy * fi[DCBYDY];
    const float cbz = fi[CBZ] + dz * fi[DCBZDZ];

    float ux = p[PUX * s + i];                     // Load momentum
    float uy = p[PUY * s + i];
    float uz = p[PUZ * s + i];
    float q  = p[PW  * s + i];
    ux += hax;                                     // Half advance E
    uy += hay;
    uz += haz;
    float v0 = precise::divide(P.qdt_2mc, precise::sqrt(one + (ux * ux + (uy * uy + uz * uz))));
    float v1 = cbx * cbx + (cby * cby + cbz * cbz);  // Boris - scalars
    float v2 = (v0 * v0) * v1;
    float v3 = v0 * (one + v2 * (one_third + v2 * two_fifteenths));
    float v4 = precise::divide(v3, one + v1 * (v3 * v3));
    v4 += v4;
    v0 = ux + v3 * (uy * cbz - uz * cby);          // Boris - uprime
    v1 = uy + v3 * (uz * cbx - ux * cbz);
    v2 = uz + v3 * (ux * cby - uy * cbx);
    ux += v4 * (v1 * cbz - v2 * cby);              // Boris - rotation
    uy += v4 * (v2 * cbx - v0 * cbz);
    uz += v4 * (v0 * cby - v1 * cbx);
    ux += hax;                                     // Half advance E
    uy += hay;
    uz += haz;
    p[PUX * s + i] = ux;                           // Store momentum
    p[PUY * s + i] = uy;
    p[PUZ * s + i] = uz;

    v0 = precise::divide(one, precise::sqrt(one + (ux * ux + (uy * uy + uz * uz))));
    ux *= P.cdt_dx;                                // Normalised displacement
    uy *= P.cdt_dy;
    uz *= P.cdt_dz;
    ux *= v0;
    uy *= v0;
    uz *= v0;
    v0 = dx + ux;                                  // Streak midpoint
    v1 = dy + uy;
    v2 = dz + uz;
    v3 = v0 + ux;                                  // New position
    v4 = v1 + uy;
    float v5 = v2 + uz;

    inbnds = v3 <= one && v4 <= one && v5 <= one && -v3 <= one && -v4 <= one && -v5 <= one;
    if (inbnds) {
      // Common case: the particle stays in its cell
      q *= P.qsp;
      p[PDX * s + i] = v3;                         // Store new position
      p[PDY * s + i] = v4;
      p[PDZ * s + i] = v5;
      v5 = q * ux * uy * uz * one_third;           // Correction term
      e = edge_currents(float3(v0, v1, v2), float3(ux, uy, uz), q, v5, P);
    } else {
      disp = float3(ux, uy, uz);
#if !defined(VPIC_EXP_NO_FOLD)
      // A cell crosser's first streak lies in its own cell: add it with the
      // in-cell currents, and continue the move from there below
      pos_move = float3(dx, dy, dz);
      q_move = P.qsp * q;           // q is still the weight here
      e = streak(pos_move, disp, q_move, axis_move, dir_move, P);
      folded = true;
#endif
    }
  }

#if defined(VPIC_EXP_SKIP_INCELL_DEPOSIT)
  deposit_in_cell(f, ii, e, false, lane, P);
#else
  deposit_in_cell(f, ii, e, valid && (inbnds || folded), lane, P);
#endif
#if defined(VPIC_EXP_COUNT_CROSSERS)
  {
    const uint crossers = simd_sum((valid && !inbnds) ? 1u : 0u);
    if (simd_is_first() && crossers) atomic_fetch_add_explicit(&counters[3], crossers, memory_order_relaxed);
  }
#endif
  if (!valid || inbnds) return;

  // The particle leaves its cell
#if defined(VPIC_EXP_NO_FOLD)
  if (!move_p(p, pidx, i, disp, f, neighbors, counters, P)) return;
#else
  if (!move_p_continue(p, pidx, i, q_move, pos_move, disp, ii, axis_move, dir_move, f, neighbors,
                       counters, P)) return;
#endif

  // Mover list. A full list sets the overflow flag; the host aborts.
  if (atomic_load_explicit(&counters[0], memory_order_relaxed) >= P.max_nm) {
    atomic_store_explicit(&counters[1], 1u, memory_order_relaxed);
    return;
  }
  const uint nm = atomic_fetch_add_explicit(&counters[0], 1u, memory_order_relaxed);
  if (nm >= P.max_nm) {
    atomic_store_explicit(&counters[1], 1u, memory_order_relaxed);
    return;
  }
  movers[3 * ulong(nm) + 0] = disp.x;
  movers[3 * ulong(nm) + 1] = disp.y;
  movers[3 * ulong(nm) + 2] = disp.z;
  movers_i[nm] = i;
  for (ulong v = 0; v < 7; ++v) copies[7 * ulong(nm) + v] = p[v * s + i];
  copies_i[nm] = pidx[i];
}
