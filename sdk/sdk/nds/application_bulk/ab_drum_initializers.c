/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_sequence_init bulk_drum_initializers_drum_sequence_init
#define drum_pcm_init bulk_drum_initializers_drum_pcm_init
#include "../../../firmware/reconstructed/nds/drum_initializers.c"
uint32_t nds_bulk_1786c(uint32_t a0) {(void)a0;return bulk_drum_initializers_drum_sequence_init(a0,(const StockIo *)0);}
uint32_t nds_bulk_17a16(uint32_t a0) {(void)a0;return bulk_drum_initializers_drum_pcm_init(a0,(const StockIo *)0);}
