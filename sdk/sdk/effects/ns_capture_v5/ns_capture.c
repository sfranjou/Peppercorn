/* NS Capture 0.5.0 (N->S group 9): + USER PROGRAMS (GP5P records, analysis/firmware/USER_PROGRAMS.md): the record's
 *   coprocessor code is validated here (gp5p_validate.h, = sdk/copro/gp5p.py), CRC-checked, copied to program memory at
 *   GP5P_USER_PC and run instead of our chains; knobs map to user cells; a watchdog bypasses the slot if the coprocessor
 *   is still busy at block start (overrun). Error code in cell UERR (code | word << 8; 0xff = watchdog).
 * NS Capture 0.4.0 (N->S group 9): our own program for OUR records (GP5N v2, v3) and STOCK SnapTone records (VTSI).
 *   GP5N v3 = the VTSI structure with a longer post filter (fits from scripts/tone_capture, WH params): +0 "GP5N" +4 u32 3
 *     +8 flags +12 biquad A[5] +32 biquad B[5] (f32) +52 clipper p1..p4 (f32) +68 FIR128 (f32, 512 B) +580 u32 post taps n
 *     (1..NS_TAPS_MAX) +584 f32 scale +588 i16 h[n]; runs the VTSI chain (MODE 1) with ceil(n/64) partitions.
 * analysis/firmware/NS_SLOT.md; coprocessor program sdk/effects/ns_capture_v3/program.py (MODE cell selects the chain).
 *   GP5N v2 (ns_record.py): +0 "GP5N" +4 u32 2 +8 flags +12 drive +16 bias +20 level, 4 biquads at +24/+44/+64/+84,
 *     +104 u32 taps n (0..NS_TAPS_MAX; 0 = unit impulse) +108 f32 scale +112 i16 h[n]. Knobs as NS Basic.
 *   VTSI (stock SnapTone, 2,696 B; layout DSP_COPROCESSOR.md section 4 / UPLOAD_PATH_017.md): +0x18 biquad A and +0x40
 *     biquad B as 5 float64 (b0 b1 b2 a1 a2), +0x68 4 float32 clipper (p1 +sat, p2 -sat, p3 slope+, p4 slope-),
 *     +0x88 FIR128, +0x288 FIR512 (float32). "Empty" (u32 words 6..25 sum to 0) bypasses. Knobs as the stock
 *     N->S (vtsi_render.py): Gain -> gain/100 ramped 1/4410 per sample, VOL -> vol/100 * 2.5119, Treble 1600 Hz
 *     shelf, Middle 800 Hz peak, Bass 125 Hz peak (Q 1/sqrt2), (k - 50) * 0.12 dB. Our own 40-tap low-pass (ns_lpf.h).
 * Anything else bypasses. init: r0 = params, r1 = &content pointer (group-9 init ABI). */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#include "copro_cells.h"
#endif
#include "gp50_biquad.h"
#include "ns_tw.h"
#include "ns_lpf.h"
#include "gp5p_validate.h"
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
/* Must match program.py (checked by sdk/test_ns_capture_v3.py). */
#define NS_PARTS_MAX 11u
#define NS_TAPS_MAX (64u * NS_PARTS_MAX)
#define NS_TW_PC 0x7cau
#define NS_SPEC_PC 0x86au
#define NS_MAGIC 0x4e355047u   /* "GP5N" */
#define NS_VTSI 0x49535456u    /* "VTSI" */
#define NS_GP5P 0x50355047u    /* "GP5P" */
#define NS_UERR 0x3a6u         /* shares VLEVEL's cell: VLEVEL is unused in user mode */
#define COPRO_RUN_REG 0x28008000u
#define COPRO_STATUS_REG 0x28008040u   /* bit 1 = busy (Probe watchdog, copro_probe4.c) */
#define NS_INLINE static inline __attribute__((always_inline))

