/* Heel dwell and bypass ownership for the block controlled by the EXP pedal. */
#include "gp50.h"

#define HEEL_ENTER 10u             /* permille */
#define HEEL_LEAVE 20u
#define DEFAULT_RELEASE_MS 200u

/* Keep the on-disk and host values used by existing EXP presets. */
enum { OFF = 1, ON = 2 };
typedef struct {
    uint32_t model, start;
    uint16_t release_ms;
    uint8_t mode, active, preset, block, timing, owned, heel, waiting;
} State;

static void awh_clear(State *s) { s->active = s->timing = s->owned = s->heel = s->waiting = 0; }

void auto_wah_load(const gp50_ctx *ctx, const uint8_t *in, uint32_t n) {
    State *s = ctx->state;
    awh_clear(s);
    uint32_t release = n == 3 ? in[1] | (uint32_t)in[2] << 8 : DEFAULT_RELEASE_MS;
    s->mode = (n == 1 || n == 3) && in[0] == ON ? ON : OFF;
    s->release_ms = release <= GP50_EXPRESSION_RELEASE_MAX ? release : DEFAULT_RELEASE_MS;
}

uint32_t auto_wah_save(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    const State *s = ctx->state;
    if (capacity < 3 || (s->mode == OFF && s->release_ms == DEFAULT_RELEASE_MS)) return 0;
    out[0] = s->mode;
    out[1] = (uint8_t)s->release_ms;
    out[2] = (uint8_t)(s->release_ms >> 8);
    return 3;
}

static void awh_configure(State *s, uint32_t mode, uint32_t release) {
    if (s->mode == mode && s->release_ms == release) return;
    s->mode = mode;
    s->release_ms = release;
    gp50_preset_mark_modified();
}

uint32_t auto_wah_set(const gp50_ctx *ctx, const uint8_t *in, uint32_t n) {
    State *s = ctx->state;
    if (n != 3 || in[0] > ON) return GP50_REFUSED;
    uint32_t release = in[1] | (uint32_t)in[2] << 8;
    if (release == 0xffffu) release = s->release_ms;
    if (release > GP50_EXPRESSION_RELEASE_MAX) return GP50_REFUSED;
    awh_configure(s, in[0] ? in[0] : s->mode, release);
    return GP50_OK;
}

uint32_t auto_wah_event(const gp50_ctx *ctx, const gp50_event *event) {
    if (event->kind != GP50_EVENT_KNOB || event->screen != GP50_SCREEN_EDITOR ||
        !event->value) return GP50_PASS;
    uint32_t page = gp50_editor_expression_page();
    if ((page != 1 || event->index != GP50_KNOB_3) &&
        (page != 2 || event->index != GP50_KNOB_1)) return GP50_PASS;
    gp50_expression expression;
    if (gp50_expression_get(0, &expression) != GP50_OK || !expression.enabled ||
        expression.block >= GP50_BLOCKS) return GP50_PASS;
    State *s = ctx->state;
    if (page == 1) awh_configure(s, event->value > 0 ? ON : OFF, s->release_ms);
    else {
        int32_t steps = event->value;
        int32_t limit = GP50_EXPRESSION_RELEASE_MAX / 10;
        if (steps < -limit) steps = -limit;
        if (steps > limit) steps = limit;
        int32_t release = s->release_ms + steps * 10;
        if (release < 0) release = 0;
        if (release > GP50_EXPRESSION_RELEASE_MAX) release = GP50_EXPRESSION_RELEASE_MAX;
        awh_configure(s, s->mode, (uint32_t)release);
    }
    return GP50_CONSUMED;
}

uint32_t auto_wah_config(const gp50_ctx *ctx) {
    const State *s = ctx->state;
    return (uint32_t)s->release_ms << 1 | (s->mode == ON);
}

void auto_wah_tick(const gp50_ctx *ctx) {
    State *s = ctx->state;
    uint32_t preset = gp50_preset_number();
    if (s->active && s->preset != preset) awh_clear(s);
    if (!s->active && s->mode != ON) return;
    gp50_expression e;
    if (gp50_expression_get(0, &e) != GP50_OK) return;
    uint32_t block = e.block;
    uint32_t model = block < GP50_BLOCKS ? gp50_block_model(block) : 0;
    uint32_t eligible = s->mode == ON && e.enabled && e.calibrated && model
        && e.param < gp50_param_count(block);
    if (s->active && (!eligible || block != s->block || model != s->model)) {
        if (s->owned && gp50_block_model(s->block) == s->model && !gp50_block_enabled(s->block))
            (void)gp50_block_set_enabled(s->block, 1);
        awh_clear(s);
    }
    if (!eligible) return;
    uint32_t started = !s->active;
    if (started) {
        s->active = 1;
        s->preset = (uint8_t)preset;
        s->block = (uint8_t)block;
        s->model = model;
    }
    uint32_t was_heel = s->heel;
    if (e.position <= HEEL_ENTER) s->heel = 1;
    else if (e.position >= HEEL_LEAVE) s->heel = 0;
    uint32_t enabled = gp50_block_enabled(block);
    /* Await first engage without claiming that we bypassed the block. */
    if (started) s->waiting = !enabled;
    if (enabled) s->waiting = s->owned = 0;
    if (!s->heel) {
        s->timing = 0;
        /* A refused enable can be tried on the next sweep, never every tick. */
        if ((s->waiting || s->owned) && (started || was_heel) &&
            gp50_block_set_enabled(block, 1) == GP50_OK)
            s->waiting = s->owned = 0;
        return;
    }
    if (!enabled) { s->timing = 0; return; }
    uint32_t now = gp50_millis();
    if (!s->timing) { s->timing = 1; s->start = now; }
    if (gp50_elapsed_ms(now, s->start) < s->release_ms) return;
    s->timing = 0;
    if (gp50_block_set_enabled(block, 0) == GP50_OK) s->owned = 1;
}

uint32_t auto_wah_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    const State *s = ctx->state;
    if (capacity < 8) return 0;
    out[0] = 2; out[1] = (uint8_t)s->active; out[2] = (uint8_t)s->owned; out[3] = (uint8_t)s->heel; out[4] = (uint8_t)s->timing;
    out[5] = s->mode == ON;
    out[6] = (uint8_t)s->release_ms;
    out[7] = (uint8_t)(s->release_ms >> 8);
    return 8;
}
