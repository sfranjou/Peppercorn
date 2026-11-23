/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define data_param_text bulk_data_settings_data_param_text
#define data_param_text_stored bulk_data_settings_data_param_text_stored
#define data_order_save bulk_data_settings_data_order_save
#define data_order_load bulk_data_settings_data_order_load
#define data_order_get bulk_data_settings_data_order_get
#define data_order_move bulk_data_settings_data_order_move
#define data_order_reset bulk_data_settings_data_order_reset
#define data_settings_save bulk_data_settings_data_settings_save
#define data_settings_defaults bulk_data_settings_data_settings_defaults
#define data_settings_upgrade bulk_data_settings_data_settings_upgrade
#define data_settings_load bulk_data_settings_data_settings_load
#include "../../../firmware/reconstructed/nds/data_settings.c"
uint32_t nds_bulk_43c92(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3,float value0) {(void)a0;(void)a1;(void)a2;(void)a3;union {float f;uint32_t u;} floatword0={.f=value0};return bulk_data_settings_data_param_text(a0,a1,a2,a3,floatword0.u,(const StockIo *)0);}
uint32_t nds_bulk_43d36(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3) {(void)a0;(void)a1;(void)a2;(void)a3;return bulk_data_settings_data_param_text_stored(a0,a1,a2,a3,(const StockIo *)0);}
