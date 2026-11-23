/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include <stdint.h>
#ifdef GP50_FS_AB   /* A/B parameter footswitches (cfg c_defines): the A/B gate runs first, then the admission gate */
extern void gp50_fs_ab_press(uint32_t);
#define FOOTSWITCH_PRESS_TOGGLE(index,io) gp50_fs_ab_press(index)
#else
extern void nds_adm_footswitch(uint32_t);
#define FOOTSWITCH_PRESS_TOGGLE(index,io) nds_adm_footswitch(index)
#endif
#define footswitch_toggle bulk_ui_footswitch_footswitch_toggle
#define footswitch_press bulk_ui_footswitch_footswitch_press
#include "../../../firmware/reconstructed/nds/ui_footswitch.c"
void nds_bulk_47452(uint32_t a0) {(void)a0;bulk_ui_footswitch_footswitch_press(a0,(const StockIo *)0);}
