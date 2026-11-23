/* A/B parameter footswitches: target glue (MOD089 draft; plan analysis/firmware/FOOTSWITCH_AB_TARGET_INTEGRATION.md).
 * Region E. Direct mode only: the components take real pointers, which equal target addresses here.
 *
 * State: gp50_fs_ab_state at FS_AB_STATE (48 reserved bytes beyond the capture cache; startup bridge -> gp50_fs_ab_reset).
 * Owner is the current preset position (0x471d6), like the knob owner at ASSIGN_STATE + 80; 255 = nothing loaded.
 * Every state change happens in the GUI/MainApp task under the stock guard 0x5c0e2/0x5c102, which is not held across
 * flash, link or parameter services. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "fs_ab_target.h"
#include "../../footswitch_ab/persistence.h"
#include "../../footswitch_ab/stock_adapter.h"
#include "../own/assign_store.h"
#ifdef GP50_FEATURES
#include "../components/platform/gp50_features.h"
#endif

#define GUARD_ENTER 0x5c0e2u
#define GUARD_LEAVE 0x5c102u
#define CURRENT_PRESET 0x471d6u
#define BLOCK_ORDINAL 0x475d0u      /* (group) -> ordinal of the block's model */
#define PARAMETER_COUNT 0x46c2au
#define ID_TO_ORDINAL 0x439dcu      /* (group, id) */
#define ORDINAL_TO_ID 0x439b6u      /* (group, ordinal) */
#define FLASH_READ 0x10f9eu         /* (address, buffer, length, retries): 0 = done */
#define SLOT_READ 0x4972eu          /* (buffer, index, length) */
#define PRESET_MODIFIED 0x43d52u
#define KNOB(k) (ASSIGN_STATE + 32u + 16u * (k))

/* Direct mode never dereferences the StockIo pointer, but the adapter refuses a null one. */
static const StockIo direct_io;
#define IO (&direct_io)
static uint32_t current(void) { return STOCK_CALL0(IO, CURRENT_PRESET); }
static void guard(int enter) { if (enter) STOCK_CALL0(IO, GUARD_ENTER); else STOCK_CALL0(IO, GUARD_LEAVE); }

static gp50_fs_ab_state *state(void) { return (gp50_fs_ab_state *)(uintptr_t)FS_AB_STATE; }

static uint32_t u32(const uint8_t *p) { return p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24; }
static void fill(void *d, uint8_t v, uint32_t n) { uint8_t *p = d; while (n--) *p++ = v; }
static void copy(void *d, const void *s, uint32_t n) { uint8_t *p = d; const uint8_t *q = s; while (n--) *p++ = *q++; }

void gp50_fs_ab_reset(void) {
    fill(state(), 0, 48);                                        /* state + message area (fs_ab_ui.c) */
    state()->owner = 255;
}

/* No assignments for `owner` (blank metadata, unreadable record, factory/default record). */
static void publish_empty(uint32_t owner) {
    gp50_fs_ab_state next = {.owner = owner < 100 ? (uint8_t)owner : 255};
    guard(1); *state() = next; guard(0);
}

/* Successor of assign_preset_read (call site: stored-preset read 0x43fa6, first slot read). For the active buffer:
 * clear the live knob bindings and foot state, then publish the slot's validated GPAM v1/v2 metadata. Knob maps get the
 * catalog admission of MOD029 (model of that block, catalog round trip); any failing knob drops all knob maps (as before).
 * Foot bindings are published as decoded; each press checks model, range and step again. Damaged/unknown metadata
 * publishes metadata_fault (save barrier) with both switches blocked. */
