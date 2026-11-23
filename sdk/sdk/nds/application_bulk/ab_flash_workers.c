/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define flash_bulk_worker bulk_flash_workers_flash_bulk_worker
#define flash_dual_worker bulk_flash_workers_flash_dual_worker
#define flash_single_worker bulk_flash_workers_flash_single_worker
#define flash_task_start bulk_flash_workers_flash_task_start
#define user_message_task_start bulk_flash_workers_user_message_task_start
#include "../../../firmware/reconstructed/nds/flash_workers.c"
uint32_t nds_bulk_498a6(uint32_t a0) {(void)a0;return bulk_flash_workers_flash_bulk_worker(a0,(const StockIo *)0);}
uint32_t nds_bulk_4990e(uint32_t a0) {(void)a0;return bulk_flash_workers_flash_dual_worker(a0,(const StockIo *)0);}
uint32_t nds_bulk_49982(uint32_t a0) {(void)a0;return bulk_flash_workers_flash_single_worker(a0,(const StockIo *)0);}
uint32_t nds_bulk_49ac8(void) {return bulk_flash_workers_flash_task_start((const StockIo *)0);}
uint32_t nds_bulk_49b16(void) {return bulk_flash_workers_user_message_task_start((const StockIo *)0);}
