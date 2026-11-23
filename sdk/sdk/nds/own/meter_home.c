/* Instruction-reviewed MOD028 assembly (work/processing_meter/source.nds: tick, drum, back, restore; in MOD054's b, where
 * the refresh calls go to nds_refresh2 and DRUM counts 4 modes). Compared with the original execution:
 * work/firmware_source/nds_meter_home/verification.json. */
#include "meter_home.h"

uint32_t meter_restore(uint32_t ctx, const StockIo *io) {
    uint32_t name = STOCK_CALL0(io, 0x472b8);                       /* current preset name */
    assign_set_text(io_r32(io, ctx + 0x34), name, io);
    return 0;
}

uint32_t meter_tick(uint32_t ctx, uint32_t event, const StockIo *io) {
    HOME_TICK_CALL(io, ctx, event);
    STOCK_CALL(io, METER_REFRESH, ctx);
    return 0;
}

uint32_t meter_drum(uint32_t ctx, uint32_t event, const StockIo *io) {
    (void)event;
    uint32_t mode = io_r32(io, METER_SHOWING) + 1;
    if (mode == 4) mode = 0;
    io_w32(io, METER_SHOWING, mode);
    if (mode) STOCK_CALL(io, METER_REFRESH, ctx);
    else meter_restore(ctx, io);
    return 0;
}

uint32_t meter_back(uint32_t ctx, uint32_t event, const StockIo *io) {
    if (!io_r32(io, METER_SHOWING)) return STOCK_CALL(io, 0x2159c, ctx, event);   /* stock home EXIT */
    io_w32(io, METER_SHOWING, 0);
    meter_restore(ctx, io);
    return 0;
}
