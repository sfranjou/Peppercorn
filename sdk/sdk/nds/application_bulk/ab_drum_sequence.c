/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_sequence_step bulk_drum_sequence_drum_sequence_step
#include "../../../firmware/reconstructed/nds/drum_sequence.c"
uint32_t nds_bulk_178ac(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;return bulk_drum_sequence_drum_sequence_step(a0,a1,a2,(const StockIo *)0);}