static float last[5];
static float base_drive, base_level;
static uint32_t designed, valid, mode, umode;
static uint16_t kcell[5], kkind[5];
static float klo[5], khi[5], kexp[5];
/* FFT scratch shares the validator's cache (never used together: user records skip the spectra). */
#define fre ((float *)gp5p_cache)
#define fim ((float *)gp5p_cache + 128)

NS_INLINE float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
NS_INLINE uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
NS_INLINE float asf(uint32_t u) { union { uint32_t u; float f; } v = { .u = u }; return v.f; }
NS_INLINE float rdf(const uint8_t *p) { return asf(rd32(p)); }
NS_INLINE int32_t rd16(const uint8_t *p) { return (int16_t)((uint16_t)p[0] | (uint16_t)p[1] << 8); }
/* float64 bit pattern -> float32, round to nearest even, integer only (no double-precision hardware or library). */
NS_INLINE float rdd(const uint8_t *p) {
 uint32_t lo = rd32(p), hi = rd32(p + 4), sign = hi & 0x80000000u;
 int32_t e = (int32_t)(hi >> 20 & 0x7ffu) - 1023 + 127;
 uint32_t m = (hi & 0xfffffu) << 3 | lo >> 29, rest = lo & 0x1fffffffu;   /* 23 mantissa bits + 29 dropped bits */
 if ((hi & 0x7fffffffu) == 0 && lo == 0) return asf(sign);
 if (e >= 255) return asf(sign | 0x7f800000u);
 if (e <= 0) return asf(sign);                                            /* below float normal range: flush */
 if (rest > 0x10000000u || (rest == 0x10000000u && (m & 1u))) { m++; if (m == 0x800000u) { m = 0; e++; if (e >= 255) return asf(sign | 0x7f800000u); } }
 return asf(sign | (uint32_t)e << 23 | m);
}
NS_INLINE void put_biquad(uint32_t cell, float b0, float b1, float b2, float a1, float a2) {
 volatile float *t = NS_CELL(cell); t[0] = b0; t[1] = b1; t[2] = b2; t[3] = a1; t[4] = a2;
}
NS_INLINE void put_coeffs(uint32_t cell, const uint8_t *p) { put_biquad(cell, rdf(p), rdf(p + 4), rdf(p + 8), rdf(p + 12), rdf(p + 16)); }
NS_INLINE void put_coeffs64(uint32_t cell, const uint8_t *p) { put_biquad(cell, rdd(p), rdd(p + 8), rdd(p + 16), rdd(p + 24), rdd(p + 32)); }
NS_INLINE void put_design(uint32_t cell, gp50_biquad b) { put_biquad(cell, b.b0, b.b1, b.b2, b.a1, b.a2); }
NS_INLINE void zero_cells(uint32_t cell, uint32_t n) { volatile float *t = NS_CELL(cell); for (uint32_t i = 0; i < n; ++i) t[i] = 0.0f; }

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

/* h(t) for the long filter: GP5N int16 taps or VTSI float32 FIR512. */
static uint32_t v3rec;
NS_INLINE float long_tap(const uint8_t *r, uint32_t t, uint32_t n, float scale) {
 if (!valid) return 0.0f;
 if (v3rec) return t < n ? scale * (float)rd16(r + 588u + 2u * t) : 0.0f;
 if (mode) return t < 512u ? rdf(r + 0x288u + 4u * t) : 0.0f;
 return n ? (t < n ? scale * (float)rd16(r + 112u + 2u * t) : 0.0f) : (t == 0u ? 1.0f : 0.0f);
}


