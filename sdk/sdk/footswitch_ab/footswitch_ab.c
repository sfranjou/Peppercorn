#include "footswitch_ab.h"

static int finite32(uint32_t u) { return (u & 0x7f800000u) != 0x7f800000u; }
/* Finite binary32 has one representation per value except signed zero. */
static int equal32(uint32_t a, uint32_t b) {
    return a == b || !((a | b) & 0x7fffffffu);
}
static int valid(const gp50_fs_ab_binding *v, gp50_fs_ab_validator check, void *ctx) {
    return v && v->valid == 1 && v->group < 10 && v->parameter < 8 && !v->flags
        && finite32(v->a) && finite32(v->b) && !equal32(v->a, v->b) && check
        && check(ctx, v->group, v->parameter, v->model, v->a)
        && check(ctx, v->group, v->parameter, v->model, v->b);
}
void gp50_fs_ab_clear(gp50_fs_ab_binding *v) {
    if (v) { gp50_fs_ab_binding zero = {0}; *v = zero; }
}
int gp50_fs_ab_make(gp50_fs_ab_binding *out, uint8_t group, uint8_t parameter,
                   uint32_t model, uint32_t a, uint32_t b,
                   gp50_fs_ab_validator check, void *ctx) {
    gp50_fs_ab_binding v = {1, group, parameter, 0, model, a, b};
    if (!out || !valid(&v, check, ctx)) return GP50_FS_AB_INVALID;
    *out = v;
    return GP50_FS_AB_READY;
}
int gp50_fs_ab_next(const gp50_fs_ab_binding *v, uint32_t model,
                   uint32_t current, gp50_fs_ab_validator check, void *ctx,
                   uint32_t *next) {
    if (!v || !next) return GP50_FS_AB_INVALID;
    if (!v->valid) {
        /* Corrupt inactive records are not silently treated as unassigned. */
        return (v->group || v->parameter || v->flags || v->model || v->a || v->b)
            ? GP50_FS_AB_INVALID : GP50_FS_AB_UNASSIGNED;
    }
    if (model != v->model) return GP50_FS_AB_STALE;
    if (!valid(v, check, ctx) || !finite32(current)) return GP50_FS_AB_INVALID;
    *next = equal32(current, v->a) ? v->b : v->a;
    return GP50_FS_AB_READY;
}
