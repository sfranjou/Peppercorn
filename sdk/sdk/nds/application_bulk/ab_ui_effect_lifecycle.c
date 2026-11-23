/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include <stdint.h>
extern const uint32_t legacy_editor_table[];
#define BULK_EDITOR_TABLE ((uint32_t)(uintptr_t)legacy_editor_table)
#include <stdint.h>
extern const uint32_t legacy_editor_table[];
#define BULK_EDITOR_TABLE ((uint32_t)(uintptr_t)legacy_editor_table)
#define effect_window_close bulk_ui_effect_lifecycle_effect_window_close
#define effect_window_open bulk_ui_effect_lifecycle_effect_window_open
#include "../../../firmware/reconstructed/nds/ui_effect_lifecycle.c"
uint32_t nds_bulk_1cc5c(uint32_t a0) {(void)a0;return bulk_ui_effect_lifecycle_effect_window_open(a0,(const StockIo *)0);}
uint32_t nds_bulk_1d2bc(uint32_t a0) {(void)a0;return bulk_ui_effect_lifecycle_effect_window_close(a0,(const StockIo *)0);}
