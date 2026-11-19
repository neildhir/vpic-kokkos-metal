#ifndef _vpic_metal_field_check_h_
#define _vpic_metal_field_check_h_

// Validation for the Metal field kernels (VPIC_METAL_FIELDS_CHECK=1): run the
// CPU and the GPU version of a kernel from the same state and require the same
// result, bit for bit. Field kernels have no atomics or reductions, so any
// difference is a bug, with one exception: Apple GPUs flush denormal floats
// (magnitude below FLT_MIN, about 1.2e-38) to zero where the CPU keeps them,
// so values that are both below FLT_MIN count as flushed, not different, and
// are reported separately. Keeps the GPU result.

#include "metal_push.h"
#include "../util/util_base.h"
#include "../vpic/kokkos_helpers.h"

#include <Kokkos_Core.hpp>
#include <cfloat>
#include <cmath>
#include <cstring>

template <class View, class Cpu, class Gpu>
void vpic_metal_field_checked( const char* what, const View& out, const Cpu& cpu, const Gpu& gpu ) {
  static_assert( std::is_same_v<typename View::value_type, float>, "field arrays hold floats" );
  Kokkos::fence();
  const auto before = k_host_clone( out );
  cpu();
  Kokkos::fence();
  const auto expect = k_host_clone( out );
  Kokkos::deep_copy( out, before );
  gpu();
  const size_t n = out.span();
  const float* a = expect.data();
  const float* b = out.data();
  size_t differ = 0, flushed = 0;
  double worst = 0;
  for( size_t i=0; i<n; i++ ) {
    if( std::memcmp( &a[i], &b[i], sizeof(float) )==0 ) continue;
    if( std::fabs( a[i] )<FLT_MIN && std::fabs( b[i] )<FLT_MIN ) { flushed++; continue; }
    differ++;
    worst = std::max( worst, std::fabs( double(a[i]) - double(b[i]) ) );
  }
  static int reported = 0;
  if( differ ) ERROR(( "Metal %s check: %zu of %zu values differ from the CPU (largest difference %.3g)",
                       what, differ, n, worst ));
  if( flushed ) MESSAGE(( "Metal %s check: all %zu values match the CPU bit for bit, except %zu denormals "
                          "flushed to zero (or the reverse)", what, n, flushed ));
  else if( reported++ < 8 ) MESSAGE(( "Metal %s check: all %zu values match the CPU bit for bit", what, n ));
}

#endif // _vpic_metal_field_check_h_
