#ifndef GP50_NDS_ASSIGN_MAP_H
#define GP50_NDS_ASSIGN_MAP_H
#include <stdint.h>
#include "stock_io.h"
#include "assign_store.h"
#include "assign_editor.h"
/* MOD026 binding table use (assembly work/ui_assignment_v2): publish a binding, look one up for a Stomp
 * knob (with staleness checks), drive the assigned parameter from that knob, show assigned names/values on the home
 * page, and keep editor/home ticks in sync. Ported to C (NDS_ASM_TO_C_INVENTORY.md). The tick wrappers that replay stock
 * prologues (editor 0x16e9ca, home 0x16ea12) stay assembly and are called by address. */
#ifdef GP50_CATALOG_DIRECT
void wah_name(uint32_t group, uint32_t parameter, uint32_t buffer, uint32_t length, const StockIo *io);
#define NAME_CALL(io, g, p, buf, n) wah_name((g), (p), (buf), (n), (io))   /* MOD027 prefixed names (MOD054 links this) */
#else
#define NAME_CALL(io, g, p, buf, n) STOCK_CALL((io), 0x16f000, (g), (p), (buf), (n))
#endif
uint32_t assign_publish(uint32_t ctx, uint32_t event, const StockIo *io);           /* 0x16e558 (v2 commit) */
uint32_t assign_valid_map(uint32_t knob, const StockIo *io);                        /* 0x16e630: binding or 0 */
uint32_t assign_home_knob(uint32_t ctx, uint32_t event, const StockIo *io);         /* 0x16e6fe */
uint32_t assign_home_refresh(uint32_t ctx, const StockIo *io);                      /* 0x16e7b0: returns 0x16e7b0's mask */
uint32_t assign_editor_tick(uint32_t ctx, uint32_t event, const StockIo *io);       /* 0x16e948 */
uint32_t assign_home_tick(uint32_t ctx, uint32_t event, const StockIo *io);         /* 0x16e9d6 */
#endif
