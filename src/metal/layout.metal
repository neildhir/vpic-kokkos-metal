// Array layouts shared by all Metal kernels. CMake concatenates the .metal
// files into one source, this one first, so the kernels use these names.
// They must match field_var, interpolator_var and particle_var in
// src/vpic/kokkos_helpers.h (checked by static_asserts in advance_p.cc) and
// grid.h's reflect_particles.

#include <metal_stdlib>
using namespace metal;

constant constexpr ulong FIELD_VARS = 16;
constant constexpr ulong JFX = 12, JFY = 13, JFZ = 14, RHOF = 15;
constant constexpr ulong INTERP_VARS = 18;
enum : ulong { EX = 0, DEXDY, DEXDZ, D2EXDYDZ, EY, DEYDZ, DEYDX, D2EYDZDX,
               EZ, DEZDX, DEZDY, D2EZDXDY, CBX, DCBXDX, CBY, DCBYDY, CBZ, DCBZDZ };
enum : ulong { PDX = 0, PDY, PDZ, PUX, PUY, PUZ, PW };
constant constexpr long REFLECT_PARTICLES = -1;
