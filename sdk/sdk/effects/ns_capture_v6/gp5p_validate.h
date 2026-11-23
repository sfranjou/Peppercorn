/* GP5P user-program validator (pedal side). Mirrors sdk/copro/gp5p.py `validate` rule for rule; the two are compared
 * on examples, rule violations and fuzzed programs by sdk/test_gp5p.py (this header compiled natively).
 * analysis/firmware/USER_PROGRAMS.md. Pure C, no hardware access; everything inline (SDK: no calls). */
#ifndef GP5P_VALIDATE_H
#define GP5P_VALIDATE_H
#include <stdint.h>
#define GP5P_INLINE static   /* v6: -Os decides (payload room for GPTC) */
#define GP5P_USER_PC 0x7cau
#define GP5P_USER_LO 0x3a8u
#define GP5P_USER_HI 0xf9cu
#define GP5P_EXIT 0xe00u
#define GP5P_MAX_WORDS 512u   /* code words (code + data <= 642 is checked by the record parser) */
#define GP5P_MAX_LOOPS 24u
enum { E_OK, E_SIZE, E_FORM, E_TARGET, E_LOOP, E_COUNTER, E_POINTER, E_ADDRESS, E_COUNT, E_BOUND, E_END, E_CRC, E_MAGIC };
enum { K_BAD, K_LI, K_CHI, K_CLO, K_ADDI, K_SUBI, K_NEG, K_LD, K_ST, K_LDI, K_STI, K_PLD, K_MOV, K_BREV, K_FMUL, K_FMAC,
       K_FADD, K_FSUB, K_IADD, K_ISHR, K_SHL, K_FSKIP, K_BSKIP, K_GSKIP, K_LOOP, K_JUMP, K_BLOCK };
enum { R_NONE, R_USER, R_WIN, R_SCR, R_PROG };
enum { S_NONE, S_IMM, S_HI, S_PTR };
typedef struct { uint8_t kind, a, b, d, inc; uint32_t v; } gp5p_word;
typedef struct { uint8_t s; uint32_t v; } gp5p_reg;

GP5P_INLINE uint32_t gp5p_region(uint32_t v, uint32_t n) {
 if (v >= GP5P_USER_LO && v < GP5P_USER_HI) return R_USER;
 if (v >= 0x13u && v < 0x53u) return R_WIN;
 if (v >= 0x113u && v < 0x193u) return R_SCR;
 if (v >= GP5P_USER_PC && v < GP5P_USER_PC + n) return R_PROG;
 return R_NONE;
}

