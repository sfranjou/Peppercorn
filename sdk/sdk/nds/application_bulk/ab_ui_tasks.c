/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include <stdint.h>
extern void gui(void);
#define GUI_RECEIVE(io) gui()
#include <stdint.h>
extern void gui(void);
#define GUI_RECEIVE(io) gui()
#define gui_main_task bulk_ui_tasks_gui_main_task
#define gui_alternate_task bulk_ui_tasks_gui_alternate_task
#include "../../../firmware/reconstructed/nds/ui_tasks.c"
void nds_bulk_27af0(void) {bulk_ui_tasks_gui_main_task((const StockIo *)0);}
void nds_bulk_27b42(void) {bulk_ui_tasks_gui_alternate_task((const StockIo *)0);}
