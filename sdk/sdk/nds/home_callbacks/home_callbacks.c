/* Compared home callbacks; existing MOD055 theme retained. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "../own/stock_io.h"
/* All word reads below are stock lwi widget pointers at aligned dialog offsets.
 * Keep byte access for flag fields; this adapter applies only to these callbacks. */
static inline uint32_t home_aligned_word(const StockIo *io,uint32_t address) {
 (void)io; return *(volatile const uint32_t *)(uintptr_t)address;
}
#define io_r32(io,address) home_aligned_word((io),(address))
#define home_noop_2159c nds_hcb_2159c
#define home_toggle_215a0 nds_hcb_215a0
#define home_disable_215b6 nds_hcb_215b6
#define home_looper_215c8 nds_hcb_215c8
#define home_tuner_215ea nds_hcb_215ea
#define home_save_2160c nds_hcb_2160c
#define home_settings_2161a nds_hcb_2161a
#define home_effect_21628 nds_hcb_21628
#define home_close_224e6 nds_hcb_224e6
#include "../../../firmware/reconstructed/nds/ui_home_navigation.c"
#define home_toggle_21636 nds_hcb_21636
#include "../../../firmware/reconstructed/nds/ui_home_toggle.c"
#define home_status_21b1a nds_hcb_21b1a
#define home_release_21cf4 nds_hcb_21cf4
#define home_mode_widgets_21d2e nds_hcb_21d2e
#define home_mode_toggle_21da6 nds_hcb_21da6
#include "../../../firmware/reconstructed/nds/ui_home_status.c"
#define home_press_21baa nds_hcb_21baa
#include "../../../firmware/reconstructed/nds/ui_home_press.c"
