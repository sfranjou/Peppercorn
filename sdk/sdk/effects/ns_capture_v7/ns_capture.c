/* Latest pedal player: exactly stock VTSI + current GPTC, with native IR512
 * fusion in GPTC mode. Historical GP5N/GP5P players stay offline in the repo.
 * Stock reload copies the complete secondary before every init. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#endif
#include "copro_cells.h"
#include "gp50_biquad.h"
#include "gp50_fir_fusion.h"
#include "../ns_capture_v6/ns_tw.h"
#include "../ns_capture_v6/ns_lpf.h"
#ifdef COPRO_CELL_G_KN
#include "../../tone_core/spline_tables.h"
static const uint32_t gpts_knot_bits[33] = GPTS_KNOT_BITS, gpts_inv_bits[32] = GPTS_INV_DK_BITS;
static const uint32_t gpts_lpf_bits[40] = GPTS_LPF_CELL_BITS, gpts_bq_bits[5] = GPTS_BQ_BITS;
#endif
#ifndef NS_CELL
#define NS_CELL(i) ((volatile float *)(uintptr_t)(0x28000000u+4u*(i)))
#define NS_PROG(i) ((volatile float *)(uintptr_t)(0x28004000u+4u*(i)))
#endif
#define NS_INLINE static
/* NS_GPTC_TW_PC 0x748 retired in MOD145: the GPTC twiddle table lives in data cells COPRO_CELL_G_TW. */
#define NS_GPTC_SPEC_PC 0x7e8u
#define NS_TW_PC 0x7cau
#define NS_SPEC_PC 0x86au
#define NS_GPTC 0x43545047u
#define TC_SIZE 2696u
#ifndef COPRO_RUN_REG
#define COPRO_RUN_REG 0x28008000u
#define COPRO_STATUS_REG 0x28008040u
#endif
static union { gp50_fir_fusion_scratch fusion; float values[512]; } scratch;
#define fre (scratch.values)
#define fim (scratch.values+128)
static uint32_t valid, gmode, designed;
/* Tone state of one capture slot: record gains and the last designed Bass/Mid/Treble (seen[2..4]; the VTSI path uses
 * the main slot's seen[0..4] as its own last-parameter copy). */
typedef struct { float in_base, out_base, seen[5]; } tone_state;
typedef struct { uint16_t in, out, eq[3]; } tone_cells;
static tone_state main_tone;
#define last (main_tone.seen)
#define glast last
#define input_base (main_tone.in_base)
#define output_base (main_tone.out_base)
static const uint8_t *selected_ir;
static uint32_t selected_ir_bytes;
#ifdef COPRO_CELL_G_PAIR
/* Capture pair (2026-11-08, analysis/tone_capture/TWO_CAPTURES_20261108.md): a second GPTC record run before the
 * main one inside this program. Only without an IR: both use four partitions, the second keeps its state in the
 * main capture's unused FDL words. pair_record is set only during ns_capture_init_pair. */
static const uint8_t *pair_record;
/* 2026-11-21: DST Capture Gain/VOL/Bass/Mid/Treble (DST working parameters 1..5, read by the resident wrapper; 0 when
 * the wrapper gives none). They drive the second slot, and the main slot in DST-capture-alone mode. */
static const volatile float *dst_tone;
static uint32_t pair_on, dst_alone;
static tone_state p2_tone;
#define NS_PAIR_HOLE (COPRO_CELL_G_FDL + 520u)
/* 2026-11-21 (two-curve in both slots): most second-slot cells lie in the main capture's unused FDL words (zeroed by
 * the main install); the few placed after them (TREBLE, OUTPUT_GAIN, PREV0, STATE) are zeroed explicitly below. */
_Static_assert(COPRO_CELL_G_P2_FDL >= NS_PAIR_HOLE && COPRO_CELL_G_P2_INPUT_GAIN < COPRO_CELL_G_FDL + 1560u,
               "second-capture state must lie in the main capture's unused FDL words");
