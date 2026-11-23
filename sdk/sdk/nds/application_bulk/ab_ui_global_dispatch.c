/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define gui_global_action bulk_ui_global_dispatch_gui_global_action
#define gui_global_action_one bulk_ui_global_dispatch_gui_global_action_one
#define gui_global_action_zero bulk_ui_global_dispatch_gui_global_action_zero
#include "../../../firmware/reconstructed/nds/ui_global_dispatch.c"
uint32_t nds_bulk_28128(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;return bulk_ui_global_dispatch_gui_global_action(a0,a1,a2,(const StockIo *)0);}
uint32_t nds_bulk_28208(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_global_dispatch_gui_global_action_one(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_28212(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_global_dispatch_gui_global_action_zero(a0,a1,(const StockIo *)0);}
