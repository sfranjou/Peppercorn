/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define gui_global_initialize bulk_ui_global_lifecycle_gui_global_initialize
#define gui_global_tick bulk_ui_global_lifecycle_gui_global_tick
#include "../../../firmware/reconstructed/nds/ui_global_lifecycle.c"
uint32_t nds_bulk_2821c(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_global_lifecycle_gui_global_initialize(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_2830e(uint32_t a0) {(void)a0;return bulk_ui_global_lifecycle_gui_global_tick(a0,(const StockIo *)0);}
