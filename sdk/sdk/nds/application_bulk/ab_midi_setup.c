/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define uart_dma_task_initialize bulk_midi_setup_uart_dma_task_initialize
#define midi_dma_task_initialize bulk_midi_setup_midi_dma_task_initialize
#define uart_port_initialize bulk_midi_setup_uart_port_initialize
#define midi_port_initialize bulk_midi_setup_midi_port_initialize
#define midi_control_change bulk_midi_setup_midi_control_change
#define midi_controller_route bulk_midi_setup_midi_controller_route
#include "../../../firmware/reconstructed/nds/midi_setup.c"
uint32_t nds_bulk_155fe(void) {return bulk_midi_setup_uart_dma_task_initialize((const StockIo *)0);}
uint32_t nds_bulk_15646(void) {return bulk_midi_setup_uart_port_initialize((const StockIo *)0);}
uint32_t nds_bulk_1630c(void) {return bulk_midi_setup_midi_dma_task_initialize((const StockIo *)0);}
uint32_t nds_bulk_16354(void) {return bulk_midi_setup_midi_port_initialize((const StockIo *)0);}
uint32_t nds_bulk_163e4(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_midi_setup_midi_control_change(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_16436(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3) {(void)a0;(void)a1;(void)a2;(void)a3;return bulk_midi_setup_midi_controller_route(a0,a1,a2,a3,(const StockIo *)0);}
