/* Auto Pan 0.1.0 (EQ group, own coprocessor program): equal-power stereo panning by an LFO.
 * Knobs: 0 Rate 0..100 -> 0.1..10 Hz (log), 1 Depth 0..100 %, 2 VOL 0..100 (50 = unity, x0.02).
 * Per block the ARM advances the LFO, computes this block's target gains (cos/sin of a pan angle)
 * and writes the start gains (the previous targets) and per-sample steps; the coprocessor ramps
 * sample by sample (sdk/effects/auto_pan/program.py). First stereo effect: stock ARM effects after
 * the coprocessor (MOD, DLY) read only the left word, so they fold the image back to mono. */
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
#ifndef PAN_CELL
#define PAN_CELL(i) ((volatile float *)(0x28000000u + 4u * (i)))
#endif
#define INLINE static __attribute__((always_inline)) inline

static float phase, cur_l, cur_r;
INLINE float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
INLINE float sin_turn(float t) {               /* sin(2 pi t), t in [0, 1) */
 return t < 0.5f ? gp50_eq_sin(2 * GP50_EQ_PI * t) : -gp50_eq_sin(2 * GP50_EQ_PI * (t - 0.5f));
}
INLINE void targets(const float *p, float *l, float *r) {
 float pan = clampf(p[1], 0, 100) * 0.01f * sin_turn(phase);          /* -1..1 */
 float th = (pan + 1) * (GP50_EQ_PI / 4), vol = clampf(p[2], 0, 100) * 0.02f;   /* 0..pi/2 */
 *l = gp50_eq_sin(GP50_EQ_PI / 2 - th) * vol;                           /* cos */
 *r = gp50_eq_sin(th) * vol;
}
GP50_INIT void auto_pan_init(const float *p) {
 *(volatile uint32_t *)PAN_CELL(COPRO_CELL_ENABLE) = 0;
 phase = 0; cur_l = cur_r = 0.70710678f * clampf(p[2], 0, 100) * 0.02f;
 *PAN_CELL(COPRO_CELL_GL) = cur_l; *PAN_CELL(COPRO_CELL_GR) = cur_r;
 *PAN_CELL(COPRO_CELL_DGL) = 0; *PAN_CELL(COPRO_CELL_DGR) = 0;
}
GP50_PROCESS void auto_pan_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 float hz = 0.1f * gp50_eq_exp2(clampf(p[0], 0, 100) * 0.01f * 6.64385619f);   /* 0.1 * 100^(v/100) */
 phase += hz * (64.0f / 44100.0f);
 if (phase >= 1.0f) phase -= 1.0f;
 float tl, tr;
 targets(p, &tl, &tr);
 *PAN_CELL(COPRO_CELL_GL) = cur_l; *PAN_CELL(COPRO_CELL_DGL) = (tl - cur_l) * (1.0f / 64);
 *PAN_CELL(COPRO_CELL_GR) = cur_r; *PAN_CELL(COPRO_CELL_DGR) = (tr - cur_r) * (1.0f / 64);
 cur_l = tl; cur_r = tr;
 *(volatile uint32_t *)PAN_CELL(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;   /* last, as stock */
}
