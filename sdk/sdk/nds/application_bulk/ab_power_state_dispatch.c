/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define power_state_update bulk_power_state_dispatch_power_state_update
#include "../../../firmware/reconstructed/nds/power_state_dispatch.c"
uint32_t nds_bulk_16fba(uint32_t a0) {(void)a0;return bulk_power_state_dispatch_power_state_update(a0,(const StockIo *)0);}
