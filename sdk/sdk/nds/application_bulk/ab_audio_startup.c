/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define audio_state_allocate bulk_audio_startup_audio_state_allocate
#define audio_peripheral_setup bulk_audio_startup_audio_peripheral_setup
#include "../../../firmware/reconstructed/nds/audio_startup.c"
uint32_t nds_bulk_49db0(uint32_t a0) {(void)a0;return bulk_audio_startup_audio_peripheral_setup(a0,(const StockIo *)0);}
uint32_t nds_bulk_49f1a(uint32_t a0) {(void)a0;return bulk_audio_startup_audio_state_allocate(a0,(const StockIo *)0);}
