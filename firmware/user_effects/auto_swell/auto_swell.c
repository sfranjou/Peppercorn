/* Auto Swell: attenuate the pick attack, then leave the note's decay intact.
 * Parameters: Attack (ms), Sens, Shape, VOL. Mono input, dual mono output. */
#include "gp50_effect.h"

static struct {
    float envelope; /* fast peak with enough release to bridge guitar periods */
    float peak;     /* highest envelope since the last detected pick */
    float valley;   /* lowest envelope after a sustained dip */
    float ramp;     /* 0..1 progress of the swell */
    uint32_t dip;
    uint32_t quiet;
    uint32_t active;
} state;

#define PEAK_RELEASE 0.00113f /* 20 ms time constant at 44.1 kHz */
#define QUIET_LEVEL 0.0005f
#define QUIET_SAMPLES 1764u  /* 40 ms below the envelope floor */
#define DIP_SAMPLES 1102u    /* at least 25 ms below one quarter of the peak */

GP50_INIT void auto_swell_init(const float *params) {
    (void)params;
    state.envelope = 0.0f;
    state.peak = 0.0f;
    state.valley = 0.0f;
    state.ramp = 0.0f;
    state.dip = 0u;
    state.quiet = 0u;
    state.active = 0u;
}

GP50_PROCESS void auto_swell_process(float *samples, uint32_t frames, const float *params,
                                     uint32_t reserved_r3, const uint8_t *enable,
                                     const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    if (*enable == 0) {
        if (state.active || state.envelope != 0.0f) auto_swell_init(params);
        return;
    }
    const float attack = params[0] >= 10.0f && params[0] <= 2000.0f ? params[0] : 400.0f;
    const float step = 1000.0f / (attack * GP50_SAMPLE_RATE);
    const float sens = params[1] * 0.01f;
    const float threshold = 0.001f + (1.0f - sens) * (1.0f - sens) * 0.024f;
    const float shape = params[2] * 0.01f;
    const float volume = params[3] * 0.02f;
    float env = state.envelope, peak = state.peak, valley = state.valley, ramp = state.ramp;
    uint32_t dip = state.dip, quiet = state.quiet, active = state.active;
    for (uint32_t i = 0; i < frames; i++) {
        const float x = samples[2 * i];
        const float amplitude = x < 0.0f ? -x : x;
        env = amplitude >= env ? amplitude : env + (amplitude - env) * PEAK_RELEASE;

        if (env < QUIET_LEVEL) {
            if (quiet < QUIET_SAMPLES) quiet++;
            if (quiet == QUIET_SAMPLES) active = 0u;
        } else quiet = 0u;

        uint32_t onset = 0;
        if (active) {
            if (env > peak) peak = env;
            if (dip == DIP_SAMPLES) {
                if (env < valley) valley = env;
                onset = env >= threshold && env > 2.0f * valley;
            } else if (env <= 0.25f * peak) {
                if (++dip == DIP_SAMPLES) valley = env;
            } else dip = 0u;
        } else onset = env >= threshold;

        if (onset) {
            active = 1u;
            ramp = 0.0f;
            peak = env;
            dip = 0u;
        }
        const float g = ramp + (ramp * ramp * ramp - ramp) * shape;
        const float y = x * g * volume;
        samples[2 * i] = y;
        samples[2 * i + 1] = y;
        if (active && ramp < 1.0f) {
            ramp += step;
            if (ramp > 1.0f) ramp = 1.0f;
        }
    }
    state.envelope = env;
    state.peak = peak;
    state.valley = valley;
    state.ramp = ramp;
    state.dip = dip;
    state.quiet = quiet;
    state.active = active;
}
