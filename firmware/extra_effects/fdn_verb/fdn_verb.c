/* FDN Verb: 8-line feedback delay network reverb with freeze (RVB group, whole 28 KB slot).
 * Written for this project from the published technique (Stautner & Puckette 1982, "Designing multi-channel
 * reverberators"; Jot & Chaigne 1991, "Digital delay networks for designing artificial reverberators"):
 *   input low cut -> 2:1 decimation -> pre-delay -> 2 allpass diffusers -> 8 delay lines mixed by an orthogonal
 *   8x8 Hadamard matrix, per-line decay gain from RT60 and line length, one-pole damping per line, slow modulation
 *   on 4 lines -> linear interpolation back to 44.1 kHz.
 * The network runs at half rate (22.05 kHz) with float lines: half the work, no int16 conversions; the audio
 * processor has no spare cycles for a full-rate tank (stock reverbs cost it almost nothing: they run elsewhere).
 * Freeze: line gains -> 1, damping -> off, nothing enters the tank (the Hadamard matrix is lossless, so the tail
 * holds), ramped over a few blocks. Mono in word 0, written to both words.
 * Parameters: 0 Mix, 1 Decay (RT60 0.4..12 s), 2 Size (line length 50..100 %), 3 Damp, 4 Pre Delay 0..40 ms,
 * 5 Freeze 0/1, 6 VOL (50 = unity). */
#include "gp50_effect.h"
#include "gp50_fmath.h"

#define FV_INLINE static __attribute__((always_inline)) inline
#define RATE (GP50_SAMPLE_RATE * 0.5f)    /* network rate */
#define MOD_MAX 6u                         /* modulation swing, network samples */
#define L0 443u
#define L1 503u
#define L2 557u
#define L3 607u
#define L4 661u
#define L5 719u
#define L6 773u
#define L7 829u                            /* mutually prime, 20..38 ms */
#define N(L) ((L) + MOD_MAX + 2u)
#define AP1 121u
#define AP2 205u
#define PRE 883u                           /* 40 ms at the network rate + 1 */
#define IN_GAIN 0.25f
#define OUT_GAIN 1.4f

static struct {
    float m0[N(L0)], m1[N(L1)], m2[N(L2)], m3[N(L3)], m4[N(L4)], m5[N(L5)], m6[N(L6)], m7[N(L7)];
    float ap1[AP1], ap2[AP2];
    int16_t pre[PRE];                                 /* int16 (x 8192): saves 1.8 KB */
    uint32_t p0, p1, p2, p3, p4, p5, p6, p7;          /* write positions */
    uint32_t ap1_pos, ap2_pos, pre_pos;
    float d0, d1, d2, d3, d4, d5, d6, d7;             /* damping states */
    float hp, half, last, freeze;
    uint32_t lfo1, lfo3, lfo5, lfo7;
} state;

FV_INLINE float fv_sin(uint32_t phase) {      /* sin(2 pi phase / 2^32), parabolic, branchless */
    const float half = (float)(phase >> 31);                                   /* plain shifts only (interpreter) */
    const float t = (float)(phase >> 8) * (1.0f / 16777216.0f) - 0.5f * half;  /* 0 .. 0.5 */
    return 16.0f * t * (0.5f - t) * (1.0f - 2.0f * half);
}
FV_INLINE float fv_allpass(float *buf, uint32_t *pos, uint32_t n, float x, float g) {
    const uint32_t p = *pos;
    const float d = buf[p], v = x + g * d;
    buf[p] = v;
    *pos = p + 1u == n ? 0u : p + 1u;
    return d - g * v;
}
/* read `whole` (+frac) samples behind write position w in a line of n samples */
FV_INLINE float fv_read(const float *m, uint32_t n, uint32_t w, uint32_t whole, float frac) {
    uint32_t a = w + n - whole; a = a >= n ? a - n : a;
    const uint32_t b = a == 0u ? n - 1u : a - 1u;
    return m[a] + (m[b] - m[a]) * frac;
}
FV_INLINE float fv_read0(const float *m, uint32_t n, uint32_t w, uint32_t whole) {
    uint32_t a = w + n - whole; a = a >= n ? a - n : a;
    return m[a];
}
FV_INLINE uint32_t fv_next(uint32_t p, uint32_t n) { return p + 1u == n ? 0u : p + 1u; }
FV_INLINE float fv_gain(float length, float rt60) {   /* -60 dB over rt60 */
    return gp50_eq_exp2(-9.9658f * length / (rt60 * RATE));
}

