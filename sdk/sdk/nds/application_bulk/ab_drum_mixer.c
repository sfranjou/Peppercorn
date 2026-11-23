/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_mix bulk_drum_mixer_drum_mix
#include "../../../firmware/reconstructed/nds/drum_mixer.c"
uint32_t nds_bulk_17acc(uint32_t a0) {(void)a0;return bulk_drum_mixer_drum_mix(a0,(const StockIo *)0);}
