/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define browser_move_1f0e4 bulk_ui_browser_navigation_browser_move_1f0e4
#define browser_activate_1f1ba bulk_ui_browser_navigation_browser_activate_1f1ba
#include "../../../firmware/reconstructed/nds/ui_browser_navigation.c"
uint32_t nds_bulk_1f0e4(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_browser_navigation_browser_move_1f0e4(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1f1ba(uint32_t a0) {(void)a0;return bulk_ui_browser_navigation_browser_activate_1f1ba(a0,(const StockIo *)0);}
