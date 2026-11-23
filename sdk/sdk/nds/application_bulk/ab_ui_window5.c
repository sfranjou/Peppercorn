/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define save_ignore bulk_ui_window5_save_ignore
#define save_home bulk_ui_window5_save_home
#define save_commit bulk_ui_window5_save_commit
#define save_clear_style bulk_ui_window5_save_clear_style
#define save_draw_slot bulk_ui_window5_save_draw_slot
#define save_turn_slot bulk_ui_window5_save_turn_slot
#define save_turn_char bulk_ui_window5_save_turn_char
#define save_exit bulk_ui_window5_save_exit
#define save_draw_cursor bulk_ui_window5_save_draw_cursor
#define save_erase_move bulk_ui_window5_save_erase_move
#define save_move bulk_ui_window5_save_move
#define save_load_name bulk_ui_window5_save_load_name
#define save_line_create bulk_ui_window5_save_line_create
#define save_box_create bulk_ui_window5_save_box_create
#define save_char_create bulk_ui_window5_save_char_create
#define save_close bulk_ui_window5_save_close
#define widget_mark bulk_ui_window5_widget_mark
#define widget_field bulk_ui_window5_widget_field
#include "../../../firmware/reconstructed/nds/ui_window5.c"
uint32_t nds_bulk_236e4(void) {return bulk_ui_window5_save_ignore((const StockIo *)0);}
uint32_t nds_bulk_236e8(void) {return bulk_ui_window5_save_home((const StockIo *)0);}
uint32_t nds_bulk_236f6(uint32_t a0) {(void)a0;return bulk_ui_window5_save_commit(a0,(const StockIo *)0);}
void nds_bulk_23744(uint32_t a0) {(void)a0;bulk_ui_window5_save_clear_style(a0,(const StockIo *)0);}
void nds_bulk_23756(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;bulk_ui_window5_save_draw_slot(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_237b4(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window5_save_turn_slot(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_237f8(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window5_save_turn_char(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_23876(uint32_t a0) {(void)a0;return bulk_ui_window5_save_exit(a0,(const StockIo *)0);}
uint32_t nds_bulk_238b4(uint32_t a0) {(void)a0;return bulk_ui_window5_save_draw_cursor(a0,(const StockIo *)0);}
uint32_t nds_bulk_23950(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window5_save_erase_move(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_239a0(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window5_save_move(a0,a1,(const StockIo *)0);}
void nds_bulk_239ca(void) {bulk_ui_window5_save_load_name((const StockIo *)0);}
uint32_t nds_bulk_23a28(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;return bulk_ui_window5_save_line_create(a0,a1,a2,(const StockIo *)0);}
uint32_t nds_bulk_23a76(uint32_t a0) {(void)a0;return bulk_ui_window5_save_box_create(a0,(const StockIo *)0);}
uint32_t nds_bulk_23ac0(uint32_t a0) {(void)a0;return bulk_ui_window5_save_char_create(a0,(const StockIo *)0);}
uint32_t nds_bulk_23f92(uint32_t a0) {(void)a0;return bulk_ui_window5_save_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_23f9e(void) {return bulk_ui_window5_save_ignore((const StockIo *)0);}
void nds_bulk_23fa2(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;bulk_ui_window5_widget_mark(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_23fd8(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window5_widget_field(a0,a1,(const StockIo *)0);}
