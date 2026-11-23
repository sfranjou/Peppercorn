/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define state_snapshot_push bulk_state_snapshots_state_snapshot_push
#define state_snapshot_pop bulk_state_snapshots_state_snapshot_pop
#include "../../../firmware/reconstructed/nds/state_snapshots.c"
uint32_t nds_bulk_170de(void) {return bulk_state_snapshots_state_snapshot_push((const StockIo *)0);}
uint32_t nds_bulk_1712a(uint32_t a0) {(void)a0;return bulk_state_snapshots_state_snapshot_pop(a0,(const StockIo *)0);}
