#include "gp50.h"

uint32_t gp50_enable_constraints(uint8_t *reasons);

uint32_t enable_constraints_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {
    (void)ctx;
    if (capacity < 1u + GP50_BLOCKS) return 0;
    out[0] = 1;
    return 1u + gp50_enable_constraints(out + 1);
}
