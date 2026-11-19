// Particle sort for Apple GPUs: a counting sort by cell, producing the order
// of VPIC's StandardSortOrder (src/particle_operations/sort.h): particles
// grouped by cell index, cells in increasing order. The order of particles
// within a cell is not deterministic (as with the CPU sort on several threads).
//
// Passes (queued in order, the particle passes in chunks of command buffers
// to stay under the macOS GPU watchdog; see metal_push.mm):
//   1. sort_count:    per-cell counts, and each particle's rank in its cell
//   2. scan_blocks / scan_add: exclusive prefix sum of the counts, giving
//                     each cell's first slot (multi-level, any number of cells)
//   3. sort_scatter:  each particle's 7 floats and cell index to its slot,
//                     in scratch arrays
//   4. a blit copies the scratch arrays back over the particle arrays

#include <metal_stdlib>
using namespace metal;

// Must match vpic_metal_sort_params in metal_push.mm
struct SortParams {
  ulong np;       // particles
  ulong stride;   // particle (i, var) is at p[var*stride + i]
  ulong first;    // first particle of this dispatch (passes are chunked)
};

kernel void sort_count(device const int*   cell   [[buffer(0)]],
                       device atomic_uint* counts [[buffer(1)]],
                       device uint*        rank   [[buffer(2)]],
                       constant SortParams& S     [[buffer(3)]],
                       uint gid [[thread_position_in_grid]]) {
  const ulong i = S.first + gid;
  if (i >= S.np) return;
  rank[i] = atomic_fetch_add_explicit(&counts[cell[i]], 1u, memory_order_relaxed);
}

// Exclusive prefix sum of data[0, n) within each threadgroup; each group's
// total goes to block_sums[group]. Threadgroups must be full multiples of the
// 32-wide SIMD group (checked on the host), and every thread runs every SIMD
// operation (no early returns: uniform control flow).
kernel void scan_blocks(device uint*        data       [[buffer(0)]],
                        device uint*        block_sums [[buffer(1)]],
                        constant uint&      n          [[buffer(2)]],
                        threadgroup uint*   sg_sums    [[threadgroup(0)]],
                        uint   gid   [[thread_position_in_grid]],
                        uint   tid   [[thread_index_in_threadgroup]],
                        uint   group [[threadgroup_position_in_grid]],
                        uint   size  [[threads_per_threadgroup]],
                        ushort lane  [[thread_index_in_simdgroup]],
                        ushort sg    [[simdgroup_index_in_threadgroup]]) {
  const uint nsg = size / 32;
  const uint v = gid < n ? data[gid] : 0u;
  uint x = simd_prefix_exclusive_sum(v);
  if (lane == 31) sg_sums[sg] = x + v;             // this SIMD group's total
  threadgroup_barrier(mem_flags::mem_threadgroup);
  // Scan the SIMD-group totals in the first SIMD group. The branch is uniform
  // within each SIMD group; the barriers stay outside it so every thread of
  // the threadgroup reaches them.
  uint offset = 0;
  if (sg == 0) offset = simd_prefix_exclusive_sum(lane < nsg ? sg_sums[lane] : 0u);
  threadgroup_barrier(mem_flags::mem_threadgroup);
  if (sg == 0 && lane < nsg) sg_sums[lane] = offset;
  threadgroup_barrier(mem_flags::mem_threadgroup);
  x += sg_sums[sg];
  if (gid < n) data[gid] = x;
  if (tid == size - 1) block_sums[group] = x + v;   // the group's total
}

// Add each threadgroup's offset (the scanned block sums) to its elements.
// Must use the same threadgroup size as scan_blocks.
kernel void scan_add(device uint*       data          [[buffer(0)]],
                     device const uint* block_offsets [[buffer(1)]],
                     constant uint&     n             [[buffer(2)]],
                     uint gid   [[thread_position_in_grid]],
                     uint group [[threadgroup_position_in_grid]]) {
  if (gid < n) data[gid] += block_offsets[group];
}

kernel void sort_scatter(device const float* p        [[buffer(0)]],
                         device const int*   cell     [[buffer(1)]],
                         device const uint*  offsets  [[buffer(2)]],
                         device const uint*  rank     [[buffer(3)]],
                         device float*       p_out    [[buffer(4)]],
                         device int*         cell_out [[buffer(5)]],
                         constant SortParams& S       [[buffer(6)]],
                         uint gid [[thread_position_in_grid]]) {
  const ulong i = S.first + gid;
  if (i >= S.np) return;
  const int c = cell[i];
  const ulong dst = ulong(offsets[c]) + rank[i];
  for (ulong v = 0; v < 7; ++v) p_out[v * S.stride + dst] = p[v * S.stride + i];
  cell_out[dst] = c;
}
