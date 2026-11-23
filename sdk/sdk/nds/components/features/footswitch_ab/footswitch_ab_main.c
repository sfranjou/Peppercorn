/* A/B parameter footswitches (MOD089..092 behaviour, moved onto the SDK). A footswitch bound to a parameter toggles it
 * between two values: when the parameter is at A it goes to B, otherwise to A. An unbound switch keeps its stock job.
 * Feedback in the home title for 2 s: "<name> <value>", "FS1 RE-ASSIGN" (the block holds another effect now),
 * "FS1 BAD DATA" (damaged stored data blocks the switch). Bindings are made on the pedal by the assignment feature
 * or from a computer:
 *   12 74 -> 12 74 01 preset 02 status {dest valid block param flags model32 a32 b32} x2   (status: blocked | 0x80 fault)
 *   11 74 01 dest block param 00 preset model32 a32 b32  (dest 3/4 = FS A/B, block ff = clear;
 *                                                         recovery: dest ff block ff, 01 instead of 00, zeros)  */
#include "gp50.h"

#define SHOW_MS 2000u
enum { MSG_NONE = 0, MSG_READY = 1, MSG_STALE = 2, MSG_INVALID = 3 };
typedef struct { uint32_t since, shown; uint8_t kind, fs, block, param; } State;

static uint32_t fab_f2u(float f) { union { float f; uint32_t u; } x = { .f = f }; return x.u; }
static float fab_u2f(uint32_t u) { union { uint32_t u; float f; } x = { .u = u }; return x.f; }
static uint32_t fab_get32(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static void fab_put32(uint8_t *p, uint32_t v) { p[0] = v; p[1] = v >> 8; p[2] = v >> 16; p[3] = v >> 24; }

/* An endpoint the parameter can hold: finite, inside its range, on its step grid. */
static uint32_t fab_endpoint_ok(uint32_t block, uint32_t param, float v) {
    float lo, hi, step;
    if (!(v == v) || gp50_param_range(block, param, &lo, &hi, &step) || v < lo || v > hi) return 0;
    if (!(step > 0.0f)) return 1;
    float q = (v - lo) / step, r = (float)(int32_t)(q + 0.5f);
    return q - r < 0.001f && r - q < 0.001f;
}
static void fab_note(State *s, uint32_t kind, uint32_t fs, uint32_t block, uint32_t param) {
    s->kind = (uint8_t)kind; s->fs = (uint8_t)fs; s->block = (uint8_t)block; s->param = (uint8_t)param;
    s->since = gp50_millis(); s->shown = 0;
}

uint32_t footswitch_ab_event(const gp50_ctx *ctx, const gp50_event *e) {
    State *s = ctx->state;
    if (e->kind != GP50_EVENT_FOOTSWITCH || e->index >= GP50_FOOTSWITCHES) return GP50_PASS;
    gp50_assignments a;
    if (gp50_assignments_get(&a) || a.preset == GP50_NONE) return GP50_PASS;
    const gp50_footswitch_binding *b = &a.footswitch[e->index];
    if (a.blocked >> e->index & 1u) { fab_note(s, MSG_INVALID, e->index, 0, 0); return GP50_CONSUMED; }
    if (!b->valid) return GP50_PASS;                                  /* unbound: stock toggle (CPU protection) */
    if (gp50_block_model(b->block) != b->model || b->param >= gp50_param_count(b->block)) {
        fab_note(s, MSG_STALE, e->index, 0, 0); return GP50_CONSUMED;
    }
    float now;
    if (gp50_param_get(b->block, b->param, &now) || !fab_endpoint_ok(b->block, b->param, b->a) || !fab_endpoint_ok(b->block, b->param, b->b)) {
        fab_note(s, MSG_INVALID, e->index, 0, 0); return GP50_CONSUMED;
    }
    (void)gp50_param_set(b->block, b->param, now == b->a ? b->b : b->a);
    fab_note(s, MSG_READY, e->index, b->block, b->param);
    return GP50_CONSUMED;
}

void footswitch_ab_tick(const gp50_ctx *ctx) {
    State *s = ctx->state;
    if (s->kind == MSG_NONE || gp50_screen() != GP50_SCREEN_HOME) return;
    if (gp50_elapsed_ms(gp50_millis(), s->since) >= SHOW_MS) { s->kind = MSG_NONE; gp50_home_title_restore(); return; }
    if (s->shown) return;
    char t[32]; uint32_t n = 0;
    if (s->kind == MSG_READY) {
        n = gp50_param_name(s->block, s->param, t, 8);
        t[n++] = ' ';
        n += gp50_param_text(s->block, s->param, t + n, sizeof t - n);
    } else {
        const char *w = s->kind == MSG_STALE ? " RE-ASSIGN" : " BAD DATA";
        t[n++] = 'F'; t[n++] = 'S'; t[n++] = (char)('1' + s->fs);
        while (*w) t[n++] = *w++;
        t[n] = 0;
    }
    if (gp50_home_title(t) == GP50_OK) s->shown = 1;
}

uint32_t footswitch_ab_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    gp50_assignments a;
    if (capacity < 38 || gp50_assignments_get(&a)) return 0;
    for (uint32_t j = 0; j < 38; j++) out[j] = 0;
    out[0] = 1; out[1] = a.preset; out[2] = 2; out[3] = (uint8_t)(a.blocked | (a.fault ? 0x80 : 0));
    for (uint32_t i = 0; i < GP50_FOOTSWITCHES; i++) {
        uint8_t *p = out + 4 + 17 * i; const gp50_footswitch_binding *b = &a.footswitch[i];
        p[0] = (uint8_t)(3 + i); p[1] = b->valid; p[2] = b->block; p[3] = b->param; p[4] = b->flags;
        fab_put32(p + 5, b->model); fab_put32(p + 9, b->valid ? fab_f2u(b->a) : 0); fab_put32(p + 13, b->valid ? fab_f2u(b->b) : 0);
    }
    return 38;
}

