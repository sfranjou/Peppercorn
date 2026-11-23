#ifndef GP50_FS_AB_STOCK_ADAPTER_H
#define GP50_FS_AB_STOCK_ADAPTER_H
#include "host.h"
#include "../nds/own/stock_io.h"
/* Unintegrated target adapter. Caller must serialize preset/model changes,
 * assignment changes and this press in the GUI execution context. Do not hold
 * the hardware IRQ mask across link calls. No state address is allocated here.
 * Compile hard-float: calls getters returning fs0 and the setter taking fs0. */
int gp50_fs_ab_stock_validate(void *io,uint8_t group,uint8_t parameter,uint32_t model,uint32_t bits);
/* UNASSIGNED alone permits fallback to the existing CPU-admission block gate.
 * All configured invalid/stale assignments consume the press without block
 * toggles. READY uses the ordinary parameter setter/link/notifications. */
int gp50_fs_ab_stock_press(uint32_t index,const gp50_fs_ab_state *,const StockIo *);
#endif
