/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define gui_global_led_leave bulk_ui_global_led_gui_global_led_leave
#define gui_global_led_enter bulk_ui_global_led_gui_global_led_enter
#include "../../../firmware/reconstructed/nds/ui_global_led.c"
uint32_t nds_bulk_27f90(void) {return bulk_ui_global_led_gui_global_led_leave((const StockIo *)0);}
uint32_t nds_bulk_27fbc(void) {return bulk_ui_global_led_gui_global_led_enter((const StockIo *)0);}
