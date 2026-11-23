/* Para EQ 0.1.0 (EQ group): low shelf, parametric mid, high shelf and level, on the stock EQ
 * coprocessor program (sdk/include/gp50_eq.h). Knobs (all 0..100 unless noted):
 *   0 LowF  40..400 Hz log     1 LowG  -50..50 = +-12 dB   2 MidF 200..5000 Hz log
 *   3 MidG  -50..50            4 MidQ  0.3..6 log          5 HighF 1.5..12 kHz log
 *   6 HighG -50..50            7 VOL   0..100, 50 = unity (x0.02, as stock)
 * A band is redesigned only when its knobs change (designed in process only, so the inlined math
 * exists once: init writes flat sections, the first block designs all three). Sections 3, 4 flat. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#endif
#include "gp50_eq.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#define INLINE static __attribute__((always_inline)) inline

static float last[8];
static uint32_t designed;
INLINE float knob(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
/* lo * ratio^(v/100) for v in 0..100 */
INLINE float logmap(float v, float lo, float log2_ratio) { return lo * gp50_eq_exp2(knob(v, 0, 100) * 0.01f * log2_ratio); }
INLINE float gain_db(float v) { return knob(v, -50, 50) * 0.24f; }

INLINE gp50_biquad band(uint32_t k, const float *p) {
 if (k == 0) return gp50_eq_low_shelf(logmap(p[0], 40.0f, 3.32192809f), gain_db(p[1]));
 if (k == 1) return gp50_eq_peak(logmap(p[2], 200.0f, 4.64385619f), gain_db(p[3]), logmap(p[4], 0.3f, 4.32192809f));
 return gp50_eq_high_shelf(logmap(p[5], 1500.0f, 3.0f), gain_db(p[6]));
}
INLINE int changed(uint32_t k, const float *p) {
 static const uint8_t first[3] = {0, 2, 5}, count[3] = {2, 3, 2};
 int c = !(designed >> k & 1u); designed |= 1u << k;
 for (uint32_t i = first[k]; i < (uint32_t)(first[k] + count[k]); i++) if (p[i] != last[i]) { last[i] = p[i]; c = 1; }
 return c;
}
GP50_INIT void para_eq_init(const float *p) {
 *(volatile uint32_t *)GP50_EQ_CELL(COPRO_CELL_ENABLE) = 0;      /* as stock: flag off first */
 designed = 0;
 for (uint32_t k = 0; k < 5; k++) gp50_eq_write(k, gp50_eq_flat(), 1);
 gp50_eq_level(knob(p[7], 0, 100) * 0.02f, 1);
}
GP50_PROCESS void para_eq_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 for (uint32_t k = 0; k < 3; k++) if (changed(k, p)) gp50_eq_write(k, band(k, p), 0);
 gp50_eq_level(knob(p[7], 0, 100) * 0.02f, 0);
 gp50_eq_enable(enable);                                         /* last, as stock */
}
