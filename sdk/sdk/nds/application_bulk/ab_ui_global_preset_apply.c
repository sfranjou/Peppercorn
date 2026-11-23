/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define gui_global_next_apply bulk_ui_global_preset_apply_gui_global_next_apply
#define gui_global_prev_apply bulk_ui_global_preset_apply_gui_global_prev_apply
#include "../../../firmware/reconstructed/nds/ui_global_preset_apply.c"
uint32_t nds_bulk_27f20(void) {return bulk_ui_global_preset_apply_gui_global_next_apply((const StockIo *)0);}
uint32_t nds_bulk_27f5a(void) {return bulk_ui_global_preset_apply_gui_global_prev_apply((const StockIo *)0);}
