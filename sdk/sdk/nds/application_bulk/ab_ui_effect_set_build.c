/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define effect_row_has_second_page bulk_ui_effect_set_build_effect_row_has_second_page
#define effect_row_page_count bulk_ui_effect_set_build_effect_row_page_count
#define effect_refresh_output_image bulk_ui_effect_set_build_effect_refresh_output_image
#define effect_refresh_heading bulk_ui_effect_set_build_effect_refresh_heading
#define effect_refresh_row_images bulk_ui_effect_set_build_effect_refresh_row_images
#include "../../../firmware/reconstructed/nds/ui_effect_set_build.c"
uint32_t nds_bulk_1b8f6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_effect_set_build_effect_row_has_second_page(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1bd28(uint32_t a0,uint32_t a1,uint32_t a2) {(void)a0;(void)a1;(void)a2;return bulk_ui_effect_set_build_effect_row_page_count(a0,a1,a2,(const StockIo *)0);}
uint32_t nds_bulk_1bf52(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_ui_effect_set_build_effect_refresh_heading(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1c038(uint32_t a0) {(void)a0;return bulk_ui_effect_set_build_effect_refresh_output_image(a0,(const StockIo *)0);}
uint32_t nds_bulk_1c074(uint32_t a0) {(void)a0;return bulk_ui_effect_set_build_effect_refresh_row_images(a0,(const StockIo *)0);}
