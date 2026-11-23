/* Knob and footswitch A/B assignment (MOD026/029/092/096 behaviour, moved onto the SDK).
 *
 * Effect editor: hold DRUM opens the assignment menu ("Assign control" / "Clear assignment" / "Clear all" when the
 * stored data is damaged); EXIT closes it, the encoder moves the cursor, PARA selects.
 * "Assign control": turn the knob of the parameter to assign (prompt 1 -> 4), DRUM, then turn the destination Stomp
 * knob (prompt 2 -> 5) and DRUM to save it, or press FS A/B: the current value becomes A, set the value B with the
 * knob and press the same footswitch again (prompts 6/7). Two-value parameters assign
 * immediately with the opposite endpoint as B. Damaged data: prompt 8.
 * Home (Stomp mode): an assigned knob drives its parameter and its tile shows the parameter name, value and position.
 * Host: 12 71 -> 12 71 n {dest block param flags model32}xn;  11 71 dest block param flags (block ff = clear). */
#include "gp50.h"

enum { IDLE = 0, PICK_PARAM = 1, PICK_DEST = 2, ASSIGNED = 3, WAIT_B = 10, BAD = 11,
       MENU = 20, PICK = 21, CONFIRM = 22, EMPTY = 23, DONE = 24, RECOVER = 25, CHANGED = 26 };
typedef struct {
    uint8_t phase, cursor, dest, owner, block, param, tiles, pad;
    uint32_t model;
    float value_a;
    gp50_assignments seen;      /* CONFIRM: the binding as picked, re-checked before clearing */
    char text[128];             /* menu page text (kept here, not on the stack) */
    gp50_assignments work;      /* the page's own copy (kept here, not on the stack) */
} State;

static const char *const PROMPT[9] = { 0, "Turn parameter knob", "Turn destination knob", "Assigned; SAVE preset",
                                       "Selected; DRUM next", "Selected; DRUM saves", "Set B, FS1 again",
                                       "Set B, FS2 again", "Bad data: reset FS" };
static const char *const BLOCK[GP50_BLOCKS] = { "NR", "PRE", "DST", "AMP", "CAB", "EQ", "MOD", "DLY", "RVB", "NS" };
static const char *const PREFIX[GP50_BLOCKS] = { "NR ", "PRE ", "OD ", "AMP ", "CAB ", "EQ ", "MOD ", "DLY ", "RVB ", "NAM " };

static uint32_t asg_put(char *d, uint32_t n, uint32_t cap, const char *s) { while (*s && n + 1 < cap) d[n++] = *s++; d[n] = 0; return n; }

