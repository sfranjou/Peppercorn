/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define link_poll_prefix bulk_task_poll_loops_link_poll_prefix
#define midi_poll_prefix bulk_task_poll_loops_midi_poll_prefix
#define input_timer_prefix bulk_task_poll_loops_input_timer_prefix
#define link_poll_task bulk_task_poll_loops_link_poll_task
#define midi_poll_task bulk_task_poll_loops_midi_poll_task
#define input_timer_task bulk_task_poll_loops_input_timer_task
#include "../../../firmware/reconstructed/nds/task_poll_loops.c"
void nds_bulk_15428(void) {bulk_task_poll_loops_link_poll_task((const StockIo *)0);}
void nds_bulk_161ae(void) {bulk_task_poll_loops_midi_poll_task((const StockIo *)0);}
void nds_bulk_49d44(void) {bulk_task_poll_loops_input_timer_task((const StockIo *)0);}
