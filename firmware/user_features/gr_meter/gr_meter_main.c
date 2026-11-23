/* GR meter (MOD035/037 behaviour, moved onto the SDK): while the effect editor shows GR Comp in PRE, the strip at the
 * top shows "Gain Reduction", the peak-held value ("3.5 dB") and a 0..20 dB bar ( "--", "ERR", "OLD", "NONE", "OFF" when there
 * is no usable reading). A computer reads the same reading with `12 7c` -> `12 7c 01 status gr_lo gr_hi`
 * (status = GP50_METER_*, gain reduction in 0.01 dB). */
#include "gp50.h"

#define GR_COMP 0x01000041u        /* public model ID (PRE) */
#define BAR_TENTHS 200u            /* bar full scale: 20.0 dB */

static void grm_put(char *d, const char *s) { while ((*d++ = *s++)) {} }

/* "d.d dB" / "dd.d dB" from 0.01 dB (clamped to 60.0 dB); returns tenths of a dB. */
static uint32_t grm_gr_text(uint32_t hold, char *d) {
    if (hold > 6000u) hold = 6000u;
    uint32_t t = (hold + 5u) / 10u;
    if (t / 100u) *d++ = (char)('0' + t / 100u);
    *d++ = (char)('0' + t / 10u % 10u);
    *d++ = '.'; *d++ = (char)('0' + t % 10u);
    grm_put(d, " dB");
    return t;
}

uint32_t gr_meter_strip(const gp50_ctx *ctx, uint32_t block, gp50_strip *s) {
    (void)ctx;
    if (block != GP50_PRE || gp50_block_model(GP50_PRE) != GR_COMP) return 0;
    gp50_meter m;
    if (gp50_meter_get(&m)) return 0;
    static const char *const word[] = {"", "--", "ERR", "OLD", "NONE", "OFF"};
    grm_put(s->label, "Gain Reduction");
    s->level_max = BAR_TENTHS; s->level = 0;
    if (m.status == GP50_METER_OK) {
        uint32_t t = grm_gr_text(m.gain_reduction, s->value);
        s->level = (uint16_t)(t < BAR_TENTHS ? t : BAR_TENTHS);
    } else grm_put(s->value, m.status < 6 ? word[m.status] : "--");
    return 1;
}

uint32_t gr_meter_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    gp50_meter m;
    if (capacity < 4 || gp50_meter_get(&m)) return 0;
    out[0] = 1; out[1] = m.status; out[2] = (uint8_t)m.gain_reduction; out[3] = (uint8_t)(m.gain_reduction >> 8);
    return 4;
}
