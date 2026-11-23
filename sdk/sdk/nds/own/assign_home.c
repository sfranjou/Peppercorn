/* Instruction-reviewed MOD029 assembly (work/ui_assignment_v3/source.nds: title_restore, bars, reset_prompt, hold, drum,
 * back, home_encoder, tick; in MOD054's b). Compared with the original execution:
 * work/firmware_source/nds_assign_home/verification.json. */
#include "assign_home.h"
#define HOME_KNOBS 0x98u   /* ctx + 0x98 + 4k: knob k widget; ctx + 0x98 also identifies the home root */
#define HOME_TITLE 0x34u

uint32_t assign_title_restore(uint32_t ctx, const StockIo *io) {
    if (io_r32(io, METER_SHOWING)) STOCK_CALL(io, METER_REFRESH, ctx);   /* meter refresh */
    else STOCK_CALL(io, 0x16f514, ctx);                              /* preset name */
    return 0;
}

uint32_t assign_reset_prompt(uint32_t ctx, const StockIo *io) {
    STOCK_CALL(io, 0x16e52c, io_r32(io, ctx + HOME_TITLE), RESET_TEXT);
    return 0;
}

uint32_t assign_bars(uint32_t ctx, const StockIo *io) {
    uint32_t root = io_r32(io, ctx + HOME_KNOBS);
    if (root != io_r32(io, ASSIGN_META + 28)) { io_w32(io, ASSIGN_META + 28, root); io_w32(io, ASSIGN_META + 24, 0); }
    uint32_t before = io_r32(io, ASSIGN_META + 24), mapped = 0;
    for (uint32_t k = 0; k < 3; k++) {
        uint32_t widget = io_r32(io, ctx + HOME_KNOBS + 4 * k), map = STOCK_CALL(io, 0x16e630, k);
        if (map) {                                                  /* assigned: bar = parameter position 0..100 */
            mapped |= 1u << k;
            uint32_t group = io_r32(io, map + 4), parameter = io_r32(io, map + 8);
            uint32_t lo = STOCK_CALL_RF2(io, 0x46c3a, group, parameter), hi = STOCK_CALL_RF2(io, 0x46c42, group, parameter);
            uint32_t value = STOCK_CALL_RF2(io, 0x46c1a, group, parameter);
            uint32_t percent = assign_percent(lo, hi, value);
            STOCK_CALL(io, 0x276da, widget, 0, 100);
            STOCK_CALL(io, 0x276b4, widget, percent, 0);
            STOCK_CALL(io, 0x293fc, STOCK_CALL(io, 0x2da52, widget, 1), 1);
        } else if (before & 1u << k) {                              /* just cleared: stock range and value once */
            STOCK_CALL(io, 0x276da, widget, k == 1 ? 40 : 0, k == 1 ? 260 : 100);
            STOCK_CALL(io, k == 0 ? 0x21ac2 : k == 1 ? 0x219d0 : 0x21a8c, ctx, 0);   /* Master / BPM / P-VOL */
        }
    }
    io_w32(io, ASSIGN_META + 24, mapped);
    return mapped;
}

uint32_t assign_hold(uint32_t ctx, uint32_t event, const StockIo *io) {
    #ifdef GP50_ASSIGNMENT_MENU
    (void)ctx; (void)event;
    io_w32(io,ASSIGN_META+8,0);
    STOCK_CALL(io,0x176a6,7,0); return 0;
    #endif
    (void)event;
    if (STOCK_CALL0(io, 0x46f20) != 1) return 0;                   /* Stomp mode only */
    io_w32(io, ASSIGN_META + 8, 1);
    io_w32(io, ASSIGN_META + 12, io_r32(io, ctx + HOME_KNOBS));
    io_w32(io, ASSIGN_META + 16, STOCK_CALL0(io, 0x471d6));
    assign_reset_prompt(ctx, io);
    return 0;
}

uint32_t assign_drum(uint32_t ctx, uint32_t event, const StockIo *io) {
    #ifdef GP50_ASSIGNMENT_MENU
    (void)ctx; (void)event;
    io_w32(io,ASSIGN_META+8,0);
    STOCK_CALL(io,0x470c0,STOCK_CALL0(io,0x470c8)==0); return 0;
    #endif
    if (!io_r32(io, ASSIGN_META + 8)) return STOCK_CALL(io, 0x16f43c, ctx, event);   /* meter cycle */
    assign_reset_prompt(ctx, io);
    return 0;
}

uint32_t assign_back(uint32_t ctx, uint32_t event, const StockIo *io) {
    if (!io_r32(io, ASSIGN_META + 8)) return STOCK_CALL(io, 0x16f4a8, ctx, event);
    io_w32(io, ASSIGN_META + 8, 0);
    assign_title_restore(ctx, io);
    return 0;
}

static int reset_still_valid(uint32_t ctx, const StockIo *io) {
    return io_r32(io, ctx + HOME_KNOBS) == io_r32(io, ASSIGN_META + 12) && STOCK_CALL0(io, 0x471d6) == io_r32(io, ASSIGN_META + 16);
}

uint32_t assign_home_encoder(uint32_t ctx, uint32_t event, const StockIo *io) {
    if (!io_r32(io, ASSIGN_META + 8)) return STOCK_CALL(io, 0x16e6fe, ctx, event);   /* v2: assigned knob or stock */
    if (STOCK_CALL0(io, 0x46f20) == 1 && reset_still_valid(ctx, io)) {
        if (!io_r32(io, event + 4)) return 0;                     /* no movement: keep waiting */
        uint32_t k = IO_R8(io, event + 1) - 1;
        if (k >= 3) return 0;                                     /* not a knob: consumed */
        uint32_t map = ASSIGN_STATE + 32 + 16 * k;
        if (io_r32(io, map)) { io_w32(io, map, 0); STOCK_CALL(io, 0x43d52, 1); }   /* clear binding, preset modified */
    }
    io_w32(io, ASSIGN_META + 8, 0);                               /* leave reset mode (done or cancelled) */
    assign_title_restore(ctx, io);
    return 0;
}

uint32_t assign_tick(uint32_t ctx, uint32_t event, const StockIo *io) {
    STOCK_CALL(io, 0x16f400, ctx, event);                         /* meter tick (MOD028) */
    assign_bars(ctx, io);
    if (!io_r32(io, ASSIGN_META + 8)) return 0;
    if (reset_still_valid(ctx, io) && STOCK_CALL0(io, 0x46f20) == 1) { assign_reset_prompt(ctx, io); return 0; }
    io_w32(io, ASSIGN_META + 8, 0);
    assign_title_restore(ctx, io);
    return 0;
}
