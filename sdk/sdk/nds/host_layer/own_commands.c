/* Our own host commands:
 *   `12 70`            -> `12 70 proto8 version[16] features32`     identity of our firmware
 *   `12 71`            -> `12 71 n8 {dest8 group8 param8 flags8 id32} x n`   the current preset's knob assignments
 *   `11 71 dest8 group8 param8 flags8`  set (group 0xff = clear) one assignment; ACK status 0 = done, 1 = refused
 *   `12 71` notification (same body) when an assignment changes on the pedal (editor DRUM flow, home "Reset knob")
 * and the `12 51` telemetry route that the MOD037..MOD055 assembly hook 0x4357a added to the stock parser (length 2 ->
 * read-table entry 12). New behaviour, not a port: tested against a model (scripts/test_nds_own_commands.py), no
 * original to compare. Written against stock_io.h like the compared sources, so the host test runs this exact file;
 * the pedal build (host_layer/own_pedal.c) compiles it with GP50_CATALOG_DIRECT.
 *
 * Assignment data: the live binding table of the knob-assignment feature (MOD026/MOD029, firmware/reconstructed/nds/
 * assign_store.h): ASSIGN_STATE + 32 + 16 k = {valid, group, parameter, model ordinal} for Stomp knob k = 0..2, owner
 * preset at ASSIGN_STATE + 80. A binding counts only for the current preset, with the block still holding the same
 * model and the parameter in range (the checks of assign_valid_map, without its side effects). Destinations 3-4
 * (footswitches 1-2) are reserved for the footswitch assignment and refused here. */
#include "own_commands.h"
#ifdef GP50_TAP_SAFE_HOST
#include "../tap/tap_host.h"
#endif

#define GUARD_ENTER 0x5c0e2u
#define GUARD_LEAVE 0x5c102u
#define CURRENT_PRESET 0x471d6u     /* () -> current preset slot */
#define BLOCK_ORDINAL 0x475d0u      /* (group) -> ordinal of the block's model */
#define PARAMETER_COUNT 0x46c2au    /* (group) -> parameter count of the block's model */
#define PRESET_MODIFIED 0x43d52u    /* (1): preset modified flag (+ stock `12 45` notice) */
#define GET_DISPATCH 0x429b4u       /* (index, ctx): gated read-class reply builder from the read table */
#define FRAME_SEND 0x40942u         /* (frame, length, ctx): read-class reply (host_reply_serialize) */
#define REPLY_QUEUE 0x15a1eu        /* (frame, length, ctx): notification queue */
#define CONNECTION 0x432ecu         /* () -> 2 when a host listens (stock notification gate) */
#define BINDING(k) (ASSIGN_STATE + 32u + 16u * (k))

/* Binding k if it is live for the current preset (read-only version of assign_valid_map), else 0. */
static uint32_t live_binding(uint32_t k, uint32_t preset, const StockIo *io) {
    uint32_t m = BINDING(k), group = io_r32(io, m + 4);
    if (!io_r32(io, m) || preset != io_r32(io, ASSIGN_STATE + 80) || group >= 10) return 0;
    if (STOCK_CALL(io, BLOCK_ORDINAL, group) != io_r32(io, m + 12)) return 0;
    if (!(io_r32(io, m + 8) < STOCK_CALL(io, PARAMETER_COUNT, group))) return 0;
    return m;
}

/* `12 71` body into `f` (OWN_ASSIGN_FRAME bytes); returns the frame length 3 + 8 n. */
uint32_t own_assign_frame(uint32_t f, const StockIo *io) {
    uint32_t preset = STOCK_CALL0(io, CURRENT_PRESET), n = 0;
    IO_W8(io, f, 0x12); IO_W8(io, f + 1, 0x71);
    for (uint32_t k = 0; k < 3; k++) {
        uint32_t m = live_binding(k, preset, io);
        if (!m) continue;
        uint32_t group = io_r32(io, m + 4), r = f + 3 + 8 * n++;
        IO_W8(io, r, (uint8_t)k); IO_W8(io, r + 1, (uint8_t)group); IO_W8(io, r + 2, (uint8_t)io_r32(io, m + 8)); IO_W8(io, r + 3, 0);
        io_w32(io, r + 4, io_r32(io, OWN_PRESET_IDS + 4 * group));   /* public model ID in that block (active record) */
    }
    IO_W8(io, f + 2, (uint8_t)n);
    return 3 + 8 * n;
}

/* Read-table entry 13 (`12 70`): identity. */
uint32_t own_identity(uint32_t ctx, const StockIo *io) {
    LOCAL_BUFFER(io, f, OWN_IDENTITY_FRAME);
    IO_W8(io, f, 0x12); IO_W8(io, f + 1, 0x70); IO_W8(io, f + 2, OWN_PROTOCOL);
    uint32_t end = 0;
    for (uint32_t i = 0; i < 16; i++) {                         /* version text (NUL-terminated, 8 bytes of room) */
        uint8_t c = end || i >= 8 ? 0 : IO_R8(io, OWN_VERSION_TEXT + i);
        if (!c) end = 1;
        IO_W8(io, f + 3 + i, c);
    }
#ifdef GP50_FEATURE_ENABLE_CONSTRAINTS
    io_w32(io, f + 19, OWN_FEATURES | (1u << 14));
#else
    io_w32(io, f + 19, OWN_FEATURES);
#endif
    return STOCK_CALL(io, FRAME_SEND, f, OWN_IDENTITY_FRAME, ctx);
}

