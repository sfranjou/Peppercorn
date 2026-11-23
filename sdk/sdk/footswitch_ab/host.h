#ifndef GP50_FS_AB_HOST_H
#define GP50_FS_AB_HOST_H
#include <stddef.h>
#include "footswitch_ab.h"
/* Draft only. Caller serializes access, including preset changes, and owns
 * preset lifetime and storage. Set byte 7 must equal the guarded owner. */
/* metadata_fault protects the whole tail from overwrite; individual foot-only
 * changes do not clear it. Read status byte5 bit7 exposes this save barrier.
 * A blocked switch consumes presses even when its binding was lost to damaged
 * metadata. When metadata_fault is clear, explicit host set/clear heals only that destination. */
typedef struct { uint8_t owner, blocked_mask, metadata_fault; gp50_fs_ab_binding binding[2]; } gp50_fs_ab_state;
typedef void (*gp50_fs_ab_dirty)(void *);
int gp50_fs_ab_host_read(const gp50_fs_ab_state *, const uint8_t *, size_t, uint8_t *, size_t, gp50_fs_ab_validator, void *);
int gp50_fs_ab_host_set(gp50_fs_ab_state *, const uint8_t *, size_t, gp50_fs_ab_validator, void *, gp50_fs_ab_dirty, void *);
/* Explicit whole-record recovery, not an ordinary foot clear. Caller must hold
 * the preset lifetime guard and supply infallible live-knob clearing plus dirty
 * callbacks. Clears all knob/foot mappings only after exact owner/packet checks.
 * No flash I/O; later transactional save still belongs to the caller. */
int gp50_fs_ab_host_recover(gp50_fs_ab_state *, const uint8_t *, size_t,
    gp50_fs_ab_dirty clear_knobs, void *, gp50_fs_ab_dirty mark_dirty, void *);
#endif
