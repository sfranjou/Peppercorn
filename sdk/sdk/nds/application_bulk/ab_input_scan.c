/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define encoder_setup bulk_input_scan_encoder_setup
#define encoder_count bulk_input_scan_encoder_count
#define encoder_step bulk_input_scan_encoder_step
#define encoder_read_pins bulk_input_scan_encoder_read_pins
#define key_sample bulk_input_scan_key_sample
#define key_check_init bulk_input_scan_key_check_init
#define key_check_update bulk_input_scan_key_check_update
#define key_check_word bulk_input_scan_key_check_word
#define gpio_channel_keys bulk_input_scan_gpio_channel_keys
#include "../../../firmware/reconstructed/nds/input_scan.c"
void nds_bulk_1575c(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;bulk_input_scan_encoder_setup(a0,a1,(const StockIo *)0);}
void nds_bulk_15c36(void) {bulk_input_scan_key_check_init((const StockIo *)0);}
uint32_t nds_bulk_15e9e(void) {return bulk_input_scan_key_check_word((const StockIo *)0);}
