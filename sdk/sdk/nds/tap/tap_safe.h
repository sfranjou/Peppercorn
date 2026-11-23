#ifndef GP50_TAP_SAFE_H
#define GP50_TAP_SAFE_H
#include "../own/stock_io.h"
/* Zero interval is ignored without changing BPM; caller ignores return value. */
uint32_t home_tap_safe(uint32_t dlg,uint32_t key,const StockIo *io);
uint32_t tap_safe_interval(uint32_t elapsed,const StockIo *io);
#endif
