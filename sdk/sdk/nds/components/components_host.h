#ifndef GP50_COMPONENT_HOST_H
#define GP50_COMPONENT_HOST_H
#include "../host_layer/host_layer_module.h"
uint32_t gp50_component_host_get(uint32_t,uint32_t,uint32_t,const StockIo *);
uint32_t gp50_component_host_set(uint32_t,uint32_t,uint32_t,uint32_t *,const StockIo *);
#endif
