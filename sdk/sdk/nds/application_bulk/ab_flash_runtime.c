/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_runtime_reset bulk_flash_runtime_drum_runtime_reset
#define flash_runtime_init bulk_flash_runtime_flash_runtime_init
#define flash_stage_allocated bulk_flash_runtime_flash_stage_allocated
#define flash_stage_ring bulk_flash_runtime_flash_stage_ring
#define flash_allocated_tick bulk_flash_runtime_flash_allocated_tick
#define audio_ring_allocate bulk_flash_runtime_audio_ring_allocate
#include "../../../firmware/reconstructed/nds/flash_runtime.c"
uint32_t nds_bulk_491fe(void) {return bulk_flash_runtime_drum_runtime_reset((const StockIo *)0);}
uint32_t nds_bulk_497a8(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_flash_runtime_flash_stage_allocated(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_497f6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_flash_runtime_flash_stage_ring(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_499e8(uint32_t a0) {(void)a0;return bulk_flash_runtime_flash_allocated_tick(a0,(const StockIo *)0);}
uint32_t nds_bulk_49a72(void) {return bulk_flash_runtime_flash_runtime_init((const StockIo *)0);}
uint32_t nds_bulk_49e50(uint32_t a0) {(void)a0;return bulk_flash_runtime_audio_ring_allocate(a0,(const StockIo *)0);}
