/* Shared prelude of the pedal builds of the UI input modules (item 9 step 3, MOD053; analysis/firmware/NDS_UI_INPUT.md):
 * the compared sources (firmware/reconstructed/nds, written against stock_io.h) compiled with plain loads/stores and
 * direct calls to the stock addresses (GP50_CATALOG_DIRECT). The StockIo pointer is never dereferenced in this mode, so
 * the stock entry patched to `j` the function passes whatever its caller left in that register.
 * Entry functions are renamed nds_ui_<address> (some readable names are also stock-API symbols, e.g. footswitch_toggle). */
#ifndef GP50_UI_INPUT_MODULE_H
#define GP50_UI_INPUT_MODULE_H
#define GP50_CATALOG_DIRECT 1
/* No switch jump tables: GCC places them inside .text, which the C disassembly round-trip gate (tier a) refuses. */
#pragma GCC optimize("no-jump-tables")
#endif
