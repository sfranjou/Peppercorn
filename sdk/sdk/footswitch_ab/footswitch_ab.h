#ifndef GP50_FOOTSWITCH_AB_H
#define GP50_FOOTSWITCH_AB_H
#include <stdint.h>

/* New policy component, not an installed hook. Values are binary32 bit patterns.
 * The caller owns serialization, preset lifetime and the ordinary parameter
 * write/admission/link/dirty/notification path. No private toggled-state bit. */
typedef struct {
    uint8_t valid, group, parameter, flags;
    uint32_t model, a, b;
} gp50_fs_ab_binding;

/* Must check the actual model, parameter, range and discrete-value semantics.
 * A nonzero result accepts one endpoint. It must not change pedal state. */
typedef int (*gp50_fs_ab_validator)(void *, uint8_t, uint8_t, uint32_t, uint32_t);
enum gp50_fs_ab_result {
    GP50_FS_AB_INVALID = -1, GP50_FS_AB_STALE = -2,
    GP50_FS_AB_UNASSIGNED = 0, GP50_FS_AB_READY = 1
};
int gp50_fs_ab_make(gp50_fs_ab_binding *, uint8_t group, uint8_t parameter,
                   uint32_t model, uint32_t a, uint32_t b,
                   gp50_fs_ab_validator, void *);
void gp50_fs_ab_clear(gp50_fs_ab_binding *);
/* READY writes next; all other results leave it unchanged. STALE/INVALID must
 * consume a configured switch press without falling through to a block toggle.
 * Only UNASSIGNED permits the existing block behavior. Current must be finite;
 * a finite intermediate value selects A. +0 and -0 compare equal. */
int gp50_fs_ab_next(const gp50_fs_ab_binding *, uint32_t current_model,
                   uint32_t current, gp50_fs_ab_validator, void *, uint32_t *next);
#endif
