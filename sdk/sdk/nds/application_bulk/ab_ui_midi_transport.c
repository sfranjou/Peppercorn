/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define midi_patch_sub_167f0 bulk_ui_midi_transport_midi_patch_sub_167f0
#define midi_patch_add_16866 bulk_ui_midi_transport_midi_patch_add_16866
#define midi_looper_play_16a92 bulk_ui_midi_transport_midi_looper_play_16a92
#define midi_looper_clear_16af6 bulk_ui_midi_transport_midi_looper_clear_16af6
#include "../../../firmware/reconstructed/nds/ui_midi_transport.c"
uint32_t nds_bulk_167f0(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_midi_transport_midi_patch_sub_167f0(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_16866(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_midi_transport_midi_patch_add_16866(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_16a92(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_midi_transport_midi_looper_play_16a92(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_16af6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_midi_transport_midi_looper_clear_16af6(a0,a1,(const StockIo *)0);}
