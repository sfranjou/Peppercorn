/* Cloud Verb: the Mutable Instruments Clouds reverb (Griesinger/Dattorro figure-eight tank) for the RVB group.
 * Port of clouds/dsp/fx/reverb.h (structure, line lengths, coefficients), adapted for this pedal: runs at half
 * rate (22.05 kHz; Clouds runs at 32 kHz: lengths scaled by 22050/32000), float lines in the slot for the four
 * input diffusers and the four tank allpasses, and the two long tank delays (16-bit) in the 166 KB RAM above the
 * looper's range (0x290d7580.., "tail_region"; analysis/firmware/LOOPER_MEMORY.md). That RAM is not zeroed at
 * boot: it is cleared in chunks after loading while the wet signal stays muted. Freeze: tank feedback -> 1,
 * damping -> off, input -> 0. Mono in word 0, written to both words.
 * Parameters: 0 Mix, 1 Decay (tank feedback 0.5..0.98), 2 Diffusion (0.4..0.75), 3 Damp, 4 Freeze 0/1, 5 VOL.
 *
 * Original code: Copyright 2014 Emilie Gillet (emilie.o.gillet@gmail.com).
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
 * documentation files (the "Software"), to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and
 * to permit persons to whom the Software is furnished to do so, subject to the following conditions:
 * The above copyright notice and this permission notice shall be included in all copies or substantial portions of
 * the Software.
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO
 * THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
 * CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE. */
#ifndef GP50_NATIVE_TEST
#include "gp50_effect.h"
#endif
#ifndef GP50_TAIL_PTR
#define GP50_TAIL_PTR(address) ((uintptr_t)(address))
#endif
#define CV_INLINE static __attribute__((always_inline)) inline

/* Clouds lengths at 32 kHz x 22050/32000, rounded */
#define AP1 78u
#define AP2 112u
#define AP3 166u
#define AP4 275u
#define DAP1A 1139u
#define DAP1B 1404u
#define DAP2A 1318u
#define DAP2B 1146u
#define DEL1 2350u
#define DEL2 3295u
#define DEL2_TAP 3225u                     /* Clouds 4680 at 32 kHz */
#define MOD2 69u                           /* Clouds LFO depth 100 at 32 kHz */
#define TAIL_BASE 0x290d7580u              /* del1 then del2, int16, x 8192 */
#define TAIL_CELLS (DEL1 + DEL2)
#define CLEAR_PER_BLOCK 256u               /* tail RAM is ~0.2 ms per 1000 accesses: spread the clearing */

static struct {
    float ap1[AP1], ap2[AP2], ap3[AP3], ap4[AP4];
    float d1a[DAP1A], d1b[DAP1B], d2a[DAP2A], d2b[DAP2B];
    uint32_t q1, q2, q3, q4, q1a, q1b, q2a, q2b, w1, w2;   /* positions */
    uint32_t cleared;                                      /* tail cells cleared since loading */
    float lp1, lp2, half, last, now, freeze;
    uint32_t lfo;
} state;

CV_INLINE int16_t *cv_cell(uint32_t index) { return (int16_t *)GP50_TAIL_PTR(TAIL_BASE + 2u * index); }
CV_INLINE float cv_tail_read(uint32_t index) {   /* unsigned load + arithmetic sign (no ldrsh: interpreter) */
    const uint32_t u = *(volatile uint16_t *)cv_cell(index);
    return ((float)u - 65536.0f * (float)(u >> 15)) * (1.0f / 8192.0f);
}
CV_INLINE void cv_tail_write(uint32_t index, float x) {
    float v = x * 8192.0f;
    v = v > 32767.0f ? 32767.0f : v;
    v = v < -32767.0f ? -32767.0f : v;
    *(volatile int16_t *)cv_cell(index) = (int16_t)v;
}
CV_INLINE uint32_t cv_next(uint32_t p, uint32_t n) { return p + 1u == n ? 0u : p + 1u; }
/* allpass as in Clouds' FxEngine: read the tail * k, write acc, out = written * -k + tail */
CV_INLINE float cv_allpass(float *buf, uint32_t *pos, uint32_t n, float acc, float k) {
    const uint32_t p = *pos;
    const float d = buf[p];
    const float v = acc + d * k;
    buf[p] = v;
    *pos = cv_next(p, n);
    return d - v * k;
}
CV_INLINE float cv_sin(uint32_t phase) {
    const float half = (float)(phase >> 31);
    const float t = (float)(phase >> 8) * (1.0f / 16777216.0f) - 0.5f * half;
    return 16.0f * t * (0.5f - t) * (1.0f - 2.0f * half);
}

