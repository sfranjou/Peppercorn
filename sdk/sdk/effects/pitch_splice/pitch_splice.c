/* Stock Pitch/Detune control layout with a period-aligned variable-delay core. */
#include "gp50_effect.h"

#define RING 1024u
#define MIN_LAG 256u
#define MAX_LAG 640u
#define INITIAL_LAG 448.0f
#define CHANGE_FADE 128u

typedef struct { float input, output; } Allpass;
typedef struct { float input, output; } Lowpass;
typedef struct {
    float slope, delay, incoming, near_delay, weight_step;
    uint32_t fade, step;
} Tap;
typedef struct {
    Tap current, next;
    Lowpass lowpass;
    uint32_t change;
} Voice;

static struct {
    int16_t line[2 * RING];
    uint32_t write, scan;
    float lag, older, previous, best, best_lag, dec_odd, dry;
    Allpass dec[3], interp[4];
    Voice voices[PITCH_VOICES];
    uint32_t bypassed;
} state;

static float allpass(Allpass *s, float input, float coefficient) {
    const float output = coefficient * (input - s->output) + s->input;
    s->input = input;
    s->output = output;
    return output;
}

static float lowpass(Lowpass *s, float input) {
    const float output = input * 0x1.11cf44p-1f + s->input * 0x1.11cf44p-1f
                       - s->output * 0x1.1cf444p-4f;
    s->input = input;
    s->output = output;
    return output;
}

static void track(void) {
    const int16_t *a = state.line + RING + state.write - 128u;
    const int16_t *b = a - state.scan;
    int32_t aa = 0, bb = 0, ab = 0;
    // Downscale to 13 signed bits so the 32-point sums fit in int32.
    for (uint32_t i = 0; i < 128; i += 4) {
        const int32_t x = a[i] >> 3, y = b[i] >> 3;
        aa += x * x;
        bb += y * y;
        ab += x * y;
    }
    const int32_t energy = aa + bb;
    const float current = energy < 16 ? 3.0f
        : 1.0f - 2.0f * (float)ab / (float)energy;
    const float prev = state.previous, older = state.older;
    if (current < 3.0f && older < 3.0f && prev <= older && prev < current) {
        const float den = older - 2.0f * prev + current;
        const float offset = den > 1e-8f ? 0.5f * (older - current) / den : 0.0f;
        const float score = prev - 0.25f * (older - current) * offset;
        if (score < state.best - 0.01f) {
            state.best = score;
            state.best_lag = (float)(state.scan - 1u) + offset;
        }
    }
    state.older = prev;
    state.previous = current;
    if (++state.scan > MAX_LAG + 1u) {
        if (state.best < 3.0f) {
            const float lag = state.best_lag;
            state.lag = lag < MIN_LAG ? MIN_LAG : lag > MAX_LAG ? MAX_LAG : lag;
        }
        state.scan = MIN_LAG - 1u;
        state.best = state.older = state.previous = 3.0f;
    }
}

static void reset_tap(Tap *tap, float slope) {
    tap->slope = slope;
    // The largest supported upward ratio moves three samples per step.
    tap->fade = slope < -1.984375f ? (uint32_t)(254.0f / -slope) : 128u;
    tap->weight_step = 1.0f / (float)tap->fade;
    tap->near_delay = slope < 0.0f ? 2.0f - (float)tap->fade * slope : 2.0f;
    tap->delay = slope < 0.0f ? tap->near_delay + state.lag : 2.0f;
    tap->incoming = 0.0f;
    tap->step = 0;
}

static float read_line(float delay) {
    const uint32_t whole = (uint32_t)delay;
    const float fraction = delay - (float)whole;
    const int16_t *p = state.line + RING + state.write - whole;
    return ((float)p[0] + fraction * (float)(p[-1] - p[0])) * (1.0f / 32768.0f);
}

static float smooth(float position) {
    return position * position * (3.0f - 2.0f * position);
}

static float step_tap(Tap *tap) {
    const float slope = tap->slope;
    tap->delay += slope;
    if (tap->step) {
        tap->incoming += slope;
        ++tap->step;
    } else if (slope < 0.0f && tap->delay <= tap->near_delay) {
        tap->incoming = tap->delay + state.lag;
        tap->step = 1;
    } else if (slope > 0.0f && tap->delay >= state.lag + 2.0f) {
        tap->incoming = tap->delay - state.lag;
        tap->step = 1;
    } else {
        return read_line(tap->delay);
    }
    const float incoming = read_line(tap->incoming);
    if (tap->step >= tap->fade) {
        tap->delay = tap->incoming;
        tap->step = 0;
        return incoming;
    }
    const float outgoing = read_line(tap->delay);
    return outgoing + smooth((float)tap->step * tap->weight_step) * (incoming - outgoing);
}