/* GP5P: validate and install a user program. Returns 1 when installed (umode), else writes the error and returns 0. */
NS_INLINE uint32_t install_user(const uint8_t *r) {
 uint32_t err = E_OK, pc = 0, bound = 0;
 uint32_t ncode = (uint32_t)r[16] | (uint32_t)r[17] << 8, ndata = (uint32_t)r[18] | (uint32_t)r[19] << 8;
 uint32_t base = (uint32_t)r[20] | (uint32_t)r[21] << 8, nzero = (uint32_t)r[22] | (uint32_t)r[23] << 8;
 if (rd32(r + 4) != 1u) err = E_MAGIC;
 else if (ncode < 2u || ncode > GP5P_MAX_WORDS || ncode + ndata > 642u) err = E_SIZE;
 else if (GP5P_USER_LO + base + ndata + nzero > GP5P_USER_HI) err = E_ADDRESS;
 if (err == E_OK) {                                     /* CRC-32 (reflected 0xEDB88320) of the code + data words */
  uint32_t crc = 0xffffffffu, len = 4u * (ncode + ndata);
  for (uint32_t i = 0; i < len; ++i) { crc ^= r[128u + i]; for (uint32_t k = 0; k < 8u; ++k) crc = crc >> 1 ^ (0xedb88320u & (0u - (crc & 1u))); }
  if ((crc ^ 0xffffffffu) != rd32(r + 12)) err = E_CRC;
 }
 if (err == E_OK) {
  if ((uint32_t)(uintptr_t)r & 3u) err = E_SIZE;                 /* the code is validated in place (word aligned) */
  else err = gp5p_validate((const uint32_t *)(r + 128u), ncode, 60000u, &bound, &pc);
 }
 for (uint32_t i = 0; err == E_OK && i < 5u; ++i) {
  const uint8_t *k = r + 32u + 16u * i; kcell[i] = (uint16_t)((uint32_t)k[0] | (uint32_t)k[1] << 8); kkind[i] = (uint16_t)((uint32_t)k[2] | (uint32_t)k[3] << 8);
  klo[i] = rdf(k + 4); khi[i] = rdf(k + 8); kexp[i] = rdf(k + 12);
  if (kkind[i] > 3u || (kkind[i] && GP5P_USER_LO + kcell[i] >= GP5P_USER_HI)) err = E_ADDRESS;
 }
 if (err != E_OK) { *(volatile uint32_t *)NS_CELL(NS_UERR) = err | pc << 8; return 0; }
 volatile uint32_t *prog = (volatile uint32_t *)NS_PROG(GP5P_USER_PC), *cells = (volatile uint32_t *)NS_CELL(GP5P_USER_LO + base);
 for (uint32_t i = 0; i < ncode; ++i) prog[i] = rd32(r + 128u + 4u * i);
 for (uint32_t i = 0; i < ndata; ++i) cells[i] = rd32(r + 128u + 4u * (ncode + i));
 for (uint32_t i = 0; i < nzero; ++i) cells[ndata + i] = 0u;
 *(volatile uint32_t *)NS_CELL(NS_UERR) = 0;
 return 1;
}

