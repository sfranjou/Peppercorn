/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define drum_ignore bulk_ui_drum_drum_ignore
#define drum_exit bulk_ui_drum_drum_exit
#define drum_sync_turn bulk_ui_drum_drum_sync_turn
#define drum_volume_turn bulk_ui_drum_drum_volume_turn
#define drum_bpm_turn bulk_ui_drum_drum_bpm_turn
#define drum_type_next bulk_ui_drum_drum_type_next
#define drum_draw_cursor bulk_ui_drum_drum_draw_cursor
#define drum_draw_volume bulk_ui_drum_drum_draw_volume
#define drum_draw_bpm bulk_ui_drum_drum_draw_bpm
#define drum_footswitch bulk_ui_drum_drum_footswitch
#define drum_draw_play bulk_ui_drum_drum_draw_play
#define drum_play_toggle bulk_ui_drum_drum_play_toggle
#define drum_draw_sync bulk_ui_drum_drum_draw_sync
#define drum_type_turn bulk_ui_drum_drum_type_turn
#define drum_open bulk_ui_drum_drum_open
#define drum_close bulk_ui_drum_drum_close
#define drum_tick bulk_ui_drum_drum_tick
#include "../../../firmware/reconstructed/nds/ui_drum.c"
uint32_t nds_bulk_1ae2c(uint32_t a0) {(void)a0;return bulk_ui_drum_drum_ignore(a0,(const StockIo *)0);}
uint32_t nds_bulk_1ae30(uint32_t a0) {(void)a0;return bulk_ui_drum_drum_exit(a0,(const StockIo *)0);}
uint32_t nds_bulk_1ae3c(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_drum_drum_sync_turn(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1ae4c(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_drum_drum_volume_turn(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1ae98(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_drum_drum_bpm_turn(a0,a1,(const StockIo *)0);}
void nds_bulk_1aee0(uint32_t a0) {(void)a0;bulk_ui_drum_drum_type_next(a0,(const StockIo *)0);}
void nds_bulk_1af04(uint32_t a0) {(void)a0;bulk_ui_drum_drum_draw_cursor(a0,(const StockIo *)0);}
void nds_bulk_1af42(uint32_t a0) {(void)a0;bulk_ui_drum_drum_draw_volume(a0,(const StockIo *)0);}
void nds_bulk_1af7c(uint32_t a0) {(void)a0;bulk_ui_drum_drum_draw_bpm(a0,(const StockIo *)0);}
uint32_t nds_bulk_1afb6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_drum_drum_footswitch(a0,a1,(const StockIo *)0);}
void nds_bulk_1afea(uint32_t a0) {(void)a0;bulk_ui_drum_drum_draw_play(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b0a6(uint32_t a0) {(void)a0;return bulk_ui_drum_drum_play_toggle(a0,(const StockIo *)0);}
void nds_bulk_1b0c2(uint32_t a0) {(void)a0;bulk_ui_drum_drum_draw_sync(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b13e(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_drum_drum_type_turn(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1b21a(uint32_t a0) {(void)a0;return bulk_ui_drum_drum_open(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b730(uint32_t a0) {(void)a0;return bulk_ui_drum_drum_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_1b73c(uint32_t a0) {(void)a0;return bulk_ui_drum_drum_tick(a0,(const StockIo *)0);}
