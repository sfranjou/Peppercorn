/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define link_meter_update bulk_link_meter_link_meter_update
#define link_meter_band bulk_link_meter_link_meter_band
#include "../../../firmware/reconstructed/nds/link_meter.c"
uint32_t nds_bulk_148c6(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_link_meter_link_meter_update(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_1499c(float value0,float value1) {union {float f;uint32_t u;} floatword0={.f=value0};union {float f;uint32_t u;} floatword1={.f=value1};return bulk_link_meter_link_meter_band(floatword0.u,floatword1.u,(const StockIo *)0);}