#endif
static int fused_prepare(void) {
 if(selected_ir?selected_ir_bytes!=2048u:selected_ir_bytes!=0u)return 0;
 /* Both pointers derive from one in-slot program-data address (the builder checks literal addresses; the staged
  * transport and the slot origin lie below PROGRAM_DATA_PC). Same words copied as before. */
 volatile uint32_t *base=(volatile uint32_t *)NS_PROG(NS_GPTC_SPEC_PC);
 __asm__ volatile("" : "+r"(base));
 volatile uint32_t *dst=base-(NS_GPTC_SPEC_PC-0x500u);
 const volatile uint32_t *src=base-(NS_GPTC_SPEC_PC-COPRO_STAGE_PC);
 for(uint32_t i=0;i<COPRO_STAGE_WORDS;i++)dst[i]=src[i];
 return 1;
}
static int fused_finish(const uint8_t *spectra) {
 return gp50_fir_fuse_q23(spectra,2080u,selected_ir,selected_ir_bytes,
  NS_PROG(NS_GPTC_SPEC_PC),1560u,&scratch.fusion,
  (const float *)NS_CELL(COPRO_CELL_G_TW));   /* MOD145: twiddles are data cells (fused_079 TW_IN_DATA) */
}
NS_INLINE float clampf(float v, float lo, float hi) { return v < lo ? lo : v > hi ? hi : v; }
NS_INLINE uint32_t rd32(const uint8_t *p) { return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
NS_INLINE float asf(uint32_t u) { union { uint32_t u; float f; } v = { .u = u }; return v.f; }
NS_INLINE float rdf(const uint8_t *p) { return asf(rd32(p)); }
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
NS_INLINE void put_coeffs64(uint32_t cell, const uint8_t *p) { put_biquad(cell, rdd(p), rdd(p + 8), rdd(p + 16), rdd(p + 24), rdd(p + 32)); }
NS_INLINE void put_design(uint32_t cell, gp50_biquad b) { put_biquad(cell, b.b0, b.b1, b.b2, b.a1, b.a2); }
/* One out-of-line copy of each design (v6: the always_inline designs were expanded nine times in process). */
static __attribute__((noinline)) void design_peak(uint32_t cell, float f, float db, float q) { put_design(cell, gp50_eq_peak(f, db, q)); }
static __attribute__((noinline)) void design_high_shelf(uint32_t cell, float f, float db) { put_design(cell, gp50_eq_high_shelf(f, db)); }
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

/* 2026-11-21 (MOD160): two-curve captures only (GPTC v2, sdk/tone_core/spline_record.py). GPTC v1 is superseded and
 * no longer played; stock VTSI is unchanged. Both slots (main N->S capture and the DST pair capture) run it. */
NS_INLINE int tc_finite(float x) { union { float f; uint32_t u; } v = { .f = x }; return (v.u & 0x7f800000u) != 0x7f800000u; }
NS_INLINE uint32_t tc_hash(const uint8_t *r) { uint32_t h = 2166136261u; for (uint32_t i = 0; i < TC_SIZE; i++) { if (i < 44u || i >= 48u) h = (h ^ r[i]) * 16777619u; } return h; }
/* GPTC v2 check, as spline_record.validate: geometry, checksum, scalars, finite bounded payload, zero centre ordinates,
 * zero padding. */
NS_INLINE int ts_check(const uint8_t *r) {
 if (!r || rd32(r) != NS_GPTC || rd32(r + 4) != 2u || rd32(r + 8) != TC_SIZE || rd32(r + 12) != 33u || rd32(r + 16) != 32u ||
     rd32(r + 20) != 16u || rd32(r + 24) != 256u || rd32(r + 28) || rd32(r + 32) || tc_hash(r) != rd32(r + 44)) return 0;
 float ig = rdf(r + 36), og = rdf(r + 40);
 if (!tc_finite(ig) || !tc_finite(og) || ig < 0 || ig > 4 || og < 0 || og > 8) return 0;
 for (uint32_t i = 48u; i < 2584u; i += 4u) { float x = rdf(r + i); if (!tc_finite(x) || x > 1e6f || x < -1e6f) return 0; }
 if (rd32(r + 240 + 64) || rd32(r + 372 + 64)) return 0;
 for (uint32_t i = 2584u; i < TC_SIZE; i++) if (r[i]) return 0;
 return 1;
}
NS_INLINE void tc_put(uint32_t cell, const uint8_t *r, uint32_t n) {
 volatile float *t = NS_CELL(cell);
 for (uint32_t i = 0; i < n; i++) { __asm__ volatile("" : "+r"(t)); *t++ = rdf(r); r += 4; }
}
/* Out of line so each caller passes one in-slot program address (the builder checks every literal address). */
static __attribute__((noinline)) void put_spectra520(volatile float *dst, const uint8_t *src) {
 for (uint32_t i = 0; i < 520u; i++) dst[i] = rdf(src + 4u * i);
}
/* One slot's two-curve cells: PRE, SECOND (= reversed interstage FIR), fixed biquad, segment line coefficients from the
 * ordinates in the binary32 order of sdk/tone_core/capture_spline.c (-ffp-contract=off). */
static __attribute__((noinline)) void put_two_curve(uint32_t pre, uint32_t second, uint32_t bq_cell, uint32_t ab_cell, const uint8_t *r) {
 tc_put(pre, r + 48, 32); tc_put(second, r + 176, 16);
 volatile uint32_t *bq = (volatile uint32_t *)NS_CELL(bq_cell);
 for (uint32_t i = 0; i < 5u; i++) bq[i] = gpts_bq_bits[i];
 volatile float *ab = NS_CELL(ab_cell);
 for (uint32_t k = 0; k < 2u; k++) {
  const uint8_t *v = r + 240u + 132u * k;
  for (uint32_t p = 0; p < 32u; p++) {
   union { uint32_t u; float f; } knot = { .u = gpts_knot_bits[p] }, inv = { .u = gpts_inv_bits[p] };
   float slope = (rdf(v + 4u * p + 4u) - rdf(v + 4u * p)) * inv.f;
   float product = knot.f * slope;
   ab[64u * k + 32u + p] = slope; ab[64u * k + p] = rdf(v + 4u * p) - product;
  }
 }
}
/* Returns 1 when the main record (and the pair record, if any) is valid GPTC v2 and the cells and program tables are
 * written, else 0 (nothing written). */
NS_INLINE uint32_t install_gptc(const uint8_t *r) {
#ifdef COPRO_CELL_G_PAIR
 /* r == 0 with a valid pair record: pre-only mode (a DST capture, no main capture, no IR): MAIN_OFF. */
 const uint32_t main = ts_check(r), pair = pair_record && !selected_ir && ts_check(pair_record);
 if ((!main && !(pair && !r)) || !fused_prepare()) return 0;
#else
 const uint32_t main = 1;
 if (!ts_check(r) || !fused_prepare()) return 0;
#endif
 for (uint32_t i = COPRO_CELL_G_ZERO; i < COPRO_CELL_G_TREBLE + 9u; i++) *NS_CELL(i) = 0;
 *NS_CELL(COPRO_CELL_G_ONE) = 1; *NS_CELL(COPRO_CELL_G_INV1024) = 1.0f / 1024;
 *NS_CELL(COPRO_CELL_G_THIRD) = 1.0f / 3; *NS_CELL(COPRO_CELL_G_TWOTHIRD) = 2.0f / 3;
 *NS_CELL(COPRO_CELL_G_CUTOFF_SQUARED) = .9025f;
 volatile float *tw = NS_CELL(COPRO_CELL_G_TW);                        /* MOD145: data cells, not program memory */
 for (uint32_t i = 0; i < 160u; i++) tw[i] = ns_tw[i];
 tw[32] = 0.0f; tw[96] = 0.0f;                                         /* compact_tw.h: exact cardinal zeros */
 /* Shared by both slots: knots and the fixed LPF40 (cell order). */
 volatile uint32_t *kn = (volatile uint32_t *)NS_CELL(COPRO_CELL_G_KN), *lpf = (volatile uint32_t *)NS_CELL(COPRO_CELL_G_LPF);
 for (uint32_t i = 0; i < 33u; i++) kn[i] = gpts_knot_bits[i];
 for (uint32_t i = 0; i < 40u; i++) lpf[i] = gpts_lpf_bits[i];
 if (main) {
 for (uint32_t i = 0; i < 5; i++) glast[i] = -999.0f;
 input_base = rdf(r + 36); output_base = rdf(r + 40);
 put_two_curve(COPRO_CELL_G_PRE, COPRO_CELL_G_SECOND, COPRO_CELL_G_BQ, COPRO_CELL_G_AB, r);
#ifdef COPRO_CELL_G_PAIR
 if (pair) put_spectra520(NS_PROG(COPRO_CELL_G_PMADDR_PAIR_SPEC), r + 504u);
 else
#endif
 put_spectra520(NS_PROG(NS_GPTC_SPEC_PC), r + 504u);
 put_design(COPRO_CELL_G_BASS, gp50_eq_flat()); put_design(COPRO_CELL_G_MID, gp50_eq_flat()); put_design(COPRO_CELL_G_TREBLE, gp50_eq_flat());
 }
#ifdef COPRO_CELL_G_PAIR
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_SPEC) = pair ? COPRO_CELL_G_PMADDR_PAIR_SPEC : NS_GPTC_SPEC_PC;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_PAIR) = 0;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_MAIN_OFF) = main ? 0u : 1u;
#endif
#ifdef COPRO_CELL_G_PARTS
 /* Run-time partition count (fused_079 RUNTIME_PARTS): without an IR the fused spectra are the record's four
  * partitions followed by exact zeros, so four partitions give the same output for a third of the multiply work. */
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_PARTS) = selected_ir ? 12u : 4u;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_SPAN) = selected_ir ? 1560u : 520u;
#endif
#ifdef COPRO_CELL_G_PAIR
 if (pair) {
  /* Second slot (DST capture): its cells are main FDL words the install above zeroed. Fixed record gains, flat tone. */
  const uint8_t *q = pair_record;
  for (uint32_t i = 0; i < 9u; i++) *NS_CELL(COPRO_CELL_G_P2_TREBLE + i) = 0;
  *NS_CELL(COPRO_CELL_G_P2_PREV0) = 0; *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_P2_STATE) = 0;
  p2_tone.in_base = rdf(q + 36); p2_tone.out_base = rdf(q + 40);
  for (uint32_t i = 0; i < 5u; i++) p2_tone.seen[i] = -999.0f;
  *NS_CELL(COPRO_CELL_G_P2_INPUT_GAIN) = p2_tone.in_base; *NS_CELL(COPRO_CELL_G_P2_OUTPUT_GAIN) = p2_tone.out_base;
  put_two_curve(COPRO_CELL_G_P2_PRE, COPRO_CELL_G_P2_SECOND, COPRO_CELL_G_P2_BQ, COPRO_CELL_G_P2_AB, q);
  put_design(COPRO_CELL_G_P2_BASS, gp50_eq_flat()); put_design(COPRO_CELL_G_P2_MID, gp50_eq_flat()); put_design(COPRO_CELL_G_P2_TREBLE, gp50_eq_flat());
  put_spectra520(NS_PROG(COPRO_CELL_G_PMADDR_P2_SPEC), q + 504u);
  *(volatile uint32_t *)NS_CELL(COPRO_CELL_G_PAIR) = 1u; pair_on = 1u;
  return 1;          /* no fusion: without an IR it would write 1560 words over the pair code */
 }