/* Read-table entry 14 (`12 71`): the current preset's knob assignments. */
uint32_t own_assign_read(uint32_t ctx, const StockIo *io) {
    LOCAL_BUFFER(io, f, OWN_ASSIGN_FRAME);
    uint32_t n = own_assign_frame(f, io);
    return STOCK_CALL(io, FRAME_SEND, f, n, ctx);
}

/* `12 71` notification to a listening host, on the stock notification path (connection state 2, reply queue ctx 1;
 * the path of `12 48` and the other stock change notices). */
uint32_t own_assign_notify(const StockIo *io) {
    if (STOCK_CALL0(io, CONNECTION) != 2) return 0;
    LOCAL_BUFFER(io, f, OWN_ASSIGN_FRAME);
    uint32_t n = own_assign_frame(f, io);
    return STOCK_CALL(io, REPLY_QUEUE, f, n, 1);
}

/* The assignment feature's "preset modified" call (editor commit, home reset): the stock call, then the notification. */
uint32_t own_assign_modified(uint32_t value, const StockIo *io) {
    uint32_t r = STOCK_CALL(io, PRESET_MODIFIED, value);
    own_assign_notify(io);
    return r;
}

/* `11 71 dest group param flags`: 0 = done, 1 = refused. Same checks as the on-pedal flow (assign_publish /
 * assign_editor_encoder: block < 10, parameter < the model's parameter count) plus the persistence limit of GPAM v1
 * (parameter < 8); knobs take no flags. A set or a clear marks the preset modified (saved by the normal Save / `11 4f`
 * path; GPAM tail written by assign_stage_copy). Clearing a binding that is not live changes nothing (status 0). */
uint32_t own_assign_set(uint32_t args, uint32_t args_length, const StockIo *io) {
    if (args_length < 4) return 1;
    uint32_t dest = IO_R8(io, args), group = IO_R8(io, args + 1), parameter = IO_R8(io, args + 2), flags = IO_R8(io, args + 3);
    if (dest >= 3 || flags) return 1;                            /* 3-4: footswitches (reserved), others invalid */
    uint32_t preset = STOCK_CALL0(io, CURRENT_PRESET), m = BINDING(dest);
    if (group == 0xff) {
        if (!live_binding(dest, preset, io)) return 0;
        STOCK_CALL0(io, GUARD_ENTER); io_w32(io, m, 0); STOCK_CALL0(io, GUARD_LEAVE);
        STOCK_CALL(io, PRESET_MODIFIED, 1);
        return 0;
    }
    if (group >= 10 || parameter >= 8 || !(parameter < STOCK_CALL(io, PARAMETER_COUNT, group))) return 1;
    uint32_t ordinal = STOCK_CALL(io, BLOCK_ORDINAL, group);
    STOCK_CALL0(io, GUARD_ENTER);                                /* publish atomically for the GUI task */
    if (preset != io_r32(io, ASSIGN_STATE + 80)) {               /* first binding of this preset: drop old ones */
        io_w32(io, ASSIGN_STATE + 80, preset);
        io_w32(io, BINDING(0), 0); io_w32(io, BINDING(1), 0); io_w32(io, BINDING(2), 0);
    }
    io_w32(io, m, 0); io_w32(io, m + 4, group); io_w32(io, m + 8, parameter); io_w32(io, m + 12, ordinal); io_w32(io, m, 1);
    STOCK_CALL0(io, GUARD_LEAVE);
    STOCK_CALL(io, PRESET_MODIFIED, 1);
    return 0;
}

/* Parser hooks (host_parse.c HOST_OWN_GET / HOST_OWN_SET): 1 = selector handled here. */
uint32_t own_get(uint32_t sel, uint32_t length, uint32_t ctx, const StockIo *io) {
    #ifdef GP50_TAP_SAFE_HOST
    if (tap_host_get(sel, length, ctx, io)) return 1;
    #endif
    if (sel == 0x51) { if (length == 2) STOCK_CALL(io, GET_DISPATCH, OWN_INDEX_TELEMETRY, ctx); return 1; }   /* MOD037 route */
    if (sel == 0x70) { STOCK_CALL(io, GET_DISPATCH, OWN_INDEX_IDENTITY, ctx); return 1; }
    if (sel == 0x71) { STOCK_CALL(io, GET_DISPATCH, OWN_INDEX_ASSIGN, ctx); return 1; }
    return 0;
}
uint32_t own_set(uint32_t sel, uint32_t args, uint32_t args_length, uint32_t *status, const StockIo *io) {
    #ifdef GP50_TAP_SAFE_HOST
    if (tap_host_set(sel, args, args_length, status, io)) return 1;
    #endif
    if (sel != 0x71) return 0;
    *status = own_assign_set(args, args_length, io);
    return 1;
}
