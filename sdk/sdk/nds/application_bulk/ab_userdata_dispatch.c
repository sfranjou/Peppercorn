/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define userdata_command_dispatch bulk_userdata_dispatch_userdata_command_dispatch
#define userdata_effect_changed bulk_userdata_dispatch_userdata_effect_changed
#define userdata_parameter_forward bulk_userdata_dispatch_userdata_parameter_forward
#include "../../../firmware/reconstructed/nds/userdata_dispatch.c"
uint32_t nds_bulk_46622(uint32_t a0) {(void)a0;return bulk_userdata_dispatch_userdata_command_dispatch(a0,(const StockIo *)0);}
uint32_t nds_bulk_47ea4(uint32_t a0,uint32_t a1,uint32_t a2,uint32_t a3,float value0) {(void)a0;(void)a1;(void)a2;(void)a3;union {float f;uint32_t u;} floatword0={.f=value0};return bulk_userdata_dispatch_userdata_parameter_forward(a0,a1,a2,a3,floatword0.u,(const StockIo *)0);}
