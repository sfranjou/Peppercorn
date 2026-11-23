/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_buffers_allocate bulk_flash_records_drum_buffers_allocate
#define drum_task_initialize bulk_flash_records_drum_task_initialize
#define flash_scan_occupied bulk_flash_records_flash_scan_occupied
#define flash_scan_last bulk_flash_records_flash_scan_last
#define flash_record_seek bulk_flash_records_flash_record_seek
#define audio_queue_notify bulk_flash_records_audio_queue_notify
#define audio_task_initialize bulk_flash_records_audio_task_initialize
#include "../../../firmware/reconstructed/nds/flash_records.c"
uint32_t nds_bulk_49382(uint32_t a0) {(void)a0;return bulk_flash_records_drum_buffers_allocate(a0,(const StockIo *)0);}
uint32_t nds_bulk_49414(uint32_t a0) {(void)a0;return bulk_flash_records_drum_task_initialize(a0,(const StockIo *)0);}
uint32_t nds_bulk_494c2(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_flash_records_flash_scan_occupied(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_494fc(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_flash_records_flash_scan_last(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_49542(uint32_t a0) {(void)a0;return bulk_flash_records_flash_record_seek(a0,(const StockIo *)0);}
uint32_t nds_bulk_49d7a(void) {return bulk_flash_records_audio_queue_notify((const StockIo *)0);}
uint32_t nds_bulk_49fba(uint32_t a0) {(void)a0;return bulk_flash_records_audio_task_initialize(a0,(const StockIo *)0);}