#endif
 return fused_finish(r + 504u);
}


/* Gain, VOL, Bass, Mid, Treble (0..100, 50 = record gain / flat; a non-finite or missing value counts as 50) into one
 * slot's gain cells; EQ redesigned only on change. Values come from v (volatile DST working parameters) or p. */
static const tone_cells MAIN_CELLS = { COPRO_CELL_G_INPUT_GAIN, COPRO_CELL_G_OUTPUT_GAIN, { COPRO_CELL_G_BASS, COPRO_CELL_G_MID, COPRO_CELL_G_TREBLE } };
#ifdef COPRO_CELL_G_PAIR
static const tone_cells P2_CELLS = { COPRO_CELL_G_P2_INPUT_GAIN, COPRO_CELL_G_P2_OUTPUT_GAIN, { COPRO_CELL_G_P2_BASS, COPRO_CELL_G_P2_MID, COPRO_CELL_G_P2_TREBLE } };
#endif
static inline __attribute__((always_inline)) void tone_controls(const volatile float *v, const float *p, const tone_cells *c, tone_state *t) {
 for (uint32_t i = 0; i < 5u; i++) {
  float x = v ? v[i] : p ? p[i] : 50.0f; x = tc_finite(x) ? clampf(x, 0, 100) : 50.0f;
  if (i < 2u) { *NS_CELL(i ? c->out : c->in) = (i ? t->out_base : t->in_base) * (x * .02f); continue; }
  if (x == t->seen[i]) continue;
  uint32_t cell = c->eq[i - 2u]; t->seen[i] = x;
  if (x == 50.0f) put_design(cell, gp50_eq_flat());
  else if (i == 4u) design_high_shelf(cell, 1600.0f, (x - 50.0f) * .12f);
  else design_peak(cell, i == 2u ? 125.0f : 800.0f, (x - 50.0f) * .12f, .70710678f);
 }
}