/* ---- editor prompts and menu pages ---- */
static void asg_prompt(State *s) {
    uint32_t p = s->phase;
    if (p == PICK_PARAM && s->param != GP50_NONE) p = 4;
    else if (p == PICK_DEST && s->dest != GP50_NONE) p = 5;
    else if (p == WAIT_B) p = s->dest == 4 ? 7 : 6;
    else if (p == BAD) p = 8;
    (void)gp50_editor_text(PROMPT[p >= 1 && p <= 8 ? p : 5], GP50_TEXT_PROMPT);
}
static uint32_t asg_dest_present(const gp50_assignments *a, uint32_t d) {
    return d < 3 ? a->knob[d].valid : (a->footswitch[d - 3].valid || (a->blocked >> (d - 3) & 1u));
}
static void asg_page(State *s) {
    char *t = s->text; const uint32_t size = sizeof s->text; uint32_t n = 0, d = s->dest;
    gp50_assignments *ap = &s->work; (void)gp50_assignments_get(ap);
#define a (*ap)
    if (s->phase == MENU) {
        n = asg_put(t, n, size, s->cursor == 0 ? "> Assign control\n" : "  Assign control\n");
        n = asg_put(t, n, size, s->cursor == 1 ? "> Clear assignment\n" : "  Clear assignment\n");
        if (a.fault) n = asg_put(t, n, size, s->cursor == 2 ? "> Clear all (bad data)\n" : "  Clear all (bad data)\n");
        n = asg_put(t, n, size, "PARA: select\nEXIT: cancel");
    } else if (s->phase == PICK) n = asg_put(t, n, size, "Clear assignment\nTurn Stomp knob\nor press FS A/B\nEXIT: cancel");
    else if (s->phase == DONE) n = asg_put(t, n, size, "Assignment cleared\nSAVE preset\nEXIT: close");
    else if (s->phase == RECOVER) n = asg_put(t, n, size, "Clear ALL assignments?\nKnobs and FS A/B\nPARA: clear all\nEXIT: cancel");
    else if (s->phase == CHANGED) n = asg_put(t, n, size, "Assignment changed\nPlease select again\nEXIT: close");
    else {
        char which[16];                                      /* built by hand: an initializer would call memset */
        asg_put(which, 0, sizeof which, d >= 3 ? "Footswitch A" : "Stomp knob 1");
        which[11] = (char)(d >= 3 ? 'A' + d - 3 : '1' + d);
        n = asg_put(t, n, size, which);
        if (s->phase == EMPTY) n = asg_put(t, n, size, "\nNot assigned\nEXIT: close");
        else {
            uint32_t block = d < 3 ? s->seen.knob[d].block : s->seen.footswitch[d - 3].block;
            uint32_t param = d < 3 ? s->seen.knob[d].param : s->seen.footswitch[d - 3].param;
            uint32_t model = d < 3 ? s->seen.knob[d].model : s->seen.footswitch[d - 3].model;
            n = asg_put(t, n, size, "\n");
            if (block < GP50_BLOCKS && gp50_block_model(block) == model && param < gp50_param_count(block)) {
                char name[GP50_NAME_TEXT_MAX + 1];
                (void)gp50_param_name(block, param, name, sizeof name);
                n = asg_put(t, n, size, BLOCK[block]); n = asg_put(t, n, size, ": "); n = asg_put(t, n, size, name);
            } else n = asg_put(t, n, size, "Stale / blocked binding");
            n = asg_put(t, n, size, "\nPARA: clear\nEXIT: cancel");
        }
    }
    (void)gp50_editor_text(t, GP50_TEXT_PAGE);
#undef a
}
static void asg_show(State *s) { if (s->phase >= MENU) asg_page(s); else if (s->phase) asg_prompt(s); }
static void asg_leave(State *s) { s->phase = IDLE; gp50_editor_text_clear(); }

