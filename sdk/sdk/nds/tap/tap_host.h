#ifndef GP50_TAP_HOST_H
#define GP50_TAP_HOST_H
#include "tap_safe.h"
/* Pending candidate integration: selectors 12 73 / 11 73, feature bit 5. */
#define TAP_POLICY 7u  /* ignore zero; clamp 40..260; ignore quotient below 30 */
uint32_t tap_host_get(uint32_t sel,uint32_t length,uint32_t ctx,const StockIo *io);
uint32_t tap_host_set(uint32_t sel,uint32_t args,uint32_t length,uint32_t *status,const StockIo *io);
#endif