GP50_INIT void clouds_verb_init(const float *params) {
    (void)params;   /* slot zeroed by the loader; the tail RAM is cleared progressively in process() */
}

GP50_PROCESS void clouds_verb_process(float *samples, uint32_t frames, const float *params,
                                      uint32_t reserved_r3, const uint8_t *enable,
                                      const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    /* clear the tail RAM first (also while bypassed): nothing old or random is ever heard */
    if (state.cleared < TAIL_CELLS) {
        uint32_t end = state.cleared + CLEAR_PER_BLOCK;
        end = end > TAIL_CELLS ? TAIL_CELLS : end;
        for (uint32_t c = state.cleared; c < end; c++) *(volatile int16_t *)cv_cell(c) = 0;
        state.cleared = end;
    }
    if (*enable == 0) return;
    const float amount = params[0] * 0.01f;
    const float volume = params[5] * 0.02f;
    if (state.cleared < TAIL_CELLS) {                     /* still clearing: dry only */
        for (uint32_t i = 0; i < frames; i++) {
            const float o = samples[2 * i] * (1.0f - amount) * volume;
            samples[2 * i] = o; samples[2 * i + 1] = o;
        }
        return;
    }
    state.freeze += ((params[4] >= 0.5f ? 1.0f : 0.0f) - state.freeze) * 0.5f;
    const float fr = state.freeze;
    const float krt = 0.5f + params[1] * 0.0048f;          /* 0.5 .. 0.98 */
    const float kr = krt + (1.0f - krt) * fr;
    const float kap = 0.4f + params[2] * 0.0035f;          /* 0.4 .. 0.75 (Clouds default 0.625) */
    const float klp_target = 1.0f - params[3] * 0.008f;     /* 1 open .. 0.2 dark (Clouds default 0.7) */
    const float klp = klp_target + (1.0f - klp_target) * fr;
    const float gain = 0.2f * (1.0f - fr);                  /* input gain (Clouds sets 0.2 in its graintable) */
    state.lfo += (uint32_t)(0.3f * (float)frames * (4294967296.0f / GP50_SAMPLE_RATE));
    const float mod = (float)DEL2_TAP + (float)MOD2 * cv_sin(state.lfo);
    const uint32_t mw = (uint32_t)mod;
    const float mf = mod - (float)mw;
    float last = state.last, now = state.now;
    for (uint32_t i = 0; i < frames; i++) {
        const float x = samples[2 * i];
        if ((i & 1u) == 0u) state.half = x;
        else {
            float acc = (state.half + x) * 0.5f * gain;
            acc = cv_allpass(state.ap1, &state.q1, AP1, acc, kap);
            acc = cv_allpass(state.ap2, &state.q2, AP2, acc, kap);
            acc = cv_allpass(state.ap3, &state.q3, AP3, acc, kap);
            acc = cv_allpass(state.ap4, &state.q4, AP4, acc, kap);
            const float apout = acc;
            /* half 1: modulated del2 -> lp -> dap1a, dap1b -> del1 */
            uint32_t a = state.w2 + DEL2 - mw; a = a >= DEL2 ? a - DEL2 : a;
            const uint32_t b = a == 0u ? DEL2 - 1u : a - 1u;
            const float ta = cv_tail_read(DEL1 + a);
            acc = apout + (ta + (cv_tail_read(DEL1 + b) - ta) * mf) * kr;
            state.lp1 += (acc - state.lp1) * klp; acc = state.lp1;
            acc = cv_allpass(state.d1a, &state.q1a, DAP1A, acc, -kap);
            acc = cv_allpass(state.d1b, &state.q1b, DAP1B, acc, kap);
            cv_tail_write(state.w1, acc);
            const float wet1 = acc * 2.0f;
            /* half 2: del1 (full length) -> lp -> dap2a, dap2b -> del2 */
            acc = apout + cv_tail_read(cv_next(state.w1, DEL1)) * kr;
            state.lp2 += (acc - state.lp2) * klp; acc = state.lp2;
            acc = cv_allpass(state.d2a, &state.q2a, DAP2A, acc, kap);
            acc = cv_allpass(state.d2b, &state.q2b, DAP2B, acc, -kap);
            cv_tail_write(DEL1 + state.w2, acc);
            const float wet2 = acc * 2.0f;
            state.w1 = cv_next(state.w1, DEL1); state.w2 = cv_next(state.w2, DEL2);
            last = now; now = (wet1 + wet2) * 0.5f;
        }
        const float wet = (i & 1u) ? now : (last + now) * 0.5f;
        const float o = (x + (wet - x) * amount) * volume;  /* Clouds: in += (wet - in) * amount */
        samples[2 * i] = o; samples[2 * i + 1] = o;
    }
    state.last = last; state.now = now;
}
