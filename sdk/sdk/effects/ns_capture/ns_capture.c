/* NS Capture 0.1.0 (N->S group 9, own coprocessor program with a long post filter; analysis/firmware/NS_SLOT.md).
 * Content record "GP5N" version 2 (ns_record.py):
 *   +0 "GP5N"  +4 u32 2  +8 u32 flags (0)  +12 f32 drive  +16 f32 bias  +20 f32 level
 *   +24 pre_a[5]  +44 pre_b[5]  +64 post_a[5]  +84 post_b[5]   (b0 b1 b2 a1 a2, a0 = 1)
 *   +104 u32 taps n (0..NS_TAPS_MAX; 0 = unit impulse)  +108 f32 scale  +112 i16 h[n] (h[k] = scale * q[k] / 32768)
 * Other records (stock SnapTones, empty slots, other versions) leave the slot bypassed: ours only, by design.
 * init: r0 = params, r1 = &content pointer (group-9 init ABI). It writes the FFT twiddles and the filter spectra
 * H_p = FFT128([h_p, 0]) / 128 (bins 0..64) into this slot's program memory above the code, as stock N->S does
 * for its FIR128. Knobs as NS Basic: Gain, VOL, Bass 120 Hz shelf, Middle 700 Hz peak, Treble 3 kHz shelf. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#include "copro_cells.h"
#endif
#include "gp50_biquad.h"
#include "ns_tw.h"
#ifdef GP50_NATIVE_TEST
#undef GP50_INIT
#undef GP50_PROCESS
#define GP50_INIT
#define GP50_PROCESS
#endif
#ifndef NS_CELL
#define NS_CELL(i) ((volatile float *)(0x28000000u + 4u * (i)))
#endif
#ifndef NS_PROG
#define NS_PROG(pc) ((volatile float *)(0x28004000u + 4u * (pc)))
#endif
/* Must match program.py (checked by sdk/test_ns_capture.py). */
#define NS_PARTS 11u
#define NS_TAPS_MAX (64u * NS_PARTS)
#define NS_TW_PC 0x7cau
#define NS_SPEC_PC 0x86au
#define NS_MAGIC 0x4e355047u   /* "GP5N" */
#define NS_INLINE static inline __attribute__((always_inline))

static float last[5];
static float base_drive, base_level;
static uint32_t designed, valid;
static float fre[128], fim[128];

NS_INLINE float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
NS_INLINE uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
NS_INLINE float rdf(const uint8_t *p) { union { uint32_t u; float f; } v = { .u = rd32(p) }; return v.f; }
NS_INLINE int32_t rd16(const uint8_t *p) { return (int16_t)((uint16_t)p[0] | (uint16_t)p[1] << 8); }
NS_INLINE void put_biquad(uint32_t cell, float b0, float b1, float b2, float a1, float a2) {
 volatile float *t = NS_CELL(cell); t[0] = b0; t[1] = b1; t[2] = b2; t[3] = a1; t[4] = a2;
}
NS_INLINE void put_coeffs(uint32_t cell, const uint8_t *p) { put_biquad(cell, rdf(p), rdf(p + 4), rdf(p + 8), rdf(p + 12), rdf(p + 16)); }
NS_INLINE void put_design(uint32_t cell, gp50_biquad b) { put_biquad(cell, b.b0, b.b1, b.b2, b.a1, b.a2); }
NS_INLINE void zero_cells(uint32_t cell, uint32_t n) { volatile float *t = NS_CELL(cell); for (uint32_t i = 0; i < n; ++i) t[i] = 0.0f; }

/* In-place radix-2 DIT FFT of fre/fim (forward, e^-i), the same structure as sdk/copro/fft.fft128. */
NS_INLINE void fft128(void) {
 for (uint32_t i = 0; i < 128u; ++i) {
  uint32_t j = 0, v = i;
  for (uint32_t b = 0; b < 7u; ++b) { j = j << 1 | (v & 1u); v >>= 1; }
  if (i < j) { float t = fre[i]; fre[i] = fre[j]; fre[j] = t; t = fim[i]; fim[i] = fim[j]; fim[j] = t; }
 }
 for (uint32_t half = 1; half < 128u; half <<= 1) {
  uint32_t step = 64u / half;
  for (uint32_t j = 0; j < half; ++j) {
   float wr = ns_tw[j * step], s = ns_tw[j * step + 96u];
   for (uint32_t k = j; k < 128u; k += 2u * half) {
    uint32_t q = k + half;
    float tr = wr * fre[q] + s * fim[q], ti = wr * fim[q] - s * fre[q];
    fre[q] = fre[k] - tr; fim[q] = fim[k] - ti; fre[k] += tr; fim[k] += ti;
   }
  }
 }
}

