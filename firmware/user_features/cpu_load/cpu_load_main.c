/* Global settings > CPU (the 12th tile, after About), refreshed about twice a second while the tile is selected:
 *   CPU load: 47%   the estimate CPU protection uses (gp50_dsp_load)
 *   ARM: 61%        measured main audio processor load, percent of an audio block (gp50_load_get)
 *   DSP: 38%        measured audio coprocessor ratio on the same scale ("--" until a reading arrives)
 * A computer reads the estimate with `12 7a` -> `12 7a 01 <percent u16 LE>` (ffff = unknown) and the measurements
 * with the existing `12 50`. Read-only: knobs do nothing on the tile; changes nothing else. */
#include "gp50.h"

static uint32_t cpl_put_number(char *out, uint32_t value) {   /* decimal, no leading zeros; returns digits written */
    char digits[10];
    uint32_t n = 0, k = 0;
    do { digits[n++] = (char)('0' + value % 10u); value /= 10u; } while (value && n < sizeof digits);
    while (n) out[k++] = digits[--n];
    return k;
}

static uint32_t cpl_percent(char *out, uint32_t value) {
    if (value > 999u) value = 999u;
    uint32_t n = cpl_put_number(out, value);
    out[n++] = '%';
    return n;
}
static uint32_t cpl_measured(char *out, float ratio) {   /* ratio of a block -> rounded percent; nonsense -> "--" */
    if (!(ratio >= 0.0f) || ratio > 9.99f) { out[0] = '-'; out[1] = '-'; return 2; }
    return cpl_percent(out, (uint32_t)(ratio * 100.0f + 0.5f));
}

uint32_t cpu_load_value(const gp50_ctx *ctx, uint32_t item, char *out, uint32_t capacity) {
    (void)ctx;
    if (capacity < 5) return 0;
    if (item == GP50_MENU_ITEM_1) {
        uint32_t load = gp50_dsp_load();
        if (load == GP50_DSP_UNKNOWN) { out[0] = '-'; out[1] = '-'; return 2; }
        return cpl_percent(out, load);
    }
    if (item != GP50_MENU_ITEM_2 && item != GP50_MENU_ITEM_3) return 0;
    gp50_load m;
    gp50_load_get(&m);
    if (m.status != GP50_METER_OK) { out[0] = '-'; out[1] = '-'; return 2; }   /* no reading yet, or stale */
    return cpl_measured(out, item == GP50_MENU_ITEM_2 ? m.arm : m.dsp);
}

uint32_t cpu_load_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    if (capacity < 3) return 0;
    uint32_t load = gp50_dsp_load();
    uint32_t v = load == GP50_DSP_UNKNOWN ? 0xffffu : load > 0xfffeu ? 0xfffeu : load;
    out[0] = 1; out[1] = (uint8_t)v; out[2] = (uint8_t)(v >> 8);
    return 3;
}
