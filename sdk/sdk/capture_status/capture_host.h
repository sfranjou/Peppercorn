#ifndef GP50_CAPTURE_HOST_H
#define GP50_CAPTURE_HOST_H
#include "capture_status.h"
#include "../nds/own/stock_io.h"
/* Component only: caller serializes cache and binds the future dispatch slot.
 * Exact read-class request is [12 72], no slot arg. Cached active record only.
 * Never starts an ARM operation while replying to the host. */
uint32_t gp50_capture_host_get(uint32_t selector,uint32_t length,uint32_t context,
 gp50_capture_cache *,uint32_t now_ms,const StockIo *);
#endif
