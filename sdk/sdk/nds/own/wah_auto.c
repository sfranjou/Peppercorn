/* Instruction-reviewed MOD027 assembly (work/wah_auto/source.nds, 0x16f000..0x16f3e7 in MOD054's b). Compared with the
 * original execution: work/firmware_source/nds_wah_auto/verification.json. */
#include "wah_auto.h"
static const char *const PREFIX[10] = { "NR ", "PRE ", "OD ", "AMP ", "CAB ", "EQ ", "MOD ", "DLY ", "RVB ", "NAM " };

void wah_name(uint32_t group, uint32_t parameter, uint32_t buffer, uint32_t length, const StockIo *io) {
    if (group >= 10) { STOCK_CALL(io, 0x46c32, group, parameter, buffer, length); return; }
    LOCAL_BUFFER(io, name, 24);
    STOCK_CALL(io, 0x46c32, group, parameter, name, 24);
    IO_W8(io, name + 23, 0);
    if (!length) return;   /* no room even for the terminator: buffer untouched */
    uint32_t out = buffer, room = length - 1;
    for (const char *p = PREFIX[group]; room && *p; p++, room--) IO_W8(io, out++, (uint8_t)*p);
    for (uint32_t s = name; room && IO_R8(io, s); s++, room--) IO_W8(io, out++, IO_R8(io, s));
    IO_W8(io, out, 0);
}

static void wah_clear(const StockIo *io) {
    io_w32(io, WAH_STATE, 0); io_w32(io, WAH_STATE + 8, 0); io_w32(io, WAH_STATE + 16, 0); io_w32(io, WAH_STATE + 20, 0);
}
static int32_t r16s(const StockIo *io, uint32_t a) { return (int16_t)io_r16(io, a); }

void wah_policy(const StockIo *io) {
    uint32_t started = 0, enabled;
    if (STOCK_CALL(io, 0x475d0, 1) != 7) goto reset;                 /* PRE block model ordinal 7 = C-Wah */
    uint32_t preset = STOCK_CALL0(io, 0x471d6);
    if (io_r32(io, WAH_STATE) && io_r32(io, WAH_STATE + 4) != preset) wah_clear(io);   /* preset changed */
    if (io_r32(io, WAH_OPTION) != 0x3f800000u) goto invalid;
    if (STOCK_CALL0(io, 0x46e80)) goto invalid;                      /* global EXP mode 0 */
    if (STOCK_CALL(io, 0x47bf8, 0) != 1) goto invalid;               /* EXP enabled */
    if (STOCK_CALL(io, 0x47d58, 0, 0) != 1) goto invalid;            /* assigned to PRE ... */
    if (STOCK_CALL(io, 0x47d60, 0, 0) != 3) goto invalid;            /* ... Position */
    int32_t low = r16s(io, WAH_CALIBRATION + 4), span = r16s(io, WAH_CALIBRATION) - low;
    if (span < 100) goto invalid;
    if (!io_r32(io, WAH_STATE)) {
        io_w32(io, WAH_STATE, 1); io_w32(io, WAH_STATE + 4, preset); started = 1;
        io_w32(io, WAH_STATE + 8, 0); io_w32(io, WAH_STATE + 16, 0); io_w32(io, WAH_STATE + 20, 0);
    }
    int32_t position = (int16_t)STOCK_CALL(io, 0x480be, 0) - low;
    if (!(span / 100 < position)) io_w32(io, WAH_STATE + 20, 1);      /* heel: <= 1 % */
    else if (!(position < span / 50)) io_w32(io, WAH_STATE + 20, 0); /* left the heel: >= 2 % */
    enabled = STOCK_CALL(io, 0x452ae, 1);
    if (started) io_w32(io, WAH_STATE + 16, 1 - enabled);
    if (!io_r32(io, WAH_STATE + 20)) {                                /* off the heel: engage if we bypassed it */
        io_w32(io, WAH_STATE + 8, 0);
        if (!io_r32(io, WAH_STATE + 16)) return;
        io_w32(io, WAH_STATE + 16, 0);
        if (enabled) return;
        STOCK_CALL(io, 0x473f0, 1, 1); return;
    }
    if (!enabled) {                                                   /* heel, already bypassed */
        uint32_t owned = io_r32(io, WAH_STATE + 16);
        if (!owned) io_w32(io, WAH_STATE + 8, owned);
        return;
    }
    io_w32(io, WAH_STATE + 16, 0);                                    /* heel, enabled: bypass after 200 ms */
    uint32_t now = io_r32(io, WAH_TICKS);
    if (!io_r32(io, WAH_STATE + 8)) { io_w32(io, WAH_STATE + 8, 1); io_w32(io, WAH_STATE + 12, now); return; }
    if (now - io_r32(io, WAH_STATE + 12) < 200u) return;
    io_w32(io, WAH_STATE + 8, 0); io_w32(io, WAH_STATE + 16, 1);
    STOCK_CALL(io, 0x473f0, 1, 0); return;
invalid:                                                              /* conditions lost: give back a bypass we own */
    if (io_r32(io, WAH_STATE) && io_r32(io, WAH_STATE + 16) && !STOCK_CALL(io, 0x452ae, 1)) {
        wah_clear(io); STOCK_CALL(io, 0x473f0, 1, 1); return;
    }
reset:
    wah_clear(io);
}

uint32_t wah_poll(const StockIo *io) {
    STOCK_CALL0(io, 0x49b52);
    wah_policy(io);
    return 0;
}