/* ---- commits ---- */
uint32_t assignment_host_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity);
static void asg_notify71(void) { uint8_t r[25]; uint32_t n = assignment_host_get(0, r, sizeof r); if (n) (void)gp50_host_notify(r, n); }
static uint32_t asg_same(const gp50_assignments *x, const gp50_assignments *y, uint32_t d) {
    if (d < 3) { const gp50_knob_binding *a = &x->knob[d], *b = &y->knob[d];
                 return a->valid == b->valid && a->block == b->block && a->param == b->param && a->model == b->model; }
    const gp50_footswitch_binding *a = &x->footswitch[d - 3], *b = &y->footswitch[d - 3];
    return a->valid == b->valid && a->block == b->block && a->param == b->param && a->model == b->model &&
           (x->blocked >> (d - 3) & 1u) == (y->blocked >> (d - 3) & 1u);
}
static void asg_pick(State *s, uint32_t d) {
    gp50_assignments a;
    if (gp50_assignments_get(&a) || a.fault) { s->phase = CHANGED; asg_page(s); return; }
    s->dest = (uint8_t)d; s->seen = a;
    s->phase = a.preset == s->owner && asg_dest_present(&a, d) ? CONFIRM : EMPTY;
    asg_page(s);
}
static void asg_confirm(State *s) {
    gp50_assignments a; uint32_t ok = 0;
    if (!gp50_assignments_get(&a) && a.preset == s->owner) {
        if (s->phase == RECOVER && a.fault) ok = gp50_assignments_recover() == GP50_OK;
        else if (s->phase == CONFIRM && s->dest < 5 && !a.fault && asg_same(&a, &s->seen, s->dest)) {
            if (s->dest < 3) a.knob[s->dest].valid = 0; else a.footswitch[s->dest - 3].valid = 0;
            ok = gp50_assignments_set(&a) == GP50_OK;
            if (ok) { gp50_preset_mark_modified(); asg_notify71(); }
        }
    }
    s->phase = ok ? DONE : CHANGED;
    asg_page(s);
}
static uint32_t asg_commit_knob(State *s) {
    gp50_assignments a;
    if (gp50_preset_number() != s->owner || s->dest >= 3 || gp50_assignments_get(&a) || a.fault) return 0;
    if (gp50_block_model(s->block) != s->model || s->param >= gp50_param_count(s->block)) return 0;
    a.preset = s->owner;
    a.knob[s->dest] = (gp50_knob_binding){ 1, s->block, s->param, 0, s->model };
    if (gp50_assignments_set(&a)) return 0;
    gp50_preset_mark_modified();
    asg_notify71();
    return 1;
}
static void asg_commit_foot_value(State *s, uint32_t fs, float b) {
    gp50_assignments a;
    if (b == s->value_a) return;           /* A == B: keep waiting */
    if (gp50_assignments_get(&a) || a.fault || gp50_block_model(s->block) != s->model) { s->phase = BAD; asg_prompt(s); return; }
    a.preset = (uint8_t)gp50_preset_number();
    a.footswitch[fs] = (gp50_footswitch_binding){ 1, s->block, s->param, 0, s->model, s->value_a, b };
    if (gp50_assignments_set(&a)) { s->phase = BAD; asg_prompt(s); return; }
    gp50_preset_mark_modified();
    s->phase = ASSIGNED; asg_prompt(s);
}