static __attribute__((noinline)) void capture_inner_init(const float *p,const uint8_t *const *content) {
 valid=0;gmode=0;designed=0;
#ifdef COPRO_CELL_G_PAIR
 pair_on=0;dst_alone=0;
#endif
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE)=0;
 const uint8_t *r=content?*content:0;
 if(r&&rd32(r)==NS_GPTC){if(install_gptc(r)){valid=1;gmode=1;}return;}
#ifdef COPRO_CELL_G_PAIR
 /* DST capture alone (no main record, no IR): install the DST record as the main capture, a plain single 4-partition
  * capture (2026-11-09: MOD147's MAIN_OFF pre-only mode ran the cleared main body on the pedal and was silent). */
 if(!r&&pair_record){const uint8_t *q=pair_record;pair_record=0;if(install_gptc(q)){valid=1;gmode=1;dst_alone=1;}return;}
#endif
 if(!r||rd32(r)!=0x49535456u)return;
 uint32_t sum=0;for(uint32_t i=6;i<26;i++)sum+=rd32(r+4*i);
 if(!sum)return;
 /* The current record classifier rejects every historical experimental magic. */
 zero_cells(0x398u,0xf9cu-0x398u);
 *NS_CELL(COPRO_CELL_ONE)=1.0f;
 *NS_CELL(COPRO_CELL_THIRD)=1.0f/3.0f;*NS_CELL(COPRO_CELL_TWOTHIRD)=2.0f/3.0f;
 *NS_CELL(COPRO_CELL_ZMIN)=-2047.0f;*NS_CELL(COPRO_CELL_INV1024)=1.0f/1024.0f;
 *NS_CELL(COPRO_CELL_RAMPK)=1.0f/4410.0f;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_PARTS)=8;
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_SPAN)=1040;
 for(uint32_t i=0;i<40;i++)*NS_CELL(COPRO_CELL_LPF+i)=ns_lpf[39-i];
 put_coeffs64(COPRO_CELL_BQA,r+0x18);put_coeffs64(COPRO_CELL_BQB,r+0x40);
 *NS_CELL(COPRO_CELL_P1)=rdf(r+0x68);*NS_CELL(COPRO_CELL_NEGP2)=-rdf(r+0x6c);
 *NS_CELL(COPRO_CELL_NEGP3)=-rdf(r+0x70);*NS_CELL(COPRO_CELL_P4)=rdf(r+0x74);
 for(uint32_t i=0;i<128;i++)*NS_CELL(COPRO_CELL_T128+i)=rdf(r+0x88+4*(127-i));
 float gain=clampf(p[0],0,100)*.01f;
 *NS_CELL(COPRO_CELL_GCUR)=gain;*NS_CELL(COPRO_CELL_GTGT)=gain;
 for(uint32_t i=0;i<160;i++)*NS_PROG(NS_TW_PC+i)=ns_tw[i];
 for(uint32_t part=0;part<8;part++){
  for(uint32_t j=0;j<128;j++){fre[j]=j<64?rdf(r+0x288+4*(64*part+j)):0;fim[j]=0;}
  fft128();
  for(uint32_t j=0;j<65;j++){
   *NS_PROG(NS_SPEC_PC+130*part+2*j)=fre[j]*(1.0f/128.0f);
   *NS_PROG(NS_SPEC_PC+130*part+2*j+1)=fim[j]*(1.0f/128.0f);
  }
 }
 valid=1;
}
/* Selected init is a resident-only extension: stable Q23 data, exact length.
 * Stock VTSI ignores the IR, retaining its existing embedded cabinet behavior. */
