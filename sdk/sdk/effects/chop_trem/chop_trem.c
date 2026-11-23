/* Chop Trem: square-wave tremolo with a short smoothing ramp. First SDK effect.
 * Parameters (storage index): 0 Depth 0..100, 1 Rate 0.1..10 Hz, 2 VOL 0..100 (50 = unity).
 * Mono in (word 0 of each frame), same signal to both output words, polarity preserved. */
#include "gp50_effect.h"

static struct {
    float phase;   /* 0..1 */
    float gain;    /* smoothed chop gain */
} state;

#define SMOOTH 0.01f /* per-sample one-pole coefficient: about 2 ms to settle */

GP50_INIT void chop_trem_init(const float *params) {
    (void)params;
    state.phase = 0.0f;
    state.gain = 1.0f;
}

GP50_PROCESS void chop_trem_process(float *samples, uint32_t frames, const float *params,
                                    uint32_t reserved_r3, const uint8_t *enable,
                                    const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    if (*enable == 0) return;
    const float depth = params[0] * 0.01f;
    const float increment = params[1] * (1.0f / GP50_SAMPLE_RATE);
    const float volume = params[2] * 0.02f;
    float phase = state.phase, gain = state.gain;
    for (uint32_t i = 0; i < frames; i++) {
        phase += increment;
        if (phase >= 1.0f) phase -= 1.0f;
        const float target = phase < 0.5f ? 1.0f : 1.0f - depth;
        gain += (target - gain) * SMOOTH;
        const float y = samples[2 * i] * gain * volume;
        samples[2 * i] = y;
        samples[2 * i + 1] = y;
    }
    state.phase = phase;
    state.gain = gain;
}
