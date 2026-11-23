/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define midi_program_dispatch bulk_midi_program_dispatch_midi_program_dispatch
#include "../../../firmware/reconstructed/nds/midi_program_dispatch.c"
uint32_t nds_bulk_midi_context_c(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3,uint32_t saved_s0) {return bulk_midi_program_dispatch_midi_program_dispatch(a0,a1,a2,a3,saved_s0,(const StockIo *)0);}