uint32_t gp50_fs_ab_preset_read(uint32_t buffer, uint32_t index, uint32_t length, const StockIo *io) {
    uint32_t result = STOCK_CALL(io, SLOT_READ, buffer, index, length);
    if (buffer != ACTIVE_RECORD) return result;
    uint32_t owner = current();
    guard(1);
    io_w32(io, KNOB(0), 0); io_w32(io, KNOB(1), 0); io_w32(io, KNOB(2), 0);
    io_w32(io, ASSIGN_META + 8, 0);                              /* reset mode off */
    io_w32(io, ASSIGN_STATE + 80, owner);
    guard(0);
    publish_empty(owner);
    /* Never-saved slot (erased record, no stock magic 0x5aa5): the caller (0x43fc2) then substitutes the backup record
     * (index + 100, read without this hook) or a default record. Such a preset has no stored assignments; it must not
     * be published as damaged metadata (that blocked both switches with BAD DATA and refused Save; MOD150 owner report
     * 2026-11-12, slot 99). */
    const uint8_t *rec = (const uint8_t *)(uintptr_t)buffer;
    uint32_t stored = !result && length == 426 && (rec[0] | (uint32_t)rec[1] << 8) == 0x5aa5u;
#ifdef GP50_FEATURES
    if (stored) gp50_features_preset_read(buffer, index);       /* SDK per-preset area (+576) */
    else gp50_features_preset_read(buffer, 100);                 /* no valid record: no stored feature bytes */
    gp50_features_preset_loaded();                               /* SDK PRESET event, delivered on the next tick */
#endif
    if (!stored || index >= 100) return result;
    uint8_t tail[64];
    if (STOCK_CALL(io, FLASH_READ, ((index + 1500u) << 10) + 512u, (uint32_t)(uintptr_t)tail, 64, 10)) return result;
    gp50_fs_ab_state next;
    gp50_gpam_maps maps;
    int r = gp50_fs_ab_load((uint8_t)(owner < 100 ? owner : 255), (const uint8_t *)(uintptr_t)buffer, 426, tail, 64, &next, &maps);
    uint32_t live[12];
    fill(live, 0, sizeof live);
    int knobs_ok = 1;
    for (uint32_t k = 0; r > 0 && k < 3; k++) {
        const gp50_gpam_knob *m = &maps.knob[k];
        if (!m->valid) continue;
        uint32_t group = m->group, id = m->model;
        if (group >= 10 || m->parameter >= 8 || io_r32(io, PRESET_IDS + 4 * group) != id) { knobs_ok = 0; break; }
        uint32_t ordinal = STOCK_CALL(io, ID_TO_ORDINAL, group, id);
        if (STOCK_CALL(io, ORDINAL_TO_ID, group, ordinal) != id) { knobs_ok = 0; break; }
        live[4 * k] = 1; live[4 * k + 1] = group; live[4 * k + 2] = m->parameter; live[4 * k + 3] = ordinal;
    }
    guard(1);
    if (r > 0 && knobs_ok) copy((void *)(uintptr_t)KNOB(0), live, sizeof live);
    *state() = next;
    guard(0);
    return result;
}

/* The active record was replaced without the stored-slot read (factory record of the current preset): no assignments
 * belong to it. Knob bindings keep their MOD029 behaviour (checked against the block's model on use). */
void gp50_fs_ab_active_replaced(void) {
    publish_empty(current());
#ifdef GP50_FEATURES
    gp50_features_preset_read(0, 100);                           /* factory record: no stored feature bytes */
    gp50_features_preset_loaded();
#endif
}

/* Knob bindings of the current preset as GPAM records (model from `record`), the checks of assign_stage_copy. */
static void knob_snapshot(gp50_gpam_knob knobs[3], uint32_t record, const StockIo *io) {
    uint32_t maps[12];
    guard(1);
    uint32_t owner = io_r32(io, ASSIGN_STATE + 80);
    copy(maps, (const void *)(uintptr_t)KNOB(0), sizeof maps);
    guard(0);
    fill(knobs, 0, 3 * sizeof(gp50_gpam_knob));
    if (current() != owner) return;                              /* bindings of another preset: none */
    for (uint32_t k = 0; k < 3; k++) {
        uint32_t *m = maps + 4 * k, group = m[1], parameter = m[2];
        if (!m[0] || group >= 10 || STOCK_CALL(io, BLOCK_ORDINAL, group) != m[3]) continue;
        if (parameter >= 8 || !(parameter < STOCK_CALL(io, PARAMETER_COUNT, group))) continue;
        knobs[k] = (gp50_gpam_knob){.valid = 1, .group = (uint8_t)group, .parameter = (uint8_t)parameter,
                                    .model = u32((const uint8_t *)(uintptr_t)(record + 38 + 4 * group))};
    }
}

/* Successor of assign_stage_copy, with a result: 1 = destination staged, 0 = refused (destination unchanged).
 * 426-byte active record: stock bytes + schema-2 tail built from the live knob/foot state (refused on metadata fault).
 * 426-byte other record (host write to another slot): stock bytes + blank tail, so it never inherits active mappings.
 * Other lengths: plain copy. On success the owners follow the record's slot (+8), as MOD029 did (Save As). */
