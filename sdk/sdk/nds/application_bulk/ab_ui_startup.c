/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define anim_ignore bulk_ui_startup_anim_ignore
#define anim_open bulk_ui_startup_anim_open
#define anim_close bulk_ui_startup_anim_close
#define anim_tick bulk_ui_startup_anim_tick
#define startup_ignore bulk_ui_startup_startup_ignore
#define startup_gif_event bulk_ui_startup_startup_gif_event
#define startup_to_about bulk_ui_startup_startup_to_about
#define startup_open bulk_ui_startup_startup_open
#define startup_close bulk_ui_startup_startup_close
#define startup_tick bulk_ui_startup_startup_tick
#include "../../../firmware/reconstructed/nds/ui_startup.c"
uint32_t nds_bulk_228b6(uint32_t a0) {(void)a0;return bulk_ui_startup_anim_ignore(a0,(const StockIo *)0);}
uint32_t nds_bulk_228ba(uint32_t a0) {(void)a0;return bulk_ui_startup_anim_open(a0,(const StockIo *)0);}
uint32_t nds_bulk_22986(uint32_t a0) {(void)a0;return bulk_ui_startup_anim_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_2299e(uint32_t a0) {(void)a0;return bulk_ui_startup_anim_tick(a0,(const StockIo *)0);}
uint32_t nds_bulk_22a5c(uint32_t a0) {(void)a0;return bulk_ui_startup_startup_ignore(a0,(const StockIo *)0);}
uint32_t nds_bulk_22a60(uint32_t a0) {(void)a0;return bulk_ui_startup_startup_gif_event(a0,(const StockIo *)0);}
uint32_t nds_bulk_22a7c(uint32_t a0) {(void)a0;return bulk_ui_startup_startup_to_about(a0,(const StockIo *)0);}
uint32_t nds_bulk_22a8a(uint32_t a0) {(void)a0;return bulk_ui_startup_startup_open(a0,(const StockIo *)0);}
uint32_t nds_bulk_22b28(uint32_t a0) {(void)a0;return bulk_ui_startup_startup_close(a0,(const StockIo *)0);}
uint32_t nds_bulk_22b7e(uint32_t a0) {(void)a0;return bulk_ui_startup_startup_tick(a0,(const StockIo *)0);}
