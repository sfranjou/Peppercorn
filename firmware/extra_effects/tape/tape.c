/* Tape: wow/flutter + tape saturation (MOD group).
 * Approach after Airwindows ToTape8 (MIT, airwindows.com): pitch wobble from a short delay line read at a position
 * swept by a sine LFO whose rate is re-drawn at random every cycle (xorshift32), and a saturation that treats lows
 * and highs differently. Code written for this project (single precision, no libm); see THIRD_PARTY for credit.
 * Parameters (storage index): 0 Wow 0..100 (slow, 0.5-1.5 Hz), 1 Flutter 0..100 (fast, 6-12 Hz),
 * 2 Drive 0..100, 3 Tone 0..100 (dark..bright), 4 Mix 0..100 (wet), 5 VOL 0..100 (50 = unity).
 * Mono in word 0, written to both words. */
#include "gp50_effect.h"

#define LINE 256u                 /* power of two; centre delay CENTER + up to 46 samples of sweep */
#define CENTER 40.0f
#define WOW_DEPTH 20.0f           /* samples, peak, at Wow 100 */
#define FLUTTER_DEPTH 3.0f        /* samples, peak, at Flutter 100 */

static struct {
    float line[LINE];
    uint32_t write, rng;
    uint32_t wow_phase, wow_rate, flut_phase, flut_rate;   /* 32-bit phase accumulators (2^32 = one cycle) */
    float split, tone;            /* one-pole states */
} state;

static float tp_random(void) {    /* 0..1 */
    uint32_t x = state.rng;
    x ^= x << 13; x ^= x >> 17; x ^= x << 5;
    state.rng = x;
    return (float)(x >> 8) * (1.0f / 16777216.0f);
}
static float tp_sin(uint32_t phase) { /* sin(2 pi phase / 2^32), parabolic approximation, branchless */
    const float t = (float)((phase & 0x7fffffffu) >> 8) * (1.0f / 16777216.0f);   /* 0 .. 0.5 (2^-32 as a literal looks like an address) */
    const float v = 16.0f * t * (0.5f - t);
    return v * (1.0f - 2.0f * (float)(phase >> 31));
}
static uint32_t tp_rate(float hz) { return (uint32_t)(hz * (4294967296.0f / GP50_SAMPLE_RATE)); }
static float tp_sat(float x) {     /* tanh-like, |x| <= 3 -> |y| <= 1 */
    if (x > 3.0f) x = 3.0f; else if (x < -3.0f) x = -3.0f;
    return x * (27.0f + x * x) / (27.0f + 9.0f * x * x);
}

GP50_INIT void tape_init(const float *params) {
    (void)params;
    for (uint32_t i = 0; i < LINE; i++) state.line[i] = 0.0f;
    state.write = 0u; state.rng = 0x9e3779b9u;
    state.wow_phase = 0u; state.wow_rate = tp_rate(1.0f);
    state.flut_phase = 0u; state.flut_rate = tp_rate(9.0f);
    state.split = 0.0f; state.tone = 0.0f;
}

GP50_PROCESS void tape_process(float *samples, uint32_t frames, const float *params,
                               uint32_t reserved_r3, const uint8_t *enable,
                               const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    if (*enable == 0) return;
    const float wow = params[0] * 0.01f * WOW_DEPTH, flutter = params[1] * 0.01f * FLUTTER_DEPTH;
    const float drive = 1.0f + params[2] * 0.08f;                         /* x1 .. x9 */
    const float makeup = (1.0f + (drive - 1.0f) * 0.3f) / drive;            /* level grows gently with drive */
    const float drive_hi = 1.0f + (drive - 1.0f) * 0.5f;                     /* highs saturate less */
    const float makeup_hi = (1.0f + (drive_hi - 1.0f) * 0.3f) / drive_hi;
    const float tone_k = 0.15f + params[3] * 0.0085f;                       /* one-pole: dark .. nearly open */
    const float wet = params[4] * 0.01f, dry = 1.0f - wet;
    const float volume = params[5] * 0.02f;
    const float split_k = 0.06f;                                            /* ~430 Hz low/high split */
    for (uint32_t i = 0; i < frames; i++) {
        const float x = samples[2 * i];
        state.line[state.write] = x;
        const uint32_t wp = state.wow_phase + state.wow_rate, fp = state.flut_phase + state.flut_rate;
        if (wp < state.wow_phase) state.wow_rate = tp_rate(0.5f + tp_random());          /* new cycle: new rate */
        if (fp < state.flut_phase) state.flut_rate = tp_rate(6.0f + 6.0f * tp_random());
        state.wow_phase = wp; state.flut_phase = fp;
        const float d = CENTER + wow * (1.0f + tp_sin(state.wow_phase)) + flutter * (1.0f + tp_sin(state.flut_phase));
        const uint32_t whole = (uint32_t)d;
        const float frac = d - (float)whole;
        const float a = state.line[(state.write - whole) & (LINE - 1u)];
        const float b = state.line[(state.write - whole - 1u) & (LINE - 1u)];
        float y = a + (b - a) * frac;
        state.write = (state.write + 1u) & (LINE - 1u);
        /* saturation: lows driven harder through the soft curve, highs gently */
        state.split += (y - state.split) * split_k;
        const float lows = state.split, highs = y - state.split;
        y = tp_sat(lows * drive) * makeup + tp_sat(highs * drive_hi) * makeup_hi;
        state.tone += (y - state.tone) * tone_k;
        y = state.tone;
        const float out = (x * dry + y * wet) * volume;
        samples[2 * i] = out;
        samples[2 * i + 1] = out;
    }
}