GP50_INIT void ns_capture_init(const float *p, const uint8_t *const *content) {
 (void)p;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE) = 0;
 *NS_CELL(COPRO_CELL_ONE) = 1.0f; *NS_CELL(COPRO_CELL_NONE) = -1.0f;
 *NS_CELL(COPRO_CELL_C15) = 1.5f; *NS_CELL(COPRO_CELL_C05) = 0.5f;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_STATE) = 0; *NS_CELL(COPRO_CELL_ZERO) = 0.0f;
 const uint32_t bq[7] = { COPRO_CELL_PRE_A, COPRO_CELL_PRE_B, COPRO_CELL_POST_A, COPRO_CELL_POST_B,
                          COPRO_CELL_BASS, COPRO_CELL_MID, COPRO_CELL_TREBLE };
 for (uint32_t i = 0; i < 7u; ++i) { put_design(bq[i], gp50_eq_flat()); zero_cells(bq[i] + 5u, 4u); }
 zero_cells(COPRO_CELL_HIST, 64u); zero_cells(COPRO_CELL_ACC, 130u); zero_cells(COPRO_CELL_BUF, 256u);
 zero_cells(COPRO_CELL_FDL, 130u * NS_PARTS);
 volatile float *tw = NS_PROG(NS_TW_PC);
 for (uint32_t i = 0; i < 160u; ++i) tw[i] = ns_tw[i];
 base_drive = 1.0f; base_level = 1.0f; *NS_CELL(COPRO_CELL_BIAS) = 0.0f;
 valid = 0; designed = 0;
 const uint8_t *r = content ? *content : 0;
 uint32_t n = 0;
 if (r && rd32(r) == NS_MAGIC && rd32(r + 4) == 2u) { n = rd32(r + 104); if (n <= NS_TAPS_MAX) valid = 1; }
 float scale = valid ? rdf(r + 108) * (1.0f / 32768.0f) : 0.0f;
 volatile float *spec = NS_PROG(NS_SPEC_PC);
 for (uint32_t part = 0; part < NS_PARTS; ++part) {
  for (uint32_t k = 0; k < 128u; ++k) {
   uint32_t t = 64u * part + k;
   float h = 0.0f;
   if (valid && k < 64u) h = n ? (t < n ? scale * (float)rd16(r + 112u + 2u * t) : 0.0f) : (t == 0u ? 1.0f : 0.0f);
   fre[k] = h; fim[k] = 0.0f;
  }
  fft128();
  for (uint32_t k = 0; k < 65u; ++k) { spec[130u * part + 2u * k] = fre[k] * (1.0f / 128.0f); spec[130u * part + 2u * k + 1u] = fim[k] * (1.0f / 128.0f); }
 }
 if (!valid) return;
 base_drive = rdf(r + 12); base_level = rdf(r + 20);
 *NS_CELL(COPRO_CELL_BIAS) = clampf(rdf(r + 16), -1.0f, 1.0f);
 put_coeffs(COPRO_CELL_PRE_A, r + 24); put_coeffs(COPRO_CELL_PRE_B, r + 44);
 put_coeffs(COPRO_CELL_POST_A, r + 64); put_coeffs(COPRO_CELL_POST_B, r + 84);
}

GP50_PROCESS void ns_capture_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 if (!designed || p[0] != last[0] || p[1] != last[1] || p[2] != last[2] || p[3] != last[3] || p[4] != last[4]) {
  for (uint32_t i = 0; i < 5u; ++i) last[i] = p[i];
  designed = 1;
  float bias = *NS_CELL(COPRO_CELL_BIAS);
  *NS_CELL(COPRO_CELL_DRIVE) = base_drive * gp50_eq_exp2((clampf(p[0], 0, 100) - 50.0f) * 0.08f);
  *NS_CELL(COPRO_CELL_DC) = bias * (1.5f - 0.5f * bias * bias);
  *NS_CELL(COPRO_CELL_LEVEL) = base_level * gp50_eq_exp2((clampf(p[1], 0, 100) - 50.0f) * 0.04f);
  put_design(COPRO_CELL_BASS, gp50_eq_low_shelf(120.0f, (clampf(p[2], 0, 100) - 50.0f) * 0.24f));
  put_design(COPRO_CELL_MID, gp50_eq_peak(700.0f, (clampf(p[3], 0, 100) - 50.0f) * 0.24f, 0.7f));
  put_design(COPRO_CELL_TREBLE, gp50_eq_high_shelf(3000.0f, (clampf(p[4], 0, 100) - 50.0f) * 0.24f));
 }
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE) = (*enable && valid) ? 1u : 0u;   /* last, as stock */
}
