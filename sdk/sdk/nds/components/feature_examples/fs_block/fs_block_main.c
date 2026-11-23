/* Right footswitch toggles one block chosen from a computer (`11 79 <block>`). Until a block is chosen the footswitch
 * keeps its normal job. The choice is stored per preset and shown in the effect editor. */
#include "gp50.h"

#define OFF 0xffu                    /* no block chosen: the footswitch keeps its normal job */
typedef struct { uint8_t block; } State;

static const char *const NAMES[GP50_BLOCKS] = {"NR", "PRE", "DST", "AMP", "CAB", "EQ", "MOD", "DLY", "RVB", "NS"};

static void tell_host(const State *s) {
    uint8_t msg[3] = {1, s->block, s->block < GP50_BLOCKS ? (uint8_t)gp50_block_enabled(s->block) : 0};
    (void)gp50_host_notify(msg, sizeof msg);        /* fine if no editor is connected */
}

void fs_block_init(const gp50_ctx *ctx) { ((State *)ctx->state)->block = OFF; }

void fs_block_load(const gp50_ctx *ctx, const uint8_t *in, uint32_t n) {
    State *s = ctx->state;
    s->block = n == 1 && (in[0] < GP50_BLOCKS || in[0] == OFF) ? in[0] : OFF;   /* none stored: normal footswitch */
}

uint32_t fs_block_save(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    if (capacity < 1) return 0;
    out[0] = ((const State *)ctx->state)->block;
    return 1;
}

uint32_t fs_block_event(const gp50_ctx *ctx, const gp50_event *e) {
    State *s = ctx->state;
    if (e->kind != GP50_EVENT_FOOTSWITCH || e->index != GP50_FOOTSWITCH_RIGHT || e->screen != GP50_SCREEN_HOME || s->block == OFF)
        return GP50_PASS;
    (void)gp50_block_set_enabled(s->block, !gp50_block_enabled(s->block));   /* refused = CPU full: nothing happens */
    tell_host(s);
    return GP50_CONSUMED;
}

/* Host: 12 79 -> 12 79 01 <block> <on>;  11 79 <block>  (0xff = off). */
uint32_t fs_block_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    const State *s = ctx->state;
    if (capacity < 3) return 0;
    out[0] = 1; out[1] = s->block; out[2] = s->block < GP50_BLOCKS ? (uint8_t)gp50_block_enabled(s->block) : 0;
    return 3;
}

uint32_t fs_block_set(const gp50_ctx *ctx, const uint8_t *in, uint32_t n) {
    State *s = ctx->state;
    if (n != 1 || (in[0] >= GP50_BLOCKS && in[0] != OFF)) return GP50_REFUSED;
    if (s->block != in[0]) { s->block = in[0]; gp50_preset_mark_modified(); }
    return GP50_OK;
}

uint32_t fs_block_status(const gp50_ctx *ctx, char *out, uint32_t capacity) {
    const State *s = ctx->state;
    if (s->block == OFF || capacity < 9) return 0;
    const char *t = "FS2: ", *name = NAMES[s->block];
    uint32_t n = 0;
    while (*t) out[n++] = *t++;
    while (*name) out[n++] = *name++;
    return n;
}
