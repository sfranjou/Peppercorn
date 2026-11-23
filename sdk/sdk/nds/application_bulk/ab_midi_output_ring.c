/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define midi_output_enqueue bulk_midi_output_ring_midi_output_enqueue
#define midi_output_dequeue bulk_midi_output_ring_midi_output_dequeue
#include "../../../firmware/reconstructed/nds/midi_output_ring.c"
uint32_t nds_bulk_15480(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3) {(void)a0;(void)a1;(void)a2;(void)a3;return bulk_midi_output_ring_midi_output_enqueue(a0,a1,a2,a3,(const StockIo *)0);}
uint32_t nds_bulk_15548(uint32_t a0) {(void)a0;return bulk_midi_output_ring_midi_output_dequeue(a0,(const StockIo *)0);}
