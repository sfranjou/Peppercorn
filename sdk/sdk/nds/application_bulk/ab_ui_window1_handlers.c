/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define w1_event bulk_ui_window1_handlers_w1_event
#define w1_ignore bulk_ui_window1_handlers_w1_ignore
#define w1_midi bulk_ui_window1_handlers_w1_midi
#define w1_home bulk_ui_window1_handlers_w1_home
#define w1_clear_style bulk_ui_window1_handlers_w1_clear_style
#define w1_sample bulk_ui_window1_handlers_w1_sample
#define w1_mode bulk_ui_window1_handlers_w1_mode
#define w1_turn bulk_ui_window1_handlers_w1_turn
#define w1_style bulk_ui_window1_handlers_w1_style
#include "../../../firmware/reconstructed/nds/ui_window1_handlers.c"
uint32_t nds_bulk_240b4(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window1_handlers_w1_event(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_240cc(void) {return bulk_ui_window1_handlers_w1_ignore((const StockIo *)0);}
void nds_bulk_240d0(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;bulk_ui_window1_handlers_w1_midi(a0,a1,a2,(const StockIo *)0);}
uint32_t nds_bulk_240e8(void) {return bulk_ui_window1_handlers_w1_home((const StockIo *)0);}
void nds_bulk_240f6(uint32_t a0) {(void)a0;bulk_ui_window1_handlers_w1_clear_style(a0,(const StockIo *)0);}
uint32_t nds_bulk_24108(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window1_handlers_w1_sample(a0,a1,(const StockIo *)0);}
void nds_bulk_241ce(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;bulk_ui_window1_handlers_w1_mode(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_2420a(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_window1_handlers_w1_turn(a0,a1,(const StockIo *)0);}
void nds_bulk_242d2(uint32_t a0) {(void)a0;bulk_ui_window1_handlers_w1_style(a0,(const StockIo *)0);}
