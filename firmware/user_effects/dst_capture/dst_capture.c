/* DST Capture (2026-11-08): selects one of the 30 user capture slots (Slot 1..30 = stored
 * capture slots 50..79) to run before the main capture inside the N->S capture program. No audio work here or in this DSP
 * program; the N->S player reads this program's signature from DSP program memory and the DST
 * enable bit / Slot parameter from the stock working config; the cells written here are informational (program.py, analysis/tone_capture/TWO_CAPTURES_20261108.md). */
#include "gp50_effect.h"
#include "copro_cells.h"
/* DSP data cell (the packaged SDK has no gp50_copro.h; same address form as the stock ARM-side writes). */
#define DST_CELL_U(cell) (*(volatile uint32_t *)(0x28000000u + 4u * (cell)))

static inline void write_cells(const float *params) {
    float s = params[0];
    uint32_t slot = !(s >= 1.0f) ? 1u : s > 30.0f ? 30u : (uint32_t)(s + 0.5f);
    DST_CELL_U(COPRO_CELL_SLOT) = slot;
}

GP50_INIT void dst_capture_init(const float *params) {
    DST_CELL_U(COPRO_CELL_ENABLE) = 0;
    write_cells(params);
}

GP50_PROCESS void dst_capture_process(float *samples, uint32_t frames, const float *params,
                                      uint32_t reserved_r3, const uint8_t *enable,
                                      const uint32_t *beat_period_ms, void *reserved_b18) {
    (void)samples; (void)frames; (void)reserved_r3; (void)beat_period_ms; (void)reserved_b18;
    write_cells(params);
    DST_CELL_U(COPRO_CELL_ENABLE) = *enable ? 1u : 0u;
}
