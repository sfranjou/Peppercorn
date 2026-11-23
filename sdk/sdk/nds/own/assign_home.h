#ifndef GP50_NDS_ASSIGN_HOME_H
#define GP50_NDS_ASSIGN_HOME_H
#include <stdint.h>
#include "stock_io.h"
#include "assign_store.h"
/* MOD029 home page: value bars for assigned knobs, latched "Reset knob" mode (hold DRUM, turn a knob, EXIT cancels),
 * header arbitration with the MOD028 meter title (assembly work/ui_assignment_v3). Handlers take the home
 * window context and the input event, as the window message table calls them. Ported to C (NDS_ASM_TO_C_INVENTORY.md).
 * Routines still in assembly are called by address: MOD028 meter tick/drum/back/restore (0x16f400/0x16f43c/0x16f4a8/
 * 0x16f514; the refresh is the C router nds_refresh2), MOD026 valid_map/home_encoder/set_text (0x16e630/0x16e6fe/0x16e52c). */
#define METER_SHOWING 0x2001f470u   /* nonzero while the meter owns the home title */
#ifdef GP50_CATALOG_DIRECT
int nds_refresh2(uint8_t *ctx);     /* sdk/nds/ui/mem_page.c: the meter-refresh router (relinks with the C segment) */
#ifdef GP50_FS_AB   /* A/B footswitches: a footswitch press in reset mode clears that switch (sdk/nds/footswitch_ab/fs_ab_ui.c) */
#define RESET_TEXT ((uint32_t)(uintptr_t)"Reset knob/FS")
#else
#define RESET_TEXT ((uint32_t)(uintptr_t)"Reset knob")
#endif
#define METER_REFRESH ((uint32_t)(uintptr_t)nds_refresh2)
#else
#define RESET_TEXT 0x16ffdcu        /* host comparison: the original string's address */
#define METER_REFRESH 0x170848u     /* host comparison: nds_refresh2 in MOD054 (MOD030+ re-pointed the MOD029 call here) */
#endif
uint32_t assign_title_restore(uint32_t ctx, const StockIo *io);           /* 0x16efa2 */
uint32_t assign_reset_prompt(uint32_t ctx, const StockIo *io);            /* 0x16fc3e */
uint32_t assign_bars(uint32_t ctx, const StockIo *io);                    /* 0x16faac: returns the mapped mask */
uint32_t assign_hold(uint32_t ctx, uint32_t event, const StockIo *io);    /* 0x16fc80: DRUM held -> reset mode */
uint32_t assign_drum(uint32_t ctx, uint32_t event, const StockIo *io);    /* 0x16fce4 */
uint32_t assign_back(uint32_t ctx, uint32_t event, const StockIo *io);    /* 0x16fd48: EXIT cancels reset mode */
uint32_t assign_home_encoder(uint32_t ctx, uint32_t event, const StockIo *io);   /* 0x16fdb4 */
uint32_t assign_tick(uint32_t ctx, uint32_t event, const StockIo *io);    /* 0x16fe84 */
#endif