GP50_INIT void ns_capture_init_selected(const float *p,const uint8_t *const *content,
 const uint8_t *ir,uint32_t bytes) {
 selected_ir=ir;selected_ir_bytes=bytes;capture_inner_init(p,content);
 selected_ir=0;selected_ir_bytes=0;
}
#ifdef COPRO_CELL_G_PAIR
/* Pair init (resident-only extension): `second` is a stable GPTC record run before the main capture. It is used only
 * when the main record is GPTC and no IR is selected; otherwise this is ns_capture_init_selected. */
GP50_INIT void ns_capture_init_pair(const float *p,const uint8_t *const *content,
 const uint8_t *ir,uint32_t bytes,const uint8_t *second) {
 pair_record=ir?0:second;ns_capture_init_selected(p,content,ir,bytes);pair_record=0;
}
/* Pair status for the resident: the PAIR data cell (COPRO_CELL_G_PAIR bit 0), 1 only while the pair is installed. */
#endif
GP50_INIT void ns_capture_init(const float *p,const uint8_t *const *content) {
 ns_capture_init_selected(p,content,0,0);__asm__ volatile("" ::: "memory");
}
GP50_PROCESS void ns_capture_process(float *samples, uint32_t frames, const float *p, uint32_t r3,
 const uint8_t *enable, const uint32_t *beat, void *r6) {
 (void)samples; (void)frames; (void)r3; (void)beat; (void)r6;
 if (gmode) {                                                          /* as tone_compact_063 process */
  if (valid) {
#ifdef COPRO_CELL_G_PAIR
   /* One inlined call site (stack bound): s = 0 the second (DST) slot when paired, s = 1 the main slot. */
   for (uint32_t s = pair_on ? 0u : 1u; s < 2u; s++)
    tone_controls(s ? (dst_alone ? dst_tone : 0) : dst_tone, s ? p : 0, s ? &MAIN_CELLS : &P2_CELLS, s ? &main_tone : &p2_tone);
#else
   tone_controls(0, p, &MAIN_CELLS, &main_tone);
#endif
  }

 } else if(valid && (!designed||p[0]!=last[0]||p[1]!=last[1]||p[2]!=last[2]||p[3]!=last[3]||p[4]!=last[4])) {
  for(uint32_t i=0;i<5;i++)last[i]=p[i];designed=1;
  *NS_CELL(COPRO_CELL_GTGT)=clampf(p[0],0,100)*.01f;
  *NS_CELL(COPRO_CELL_VLEVEL)=clampf(p[1],0,100)*.01f*2.5118999f;
  design_peak(COPRO_CELL_BASS,125,(clampf(p[2],0,100)-50)*.12f,.70710678f);
  design_peak(COPRO_CELL_MID,800,(clampf(p[3],0,100)-50)*.12f,.70710678f);
  design_high_shelf(COPRO_CELL_TREBLE,1600,(clampf(p[4],0,100)-50)*.12f);
 }
 if(gmode&&valid&&(*(volatile uint32_t *)COPRO_STATUS_REG&2u)){
  *(volatile uint32_t *)COPRO_RUN_REG=0;*(volatile uint32_t *)COPRO_STATUS_REG=0;valid=0;
 }
 *(volatile uint32_t *)NS_CELL(COPRO_CELL_ENABLE)=(*enable&&valid)?1u:0u;
}
