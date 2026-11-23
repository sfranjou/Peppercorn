#ifndef GP50_FS_AB_PERSISTENCE_H
#define GP50_FS_AB_PERSISTENCE_H
#include "host.h"
#include "metadata.h"
/* Standalone load/save policy. Integration must read the exact tail, snapshot
 * the matching active record, serialize owner changes, and publish atomically.
 * Structural load is followed by catalog admission before publishing knob maps;
 * parameter endpoints are checked again at each press. No flash I/O here. */
enum {GP50_FS_LOAD_BLOCKED=-1, GP50_FS_LOAD_NONE=0,
      GP50_FS_LOAD_V1=1, GP50_FS_LOAD_V2=2};
int gp50_fs_ab_load(uint8_t owner, const uint8_t *stock, size_t stock_bytes,
                    const uint8_t *tail, size_t tail_bytes,
                    gp50_fs_ab_state *, gp50_gpam_maps *);
/* metadata_fault remains a save barrier even after both feet are healed.
 * Never overwrite damaged/unknown knob metadata without an explicit whole-record
 * recovery decision (host_recover, routed separately by integration). Model changes omit stale knobs and
 * persist stale feet as blocked; valid unrelated assignments survive. Target
 * integration must also apply catalog/count/dynamic endpoint validation. */
int gp50_fs_ab_save(const gp50_fs_ab_state *, uint8_t current_owner,
                    const gp50_gpam_knob knobs[3],
                    const uint8_t *stock, size_t stock_bytes,
                    uint8_t *tail, size_t capacity);
/* Prepare stock and metadata together in RAM, without touching padding or
 * flash. Refuses BEFORE changing destination on any validation failure.
 * Source must be disjoint from destination, or exactly destination. Caller
 * snapshots/serializes ownership and must call this before flash erase/program;
 * replacing only the old memcpy hook is insufficient to abort a stock save. */
int gp50_fs_ab_stage(const gp50_fs_ab_state *, uint8_t current_owner,
                    const gp50_gpam_knob knobs[3], const uint8_t *stock,
                    size_t stock_bytes, uint8_t *destination, size_t capacity);
#endif
