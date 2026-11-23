/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define reset_ignore bulk_ui_window11_reset_ignore
#define reset_draw_state bulk_ui_window11_reset_draw_state
#define reset_exit8 bulk_ui_window11_reset_exit8
#define reset_exit6 bulk_ui_window11_reset_exit6
#define reset_exit7 bulk_ui_window11_reset_exit7
#define reset_exit9 bulk_ui_window11_reset_exit9
#define reset_exit5 bulk_ui_window11_reset_exit5
#define reset_confirm bulk_ui_window11_reset_confirm
#define reset_draw_selection bulk_ui_window11_reset_draw_selection
#define reset_turn bulk_ui_window11_reset_turn
#define reset_close bulk_ui_window11_reset_close
#define reset_tick bulk_ui_window11_reset_tick
#include "../../../firmware/reconstructed/nds/ui_window11.c"
uint32_t nds_bulk_22be0(void) {return bulk_ui_window11_reset_ignore((const StockIo *)0);}
void nds_bulk_22be4(uint32_t a0) {(void)a0;bulk_ui_window11_reset_draw_state(a0,(const StockIo *)0);}
uint32_t nds_bulk_22e28(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_exit8(a0,(const StockIo *)0);}
uint32_t nds_bulk_22e46(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_exit6(a0,(const StockIo *)0);}
uint32_t nds_bulk_22e64(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_exit7(a0,(const StockIo *)0);}
uint32_t nds_bulk_22e82(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_exit9(a0,(const StockIo *)0);}
uint32_t nds_bulk_22e9c(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_exit5(a0,(const StockIo *)0);}
void nds_bulk_22eba(uint32_t a0) {(void)a0;bulk_ui_window11_reset_confirm(a0,(const StockIo *)0);}
void nds_bulk_22f00(uint32_t a0) {(void)a0;bulk_ui_window11_reset_draw_selection(a0,(const StockIo *)0);}
void nds_bulk_22ff6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;bulk_ui_window11_reset_turn(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_2361a(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_23648(uint32_t a0) {(void)a0;return bulk_ui_window11_reset_tick(a0,(const StockIo *)0);}
