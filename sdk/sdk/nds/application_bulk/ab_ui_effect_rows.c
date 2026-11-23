/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define effect_rows_load bulk_ui_effect_rows_effect_rows_load
#define effect_rows_build bulk_ui_effect_rows_effect_rows_build
#include "../../../firmware/reconstructed/nds/ui_effect_rows.c"
uint32_t nds_bulk_1ba8c(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_effect_rows_effect_rows_load(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1c70a(uint32_t a0) {(void)a0;return bulk_ui_effect_rows_effect_rows_build(a0,(const StockIo *)0);}
