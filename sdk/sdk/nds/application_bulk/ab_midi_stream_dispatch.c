/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define midi_stream_dispatch bulk_midi_stream_dispatch_midi_stream_dispatch
#include "../../../firmware/reconstructed/nds/midi_stream_dispatch.c"
uint32_t nds_bulk_16072(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;return bulk_midi_stream_dispatch_midi_stream_dispatch(a0,a1,a2,(const StockIo *)0);}