GP50_INIT void ns_capture_init(const float *p, const uint8_t *const *content) {
 (void)p;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE) = 0;
 *NS_CELL(COPRO_CELL_ONE) = 1.0f; *NS_CELL(COPRO_CELL_NONE) = -1.0f;
 *NS_CELL(COPRO_CELL_C15) = 1.5f; *NS_CELL(COPRO_CELL_C05) = 0.5f;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_STATE) = 0; *NS_CELL(COPRO_CELL_ZERO) = 0.0f;
 *NS_CELL(COPRO_CELL_VLEVEL) = 1.0f;
 const uint32_t bq[9] = { COPRO_CELL_PRE_A, COPRO_CELL_PRE_B, COPRO_CELL_POST_A, COPRO_CELL_POST_B,
                          COPRO_CELL_BASS, COPRO_CELL_MID, COPRO_CELL_TREBLE, COPRO_CELL_BQA, COPRO_CELL_BQB };
 for (uint32_t i = 0; i < 9u; ++i) { put_design(bq[i], gp50_eq_flat()); zero_cells(bq[i] + 5u, 4u); }
 zero_cells(COPRO_CELL_HIST, 64u); zero_cells(COPRO_CELL_ACC, 130u); zero_cells(COPRO_CELL_BUF, 256u);
 zero_cells(COPRO_CELL_FDL, 130u * NS_PARTS_MAX); zero_cells(COPRO_CELL_T128, 128u); zero_cells(COPRO_CELL_H128, 128u + 63u);
 zero_cells(COPRO_CELL_OS, 39u + 256u); *NS_CELL(COPRO_CELL_PREV) = 0.0f;
 volatile float *lpf = NS_CELL(COPRO_CELL_LPF);
 for (uint32_t j = 0; j < 40u; ++j) lpf[j] = ns_lpf[39u - j];              /* reversed for the dot word */
 *NS_CELL(COPRO_CELL_THIRD) = 1.0f / 3.0f; *NS_CELL(COPRO_CELL_TWOTHIRD) = 2.0f / 3.0f;
 *NS_CELL(COPRO_CELL_ZMIN) = -2047.0f; *NS_CELL(COPRO_CELL_INV1024) = 1.0f / 1024.0f; *NS_CELL(COPRO_CELL_RAMPK) = 1.0f / 4410.0f;

 base_drive = 1.0f; base_level = 1.0f; *NS_CELL(COPRO_CELL_BIAS) = 0.0f;
 valid = 0; designed = 0; mode = 0; v3rec = 0; umode = 0;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_UMODE) = 0;
 const uint8_t *r = content ? *content : 0;
 uint32_t n = 0, parts = 1;
 if (r && rd32(r) == NS_MAGIC && rd32(r + 4) == 2u) { n = rd32(r + 104); if (n <= NS_TAPS_MAX) { valid = 1; parts = n ? (n + 63u) / 64u : 1u; } }
 else if (r && rd32(r) == NS_VTSI) {
  uint32_t sum = 0;
  for (uint32_t w = 6; w < 26u; ++w) sum += rd32(r + 4u * w);
  if (sum) { valid = 1; mode = 1; parts = 8u; }
 }
 else if (r && rd32(r) == NS_GP5P) { if (install_user(r)) { valid = 1; umode = 1; } }
 else if (r && rd32(r) == NS_MAGIC && rd32(r + 4) == 3u) { n = rd32(r + 580); if (n >= 1u && n <= NS_TAPS_MAX) { valid = 1; mode = 1; v3rec = 1; parts = (n + 63u) / 64u; } }
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_MODE) = mode;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_PARTS) = parts; *(volatile uint32_t *)NS_CELL(COPRO_CELL_SPAN) = 130u * parts;
 float scale = !valid ? 0.0f : v3rec ? rdf(r + 584) * (1.0f / 32768.0f) : !mode ? rdf(r + 108) * (1.0f / 32768.0f) : 0.0f;
 if (umode) { *(volatile uint32_t *)NS_CELL(COPRO_CELL_UMODE) = 1u; return; }   /* tables/spectra region now holds user code */
 volatile float *tw = NS_PROG(NS_TW_PC);
 for (uint32_t i = 0; i < 160u; ++i) tw[i] = ns_tw[i];
 volatile float *spec = NS_PROG(NS_SPEC_PC);
 for (uint32_t part = 0; part < NS_PARTS_MAX; ++part) {
  for (uint32_t k = 0; k < 128u; ++k) { fre[k] = k < 64u ? long_tap(r, 64u * part + k, n, scale) : 0.0f; fim[k] = 0.0f; }
  fft128();
  for (uint32_t k = 0; k < 65u; ++k) { spec[130u * part + 2u * k] = fre[k] * (1.0f / 128.0f); spec[130u * part + 2u * k + 1u] = fim[k] * (1.0f / 128.0f); }
 }
 if (!valid) return;
 if (mode) {
  const uint32_t nl = v3rec ? 52u : 0x68u, fir = v3rec ? 68u : 0x88u;
  if (v3rec) { put_coeffs(COPRO_CELL_BQA, r + 12); put_coeffs(COPRO_CELL_BQB, r + 32); }
  else { put_coeffs64(COPRO_CELL_BQA, r + 0x18); put_coeffs64(COPRO_CELL_BQB, r + 0x40); }
  float p1 = rdf(r + nl), p2 = rdf(r + nl + 4u), p3 = rdf(r + nl + 8u), p4 = rdf(r + nl + 12u);
  *NS_CELL(COPRO_CELL_P1) = p1; *NS_CELL(COPRO_CELL_NEGP2) = -p2; *NS_CELL(COPRO_CELL_NEGP3) = -p3; *NS_CELL(COPRO_CELL_P4) = p4;
  volatile float *t128 = NS_CELL(COPRO_CELL_T128);
  for (uint32_t j = 0; j < 128u; ++j) t128[j] = rdf(r + fir + 4u * (127u - j));     /* reversed for fir_long_block */
  float g = clampf(p[0], 0, 100) * 0.01f; *NS_CELL(COPRO_CELL_GCUR) = g; *NS_CELL(COPRO_CELL_GTGT) = g;
  return;
 }
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
  if (umode) {
   for (uint32_t i = 0; i < 5u; ++i) {
    if (!kkind[i]) continue;
    float k = clampf(p[i], 0, 100) * 0.01f, v;
    if (kkind[i] == 1u) v = klo[i] + (khi[i] - klo[i]) * k;
    else if (kkind[i] == 2u) v = klo[i] * gp50_eq_exp2(kexp[i] * k);                       /* kexp = log2(hi / lo), host */
    else v = gp50_eq_exp2((klo[i] + (khi[i] - klo[i]) * k) * 0.166096405f);                /* dB -> gain */
    *NS_CELL(GP5P_USER_LO + kcell[i]) = v;
   }
  } else if (mode) {
   *NS_CELL(COPRO_CELL_GTGT) = clampf(p[0], 0, 100) * 0.01f;
   *NS_CELL(COPRO_CELL_VLEVEL) = clampf(p[1], 0, 100) * 0.01f * 2.5118999f;
   put_design(COPRO_CELL_BASS, gp50_eq_peak(125.0f, (clampf(p[2], 0, 100) - 50.0f) * 0.12f, 0.70710678f));
   put_design(COPRO_CELL_MID, gp50_eq_peak(800.0f, (clampf(p[3], 0, 100) - 50.0f) * 0.12f, 0.70710678f));
   put_design(COPRO_CELL_TREBLE, gp50_eq_high_shelf(1600.0f, (clampf(p[4], 0, 100) - 50.0f) * 0.12f));
  } else {
   float bias = *NS_CELL(COPRO_CELL_BIAS);
   *NS_CELL(COPRO_CELL_DRIVE) = base_drive * gp50_eq_exp2((clampf(p[0], 0, 100) - 50.0f) * 0.08f);
   *NS_CELL(COPRO_CELL_DC) = bias * (1.5f - 0.5f * bias * bias);
   *NS_CELL(COPRO_CELL_LEVEL) = base_level * gp50_eq_exp2((clampf(p[1], 0, 100) - 50.0f) * 0.04f);
   put_design(COPRO_CELL_BASS, gp50_eq_low_shelf(120.0f, (clampf(p[2], 0, 100) - 50.0f) * 0.24f));
   put_design(COPRO_CELL_MID, gp50_eq_peak(700.0f, (clampf(p[3], 0, 100) - 50.0f) * 0.24f, 0.7f));
   put_design(COPRO_CELL_TREBLE, gp50_eq_high_shelf(3000.0f, (clampf(p[4], 0, 100) - 50.0f) * 0.24f));
  }
 }
 if (umode && valid && (*(volatile uint32_t *)COPRO_STATUS_REG & 2u)) {   /* user program overran the previous block */
  *(volatile uint32_t *)COPRO_RUN_REG = 0; *(volatile uint32_t *)COPRO_STATUS_REG = 0;
  valid = 0; *(volatile uint32_t *)NS_CELL(NS_UERR) = 0xffu;
 }
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE) = (*enable && valid) ? 1u : 0u;   /* last, as stock */
}
