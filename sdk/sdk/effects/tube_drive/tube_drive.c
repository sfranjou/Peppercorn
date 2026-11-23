/* Tube Drive: DST-group effect whose audio runs on the DSP coprocessor (program.py).
 * This ARM half only turns the knobs into float cells; it never touches the sample buffer.
 * Parameters (storage index): 0 Gain 0..100, 1 Tone 0..100, 2 VOL 0..100.
 *   drive = 3 + Gain^2 * 0.0147                      3 .. 150   (smoothed by the program)
 *   a     = 0.09 + (Tone/100)^2 * 0.6                one-pole low-pass coefficient, about 0.7 .. 8 kHz
 *   level = (VOL/50)^2 * (0.08 + 0.75/drive) + 1e-6  output level with make-up (smoothed by the program);
 *                                                    the floor keeps the level ramp away from denormals
 * The high-pass coefficients are fixed (140 Hz Butterworth) and written by init only, as stock
 * DST overlays do with their fixed filters. Smoothing follows the stock split: the ARM half
 * stores targets, the program ramps (Sora Fuzz D[0x1ae]/D[0x1af]). The same constants are in
 * model.py; sdk/test_tube_drive.py compares the cells bit for bit. */
#include "gp50_effect.h"
#include "gp50_copro.h"
#include "copro_cells.h"

#define DRIVE_MIN 3.0f
#define DRIVE_CURVE 0.0147f
#define TONE_MIN 0.09f
#define TONE_CURVE 0.6f
#define OUT_SCALE 0.08f
#define MAKEUP 0.75f
#define LEVEL_FLOOR 1e-6f

static inline float drive_of(const float *params) {
    const float g = params[0];
    return DRIVE_MIN + g * g * DRIVE_CURVE;
}

static inline float level_of(const float *params, float drive) {
    const float v = params[2] * 0.02f;
    return v * v * (OUT_SCALE + MAKEUP / drive) + LEVEL_FLOOR;
}

static inline float tone_of(const float *params) {
    const float t = params[1] * 0.01f;
    return TONE_MIN + t * t * TONE_CURVE;
}

GP50_INIT void tube_drive_init(const float *params) {
    const float drive = drive_of(params);
    const float level = level_of(params, drive);
    GP50_COPRO_U(COPRO_CELL_ENABLE) = 0;
    GP50_COPRO_F(COPRO_CELL_HP_B0) = 0.985994606f;
    GP50_COPRO_F(COPRO_CELL_HP_B1) = -1.97198921f;
    GP50_COPRO_F(COPRO_CELL_HP_B2) = 0.985994606f;
    GP50_COPRO_F(COPRO_CELL_HP_A1) = -1.97179305f;
    GP50_COPRO_F(COPRO_CELL_HP_A2) = 0.972185372f;
    GP50_COPRO_U(COPRO_CELL_HP_S1) = 0;
    GP50_COPRO_U(COPRO_CELL_HP_S2) = 0;
    GP50_COPRO_F(COPRO_CELL_DRIVE_TGT) = drive;
    GP50_COPRO_F(COPRO_CELL_DRIVE_CUR) = drive;
    GP50_COPRO_F(COPRO_CELL_TONE_A) = tone_of(params);
    GP50_COPRO_U(COPRO_CELL_TONE_Z) = 0;
    GP50_COPRO_F(COPRO_CELL_LEVEL_TGT) = level;
    GP50_COPRO_F(COPRO_CELL_LEVEL_CUR) = level;
}

GP50_PROCESS void tube_drive_process(float *samples, uint32_t frames, const float *params,
                                     uint32_t reserved_r3, const uint8_t *enable,
                                     const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)samples; (void)frames; (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    const float drive = drive_of(params);
    GP50_COPRO_F(COPRO_CELL_DRIVE_TGT) = drive;
    GP50_COPRO_F(COPRO_CELL_TONE_A) = tone_of(params);
    GP50_COPRO_F(COPRO_CELL_LEVEL_TGT) = level_of(params, drive);
    GP50_COPRO_U(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;
}
