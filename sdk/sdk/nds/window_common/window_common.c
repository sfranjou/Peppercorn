/* Compared window manager and GUI helpers; linked composition review required. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "../own/stock_io.h"
/* Stock uses lwi/swi for aligned queue messages, callback tables and globals.
 * LOCAL_BUFFER is word-aligned; the send payload halfword is at offset two.
 * These overrides are private to this target adapter, never packed presets. */
static inline uint32_t wc_read_word(const StockIo *io,uint32_t address) {
 (void)io; return *(volatile const uint32_t *)(uintptr_t)address;
}
static inline void wc_write_word(const StockIo *io,uint32_t address,uint32_t value) {
 (void)io; *(volatile uint32_t *)(uintptr_t)address=value;
}
static inline void wc_write_half(const StockIo *io,uint32_t address,uint32_t value) {
 (void)io; *(volatile uint16_t *)(uintptr_t)address=(uint16_t)value;
}
#define io_r32(io,address) wc_read_word((io),(address))
#define io_w32(io,address,value) wc_write_word((io),(address),(value))
#define io_w16(io,address,value) wc_write_half((io),(address),(value))
#define window_manager_init nds_wc_17578
#define window_dispatch nds_wc_175d8
#define window_manager_update nds_wc_17632
#define window_set_period nds_wc_176a0
#define window_switch nds_wc_176a6
#define window_reopen nds_wc_176f4
#define window_current nds_wc_17742
#define window_open nds_wc_17748
#define window_register nds_wc_17786
#define window_register_global nds_wc_1779e
#define window_register_messages nds_wc_177aa
#define window_register_global_messages nds_wc_177f6
#define window_send nds_wc_17842
#include "../../../firmware/reconstructed/nds/ui_window_manager.c"
#define gui_setting_image nds_wc_278b0
#define gui_home_image nds_wc_278ec
#define gui_common_message nds_wc_27928
#define gui_common_reset_message nds_wc_27950
#define gui_adc_mode nds_wc_27968
#define gui_event_pump nds_wc_27ae4
#include "../../../firmware/reconstructed/nds/ui_common.c"
