/* NS Basic 0.1.0 (N->S group 9, own coprocessor program): the first own replacement of the SnapTone
 * slot (analysis/firmware/NS_SLOT.md, option A). The slot's 2,696-byte content record selects the
 * model; this effect reads its own "GP5N" format (sdk/effects/ns_basic/ns_record.py):
 *   +0 "GP5N"  +4 u32 version 1  +8 u32 flags (0)
 *   +12 f32 drive  +16 f32 bias  +20 f32 level
 *   +24 pre_a[5]  +44 pre_b[5]  +64 post_a[5]  +84 post_b[5]   (b0 b1 b2 a1 a2, a0 = 1)
 *   +104 u32 fir_taps (0..128)  +108 f32 fir[128] (h[0..n-1], rest ignored)
 * Any other record (stock VTSI, empty slot) leaves the slot bypassed (dry): ours only, by design.
 * Knobs: 0 Gain 0..100 -> drive x2^((g-50)/12.5), 1 VOL -> level x2^((v-50)/25), 2/3/4 Bass /
 * Middle / Treble -> low shelf 120 Hz, peak 700 Hz Q 0.7, high shelf 3 kHz, +-12 dB (50 = flat).
 * init: r0 = params, r1 = &content pointer (group-9 init ABI, 0x6f34). */
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
#ifndef NS_CELL
#define NS_CELL(i) ((volatile float *)(0x28000000u + 4u * (i)))
#endif
#define NS_FIR_MAX 128u
#define NS_MAGIC 0x4e355047u   /* "GP5N" little-endian */

static float last[5];
static float base_drive, base_level;
static uint32_t designed, valid;

static inline __attribute__((always_inline)) float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
static inline __attribute__((always_inline)) uint32_t rd32(const uint8_t *p) {
 return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static inline __attribute__((always_inline)) float rdf(const uint8_t *p) {
 union { uint32_t u; float f; } v = { .u = rd32(p) }; return v.f;
}
static inline __attribute__((always_inline)) void put_biquad(uint32_t cell, float b0, float b1, float b2, float a1, float a2) {
 volatile float *t = NS_CELL(cell);
 t[0] = b0; t[1] = b1; t[2] = b2; t[3] = a1; t[4] = a2;
}
static inline __attribute__((always_inline)) void put_coeffs(uint32_t cell, const uint8_t *p) {
 put_biquad(cell, rdf(p), rdf(p + 4), rdf(p + 8), rdf(p + 12), rdf(p + 16));
}
static inline __attribute__((always_inline)) void put_design(uint32_t cell, gp50_biquad b) { put_biquad(cell, b.b0, b.b1, b.b2, b.a1, b.a2); }
static inline __attribute__((always_inline)) void clear_state(uint32_t cell) {
 volatile float *t = NS_CELL(cell + 5); t[0] = 0; t[1] = 0; t[2] = 0; t[3] = 0;
}

GP50_INIT void ns_basic_init(const float *p, const uint8_t *const *content) {
 (void)p;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE) = 0;
 *NS_CELL(COPRO_CELL_ONE) = 1.0f; *NS_CELL(COPRO_CELL_NONE) = -1.0f;
 *NS_CELL(COPRO_CELL_C15) = 1.5f; *NS_CELL(COPRO_CELL_C05) = 0.5f;
 const uint32_t bq[7] = { COPRO_CELL_PRE_A, COPRO_CELL_PRE_B, COPRO_CELL_POST_A, COPRO_CELL_POST_B,
                          COPRO_CELL_BASS, COPRO_CELL_MID, COPRO_CELL_TREBLE };
 for (uint32_t i = 0; i < 7u; ++i) { put_design(bq[i], gp50_eq_flat()); clear_state(bq[i]); }
 volatile float *taps = NS_CELL(COPRO_CELL_TAPS), *hist = NS_CELL(COPRO_CELL_HIST);
 for (uint32_t i = 0; i < NS_FIR_MAX; ++i) taps[i] = 0.0f;
 for (uint32_t i = 0; i < NS_FIR_MAX + 63u; ++i) hist[i] = 0.0f;
 taps[NS_FIR_MAX - 1u] = 1.0f;                 /* identity FIR (taps stored reversed) */
 base_drive = 1.0f; base_level = 1.0f; *NS_CELL(COPRO_CELL_BIAS) = 0.0f;
 valid = 0; designed = 0;
 const uint8_t *r = content ? *content : 0;
 if (!r || rd32(r) != NS_MAGIC || rd32(r + 4) != 1u) return;
 uint32_t n = rd32(r + 104);
 if (n > NS_FIR_MAX) return;
 base_drive = rdf(r + 12); base_level = rdf(r + 20);
 float bias = clampf(rdf(r + 16), -1.0f, 1.0f);
 *NS_CELL(COPRO_CELL_BIAS) = bias;
 put_coeffs(COPRO_CELL_PRE_A, r + 24); put_coeffs(COPRO_CELL_PRE_B, r + 44);
 put_coeffs(COPRO_CELL_POST_A, r + 64); put_coeffs(COPRO_CELL_POST_B, r + 84);
 if (n) {
  taps[NS_FIR_MAX - 1u] = 0.0f;
  for (uint32_t k = 0; k < n; ++k) taps[NS_FIR_MAX - 1u - k] = rdf(r + 108 + 4u * k);   /* h[k] reversed */
 }
 valid = 1;
}

GP50_PROCESS void ns_basic_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 if (!designed || p[0] != last[0] || p[1] != last[1] || p[2] != last[2] || p[3] != last[3] || p[4] != last[4]) {
  for (uint32_t i = 0; i < 5u; ++i) last[i] = p[i];
  designed = 1;
  float drive = base_drive * gp50_eq_exp2((clampf(p[0], 0, 100) - 50.0f) * 0.08f);
  float bias = *NS_CELL(COPRO_CELL_BIAS);
  *NS_CELL(COPRO_CELL_DRIVE) = drive;
  *NS_CELL(COPRO_CELL_DC) = bias * (1.5f - 0.5f * bias * bias);
  *NS_CELL(COPRO_CELL_LEVEL) = base_level * gp50_eq_exp2((clampf(p[1], 0, 100) - 50.0f) * 0.04f);
  put_design(COPRO_CELL_BASS, gp50_eq_low_shelf(120.0f, (clampf(p[2], 0, 100) - 50.0f) * 0.24f));
  put_design(COPRO_CELL_MID, gp50_eq_peak(700.0f, (clampf(p[3], 0, 100) - 50.0f) * 0.24f, 0.7f));
  put_design(COPRO_CELL_TREBLE, gp50_eq_high_shelf(3000.0f, (clampf(p[4], 0, 100) - 50.0f) * 0.24f));
 }
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE) = (*enable && valid) ? 1u : 0u;   /* last, as stock */
}
