/* Hard Clip: first SDK effect whose audio runs on the DSP coprocessor (DST group).
 * This ARM half only turns the knobs into the float cells the coprocessor program reads
 * (sdk/effects/hard_clip/program.py); it never touches the sample buffer.
 * Parameters (storage index): 0 Gain 0..100, 1 VOL 0..100 (50 = unity).
 *   gain  = 1 + Gain^2 * 0.0049        1 .. 50 (0 .. +34 dB)
 *   limit = 0.05                       clip level in the chain's float scale (stock Sora Fuzz
 *                                      clips at 1.0 after a fixed x50; guitar peaks measured
 *                                      at the EQ input were about 0.03 .. 0.06)
 *   level = (VOL * 0.02)^2             0 .. 4
 * Gain 0 / VOL 50 gives gain = level = 1.0 exactly: bit-transparent below the limit. */
#include "gp50_effect.h"
#include "gp50_copro.h"
#include "copro_cells.h"

#define GAIN_CURVE 0.0049f
#define LIMIT 0.05f

static inline void write_cells(const float *params) {
    const float g = params[0];
    const float v = params[1] * 0.02f;
    GP50_COPRO_F(COPRO_CELL_GAIN) = 1.0f + g * g * GAIN_CURVE;
    GP50_COPRO_F(COPRO_CELL_LIMIT) = LIMIT;
    GP50_COPRO_F(COPRO_CELL_NLIMIT) = -LIMIT;
    GP50_COPRO_F(COPRO_CELL_LEVEL) = v * v;
}

GP50_INIT void hard_clip_init(const float *params) {
    GP50_COPRO_U(COPRO_CELL_ENABLE) = 0;
    write_cells(params);
}

GP50_PROCESS void hard_clip_process(float *samples, uint32_t frames, const float *params,
                                    uint32_t reserved_r3, const uint8_t *enable,
                                    const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)samples; (void)frames; (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    write_cells(params);
    GP50_COPRO_U(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;
}
