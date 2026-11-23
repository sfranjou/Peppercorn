/* Auto Swell: a new pick fades in over Attack ms. Keep the swell open through
 * the note's decay; onset sensitivity must not double as a sustain gate.
 * Re-arm only after 120 ms below -80 dBFS, then close over 60 ms.
 * Parameters: Attack, Sens, Shape, VOL. Mono input, dual mono output. */
#include "gp50_effect.h"

static struct {
    float env;     /* peak envelope */
    float ramp;    /* 0..1 progress of the current swell */
    uint32_t quiet; /* consecutive samples near silence */
    uint32_t armed;/* 1 at startup or after sustained near-silence */
} state;

#define ENV_ATTACK  0.0225f   /* 1 - exp(-1/(1 ms * fs)) */
#define ENV_RELEASE 0.000453f /* 1 - exp(-1/(50 ms * fs)) */
#define SILENCE_LEVEL 0.0001f
#define QUIET_SAMPLES 5292u /* 120 ms at 44.1 kHz */
#define FADE_STEP (1.0f / 2646.0f) /* 60 ms, after sustained silence */

GP50_INIT void auto_swell_init(const float *params) {
    (void)params;
    state.env = 0.0f;
    state.ramp = 0.0f;
    state.quiet = 0u;
    state.armed = 1u;
}

GP50_PROCESS void auto_swell_process(float *samples, uint32_t frames, const float *params,
                                     uint32_t reserved_r3, const uint8_t *enable,
                                     const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    if (*enable == 0) return;
    const float step = 1000.0f / (params[0] * GP50_SAMPLE_RATE);          /* ramp per sample */
    const float sens = params[1] * 0.01f;
    const float threshold = 0.001f + (1.0f - sens) * (1.0f - sens) * 0.2f; /* sens 100 = most sensitive */
    const float shape = params[2] * 0.01f;
    const float volume = params[3] * 0.02f;
    float env = state.env, ramp = state.ramp;
    uint32_t armed = state.armed, quiet = state.quiet;
    for (uint32_t i = 0; i < frames; i++) {
        const float x = samples[2 * i];
        const float a = x < 0.0f ? -x : x;
        env += (a - env) * (a > env ? ENV_ATTACK : ENV_RELEASE);
        if (env < SILENCE_LEVEL) {
            if (quiet < QUIET_SAMPLES) quiet++;
            if (quiet == QUIET_SAMPLES) armed = 1u;
        } else quiet = 0u;
        if (armed && env > threshold) { armed = 0u; ramp = 0.0f; }
        if (armed) { ramp -= FADE_STEP; if (ramp < 0.0f) ramp = 0.0f; }
        else if (ramp < 1.0f) { ramp += step; if (ramp > 1.0f) ramp = 1.0f; }
        /* shape: blend linear with cubic (slow start) */
        const float g = ramp + (ramp * ramp * ramp - ramp) * shape;
        const float y = x * g * volume;
        samples[2 * i] = y;
        samples[2 * i + 1] = y;
    }
    state.env = env; state.ramp = ramp; state.armed = armed; state.quiet = quiet;
}
