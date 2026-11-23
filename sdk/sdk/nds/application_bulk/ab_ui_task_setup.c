/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define gui_register_windows bulk_ui_task_setup_gui_register_windows
#define gui_task_create bulk_ui_task_setup_gui_task_create
#include "../../../firmware/reconstructed/nds/ui_task_setup.c"
uint32_t nds_bulk_279c8(uint32_t a0) {(void)a0;return bulk_ui_task_setup_gui_register_windows(a0,(const StockIo *)0);}
uint32_t nds_bulk_27b74(uint32_t a0) {(void)a0;return bulk_ui_task_setup_gui_task_create(a0,(const StockIo *)0);}
