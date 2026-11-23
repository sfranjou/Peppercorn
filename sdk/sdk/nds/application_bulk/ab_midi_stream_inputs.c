/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define midi_sysex_accumulate bulk_midi_stream_inputs_midi_sysex_accumulate
#define midi_stream_scan bulk_midi_stream_inputs_midi_stream_scan
#include "../../../firmware/reconstructed/nds/midi_stream_inputs.c"
uint32_t nds_bulk_16520(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;return bulk_midi_stream_inputs_midi_sysex_accumulate(a0,a1,a2,(const StockIo *)0);}
uint32_t nds_bulk_165e2(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_midi_stream_inputs_midi_stream_scan(a0,a1,(const StockIo *)0);}
