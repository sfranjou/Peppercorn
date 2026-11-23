/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define tuner_ignore_25994 bulk_ui_tuner_handlers_tuner_ignore_25994
#define tuner_back_25998 bulk_ui_tuner_handlers_tuner_back_25998
#define tuner_mode_25a5a bulk_ui_tuner_handlers_tuner_mode_25a5a
#define tuner_close_26e7a bulk_ui_tuner_handlers_tuner_close_26e7a
#include "../../../firmware/reconstructed/nds/ui_tuner_handlers.c"
uint32_t nds_bulk_25994(void) {return bulk_ui_tuner_handlers_tuner_ignore_25994((const StockIo *)0);}
uint32_t nds_bulk_25998(void) {return bulk_ui_tuner_handlers_tuner_back_25998((const StockIo *)0);}
uint32_t nds_bulk_25a5a(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_tuner_handlers_tuner_mode_25a5a(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_26e7a(uint32_t a0) {(void)a0;return bulk_ui_tuner_handlers_tuner_close_26e7a(a0,(const StockIo *)0);}
