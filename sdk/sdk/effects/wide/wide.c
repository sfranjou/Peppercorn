/* Wide 0.1.0 (EQ group, own coprocessor program): complementary-tilt stereo widener.
 * Left gets a high shelf of +W dB and a matching low-shelf cut; right the mirror image, from a
 * mono input. Knobs: 0 Width 0..100 -> 0..9 dB, 1 Freq 0..100 -> 300..3000 Hz (log), 2 VOL 0..100
 * (50 = unity, applied in the shelf gain). Designs only when a knob changes (in process: one copy
 * of the inlined math). Own program has no rsqrt scale, so coefficients are written as designed. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#include "copro_cells.h"
#endif
#include "gp50_biquad.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#ifndef WIDE_CELL
#define WIDE_CELL(i) ((volatile float *)(0x28000000u + 4u * (i)))
#endif
#define INLINE static __attribute__((always_inline)) inline

static float last[3];
static uint32_t designed;
INLINE float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
INLINE void put(uint32_t cell, gp50_biquad b, float gain, int reset) {
 volatile float *c = WIDE_CELL(cell);
 c[0] = b.b0 * gain; c[1] = b.b1 * gain; c[2] = b.b2 * gain; c[3] = b.a1; c[4] = b.a2;
 if (reset) { c[5] = 0; c[6] = 0; c[7] = 0; c[8] = 0; }
}
INLINE void flat(uint32_t cell, float gain) { gp50_biquad b = {1, 0, 0, 0, 0}; put(cell, b, gain, 1); }
GP50_INIT void wide_init(const float *p) {
 *(volatile uint32_t *)WIDE_CELL(COPRO_CELL_ENABLE) = 0;
 designed = 0;
 float vol = clampf(p[2], 0, 100) * 0.02f;
 flat(COPRO_CELL_BQ_L, vol); flat(COPRO_CELL_BQ_R, vol);
}
GP50_PROCESS void wide_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 if (!designed || p[0] != last[0] || p[1] != last[1] || p[2] != last[2]) {
  last[0] = p[0]; last[1] = p[1]; last[2] = p[2]; designed = 1;
  float db = clampf(p[0], 0, 100) * 0.09f, f = 300.0f * gp50_eq_exp2(clampf(p[1], 0, 100) * 0.01f * 3.32192809f);
  float vol = clampf(p[2], 0, 100) * 0.02f;
  /* High shelf +db combined with -db/2 overall keeps the mid band level: tilt around f. */
  float tilt = gp50_eq_amp(-db);                      /* 10^(-db/40): half of db in amplitude */
  put(COPRO_CELL_BQ_L, gp50_eq_high_shelf(f, db), vol * tilt, 0);
  put(COPRO_CELL_BQ_R, gp50_eq_low_shelf(f, db), vol * tilt, 0);
 }
 *(volatile uint32_t *)WIDE_CELL(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;
}
