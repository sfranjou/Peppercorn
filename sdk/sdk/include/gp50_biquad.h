/* RBJ biquad designs for ARM-side effect code (always_inline, no libm, no calls), normalized
 * (a0 = 1). Used by gp50_eq.h (stock EQ program) and by own coprocessor programs
 * (sdk/copro/asm.py biquad_block). Accuracy: sdk/effects/para_eq/test_para_eq.c. */
#ifndef GP50_BIQUAD_H
#define GP50_BIQUAD_H
#include "gp50_fmath.h"
typedef struct { float b0, b1, b2, a1, a2; } gp50_biquad;   /* normalized: a0 = 1 */

/* 10^(db/40): the RBJ "A" for peaking and shelving filters. */
GP50_EQ_INLINE float gp50_eq_amp(float db) { return gp50_eq_exp2(db * (3.32192809f / 40.0f)); }

/* RBJ Audio EQ Cookbook designs, normalized by a0. f in Hz, 44.1 kHz. Written with
 * h = sin^2(w/2) (cos w = 1 - 2h) so the near-cancelling terms at low frequencies keep float32
 * precision; native test: < 0.04 dB beyond float32's own rounding of the exact design (worst near DC under
 * low shelves, where 1+a1+a2 ~ 1e-4 makes any float32 design sensitive). */
GP50_EQ_INLINE float gp50_eq_h(float w) { float t = gp50_eq_sin_core(0.5f * w); return t * t; }
GP50_EQ_INLINE gp50_biquad gp50_eq_peak(float f, float db, float q) {
 float w = 2 * GP50_EQ_PI * f / 44100.0f, s = gp50_eq_sin(w), h = gp50_eq_h(w);
 float A = gp50_eq_amp(db), alpha = s / (2 * q), ia0 = 1.0f / (1 + alpha / A), m = (-2 + 4 * h) * ia0;
 gp50_biquad b = { (1 + alpha * A) * ia0, m, (1 - alpha * A) * ia0, m, (1 - alpha / A) * ia0 };
 return b;
}
GP50_EQ_INLINE gp50_biquad gp50_eq_low_shelf(float f, float db) {   /* shelf slope S = 1 */
 float w = 2 * GP50_EQ_PI * f / 44100.0f, s = gp50_eq_sin(w), h = gp50_eq_h(w);
 float A = gp50_eq_amp(db), sq = 2 * gp50_eq_amp(db * 0.5f) * (s * 0.70710678f);   /* 2 sqrt(A) alpha */
 float p = 2 + 2 * (A - 1) * h, n = 2 * A - 2 * (A - 1) * h;        /* (A+1)-(A-1)c, (A+1)+(A-1)c */
 float ia0 = 1.0f / (n + sq);
 gp50_biquad b = { A * (p + sq) * ia0, 2 * A * (-2 + 2 * (A + 1) * h) * ia0, A * (p - sq) * ia0,
                   -2 * (2 * A - 2 * (A + 1) * h) * ia0, (n - sq) * ia0 };
 return b;
}
GP50_EQ_INLINE gp50_biquad gp50_eq_high_shelf(float f, float db) {  /* shelf slope S = 1 */
 float w = 2 * GP50_EQ_PI * f / 44100.0f, s = gp50_eq_sin(w), h = gp50_eq_h(w);
 float A = gp50_eq_amp(db), sq = 2 * gp50_eq_amp(db * 0.5f) * (s * 0.70710678f);
 float p = 2 + 2 * (A - 1) * h, n = 2 * A - 2 * (A - 1) * h;
 float ia0 = 1.0f / (p + sq);
 gp50_biquad b = { A * (n + sq) * ia0, -2 * A * (2 * A - 2 * (A + 1) * h) * ia0, A * (n - sq) * ia0,
                   2 * (-2 + 2 * (A + 1) * h) * ia0, (p - sq) * ia0 };
 return b;
}
GP50_EQ_INLINE gp50_biquad gp50_eq_flat(void) { gp50_biquad b = { 1, 0, 0, 0, 0 }; return b; }

#endif
