/* stock_in_place (patching release): the effect-set window's four footswitch handlers run as stock code. These entry
 * wrappers keep the A/B footswitch assignment check (fs_ab_ui.c) in front of each stock handler, as the compiled
 * translation did: a consumed press returns 0, otherwise the stock handler runs through its prologue-replay tail
 * (es_stock_<entry>, application_bulk_c CODE) and its result is returned. */
#include <stdint.h>

uint32_t gp50_fs_ab_editor_foot(uint32_t dlg, uint32_t fs, uint32_t down);
uint32_t es_stock_1b9ec(uint32_t dlg);
uint32_t es_stock_1ba16(uint32_t dlg);
uint32_t es_stock_1bdf0(uint32_t dlg);
uint32_t es_stock_1be38(uint32_t dlg);

uint32_t gp50_es_foot_1b9ec(uint32_t dlg) { return gp50_fs_ab_editor_foot(dlg, 1, 0) ? 0 : es_stock_1b9ec(dlg); }   /* B release */
uint32_t gp50_es_foot_1ba16(uint32_t dlg) { return gp50_fs_ab_editor_foot(dlg, 0, 0) ? 0 : es_stock_1ba16(dlg); }   /* A release */
uint32_t gp50_es_foot_1bdf0(uint32_t dlg) { return gp50_fs_ab_editor_foot(dlg, 1, 1) ? 0 : es_stock_1bdf0(dlg); }   /* B press */
uint32_t gp50_es_foot_1be38(uint32_t dlg) { return gp50_fs_ab_editor_foot(dlg, 0, 1) ? 0 : es_stock_1be38(dlg); }   /* A press */
