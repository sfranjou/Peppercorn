/* Instruction-reviewed MOD029 assembly (work/ui_assignment_v3/source.nds: crc32, u32, preset_read, stage_copy, commit,
 * percent; 0x16ec00..0x16efa2 and 0x16f900..0x16faac in MOD054's b). Compared with the original execution:
 * work/firmware_source/nds_assign_store/verification.json. */
#include "assign_store.h"

uint32_t assign_crc32(uint32_t address, uint32_t length, const StockIo *io) {
    uint32_t crc = 0xffffffffu;
    for (; length; length--, address++) {
        crc ^= IO_R8(io, address);
        for (int k = 0; k < 8; k++) crc = crc & 1u ? crc >> 1 ^ 0xedb88320u : crc >> 1;
    }
    return ~crc;
}

uint32_t assign_u32(uint32_t address, const StockIo *io) { return io_r32(io, address); }

static void clear_live(const StockIo *io) {
    io_w32(io, ASSIGN_STATE + 32, 0); io_w32(io, ASSIGN_STATE + 48, 0); io_w32(io, ASSIGN_STATE + 64, 0);
}

uint32_t assign_preset_read(uint32_t buffer, uint32_t slot, uint32_t length, const StockIo *io) {
    uint32_t result = STOCK_CALL(io, 0x4972e, buffer, slot, length);
    if (buffer != ACTIVE_RECORD) return result;                  /* temporary buffers: stock behaviour only */
    clear_live(io); io_w32(io, ASSIGN_META + 8, 0);              /* no stale bindings, reset mode off */
    io_w32(io, ASSIGN_STATE + 80, STOCK_CALL0(io, 0x471d6));
    if (result || slot >= 100 || length != 426 || assign_u32(buffer, io) != 0x15aa5u) return result;
    LOCAL_BUFFER(io, tail, 64);
    LOCAL_BUFFER(io, live, 48);
    if (STOCK_CALL(io, 0x10f9e, ((slot + 1500) << 10) + 512, tail, 64, 10)) return result;   /* flash read of the tail */
    if (io_r32(io, tail) != GPAM_MAGIC || io_r32(io, tail + 4) != GPAM_VERSION || io_r32(io, tail + 12)
        || io_r32(io, tail + 52) || io_r32(io, tail + 56)) return result;
    if (assign_crc32(buffer, 426, io) != io_r32(io, tail + 8) || assign_crc32(tail, 60, io) != io_r32(io, tail + 60)) return result;
    STOCK_CALL(io, 0xd0c6c, live, 0, 48);
    for (uint32_t k = 0; k < 3; k++) {
        uint32_t rec = tail + 16 + 12 * k, valid = IO_R8(io, rec);
        if (!valid) {
            if (io_r32(io, rec) || io_r32(io, rec + 4) || io_r32(io, rec + 8)) goto bad;
            continue;
        }
        uint32_t group = IO_R8(io, rec + 1), parameter = IO_R8(io, rec + 2), id = io_r32(io, rec + 4);
        if (valid != 1 || group >= 10 || parameter >= 8 || IO_R8(io, rec + 3) || io_r32(io, rec + 8)) goto bad;
        if (assign_u32(PRESET_IDS + 4 * group, io) != id) goto bad;    /* binding belongs to the model in that block */
        uint32_t ordinal = STOCK_CALL(io, 0x439dc, group, id);
        if (STOCK_CALL(io, 0x439b6, group, ordinal) != id) goto bad;  /* catalog round trip */
        uint32_t out = live + 16 * k;
        io_w32(io, out + 12, ordinal); io_w32(io, out + 4, group); io_w32(io, out + 8, parameter); io_w32(io, out, 1);
    }
    STOCK_CALL0(io, 0x5c0e2);                                     /* publish under the stock guard */
    STOCK_CALL(io, 0xd0b90, ASSIGN_STATE + 32, live, 48);
    STOCK_CALL0(io, 0x5c102);
    return result;
bad:
    clear_live(io);
    return result;
}

uint32_t assign_stage_copy(uint32_t destination, uint32_t source, uint32_t length, const StockIo *io) {
    uint32_t result = STOCK_CALL(io, 0xd0b90, destination, source, length);
    if (length != 426) return result;
    STOCK_CALL(io, 0xd0c6c, destination + 512, 0, 64);           /* tail always rewritten: none, or ours */
    if (source != ACTIVE_RECORD) return result;
    LOCAL_BUFFER(io, maps, 48);
    STOCK_CALL0(io, 0x5c0e2);
    uint32_t owner = io_r32(io, ASSIGN_STATE + 80);
    STOCK_CALL(io, 0xd0b90, maps, ASSIGN_STATE + 32, 48);
    STOCK_CALL0(io, 0x5c102);
    if (STOCK_CALL0(io, 0x471d6) != owner) return result;        /* bindings of another preset: write none */
    io_w32(io, destination + 512, GPAM_MAGIC); io_w32(io, destination + 516, GPAM_VERSION);
    io_w32(io, destination + 520, assign_crc32(source, 426, io));
    for (uint32_t k = 0; k < 3; k++) {
        uint32_t m = maps + 16 * k;
        if (!io_r32(io, m)) continue;
        uint32_t group = io_r32(io, m + 4);
        if (group >= 10 || STOCK_CALL(io, 0x475d0, group) != io_r32(io, m + 12)) continue;   /* model changed since */
        uint32_t parameter = io_r32(io, m + 8);
        if (!(parameter < STOCK_CALL(io, 0x46c2a, group))) continue;                          /* parameter count */
        uint32_t rec = destination + 528 + 12 * k;
        IO_W8(io, rec, 1); IO_W8(io, rec + 1, group); IO_W8(io, rec + 2, parameter);
        io_w32(io, rec + 4, assign_u32(source + 38 + 4 * group, io));
    }
    io_w32(io, destination + 572, assign_crc32(destination + 512, 60, io));
    uint32_t slot = IO_R8(io, source + 8) | (uint32_t)IO_R8(io, source + 9) << 8;
    if (slot < 100) io_w32(io, ASSIGN_STATE + 80, slot);
    return result;
}

uint32_t assign_commit(uint32_t context, uint32_t event, const StockIo *io) {
    if (!STOCK_CALL(io, 0x16e558, context, event)) return 0;     /* v2 commit (transactional) */
    STOCK_CALL(io, 0x43d52, 1);                                   /* preset modified */
    return 1;
}

static int exponent_max(uint32_t bits) { return (bits >> 23 & 0xff) == 0xff; }
static float fbits(uint32_t u) { union { uint32_t u; float f; } v = { .u = u }; return v.f; }
uint32_t assign_percent(uint32_t minimum, uint32_t maximum, uint32_t current) {
    if (exponent_max(minimum) || exponent_max(maximum) || exponent_max(current)) return 0;
    float lo = fbits(minimum), hi = fbits(maximum), v = fbits(current);
    if (hi <= lo || v <= lo) return 0;
    if (hi <= v) return 100;
    int32_t p = (int32_t)((v - lo) / (hi - lo) * 100.0f);
    if (p < 0) return 0;
    return (uint32_t)p < 101u ? (uint32_t)p : 100;
}
