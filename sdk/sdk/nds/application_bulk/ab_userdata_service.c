/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define userdata_service_wait bulk_userdata_service_userdata_service_wait
#define userdata_drain_link bulk_userdata_service_userdata_drain_link
#define userdata_catalog_a_send bulk_userdata_service_userdata_catalog_a_send
#define userdata_catalog_b_send bulk_userdata_service_userdata_catalog_b_send
#define userdata_summary_send bulk_userdata_service_userdata_summary_send
#define userdata_sync_all bulk_userdata_service_userdata_sync_all
#define userdata_level_a_notify_bits bulk_userdata_service_userdata_level_a_notify_bits
#define userdata_level_b_notify bulk_userdata_service_userdata_level_b_notify
#define userdata_level_a_exchange_bits bulk_userdata_service_userdata_level_a_exchange_bits
#include "../../../firmware/reconstructed/nds/userdata_service.c"
uint32_t nds_bulk_46c80(float value0) {union {float f;uint32_t u;} floatword0={.f=value0};return bulk_userdata_service_userdata_level_a_notify_bits(floatword0.u,(const StockIo *)0);}
uint32_t nds_bulk_46caa(void) {return bulk_userdata_service_userdata_level_b_notify((const StockIo *)0);}
uint32_t nds_bulk_46ce4(float value0) {union {float f;uint32_t u;} floatword0={.f=value0};return bulk_userdata_service_userdata_level_a_exchange_bits(floatword0.u,(const StockIo *)0);}