/* ---- events ---- */
static uint32_t asg_editor(State *s, const gp50_event *e) {
    uint32_t p = s->phase;
    if (e->kind == GP50_EVENT_DRUM_HOLD && p == IDLE) {
        s->owner = (uint8_t)gp50_preset_number(); s->cursor = 0; s->phase = MENU; asg_page(s); return GP50_CONSUMED;
    }
    if (p == IDLE) return GP50_PASS;                         /* the editor's own behaviour (DRUM: drum_control) */
    if (e->kind == GP50_EVENT_BACK) { asg_leave(s); return GP50_CONSUMED; }
    if (p >= MENU) {
        gp50_assignments a; (void)gp50_assignments_get(&a);
        if (p == MENU && e->kind == GP50_EVENT_ENCODER) {
            uint32_t max = a.fault ? 2 : 1;
            uint32_t c = s->cursor;
            s->cursor = (uint8_t)(e->value > 0 ? (c >= max ? 0u : c + 1u) : (c == 0 ? max : c - 1u));
            asg_page(s);
        } else if (e->kind == GP50_EVENT_PARA) {
            if (p == MENU && s->cursor == 0 && !a.fault) {
                s->phase = PICK_PARAM; s->param = GP50_NONE; s->dest = GP50_NONE; asg_prompt(s);
            } else if (p == MENU && s->cursor == 1 && !a.fault) { s->phase = PICK; asg_page(s); }
            else if (p == MENU && s->cursor == 2 && a.fault) { s->phase = RECOVER; asg_page(s); }
            else if (p == CONFIRM || p == RECOVER) asg_confirm(s);
        } else if (p == PICK && e->kind == GP50_EVENT_KNOB && e->value) asg_pick(s, e->index);
        else if (p == PICK && e->kind == GP50_EVENT_FOOTSWITCH) asg_pick(s, 3u + e->index);
        return GP50_CONSUMED;                                /* a menu page takes every input */
    }
    switch (e->kind) {                                       /* MOD026 assign flow (phases 1..11) */
    case GP50_EVENT_DRUM:
        if (p == PICK_PARAM) { if (s->param != GP50_NONE) { s->phase = PICK_DEST; asg_prompt(s); } }
        else if (p == PICK_DEST) { if (s->dest != GP50_NONE) { if (asg_commit_knob(s)) { s->phase = ASSIGNED; asg_prompt(s); } else asg_leave(s); } }
        else asg_leave(s);
        return GP50_CONSUMED;
    case GP50_EVENT_KNOB:
        if (p == WAIT_B) return GP50_PASS;                   /* knobs set the value B */
        if (!e->value) return GP50_CONSUMED;
        if (p == PICK_PARAM) {
            uint32_t param = gp50_editor_knob_param(e->index), block = gp50_editor_block();
            if (param == GP50_NONE || block >= GP50_BLOCKS) return GP50_CONSUMED;
            s->block = (uint8_t)block; s->param = (uint8_t)param; s->model = gp50_block_model(block); asg_prompt(s);
        } else if (p == PICK_DEST) { s->dest = e->index; asg_prompt(s); }
        return GP50_CONSUMED;
    case GP50_EVENT_FOOTSWITCH:
        if ((p == PICK_PARAM || p == PICK_DEST) && s->param != GP50_NONE) {
            if (gp50_param_get(s->block, s->param, &s->value_a)) return GP50_CONSUMED;
            s->dest = (uint8_t)(3 + e->index); s->phase = WAIT_B; asg_prompt(s);
            /* Exactly two legal values: current value A, the other endpoint B.
             * Do not alter the sounding parameter just to record the binding. */
            float lo, hi, step;
            if (!gp50_param_range(s->block, s->param, &lo, &hi, &step) &&
                hi > lo && step == hi - lo && (s->value_a == lo || s->value_a == hi))
                asg_commit_foot_value(s, e->index, s->value_a == lo ? hi : lo);
        } else if (p == WAIT_B && s->dest == 3 + e->index) {
            float b;
            if (!gp50_param_get(s->block, s->param, &b)) asg_commit_foot_value(s, e->index, b);
        }
        return GP50_CONSUMED;
    case GP50_EVENT_ENCODER: return GP50_CONSUMED;
    case GP50_EVENT_PARA: return GP50_PASS;                  /* page switch; the prompt is redrawn on tick */
    default: return GP50_PASS;
    }
}

uint32_t assignment_on_event(const gp50_ctx *ctx, const gp50_event *e) {
    State *s = ctx->state;
    /* A preset load keeps the record of customised tiles, so the next tick gives a tile whose binding is gone back
     * to the stock display. A new screen rebuilds them. */
    if (e->kind == GP50_EVENT_PRESET) { s->phase = IDLE; return GP50_PASS; }
    if (e->kind == GP50_EVENT_SCREEN) { s->phase = IDLE; s->tiles = 0; return GP50_PASS; }
    if (e->screen == GP50_SCREEN_EDITOR) return asg_editor(s, e);
    if (e->screen == GP50_SCREEN_HOME && e->kind == GP50_EVENT_KNOB && e->value && gp50_pedal_mode() == GP50_MODE_STOMP) {
        gp50_assignments a;
        if (!gp50_assignments_get(&a) && a.knob[e->index].valid) {
            (void)gp50_param_nudge(a.knob[e->index].block, a.knob[e->index].param, e->value);
            return GP50_CONSUMED;
        }
    }
    return GP50_PASS;
}

