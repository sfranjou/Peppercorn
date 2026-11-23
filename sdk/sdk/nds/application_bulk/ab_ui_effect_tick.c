/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define effect_window_tick bulk_ui_effect_tick_effect_window_tick
#include "../../../firmware/reconstructed/nds/ui_effect_tick.c"
uint32_t nds_bulk_1d2c8(uint32_t a0) {(void)a0;return bulk_ui_effect_tick_effect_window_tick(a0,(const StockIo *)0);}
