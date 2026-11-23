/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_scale_block bulk_drum_scaler_drum_scale_block
#include "../../../firmware/reconstructed/nds/drum_scaler.c"
uint32_t nds_bulk_49236(uint32_t a0) {(void)a0;return bulk_drum_scaler_drum_scale_block(a0,(const StockIo *)0);}
