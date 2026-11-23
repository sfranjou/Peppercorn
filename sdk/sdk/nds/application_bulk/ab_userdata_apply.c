/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define userdata_preset_changed bulk_userdata_apply_userdata_preset_changed
#define userdata_preset_apply bulk_userdata_apply_userdata_preset_apply
#define userdata_tempo_apply bulk_userdata_apply_userdata_tempo_apply
#define userdata_switch_mode_apply bulk_userdata_apply_userdata_switch_mode_apply
#define userdata_switches_refresh bulk_userdata_apply_userdata_switches_refresh
#define userdata_link_mode_reset bulk_userdata_apply_userdata_link_mode_reset
#define userdata_window_state bulk_userdata_apply_userdata_window_state
#define userdata_pin_option bulk_userdata_apply_userdata_pin_option
#define userdata_expression_apply bulk_userdata_apply_userdata_expression_apply
#include "../../../firmware/reconstructed/nds/userdata_apply.c"
uint32_t nds_bulk_471e8(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_preset_changed(a0,(const StockIo *)0);}
uint32_t nds_bulk_4722a(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_preset_apply(a0,(const StockIo *)0);}
uint32_t nds_bulk_47302(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_tempo_apply(a0,(const StockIo *)0);}
uint32_t nds_bulk_474ae(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_switch_mode_apply(a0,(const StockIo *)0);}
uint32_t nds_bulk_47526(void) {return bulk_userdata_apply_userdata_switches_refresh((const StockIo *)0);}
uint32_t nds_bulk_47860(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_link_mode_reset(a0,(const StockIo *)0);}
uint32_t nds_bulk_47af6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_userdata_apply_userdata_window_state(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_47b20(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_pin_option(a0,(const StockIo *)0);}
uint32_t nds_bulk_47b64(uint32_t a0) {(void)a0;return bulk_userdata_apply_userdata_expression_apply(a0,(const StockIo *)0);}
