/* Keep all outer assignment/meter wrappers; replace only the stock body call. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define home_tick_body home_tick_body_c
#include "../../../firmware/reconstructed/nds/ui_home_tick.c"
