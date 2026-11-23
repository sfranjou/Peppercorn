/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define userdata_boot_version_text bulk_userdata_signal_userdata_boot_version_text
#define userdata_text_format bulk_userdata_signal_userdata_text_format
#define userdata_link_version_text bulk_userdata_signal_userdata_link_version_text
#define userdata_signal_init bulk_userdata_signal_userdata_signal_init
#define userdata_signal_sample bulk_userdata_signal_userdata_signal_sample
#define userdata_signal_changed bulk_userdata_signal_userdata_signal_changed
#include "../../../firmware/reconstructed/nds/userdata_signal.c"
uint32_t nds_bulk_479d4(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_userdata_signal_userdata_boot_version_text(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_47a22(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_userdata_signal_userdata_text_format(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_47a36(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_userdata_signal_userdata_link_version_text(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_47f22(void) {return bulk_userdata_signal_userdata_signal_init((const StockIo *)0);}
uint32_t nds_bulk_47f7c(void) {return bulk_userdata_signal_userdata_signal_sample((const StockIo *)0);}
uint32_t nds_bulk_47fc2(uint32_t a0) {(void)a0;return bulk_userdata_signal_userdata_signal_changed(a0,(const StockIo *)0);}
