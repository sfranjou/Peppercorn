#include "gp50.h"

#define BAR_TENTHS 200u

static void copy_text(char *dst, const char *src) {
    while ((*dst++ = *src++)) {}
}

uint32_t stock_gr_meter_strip(const gp50_ctx *ctx, uint32_t block, gp50_strip *strip) {
    (void)ctx;
    if (block != GP50_NR && block != GP50_PRE) return 0;
    uint32_t model = gp50_block_model(block);
    if (block == GP50_NR ? model != 0x1bu : model > 1u) return 0;
    gp50_meter gate, pre;
    if (gp50_stock_meters_get(&gate, &pre)) return 0;
    const gp50_meter *meter = block == GP50_NR ? &gate : &pre;
    copy_text(strip->label, "Gain Reduction");
    strip->level_max = BAR_TENTHS;
    strip->level = 0;
    if (meter->status == GP50_METER_OK) {
        uint32_t tenths = (meter->gain_reduction + 5u) / 10u;
        uint32_t shown = tenths <= 600u ? tenths : 600u;
        char *value = strip->value;
        if (shown >= 100u) *value++ = (char)('0' + shown / 100u);
        *value++ = (char)('0' + shown / 10u % 10u);
        *value++ = '.';
        *value++ = (char)('0' + shown % 10u);
        copy_text(value, " dB");
        strip->level = (uint16_t)(tenths < BAR_TENTHS ? tenths : BAR_TENTHS);
    } else {
        static const char *const words[] = {"", "--", "ERR", "OLD", "NONE", "OFF"};
        copy_text(strip->value, meter->status < 6 ? words[meter->status] : "--");
    }
    return 1;
}

static void encode(uint8_t *out, const gp50_meter *meter) {
    out[0] = meter->status;
    out[1] = (uint8_t)meter->gain_reduction;
    out[2] = (uint8_t)(meter->gain_reduction >> 8);
}

uint32_t stock_gr_meter_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    gp50_meter gate, pre;
    if (capacity < 7 || gp50_stock_meters_get(&gate, &pre)) return 0;
    out[0] = 1;
    encode(out + 1, &gate);
    encode(out + 4, &pre);
    return 7;
}
