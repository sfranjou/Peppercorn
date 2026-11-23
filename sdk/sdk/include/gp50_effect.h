/* GP-50 V1.1.0 ARM overlay ABI for the ARM-side effect groups (NR, PRE, MOD, DLY).
 * Evidence: analysis/firmware/DSP_CALL_ABI.md, DSP_LOADER.md, ARM_ARCHITECTURE.md 4.2,
 * prototype/sine_trem_model.py (instruction-level reading of a stock overlay, confirmed
 * against pedal audio 2026-10-11).
 *
 * The loader clears the group's execution slot, copies the overlay's primary payload to
 * the slot base and calls init once; process is then called from the audio PendSV handler
 * for every 64-frame block, bypassed or not.
 *
 * Rules for overlay code (all followed by the stock overlays):
 *  - no libc/libm, no calls or data references outside the slot, no heap;
 *  - single-precision float only; FPSCR has flush-to-zero and default-NaN set;
 *  - small stack (handler mode, 4 KiB main stack already holding a 0x914-byte frame);
 *  - never block; cost matters (see work/host_effect_control/model_matrix_full);
 *  - zero-initialised state lives after the payload inside the slot (.bss).
 */
#ifndef GP50_EFFECT_H
#define GP50_EFFECT_H
#include <stdint.h>

#define GP50_SAMPLE_RATE 44100.0f
#define GP50_BLOCK_FRAMES 64u

/* params: eight float32 indexed by the catalog storage index, already clamped and stepped
 * by the NDS32 application (protocol/param_rules.py). */
typedef void gp50_init_fn(const float *params);

/* samples: interleaved stereo float32, processed in place; the chain is mono in practice
 *          (stock overlays read word 0 of each frame and write both words).
 * frames:  64 in stock firmware; honour the argument.
 * enable:  *enable == 0 means bypassed: stock overlays return without touching anything.
 * beat_period_ms: 60000 / tempo, for tempo-synced effects. */
typedef void gp50_process_fn(float *samples, uint32_t frames, const float *params,
                             uint32_t reserved_r3, const uint8_t *enable,
                             const uint32_t *beat_period_ms, void *reserved_b18);

#define GP50_INIT    __attribute__((section(".text.gp50_init"), used, noinline))
#define GP50_PROCESS __attribute__((section(".text.gp50_process"), used, noinline))
#endif