uint32_t footswitch_ab_set(const gp50_ctx *ctx, const uint8_t *m, uint32_t n) {
    (void)ctx;
    gp50_assignments a;
    if (n != 18 || m[0] != 1 || gp50_assignments_get(&a) || a.preset == GP50_NONE || m[5] > 99 || m[5] != a.preset) return GP50_REFUSED;
    if (m[1] == 255) {                                                /* explicit recovery of damaged data */
        if (m[2] != 255 || m[3] || m[4] != 1 || fab_get32(m + 6) || fab_get32(m + 10) || fab_get32(m + 14) || !a.fault) return GP50_REFUSED;
        return gp50_assignments_recover();
    }
    if (m[1] < 3 || m[1] > 4 || m[4] || a.fault) return GP50_REFUSED;
    uint32_t i = m[1] - 3u;
    if (m[2] == 255) {
        if (m[3] || fab_get32(m + 6) || fab_get32(m + 10) || fab_get32(m + 14)) return GP50_REFUSED;
        a.footswitch[i].valid = 0;
    } else {
        float va = fab_u2f(fab_get32(m + 10)), vb = fab_u2f(fab_get32(m + 14));
        if (m[2] >= GP50_BLOCKS || m[3] >= 8 || gp50_block_model(m[2]) != fab_get32(m + 6) || m[3] >= gp50_param_count(m[2]) ||
            va == vb || !fab_endpoint_ok(m[2], m[3], va) || !fab_endpoint_ok(m[2], m[3], vb)) return GP50_REFUSED;
        a.footswitch[i] = (gp50_footswitch_binding){ 1, m[2], m[3], 0, fab_get32(m + 6), va, vb };
    }
    if (gp50_assignments_set(&a)) return GP50_REFUSED;
    gp50_preset_mark_modified();
    return GP50_OK;
}