/* ---- tick: keep prompts valid, draw home tiles ---- */
static uint32_t asg_percent(float lo, float hi, float v) {
    if (!(hi > lo) || !(v > lo)) return 0;
    if (!(v < hi)) return 100;
    int32_t p = (int32_t)((v - lo) / (hi - lo) * 100.0f);
    return p < 0 ? 0 : p > 100 ? 100 : (uint32_t)p;
}
void assignment_on_tick(const gp50_ctx *ctx) {
    State *s = ctx->state;
    uint32_t screen = gp50_screen();
    if (screen == GP50_SCREEN_EDITOR && s->phase) {
        if (gp50_preset_number() != s->owner && s->phase < MENU) { asg_leave(s); return; }
        if (s->phase < MENU && s->param != GP50_NONE && gp50_block_model(s->block) != s->model) { asg_leave(s); return; }
        if (s->phase == CONFIRM) {
            gp50_assignments a;
            if (gp50_assignments_get(&a) || a.fault || !asg_same(&a, &s->seen, s->dest)) s->phase = CHANGED;
        }
        asg_show(s);
    }
    if (screen != GP50_SCREEN_HOME) return;
    gp50_assignments a;
    uint32_t stomp = gp50_pedal_mode() == GP50_MODE_STOMP, ok = !gp50_assignments_get(&a);
    for (uint32_t k = 0; k < GP50_KNOBS; k++) {
        const gp50_knob_binding *b = &a.knob[k];
        if (ok && stomp && b->valid) {
            char name[24], value[24]; float lo, hi, v;
            uint32_t n = asg_put(name, 0, sizeof name, PREFIX[b->block]);
            (void)gp50_param_name(b->block, b->param, name + n, sizeof name - n);
            (void)gp50_param_text(b->block, b->param, value, sizeof value);
            uint32_t pct = !gp50_param_range(b->block, b->param, &lo, &hi, 0) && !gp50_param_get(b->block, b->param, &v) ? asg_percent(lo, hi, v) : 0;
            if (gp50_home_knob_tile(k, name, value, pct) == GP50_OK) s->tiles |= (uint8_t)(1u << k);
        } else if (s->tiles >> k & 1u) { gp50_home_knob_tile_reset(k); s->tiles &= (uint8_t)~(1u << k); }
    }
}

/* ---- host 11/12 71 ---- */
uint32_t assignment_host_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    gp50_assignments a;
    if (capacity < 25 || gp50_assignments_get(&a)) return 0;
    uint32_t n = 0;
    for (uint32_t k = 0; k < GP50_KNOBS; k++) {
        if (!a.knob[k].valid) continue;
        uint8_t *r = out + 1 + 8 * n++;
        r[0] = (uint8_t)k; r[1] = a.knob[k].block; r[2] = a.knob[k].param; r[3] = 0;
        for (uint32_t i = 0; i < 4; i++) r[4 + i] = (uint8_t)(a.knob[k].model >> (8 * i));
    }
    out[0] = (uint8_t)n;
    return 1 + 8 * n;
}
uint32_t assignment_host_set(const gp50_ctx *ctx, const uint8_t *in, uint32_t length) {
    (void)ctx;
    gp50_assignments a;
    if (length != 4 || in[0] >= 3 || in[3] || gp50_assignments_get(&a) || a.fault) return GP50_REFUSED;
    a.preset = (uint8_t)gp50_preset_number();
    if (in[1] == 0xff) { if (in[2]) return GP50_REFUSED; if (!a.knob[in[0]].valid) return GP50_OK; a.knob[in[0]].valid = 0; }
    else {
        if (in[1] >= GP50_BLOCKS || in[2] >= 8 || in[2] >= gp50_param_count(in[1]) || !gp50_block_model(in[1])) return GP50_REFUSED;
        a.knob[in[0]] = (gp50_knob_binding){ 1, in[1], in[2], 0, gp50_block_model(in[1]) };
    }
    if (gp50_assignments_set(&a)) return GP50_REFUSED;
    gp50_preset_mark_modified();
    asg_notify71();                                               /* 12 71 notice, as the platform sent */
    return GP50_OK;
}
