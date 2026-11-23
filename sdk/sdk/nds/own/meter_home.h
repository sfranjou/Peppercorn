#ifndef GP50_NDS_METER_HOME_H
#define GP50_NDS_METER_HOME_H
#include <stdint.h>
#include "stock_io.h"
#include "assign_home.h"
#include "assign_editor.h"
/* MOD028 home-title meter handlers still in assembly in MOD054 (tick, DRUM mode cycle, EXIT, name restore; the refresh
 * itself is the C router nds_refresh2), ported to C (NDS_ASM_TO_C_INVENTORY.md). DRUM cycles METER_SHOWING 0..3
 * (MOD030+ raised the MOD028 count 3 -> 4); 0 = preset name. */
#ifdef GP50_CATALOG_DIRECT
uint32_t assign_home_tick(uint32_t ctx, uint32_t event, const StockIo *io);
#define HOME_TICK_CALL(io, c, e) assign_home_tick((c), (e), (io))
#else
#define HOME_TICK_CALL(io, c, e) STOCK_CALL((io), 0x16e9d6, (c), (e))   /* host: MOD026 home_tick in MOD054 */
#endif
uint32_t meter_tick(uint32_t ctx, uint32_t event, const StockIo *io);      /* 0x16f400 */
uint32_t meter_drum(uint32_t ctx, uint32_t event, const StockIo *io);      /* 0x16f43c */
uint32_t meter_back(uint32_t ctx, uint32_t event, const StockIo *io);      /* 0x16f4a8 */
uint32_t meter_restore(uint32_t ctx, const StockIo *io);                   /* 0x16f514: preset name in the title */
#endif
