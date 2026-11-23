/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define window12_ignore bulk_ui_window12_window12_ignore
#define window12_back bulk_ui_window12_window12_back
#define window12_scroll bulk_ui_window12_window12_scroll
#define window12_press bulk_ui_window12_window12_press
#define window12_draw_highlight bulk_ui_window12_window12_draw_highlight
#define window12_draw_title bulk_ui_window12_window12_draw_title
#define window12_draw_rows bulk_ui_window12_window12_draw_rows
#define window12_draw_footer bulk_ui_window12_window12_draw_footer
#define window12_open bulk_ui_window12_window12_open
#define window12_close bulk_ui_window12_window12_close
#define window12_tick bulk_ui_window12_window12_tick
#include "../../../firmware/reconstructed/nds/ui_window12.c"
uint32_t nds_bulk_1a0a2(uint32_t a0) {(void)a0;return bulk_ui_window12_window12_ignore(a0,(const StockIo *)0);}
uint32_t nds_bulk_1a0a6(uint32_t a0) {(void)a0;return bulk_ui_window12_window12_back(a0,(const StockIo *)0);}
uint32_t nds_bulk_1a0b6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window12_window12_scroll(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1a136(uint32_t a0) {(void)a0;return bulk_ui_window12_window12_press(a0,(const StockIo *)0);}
void nds_bulk_1a17e(uint32_t a0) {(void)a0;bulk_ui_window12_window12_draw_highlight(a0,(const StockIo *)0);}
void nds_bulk_1a22a(uint32_t a0) {(void)a0;bulk_ui_window12_window12_draw_title(a0,(const StockIo *)0);}
void nds_bulk_1a264(uint32_t a0) {(void)a0;bulk_ui_window12_window12_draw_rows(a0,(const StockIo *)0);}
void nds_bulk_1a4a6(uint32_t a0) {(void)a0;bulk_ui_window12_window12_draw_footer(a0,(const StockIo *)0);}
uint32_t nds_bulk_1a620(uint32_t a0) {(void)a0;return bulk_ui_window12_window12_open(a0,(const StockIo *)0);}
uint32_t nds_bulk_1ac40(uint32_t a0) {(void)a0;return bulk_ui_window12_window12_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_1ac66(uint32_t a0) {(void)a0;return bulk_ui_window12_window12_tick(a0,(const StockIo *)0);}
