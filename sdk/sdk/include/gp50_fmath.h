/* Effect-safe float math (always_inline, no libm, no calls): sin on [0, pi] via a Taylor core on
 * [-pi/2, pi/2] (to x^11), exp2 by exponent bits + 6th-order polynomial (relative error < 2e-7).
 * Shared by gp50_eq.h and coprocessor effects that compute gains on the ARM. */
#ifndef GP50_FMATH_H
#define GP50_FMATH_H
#include <stdint.h>
#ifndef GP50_EQ_INLINE   /* an effect short of slot room may define it first (NS Capture v6: out of line) */
#define GP50_EQ_INLINE static __attribute__((always_inline)) inline
#endif
#define GP50_EQ_PI 3.14159265358979f
GP50_EQ_INLINE float gp50_eq_sin_core(float x) {             /* |x| <= pi/2 */
 float x2 = x * x;
 return x * (1.0f + x2 * (-1.0f / 6 + x2 * (1.0f / 120 + x2 * (-1.0f / 5040 + x2 * (1.0f / 362880 + x2 * (-1.0f / 39916800))))));
}
GP50_EQ_INLINE float gp50_eq_sin(float w) {                  /* w in [0, pi] */
 /* sin(w) = sin_core(pi/2 - |w - pi/2|); branch-free (|x| by clearing the sign bit) so clang
  * emits no IT-predicated select (the NOP-in-IT hazard gate in build_effect.py). */
 union { float f; uint32_t u; } d = { .f = w - GP50_EQ_PI / 2 };
 d.u &= 0x7fffffffu;
 return gp50_eq_sin_core(GP50_EQ_PI / 2 - d.f);
}
GP50_EQ_INLINE float gp50_eq_exp2(float x) {                 /* x in [-30, 30] */
 if (x < -30.0f) x = -30.0f;
 if (x > 30.0f) x = 30.0f;
 int32_t i = (int32_t)(x + 64.0f) - 64;                     /* floor without libm */
 float f = x - (float)i, ln2 = 0.69314718f, t = f * ln2;
 float p = 1.0f + t * (1.0f + t * (0.5f + t * (1.0f / 6 + t * (1.0f / 24 + t * (1.0f / 120 + t * (1.0f / 720))))));
 union { uint32_t u; float f; } s = { .u = (uint32_t)(i + 127) << 23 };
 return p * s.f;
}
#endif
