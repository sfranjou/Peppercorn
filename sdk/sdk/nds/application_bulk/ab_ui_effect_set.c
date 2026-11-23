/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define effect_set_knob_enc bulk_ui_effect_set_effect_set_knob_enc
#define effect_set_next_page bulk_ui_effect_set_effect_set_next_page
#define effect_set_overlay_on bulk_ui_effect_set_effect_set_overlay_on
#define effect_set_overlay_off bulk_ui_effect_set_effect_set_overlay_off
#define effect_set_hold_release bulk_ui_effect_set_effect_set_hold_release
#define effect_set_show_name bulk_ui_effect_set_effect_set_show_name
#define effect_set_refresh_name bulk_ui_effect_set_effect_set_refresh_name
#define effect_set_exit_to_8 bulk_ui_effect_set_effect_set_exit_to_8
#define effect_set_exit_to_6 bulk_ui_effect_set_effect_set_exit_to_6
#define effect_set_exit_to_3 bulk_ui_effect_set_effect_set_exit_to_3
#define effect_set_footswitch_b_up bulk_ui_effect_set_effect_set_footswitch_b_up
#define effect_set_footswitch_a_up bulk_ui_effect_set_effect_set_footswitch_a_up
#define effect_set_read_globals bulk_ui_effect_set_effect_set_read_globals
#define effect_set_page_info bulk_ui_effect_set_effect_set_page_info
#define effect_set_preset_up bulk_ui_effect_set_effect_set_preset_up
#define effect_set_preset_down bulk_ui_effect_set_effect_set_preset_down
#define effect_set_footswitch_b_down bulk_ui_effect_set_effect_set_footswitch_b_down
#define effect_set_footswitch_a_down bulk_ui_effect_set_effect_set_footswitch_a_down
#define effect_set_encoder bulk_ui_effect_set_effect_set_encoder
#define effect_set_load_params bulk_ui_effect_set_effect_set_load_params
#define effect_set_row_marks bulk_ui_effect_set_effect_set_row_marks
#define effect_set_switch_style bulk_ui_effect_set_effect_set_switch_style
#define effect_set_clear_rows bulk_ui_effect_set_effect_set_clear_rows
#define effect_set_rebuild bulk_ui_effect_set_effect_set_rebuild
#define effect_set_tab_colours bulk_ui_effect_set_effect_set_tab_colours
#define EFFECT_SWITCH_ON_COLOUR 0xfffffe23u   /* stock blue */
#include "../../../firmware/reconstructed/nds/ui_effect_set.c"
uint32_t nds_bulk_1b912(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_next_page(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b93e(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_overlay_on(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b948(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_hold_release(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b958(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_overlay_off(a0,(const StockIo *)0);}
void nds_bulk_1b962(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_show_name(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b99a(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_refresh_name(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b9a4(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_exit_to_8(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b9be(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_exit_to_6(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b9d8(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_exit_to_3(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b9ec(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_footswitch_b_up(a0,(const StockIo *)0);}
uint32_t nds_bulk_1ba16(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_footswitch_a_up(a0,(const StockIo *)0);}
void nds_bulk_1ba40(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_read_globals(a0,(const StockIo *)0);}
void nds_bulk_1bd08(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;bulk_ui_effect_set_effect_set_page_info(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1bd62(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_preset_up(a0,(const StockIo *)0);}
uint32_t nds_bulk_1bda8(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_preset_down(a0,(const StockIo *)0);}
uint32_t nds_bulk_1bdf0(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_footswitch_b_down(a0,(const StockIo *)0);}
uint32_t nds_bulk_1be38(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_footswitch_a_down(a0,(const StockIo *)0);}
void nds_bulk_1bfe6(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_load_params(a0,(const StockIo *)0);}
void nds_bulk_1c128(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_switch_style(a0,(const StockIo *)0);}
void nds_bulk_1c2d0(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_row_marks(a0,(const StockIo *)0);}
void nds_bulk_1cb10(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_clear_rows(a0,(const StockIo *)0);}
uint32_t nds_bulk_1cb56(uint32_t a0) {(void)a0;return bulk_ui_effect_set_effect_set_rebuild(a0,(const StockIo *)0);}
void nds_bulk_1cc04(uint32_t a0) {(void)a0;bulk_ui_effect_set_effect_set_tab_colours(a0,(const StockIo *)0);}
