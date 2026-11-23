/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#define identity_blob_send bulk_wext_packets_identity_blob_send
#define identity_blob_apply bulk_wext_packets_identity_blob_apply
#include "../../../firmware/reconstructed/nds/wext_packets.c"
uint32_t nds_bulk_4194e(uint32_t a0) {(void)a0;return bulk_wext_packets_identity_blob_send(a0,(const StockIo *)0);}