uint32_t gp50_fs_ab_stage_record(uint32_t destination, uint32_t source, uint32_t length, const StockIo *io) {
    uint8_t *d = (uint8_t *)(uintptr_t)destination;
    const uint8_t *s = (const uint8_t *)(uintptr_t)source;
    if (length != 426) { copy(d, s, length); return 1; }
    if (source != ACTIVE_RECORD) {
        copy(d, s, 426); fill(d + 512, 0, 64);
#ifdef GP50_FEATURES
        gp50_features_stage(d, s, 0);                            /* other records never inherit feature bytes */
#endif
        return 1;
    }
    gp50_gpam_knob knobs[3];
    knob_snapshot(knobs, source, io);
    uint32_t owner = current();
    if (owner >= 100) return 0;
    gp50_fs_ab_state snap;
    guard(1); snap = *state(); guard(0);
    if (snap.owner != owner) snap = (gp50_fs_ab_state){.owner = (uint8_t)owner};   /* nothing loaded for this preset */
    if (!gp50_fs_ab_stage(&snap, (uint8_t)owner, knobs, s, 426, d, 1024)) return 0;
#ifdef GP50_FEATURES
    gp50_features_stage(d, s, 1);                                /* SDK per-preset area +576..+1023 */
#endif
    uint32_t slot = s[8] | (uint32_t)s[9] << 8;
    if (slot < 100) {
        guard(1);
        io_w32(io, ASSIGN_STATE + 80, slot);
        if (state()->owner == owner) state()->owner = (uint8_t)slot;
        guard(0);
    }
    return 1;
}

/* Footswitch press (replaces nds_adm_footswitch at the press-toggle call): a configured A/B switch writes its parameter
 * (READY) or consumes the press (STALE/INVALID); only an unassigned switch goes on to the CPU-admission gate and the
 * stock block toggle. The state is copied under the guard; the parameter services run outside it. */
void gp50_fs_ab_press(uint32_t index) {
#ifndef GP50_FEATURE_FOOTSWITCH_AB   /* else the SDK feature footswitch_ab owns A/B presses */
    if (gp50_fs_ab_reset_press(index)) return;                   /* "Reset knob/FS" mode: clear, never toggle */
    gp50_fs_ab_state snap;
    guard(1); snap = *state(); guard(0);
    if (index < 2 && snap.owner < 100) {
        int r = gp50_fs_ab_stock_press(index, &snap, IO);
        if (r != GP50_FS_AB_UNASSIGNED) {
            gp50_fs_ab_note(r == GP50_FS_AB_READY ? FS_AB_MSG_READY : r == GP50_FS_AB_STALE ? FS_AB_MSG_STALE : FS_AB_MSG_INVALID, index);
            return;
        }
    }
#endif
#ifdef GP50_FEATURES   /* unassigned switch: SDK features first, then the CPU-admission gate and stock toggle */
    if (gp50_features_footswitch(index)) return;
#endif
    nds_adm_footswitch(index);
}

/* Save barrier for the knob commands (`11 71`) and the host status. */
uint32_t gp50_fs_ab_metadata_fault(void) { return state()->metadata_fault && state()->owner == current(); }   /* flag first: no stock call unless faulted */

static void mark_dirty(void *ctx) { (void)ctx; STOCK_CALL(IO, PRESET_MODIFIED, 1); }
static void clear_knobs(void *ctx) {
    (void)ctx;
    guard(1); io_w32(IO, KNOB(0), 0); io_w32(IO, KNOB(1), 0); io_w32(IO, KNOB(2), 0); guard(0);
}

/* `12 74` read: 40-byte frame into `out`; 0 when the state is not for the current preset. */
uint32_t gp50_fs_ab_read_frame(uint8_t *out) {
    static const uint8_t request[2] = {0x12, 0x74};
    gp50_fs_ab_state snap;
    guard(1); snap = *state(); guard(0);
    if (snap.owner != current()) return 0;
    return (uint32_t)gp50_fs_ab_host_read(&snap, request, 2, out, 40, 0, 0);
}

/* `11 74` set/clear (destination 3/4) or explicit recovery (destination 255, op 1): 0 = done, 1 = refused.
 * Endpoints are validated against the live model/range/step (stock adapter). The edit is made on a copy and published
 * under the guard only if the owner is still current. */
uint32_t gp50_fs_ab_command(const uint8_t *message, uint32_t length) {
    gp50_fs_ab_state work;
    guard(1); work = *state(); guard(0);
    if (work.owner != current()) return 1;
    int done = length == 20 && message[3] == 255
        ? gp50_fs_ab_host_recover(&work, message, 20, clear_knobs, 0, mark_dirty, 0)
        : gp50_fs_ab_host_set(&work, message, length, gp50_fs_ab_stock_validate, (void *)IO, mark_dirty, 0);
    if (!done) return 1;
    guard(1);
    int still = state()->owner == work.owner;
    if (still) *state() = work;
    guard(0);
    return still ? 0 : 1;
}