GP50_INIT void fdn_verb_init(const float *params) {
    (void)params;   /* the loader zeroes the slot: lines start silent, positions 0 */
    state.lfo3 = 0x40000000u; state.lfo5 = 0x80000000u; state.lfo7 = 0xc0000000u;
}

GP50_PROCESS void fdn_verb_process(float *samples, uint32_t frames, const float *params,
                                   uint32_t reserved_r3, const uint8_t *enable,
                                   const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    if (*enable == 0) return;
    const float wet = params[0] * 0.01f, dry = 1.0f - wet;
    const float rt60 = 0.4f * gp50_eq_exp2(params[1] * 0.0491f);           /* 0.4 .. ~12 s */
    const float size = 0.5f + params[2] * 0.005f;
    const float damp_target = 1.0f - params[3] * 0.0075f;                   /* 1 = open .. 0.25 = dark */
    const uint32_t pre = (uint32_t)(params[4] * (RATE / 1000.0f));
    const float volume = params[6] * 0.02f;
    state.freeze += ((params[5] >= 0.5f ? 1.0f : 0.0f) - state.freeze) * 0.5f;   /* ~3 blocks */
    const float fr = state.freeze, input_gain = (1.0f - fr) * IN_GAIN;
    const float dk = damp_target + (1.0f - damp_target) * fr;
    /* per block: lengths, gains, slow modulation offsets */
    const float f0 = (float)L0 * size, f1 = (float)L1 * size, f2 = (float)L2 * size, f3 = (float)L3 * size;
    const float f4 = (float)L4 * size, f5 = (float)L5 * size, f6 = (float)L6 * size, f7 = (float)L7 * size;
    float g0 = fv_gain(f0, rt60), g1 = fv_gain(f1, rt60), g2 = fv_gain(f2, rt60), g3 = fv_gain(f3, rt60);
    float g4 = fv_gain(f4, rt60), g5 = fv_gain(f5, rt60), g6 = fv_gain(f6, rt60), g7 = fv_gain(f7, rt60);
    g0 += (1.0f - g0) * fr; g1 += (1.0f - g1) * fr; g2 += (1.0f - g2) * fr; g3 += (1.0f - g3) * fr;
    g4 += (1.0f - g4) * fr; g5 += (1.0f - g5) * fr; g6 += (1.0f - g6) * fr; g7 += (1.0f - g7) * fr;
    const float cycles = (float)frames * (4294967296.0f / GP50_SAMPLE_RATE);   /* phase per Hz per block */
    state.lfo1 += (uint32_t)(0.40f * cycles); state.lfo3 += (uint32_t)(0.53f * cycles);
    state.lfo5 += (uint32_t)(0.61f * cycles); state.lfo7 += (uint32_t)(0.79f * cycles);
    const float h = (float)MOD_MAX * 0.5f;
    const float m1 = f1 + h * (1.0f + fv_sin(state.lfo1)), m3 = f3 + h * (1.0f + fv_sin(state.lfo3));
    const float m5 = f5 + h * (1.0f + fv_sin(state.lfo5)), m7 = f7 + h * (1.0f + fv_sin(state.lfo7));
    const uint32_t w0 = (uint32_t)f0, w2 = (uint32_t)f2, w4 = (uint32_t)f4, w6 = (uint32_t)f6;
    const uint32_t w1 = (uint32_t)m1, w3 = (uint32_t)m3, w5 = (uint32_t)m5, w7 = (uint32_t)m7;
    const float r1 = m1 - (float)w1, r3 = m3 - (float)w3, r5 = m5 - (float)w5, r7 = m7 - (float)w7;
    float last = state.last, now = state.last;
    for (uint32_t i = 0; i < frames; i++) {
        const float x = samples[2 * i];
        state.hp += (x - state.hp) * 0.0141f;                                 /* ~100 Hz low cut */
        const float lc = x - state.hp;
        if ((i & 1u) == 0u) { state.half = lc; }                              /* first of the pair */
        else {
            /* network step at 22.05 kHz on the pair average */
            float v = (state.half + lc) * 4096.0f;                            /* pair average x 8192 */
            v = v > 32767.0f ? 32767.0f : v; v = v < -32767.0f ? -32767.0f : v;
            state.pre[state.pre_pos] = (int16_t)v;
            uint32_t r = state.pre_pos + PRE - pre; r = r >= PRE ? r - PRE : r;
            float in = (float)state.pre[r] * (1.0f / 8192.0f);
            state.pre_pos = fv_next(state.pre_pos, PRE);
            in = fv_allpass(state.ap1, &state.ap1_pos, AP1, in, 0.7f);
            in = fv_allpass(state.ap2, &state.ap2_pos, AP2, in, 0.625f) * input_gain;
            state.d0 += (fv_read0(state.m0, N(L0), state.p0, w0) - state.d0) * dk;
            state.d1 += (fv_read(state.m1, N(L1), state.p1, w1, r1) - state.d1) * dk;
            state.d2 += (fv_read0(state.m2, N(L2), state.p2, w2) - state.d2) * dk;
            state.d3 += (fv_read(state.m3, N(L3), state.p3, w3, r3) - state.d3) * dk;
            state.d4 += (fv_read0(state.m4, N(L4), state.p4, w4) - state.d4) * dk;
            state.d5 += (fv_read(state.m5, N(L5), state.p5, w5, r5) - state.d5) * dk;
            state.d6 += (fv_read0(state.m6, N(L6), state.p6, w6) - state.d6) * dk;
            state.d7 += (fv_read(state.m7, N(L7), state.p7, w7, r7) - state.d7) * dk;
            const float y0 = state.d0 * g0, y1 = state.d1 * g1, y2 = state.d2 * g2, y3 = state.d3 * g3;
            const float y4 = state.d4 * g4, y5 = state.d5 * g5, y6 = state.d6 * g6, y7 = state.d7 * g7;
            last = now;
            now = (y0 - y1 + y2 - y3 + y4 - y5 + y6 - y7) * OUT_GAIN;
            /* 8x8 Hadamard (fast transform) scaled 1/sqrt(8): lossless */
            const float a0 = y0 + y1, a1 = y0 - y1, a2 = y2 + y3, a3 = y2 - y3, a4 = y4 + y5, a5 = y4 - y5, a6 = y6 + y7, a7 = y6 - y7;
            const float b0 = a0 + a2, b1 = a1 + a3, b2 = a0 - a2, b3 = a1 - a3, b4 = a4 + a6, b5 = a5 + a7, b6 = a4 - a6, b7 = a5 - a7;
            const float s = 0.35355339f;
            state.m0[state.p0] = (b0 + b4) * s + in; state.p0 = fv_next(state.p0, N(L0));
            state.m1[state.p1] = (b1 + b5) * s + in; state.p1 = fv_next(state.p1, N(L1));
            state.m2[state.p2] = (b2 + b6) * s + in; state.p2 = fv_next(state.p2, N(L2));
            state.m3[state.p3] = (b3 + b7) * s + in; state.p3 = fv_next(state.p3, N(L3));
            state.m4[state.p4] = (b0 - b4) * s + in; state.p4 = fv_next(state.p4, N(L4));
            state.m5[state.p5] = (b1 - b5) * s + in; state.p5 = fv_next(state.p5, N(L5));
            state.m6[state.p6] = (b2 - b6) * s + in; state.p6 = fv_next(state.p6, N(L6));
            state.m7[state.p7] = (b3 - b7) * s + in; state.p7 = fv_next(state.p7, N(L7));
        }
        /* Causal 2x reconstruction: previous tank value, then the midpoint
         * toward the newly computed value. Next even sample reaches that value.
         * The old ordering stepped backward in time and added coloration. */
        const float out = (i & 1u) ? (last + now) * 0.5f : now;
        const float o = (x * dry + out * wet) * volume;
        samples[2 * i] = o;
        samples[2 * i + 1] = o;
    }
    state.last = now;
}
