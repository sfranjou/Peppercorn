/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define expcal_pedal bulk_ui_exp_calibrate_expcal_pedal
#define expcal_ignore bulk_ui_exp_calibrate_expcal_ignore
#define expcal_exit bulk_ui_exp_calibrate_expcal_exit
#define expcal_draw_step bulk_ui_exp_calibrate_expcal_draw_step
#define expcal_draw_footer bulk_ui_exp_calibrate_expcal_draw_footer
#define expcal_press bulk_ui_exp_calibrate_expcal_press
#define expcal_box_create bulk_ui_exp_calibrate_expcal_box_create
#define expcal_open bulk_ui_exp_calibrate_expcal_open
#define expcal_close bulk_ui_exp_calibrate_expcal_close
#define expcal_tick bulk_ui_exp_calibrate_expcal_tick
#include "../../../firmware/reconstructed/nds/ui_exp_calibrate.c"
uint32_t nds_bulk_2115c(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_exp_calibrate_expcal_pedal(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_21178(uint32_t a0) {(void)a0;return bulk_ui_exp_calibrate_expcal_ignore(a0,(const StockIo *)0);}
uint32_t nds_bulk_2117c(uint32_t a0) {(void)a0;return bulk_ui_exp_calibrate_expcal_exit(a0,(const StockIo *)0);}
void nds_bulk_21190(uint32_t a0) {(void)a0;bulk_ui_exp_calibrate_expcal_draw_step(a0,(const StockIo *)0);}
void nds_bulk_2123c(uint32_t a0) {(void)a0;bulk_ui_exp_calibrate_expcal_draw_footer(a0,(const StockIo *)0);}
uint32_t nds_bulk_21290(uint32_t a0) {(void)a0;return bulk_ui_exp_calibrate_expcal_press(a0,(const StockIo *)0);}
uint32_t nds_bulk_21318(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3) {(void)a0;(void)a1;(void)a2;(void)a3;return bulk_ui_exp_calibrate_expcal_box_create(a0,a1,a2,a3,(const StockIo *)0);}
uint32_t nds_bulk_213a4(uint32_t a0) {(void)a0;return bulk_ui_exp_calibrate_expcal_open(a0,(const StockIo *)0);}
uint32_t nds_bulk_2158c(uint32_t a0) {(void)a0;return bulk_ui_exp_calibrate_expcal_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_21598(uint32_t a0) {(void)a0;return bulk_ui_exp_calibrate_expcal_tick(a0,(const StockIo *)0);}
