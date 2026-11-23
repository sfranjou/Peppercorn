/* C-Wah auto engage (MOD027 behaviour, moved onto the SDK): with C-Wah in PRE, its "Auto Engage" switch on and the
 * expression pedal driving PRE Position, rocking the pedal to the heel bypasses the wah after 200 ms and leaving the
 * heel turns it back on. Only a bypass this feature made is undone; when the conditions go away, it gives that
 * bypass back. A computer reads the state with `12 7b` -> `12 7b 01 active owned heel timing`.
 * Thresholds: heel at <= 1 % travel, left at >= 2 % (hysteresis). */
#include "gp50.h"

#define C_WAH 0x05000008u          /* public model ID */
#define AUTO_ENGAGE 4u             /* C-Wah parameter: Auto Engage, 0 or 1 */
#define POSITION 3u                /* C-Wah parameter the pedal must drive */
#define HEEL_ENTER 10u             /* permille */
#define HEEL_LEAVE 20u
#define BYPASS_AFTER_MS 200u

typedef struct {
    uint32_t active, preset, timing, start, owned, heel;   /* owned: the current bypass is ours to undo */
} State;

static void awh_clear(State *s) { s->active = s->timing = s->owned = s->heel = 0; }

static uint32_t awh_conditions_hold(void) {
    float engage;
    gp50_expression e;
    if (gp50_param_get(GP50_PRE, AUTO_ENGAGE, &engage) || engage != 1.0f) return 0;
    if (gp50_expression_get(0, &e) || !e.enabled || e.block != GP50_PRE || e.param != POSITION || !e.calibrated) return 0;
    return 1;
}

void auto_wah_tick(const gp50_ctx *ctx) {
    State *s = ctx->state;
    if (gp50_block_model(GP50_PRE) != C_WAH) { awh_clear(s); return; }
    uint32_t preset = gp50_preset_number();
    if (s->active && s->preset != preset) awh_clear(s);                 /* another preset: start over */
    if (!awh_conditions_hold()) {                                       /* give back a bypass we own */
        if (s->active && s->owned && !gp50_block_enabled(GP50_PRE)) (void)gp50_block_set_enabled(GP50_PRE, 1);
        awh_clear(s);
        return;
    }
    uint32_t started = 0;
    if (!s->active) { s->active = 1; s->preset = preset; s->timing = s->owned = s->heel = 0; started = 1; }
    gp50_expression e;
    (void)gp50_expression_get(0, &e);
    if (e.position <= HEEL_ENTER) s->heel = 1;
    else if (e.position >= HEEL_LEAVE) s->heel = 0;
    uint32_t enabled = gp50_block_enabled(GP50_PRE);
    if (started) s->owned = !enabled;                               /* bypassed when we started: ours to engage */
    if (!s->heel) {                                                 /* off the heel: engage a bypass we own */
        s->timing = 0;
        if (!s->owned) return;
        s->owned = 0;
        if (!enabled) (void)gp50_block_set_enabled(GP50_PRE, 1);
        return;
    }
    if (!enabled) { if (!s->owned) s->timing = 0; return; }        /* heel, already bypassed */
    s->owned = 0;                                                   /* heel, enabled: bypass after the dwell */
    uint32_t now = gp50_millis();
    if (!s->timing) { s->timing = 1; s->start = now; return; }
    if (gp50_elapsed_ms(now, s->start) < BYPASS_AFTER_MS) return;
    s->timing = 0;
    if (gp50_block_set_enabled(GP50_PRE, 0) == GP50_OK) s->owned = 1;
}

uint32_t auto_wah_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    const State *s = ctx->state;
    if (capacity < 5) return 0;
    out[0] = 1; out[1] = (uint8_t)s->active; out[2] = (uint8_t)s->owned; out[3] = (uint8_t)s->heel; out[4] = (uint8_t)s->timing;
    return 5;
}
