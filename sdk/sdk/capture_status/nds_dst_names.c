/* DST Capture Slot shows the capture name.
 *
 * Stock parameter value text: 0x43c92 (module, parameter, buffer, length, value in fs0) and its stored-value form
 * 0x43d36 (module, parameter, buffer, length) — firmware/reconstructed/nds/data_settings.c data_param_text /
 * data_param_text_stored. Every parameter text on the pedal goes through them (effect editor rows, home knob tiles,
 * A/B footswitch messages). Both entries are hooked (scripts/nds_ui/features/capture_status_c.py):
 *   0x43c92 -> gp50_dst_param_text: the DST Capture Slot (block 2 holding public ID 0x0300007c, parameter 0,
 *              value 1..30 = user capture slot 50..79) prints the SnapTone slot name exactly as the N->S block's
 *              model name does (stock data_algo_info module 9 -> slot-table name copy 0x19d62); anything else goes
 *              to the stock body through the prologue-replay stub gp50_param_text_stock_43c92.
 *   0x43d36 -> gp50_dst_param_text_stored: stored value (stock 0x43a9e, fs0) then gp50_dst_param_text, as the stock
 *              0x43d36 does with 0x43c92.
 * Hard float (C_HARD_FLOAT_SOURCES): only stock code calls these, through the hook sites, with the stock fs0
 * convention. */
#include <stdint.h>

#define DST_BLOCK 2u
#define DST_CAPTURE_ID 0x0300007cu
#define LIVE_MODEL_IDS 0x200106d3u   /* live public model IDs, u32 LE unaligned, 4 per block (gp50_services.c) */
#define SNAPTONE_NAME 0x19d62u       /* (slot, buffer, size): SnapTone slot name copy, at most 16 bytes, no NUL when full */
#define STORED_VALUE 0x43a9eu        /* (module, parameter) -> stored value (fs0) */

uint32_t gp50_param_text_stock_43c92(uint32_t module, uint32_t parameter, uint32_t buffer, uint32_t length, float value);

static uint32_t dst_holds_capture(void) {
    const volatile uint8_t *ids = (const volatile uint8_t *)(uintptr_t)(LIVE_MODEL_IDS + 4u * DST_BLOCK);
    uint32_t id = (uint32_t)ids[0] | (uint32_t)ids[1] << 8 | (uint32_t)ids[2] << 16 | (uint32_t)ids[3] << 24;
    return id == DST_CAPTURE_ID;
}

uint32_t gp50_dst_param_text(uint32_t module, uint32_t parameter, uint32_t buffer, uint32_t length, float value) {
    if (module == DST_BLOCK && parameter == 0 && length >= 2u && length <= 64u && value >= 0.5f && value < 30.5f &&
        dst_holds_capture()) {
        volatile uint8_t *out = (volatile uint8_t *)(uintptr_t)buffer;
        for (uint32_t i = 0; i < length; i++) out[i] = 0;
        uint32_t size = length - 1u < 16u ? length - 1u : 16u;   /* leaves the NUL */
        ((uint32_t (*)(uint32_t, uint8_t *, int32_t))(uintptr_t)SNAPTONE_NAME)(49u + (uint32_t)(value + 0.5f),
                                                                              (uint8_t *)(uintptr_t)buffer, (int32_t)size);
        return 0;
    }
    return gp50_param_text_stock_43c92(module, parameter, buffer, length, value);
}

uint32_t gp50_dst_param_text_stored(uint32_t module, uint32_t parameter, uint32_t buffer, uint32_t length) {
    float value = ((float (*)(uint32_t, uint32_t))(uintptr_t)STORED_VALUE)(module, parameter);
    return gp50_dst_param_text(module, parameter, buffer, length, value);
}