static void prepare_voice(Voice *voice, float slope) {
    if (voice->current.slope != slope && !voice->change) {
        reset_tap(&voice->next, slope);
        voice->change = 1;
    }
}

static float render_voice(Voice *voice) {
    float output = step_tap(&voice->current);
    if (voice->change) {
        const float next = step_tap(&voice->next);
        output += smooth((float)voice->change / CHANGE_FADE) * (next - output);
        if (voice->change == CHANGE_FADE) {
            voice->current = voice->next;
            voice->change = 0;
        } else {
            ++voice->change;
        }
    }
    return lowpass(&voice->lowpass, output);
}

static float decimate(float even, float odd) {
    float a = allpass(&state.dec[0], even, 0x1.d4e3aep-4f);
    a = allpass(&state.dec[1], a, 0x1.8a35fep-1f);
    const float half = (a + state.dec_odd) * 0.5f;
    state.dec_odd = allpass(&state.dec[2], odd, 0x1.97628p-2f);
    return half;
}

static void reset(const float *params) {
#if defined(__clang__)
#pragma clang loop unroll_count(8)
#endif
    for (uint32_t i = 0; i < 2 * RING; ++i) state.line[i] = 0;
    for (uint32_t i = 0; i < 3; ++i) state.dec[i] = (Allpass){0};
    for (uint32_t i = 0; i < 4; ++i) state.interp[i] = (Allpass){0};
    state.write = 0;
    state.scan = MIN_LAG - 1u;
    state.lag = INITIAL_LAG;
    state.best = state.older = state.previous = 3.0f;
    state.dec_odd = 0;
    state.dry = params[2] * 0.01f;
    state.bypassed = 0;
    for (uint32_t i = 0; i < PITCH_VOICES; ++i) {
        Voice *voice = &state.voices[i];
        voice->change = 0;
        voice->lowpass = (Lowpass){0};
        reset_tap(&voice->current, requested_slope(params, i));
    }
}

static void mix_pair(float *pair, float dry, float shifted) {
#if PITCH_VOICES == 2
    if (state.dry < dry) {
        state.dry += 0.0001f;
        if (state.dry > dry) state.dry = dry;
    } else if (state.dry > dry) {
        state.dry -= 0.0001f;
        if (state.dry < dry) state.dry = dry;
    }
#else
    state.dry = dry;
#endif
    const float left = pair[0] * state.dry + shifted;
#if PITCH_VOICES == 2
    pair[1] = pair[1] * state.dry + shifted;
#else
    pair[1] = left;
#endif
    pair[0] = left;
}

GP50_INIT void PITCH_INIT(const float *params) {
    reset(params);
}

GP50_PROCESS void PITCH_PROCESS(float *samples, uint32_t frames, const float *params,
                                 uint32_t reserved_r3, const uint8_t *enable,
                                 const uint32_t *period, void *reserved) {
    (void)reserved_r3;
    (void)period;
    (void)reserved;
    if (!*enable) {
        state.bypassed = 1;
        return;
    }
    if (state.bypassed) reset(params);

    float gains[PITCH_VOICES];
    for (uint32_t i = 0; i < PITCH_VOICES; ++i) {
        prepare_voice(&state.voices[i], requested_slope(params, i));
        gains[i] = params[WET_SLOT + i] * 0.01f;
    }

    const float dry = params[2] * 0.01f;
    for (uint32_t i = 0; i + 1 < frames; i += 2) {
        const float half = decimate(samples[2 * i], samples[2 * i + 2]);
        const float scaled = half * 32768.0f;
        const int16_t sample = scaled > 32767.0f ? 32767
            : scaled < -32768.0f ? -32768 : (int16_t)scaled;
        state.line[state.write] = state.line[state.write + RING] = sample;
        state.write = (state.write + 1u) & (RING - 1u);
        if ((state.write & 3u) == 1u) track();

        float wet = 0.0f;
        for (uint32_t v = 0; v < PITCH_VOICES; ++v)
            wet += render_voice(&state.voices[v]) * gains[v];
        wet *= 0.7f;
        float a = allpass(&state.interp[0], wet, 0x1.472204p-4f);
        a = allpass(&state.interp[1], a, 0x1.1734aap-1f);
        float b = allpass(&state.interp[2], wet, 0x1.22a428p-2f);
        b = allpass(&state.interp[3], b, 0x1.ab380ap-1f);
        mix_pair(samples + 2 * i, dry, a);
        mix_pair(samples + 2 * i + 2, dry, b);
    }
}
