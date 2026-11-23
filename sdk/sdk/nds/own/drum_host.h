#ifndef GP50_DRUM_HOST_H
#define GP50_DRUM_HOST_H
#include "stock_io.h"
uint32_t drum_host_get(uint32_t length,uint32_t ctx,const StockIo *io);
uint32_t drum_host_set(uint32_t args,uint32_t length,uint32_t *status,const StockIo *io);
#endif