GP5P_INLINE gp5p_word gp5p_decode(uint32_t w) {
 gp5p_word x = { K_BAD, 0, 0, 0, 0, 0 };
 uint32_t op = w >> 28, a = w >> 24 & 15u, b = w >> 20 & 15u, mode = w >> 16 & 15u, imm = w & 0xffffu, d = imm & 15u;
 x.a = (uint8_t)a; x.b = (uint8_t)b; x.d = (uint8_t)d; x.v = imm;
 if (op == 7u) {
  if (b == 0 && mode == 6u && imm <= 0x7fffu && a <= 13u) { x.kind = K_LI; return x; }
  if (b == 0xcu && mode == 6u && a <= 13u) { x.kind = K_CHI; return x; }
  if (b == 8u && mode == 6u && a <= 13u) { x.kind = K_CLO; return x; }
  if (b == 0 && (mode == 0 || mode == 2u) && a <= 13u) { x.kind = mode ? K_SUBI : K_ADDI; return x; }
  if (b == 0xcu && mode == 0xcu && imm == 0x8000u && a <= 13u) { x.kind = K_NEG; return x; }
 }
 if (op == 5u && b == 0 && (mode == 0 || mode == 8u) && imm < 0x1000u && a <= 13u) { x.kind = mode ? K_ST : K_LD; return x; }
 if (op == 0xeu && imm == 0 && a <= 13u && b <= 13u) {
  if ((mode == 2u || mode == 3u) && !(mode == 3u && a == b)) { x.kind = K_LDI; x.inc = mode == 3u; return x; }
  if ((mode == 4u || mode == 5u) && !(mode == 5u && a == b)) { x.kind = K_STI; x.inc = mode == 5u; return x; }
  if ((mode == 6u || mode == 7u) && !(mode == 7u && a == b)) { x.kind = K_PLD; x.inc = mode == 7u; return x; }
 }
 if (op == 0xfu && mode == 4u && imm == 0 && a <= 13u && b <= 13u) { x.kind = K_MOV; return x; }
 if (op == 0xfu && mode == 0xcu && b == 0 && imm >> 8 == 0 && a <= 13u && d <= 13u) {
  uint32_t width = (imm >> 4) >> 1; if (width == 4u || width == 6u || width == 7u) { x.kind = K_BREV; return x; }
 }
 if (op == 8u && imm >> 4 == 0 && (mode == 6u || mode == 0xau) && a <= 13u && b <= 13u && d <= 13u && d != a && d != b) { x.kind = mode == 6u ? K_FMUL : K_FMAC; return x; }
 if (op == 0xcu && imm >> 4 == 0 && (mode == 0xeu || mode == 0xfu) && a <= 13u && b <= 13u && d <= 13u && d != a && d != b) { x.kind = mode == 0xeu ? K_FADD : K_FSUB; return x; }
 if (op == 0xcu && imm >> 4 == 0 && mode == 0 && a <= 13u && b <= 13u && d <= 13u) { x.kind = K_IADD; return x; }
 if (op == 0xcu && imm >> 4 == 0x400u && mode == 7u && a <= 13u && b <= 13u && d <= 13u) { x.kind = K_ISHR; return x; }
 if (op == 0xdu && b == 0 && mode == 2u && imm >> 12 == 0 && (imm >> 4) >> 1 <= 8u && a <= 13u && d <= 13u) { x.kind = K_SHL; return x; }
 if (op == 9u) {
  if (w == 0x9f0a3c01u || w == 0x9f083c01u) { x.kind = K_FSKIP; return x; }
  if (b == 0 && mode == 8u && imm == 1u && a <= 13u) { x.kind = K_BSKIP; return x; }
  if (mode == 2u && imm == 1u && a <= 13u && b <= 13u) { x.kind = K_GSKIP; return x; }
 }
 if (op == 0xau && b == 0 && mode == 4u && imm < 0x1000u && a <= 13u) { x.kind = K_LOOP; return x; }
 if (op == 0xau && a == 0 && b == 0 && mode == 8u && imm < 0x1000u) { x.kind = K_JUMP; return x; }
 if (op == 2u && a == 0 && b == 0 && imm == 0 && (mode == 0 || mode == 3u || mode == 4u || mode == 7u || mode == 8u || mode == 0xdu)) { x.kind = K_BLOCK; x.d = (uint8_t)mode; return x; }
 return x;
}

/* Registers written (bit r of *w) and whether every write keeps a pointer region (bit r of *keep). */
GP5P_INLINE void gp5p_writes(const gp5p_word *x, uint32_t *w, uint32_t *keep) {
 uint32_t W = 0, K = 0;
 switch (x->kind) {
 case K_LI: case K_CHI: case K_CLO: case K_NEG: case K_LD: W = 1u << x->a; break;
 case K_MOV: W = 1u << x->a; break;
 case K_BREV: case K_SHL: W = 1u << x->d; break;
 case K_ADDI: case K_SUBI: W = K = 1u << x->a; break;
 case K_LDI: case K_PLD: W = 1u << x->a; if (x->inc) { W |= 1u << x->b; K |= 1u << x->b; } break;
 case K_STI: if (x->inc) { W = K = 1u << x->a; } break;
 case K_FMUL: case K_FMAC: case K_FADD: case K_FSUB: case K_IADD: case K_ISHR: W = 1u << x->d; break;
 case K_LOOP: W = 1u << x->a; break;
 case K_BLOCK: W = (1u << 9) | (1u << 10) | (1u << 11); K = (1u << 9) | (x->d != 0xdu ? 1u << 11 : 0u);
  if (x->d == 3u || x->d == 7u || x->d == 0xdu) { W |= 1u << 8; K |= 1u << 8; } break;
 default: break;
 }
 /* a write that is not a keep-write anywhere in this word clears the keep bit */
 *w = W; *keep = K;
}

GP5P_INLINE uint32_t gp5p_is_skip(uint32_t k) { return k == K_FSKIP || k == K_BSKIP || k == K_GSKIP; }

GP5P_INLINE uint32_t gp5p_reg_region(const gp5p_reg *s, uint32_t n) {
 if (s->s == S_PTR) return s->v;
 if (s->s == S_IMM) return gp5p_region(s->v, n);
 return R_NONE;
}
GP5P_INLINE uint32_t gp5p_ptr_ok(const gp5p_reg *s, uint32_t n, uint32_t prog) {
 uint32_t r = gp5p_reg_region(s, n);
 return prog ? r == R_PROG : (r == R_USER || r == R_WIN || r == R_SCR);
}
GP5P_INLINE void gp5p_apply_write(gp5p_reg *s, uint32_t keep, uint32_t n) {
 uint32_t r = gp5p_reg_region(s, n);
 if (keep && r != R_NONE) { s->s = S_PTR; s->v = r; } else { s->s = S_NONE; s->v = 0; }
}

