/* Soft Amp 0.1.0 (AMP group, own coprocessor program): drive into a smooth cubic soft clipper and
 * a tone shelf. Knobs: 0 Drive 0..100 -> x1..x32 (log), 1 Tone 0..100 -> high shelf -12..+6 dB at
 * 1.5 kHz, 2 VOL 0..100 (50 = unity, x0.02). Coefficients designed only when a knob changes.
 * Not loaded while N->S is enabled (N->S occupies the AMP and CAB slots). */
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
#ifndef AMP_CELL
#define AMP_CELL(i) ((volatile float *)(0x28000000u + 4u * (i)))
#endif
static float last[3];
static uint32_t designed;
static inline __attribute__((always_inline)) float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
GP50_INIT void soft_amp_init(const float *p) {
 (void)p;
 *(volatile uint32_t *)AMP_CELL(COPRO_CELL_ENABLE) = 0;
 *AMP_CELL(COPRO_CELL_ONE) = 1.0f; *AMP_CELL(COPRO_CELL_NONE) = -1.0f;
 *AMP_CELL(COPRO_CELL_C15) = 1.5f; *AMP_CELL(COPRO_CELL_C05) = 0.5f;
 *AMP_CELL(COPRO_CELL_GAIN) = 1.0f; *AMP_CELL(COPRO_CELL_LEVEL) = 0.0f;
 volatile float *t = AMP_CELL(COPRO_CELL_TONE);
 t[0] = 1; t[1] = 0; t[2] = 0; t[3] = 0; t[4] = 0; t[5] = 0; t[6] = 0; t[7] = 0; t[8] = 0;
 designed = 0;
}
GP50_PROCESS void soft_amp_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 if (!designed || p[0] != last[0] || p[1] != last[1] || p[2] != last[2]) {
  last[0] = p[0]; last[1] = p[1]; last[2] = p[2]; designed = 1;
  *AMP_CELL(COPRO_CELL_GAIN) = gp50_eq_exp2(clampf(p[0], 0, 100) * 0.05f);       /* 1..32 */
  *AMP_CELL(COPRO_CELL_LEVEL) = clampf(p[2], 0, 100) * 0.02f;
  gp50_biquad b = gp50_eq_high_shelf(1500.0f, -12.0f + clampf(p[1], 0, 100) * 0.18f);
  volatile float *t = AMP_CELL(COPRO_CELL_TONE);
  t[0] = b.b0; t[1] = b.b1; t[2] = b.b2; t[3] = b.a1; t[4] = b.a2;
 }
 *(volatile uint32_t *)AMP_CELL(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;   /* last, as stock */
}
