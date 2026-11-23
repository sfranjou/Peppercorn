#ifndef GP50_NDS_WAH_AUTO_H
#define GP50_NDS_WAH_AUTO_H
#include <stdint.h>
#include "stock_io.h"
/* MOD027 C-Wah auto-engage and category-prefixed parameter names (assembly, work/wah_auto; design
 * sdk/ui/wah_auto/README.md), ported to C (analysis/firmware/NDS_ASM_TO_C_INVENTORY.md). */
#define WAH_STATE 0x2001f450u        /* +0 active, +4 preset, +8 timer running, +12 start tick, +16 owned bypass, +20 heel */
#define WAH_OPTION 0x2001072bu       /* stored float slot: Auto Engage (exactly 1.0f = on) */
#define WAH_CALIBRATION 0x2001068au  /* s16 maximum at +0, s16 minimum at +4 (stock 0x44bf0 fields) */
#define WAH_TICKS 0x20006358u        /* unsigned 1 ms IRQ count (NDS_TICK_UNITS.md) */
/* name (MOD027 0x16f000): parameter name with a block prefix ("PRE ", "OD ", ...) for groups 0..9, else stock 0x46c32. */
void wah_name(uint32_t group, uint32_t parameter, uint32_t buffer, uint32_t length, const StockIo *io);
/* poll (0x16f0e8, replaces `jal 0x49b52` at 0x49c7e): the stock poll, then the auto-engage policy. Returns 0. */
uint32_t wah_poll(const StockIo *io);
void wah_policy(const StockIo *io);   /* wah (0x16f124) */
#endif
