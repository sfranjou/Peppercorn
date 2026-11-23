/* FIR Lowpass 0.1.0 (DST group, own coprocessor program): 32-tap Hann-windowed-sinc low-pass,
 * linear phase (15.5-sample delay), unity DC gain. Knobs: 0 Cutoff 0..100 -> 500..12000 Hz (log),
 * 1 VOL 0..100 (50 = unity, x0.02). Taps are written reversed (fir_block convention) and only
 * redesigned when Cutoff changes. History cells are zeroed at init. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#include "copro_cells.h"
#endif
#include "gp50_fmath.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#ifndef FIR_CELL
#define FIR_CELL(i) ((volatile float *)(0x28000000u + 4u * (i)))
#endif
#define NTAPS 32
static float last_cut = -1.0f;
static inline __attribute__((always_inline)) float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
static inline __attribute__((always_inline)) float sin_any(float x) {      /* any x, via turns */
 float t = x * (1.0f / (2 * GP50_EQ_PI));
 int32_t i = (int32_t)(t + 1024.0f) - 1024; t -= (float)i;                 /* [0, 1) */
 return t < 0.5f ? gp50_eq_sin(2 * GP50_EQ_PI * t) : -gp50_eq_sin(2 * GP50_EQ_PI * (t - 0.5f));
}
GP50_INIT void fir_lowpass_init(const float *p) {
 *(volatile uint32_t *)FIR_CELL(COPRO_CELL_ENABLE) = 0;
 for (uint32_t k = 0; k < NTAPS + 63; k++) *FIR_CELL(COPRO_CELL_HIST + k) = 0;
 for (uint32_t k = 0; k < NTAPS; k++) *FIR_CELL(COPRO_CELL_TAPS + k) = k == NTAPS - 1 ? 1.0f : 0.0f;   /* h = delta until designed */
 *FIR_CELL(COPRO_CELL_LEVEL) = clampf(p[1], 0, 100) * 0.02f;
 last_cut = -1.0f;
}
GP50_PROCESS void fir_lowpass_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 if (p[0] != last_cut) {
  last_cut = p[0];
  float fc = 500.0f * gp50_eq_exp2(clampf(p[0], 0, 100) * 0.01f * 4.5849625f);  /* 500 * 24^(v/100) */
  float w = 2 * fc / 44100.0f, h[NTAPS], sum = 0;
  for (uint32_t k = 0; k < NTAPS; k++) {
   float m = (float)k - (NTAPS - 1) * 0.5f;                                 /* never 0 for even NTAPS */
   float sinc = sin_any(GP50_EQ_PI * w * m) / (GP50_EQ_PI * m);
   float hann = 0.5f - 0.5f * sin_any(2 * GP50_EQ_PI * (float)k / (NTAPS - 1) + GP50_EQ_PI / 2);
   h[k] = sinc * hann; sum += h[k];
  }
  float inv = 1.0f / sum;
  for (uint32_t k = 0; k < NTAPS; k++) *FIR_CELL(COPRO_CELL_TAPS + k) = h[NTAPS - 1 - k] * inv;
 }
 *FIR_CELL(COPRO_CELL_LEVEL) = clampf(p[1], 0, 100) * 0.02f;
 *(volatile uint32_t *)FIR_CELL(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;
}
