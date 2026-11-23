/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include <stdint.h>
extern const uint32_t legacy_home_table[];
#define BULK_HOME_TABLE ((uint32_t)(uintptr_t)legacy_home_table)
#define home_open_21e44 bulk_ui_home_open_home_open_21e44
#include "../../../firmware/reconstructed/nds/ui_home_open.c"
uint32_t nds_bulk_21e44(uint32_t a0) {(void)a0;return bulk_ui_home_open_home_open_21e44(a0,(const StockIo *)0);}