/* Decoded words, filled once per validation (the SDK inlines everything; decoding at every use would not fit). */
/* One buffer, so an includer can reuse it while no validation runs (NS Capture: FFT scratch for GP5N/VTSI records). */
static uint32_t gp5p_cache[(6u * GP5P_MAX_WORDS + 3u) / 4u];
#define gp5p_ck ((uint8_t *)gp5p_cache)
#define gp5p_ca ((uint8_t *)gp5p_cache + GP5P_MAX_WORDS)
#define gp5p_cb ((uint8_t *)gp5p_cache + 2u * GP5P_MAX_WORDS)
#define gp5p_cd ((uint8_t *)gp5p_cache + 3u * GP5P_MAX_WORDS)
#define gp5p_cv ((uint16_t *)((uint8_t *)gp5p_cache + 4u * GP5P_MAX_WORDS))
GP5P_INLINE gp5p_word gp5p_get(uint32_t i) {
 gp5p_word x; x.kind = gp5p_ck[i]; x.a = gp5p_ca[i]; x.b = gp5p_cb[i]; x.d = gp5p_cd[i] & 15u; x.inc = gp5p_cd[i] >> 7; x.v = gp5p_cv[i];
 return x;
}

/* Returns E_OK and *bound, or an error code and *pc. words: code words (n). */
GP5P_INLINE uint32_t gp5p_validate(const uint32_t *words, uint32_t n, uint32_t budget, uint32_t *bound, uint32_t *pc) {
 static uint16_t lt[GP5P_MAX_LOOPS], le[GP5P_MAX_LOOPS]; static uint8_t lr[GP5P_MAX_LOOPS]; static uint32_t lw[GP5P_MAX_LOOPS], lk[GP5P_MAX_LOOPS], lc[GP5P_MAX_LOOPS];
 static uint8_t target[(GP5P_MAX_WORDS + 7u) / 8u];
 uint32_t nl = 0; *pc = 0; *bound = 0;
 if (n < 2u || n > GP5P_MAX_WORDS) return E_SIZE;
 for (uint32_t i = 0; i < (GP5P_MAX_WORDS + 7u) / 8u; ++i) target[i] = 0;
 for (uint32_t i = 0; i < n; ++i) {
  gp5p_word x = gp5p_decode(words[i]); *pc = i;
  gp5p_ck[i] = x.kind; gp5p_ca[i] = x.a; gp5p_cb[i] = x.b; gp5p_cd[i] = (uint8_t)(x.d | x.inc << 7); gp5p_cv[i] = (uint16_t)x.v;
  if (x.kind == K_BAD) return E_FORM;
  if (x.kind == K_CLO && (!i || gp5p_ck[i - 1] != K_CHI || gp5p_ca[i - 1] != x.a)) return E_FORM;
  if (x.kind == K_FSKIP && (!i || gp5p_ck[i - 1] != K_FSUB)) return E_FORM;
 }
 if (gp5p_ck[n - 1] != K_JUMP) { *pc = n - 1; return E_END; }
 for (uint32_t i = 0; i < n; ++i) {
  gp5p_word x = gp5p_get(i); *pc = i;
  if (x.kind == K_JUMP && x.v != GP5P_EXIT) {
   if (!(x.v > GP5P_USER_PC + i && x.v < GP5P_USER_PC + n)) return E_TARGET;
   uint32_t t = x.v - GP5P_USER_PC; target[t >> 3] |= (uint8_t)(1u << (t & 7u));
  }
  if (gp5p_is_skip(x.kind) && i + 2u > n - 1u) return E_TARGET;
  if (x.kind == K_LOOP) {
   if (x.v < GP5P_USER_PC || x.v - GP5P_USER_PC > i) return E_LOOP;
   if (nl == GP5P_MAX_LOOPS) return E_LOOP;
   lt[nl] = (uint16_t)(x.v - GP5P_USER_PC); le[nl] = (uint16_t)i; lr[nl] = x.a; nl++;
  }
 }
 for (uint32_t p = 0; p < nl; ++p) for (uint32_t q = 0; q < nl; ++q)
  if (p != q && lt[p] < lt[q] && lt[q] <= le[p] && le[p] < le[q]) { *pc = le[q]; return E_LOOP; }
 for (uint32_t i = 0; i < n; ++i) {                      /* no entry into a loop body from outside */
  gp5p_word x = gp5p_get(i); uint32_t t;
  if (x.kind == K_JUMP && x.v != GP5P_EXIT) t = x.v - GP5P_USER_PC; else if (gp5p_is_skip(x.kind)) t = i + 2u; else continue;
  for (uint32_t p = 0; p < nl; ++p) if (lt[p] < t && t <= le[p] && !(lt[p] <= i && i <= le[p])) { *pc = i; return E_TARGET; }
 }
 for (uint32_t p = 0; p < nl; ++p) {
  uint32_t W = 0, K = 0x3fffu;
  for (uint32_t j = lt[p]; j < le[p]; ++j) {
   gp5p_word x = gp5p_get(j); uint32_t w, k; gp5p_writes(&x, &w, &k);
   W |= w; K &= ~(w & ~k);
  }
  lw[p] = W; lk[p] = K & W;
  if (W >> lr[p] & 1u) { *pc = le[p]; return E_COUNTER; }
 }
 gp5p_reg st[14], save[14]; uint32_t have_save = 0;
 for (uint32_t r = 0; r < 14u; ++r) { st[r].s = S_NONE; st[r].v = 0; }
 for (uint32_t i = 0; i < n; ++i) {
  gp5p_word x = gp5p_get(i); *pc = i;
  if (target[i >> 3] >> (i & 7u) & 1u) for (uint32_t r = 0; r < 14u; ++r) { st[r].s = S_NONE; st[r].v = 0; }
  for (uint32_t p = 0; p < nl; ++p) if (lt[p] == i) {
   gp5p_reg *c = &st[lr[p]];
   if (!(c->s == S_IMM && c->v >= 1u && c->v <= 0x7fffu)) { *pc = le[p]; return E_COUNTER; }
   lc[p] = c->v;
   for (uint32_t r = 0; r < 14u; ++r) if (lw[p] >> r & 1u) gp5p_apply_write(&st[r], lk[p] >> r & 1u, n);
  }
  if ((x.kind == K_LD || x.kind == K_ST)) { uint32_t g = gp5p_region(x.v, 0); if (!(g == R_USER || g == R_WIN || g == R_SCR)) return E_ADDRESS; }
  if (x.kind == K_LDI && !gp5p_ptr_ok(&st[x.b], n, 0)) return E_POINTER;
  if (x.kind == K_STI && !gp5p_ptr_ok(&st[x.a], n, 0)) return E_POINTER;
  if (x.kind == K_PLD && !gp5p_ptr_ok(&st[x.b], n, 1)) return E_POINTER;
  uint32_t elements = 0;
  if (x.kind == K_BLOCK) {
   uint32_t m = x.d, p8 = m == 3u || m == 7u || m == 0xdu;
   if (!(gp5p_ptr_ok(&st[9], n, 0) && (m == 0xdu || gp5p_ptr_ok(&st[11], n, 0)) && (!p8 || gp5p_ptr_ok(&st[8], n, 0)))) return E_POINTER;
   if (!(st[10].s == S_IMM && st[10].v >= 1u && st[10].v <= 0x7fffu)) return E_COUNT;
   elements = st[10].v;
  }
  if (x.kind == K_LI) { st[x.a].s = S_IMM; st[x.a].v = x.v; }
  else if (x.kind == K_CHI) { st[x.a].s = S_HI; st[x.a].v = x.v; }
  else if (x.kind == K_CLO) { if (st[x.a].s == S_HI) { st[x.a].s = S_IMM; st[x.a].v = st[x.a].v << 16 | x.v; } else { st[x.a].s = S_NONE; st[x.a].v = 0; } }
  else {
   uint32_t w, k; gp5p_writes(&x, &w, &k);
   for (uint32_t r = 0; r < 14u; ++r) if (w >> r & 1u) gp5p_apply_write(&st[r], k >> r & 1u, n);
   if (x.kind == K_BLOCK) { st[10].s = S_IMM; st[10].v = 0; }
  }
  if (have_save) { for (uint32_t r = 0; r < 14u; ++r) if (st[r].s != save[r].s || st[r].v != save[r].v) { st[r].s = S_NONE; st[r].v = 0; } have_save = 0; }
  if (gp5p_is_skip(x.kind)) { for (uint32_t r = 0; r < 14u; ++r) save[r] = st[r]; have_save = 1; }
  if (x.kind == K_JUMP) for (uint32_t r = 0; r < 14u; ++r) { st[r].s = S_NONE; st[r].v = 0; }
  uint32_t mult = 1;
  for (uint32_t p = 0; p < nl; ++p) if (lt[p] <= i && i <= le[p]) { mult *= lc[p]; if (mult > 0x7fffffffu / 0x8000u) mult = 0x7fffffffu / 0x8000u; }
  uint32_t add = mult * (1u + elements);
  *bound = *bound > 0x7fffffffu - add ? 0x7fffffffu : *bound + add;   /* saturating; judged after the scan, as gp5p.py */
 }
 *pc = 0; return *bound > budget ? E_BOUND : E_OK;
}
#endif
