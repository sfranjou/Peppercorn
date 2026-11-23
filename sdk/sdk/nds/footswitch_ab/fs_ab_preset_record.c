/* A/B footswitch successor of sdk/nds/host_layer/preset_record.c (host_layer_c source when footswitch_ab_c is enabled;
 * region E). The compared preset_record.c stays as-is for the unchanged entries; changed here:
 * - stored-slot read hook -> gp50_fs_ab_preset_read (GPAM v1 knobs + v2 knobs/feet);
 * - factory record of the current preset -> foot state cleared after the stock behaviour;
 * - save chain (preset_save 0x4468a -> flash_store_request 0x49772 -> flash_stage_sector 0x4965a) propagates refusal:
 *   the sector buffer is read and the record staged (gp50_fs_ab_stage_record) before the flash-store object is touched,
 *   the Flash task request is set only after a successful stage, and a refused stage frees only its own buffer.
 *   Stock queued the write even after a failed read/allocation and published the buffer before staging. */
#include "../host_layer/host_layer_module.h"
#include "fs_ab_target.h"
#define PRESET_READ_SLOT ((uintptr_t)gp50_fs_ab_preset_read)
#undef preset_load_factory
#undef preset_save
#undef flash_store_request
#undef flash_stage_sector
#define preset_load_factory fs_ab_stock_preset_load_factory
#define preset_save fs_ab_stock_preset_save
#define flash_store_request fs_ab_stock_flash_store_request
#define flash_stage_sector fs_ab_stock_flash_stage_sector
#include "../../../firmware/reconstructed/nds/preset_record.c"
#undef preset_load_factory
#undef preset_save
#undef flash_store_request
#undef flash_stage_sector

#define FLASH_ALLOC 0x5cfb0u
#define FLASH_RELEASE 0x5cfd8u
#define FLASH_READ 0x10f9eu
#define FLASH_BUSY 0x49a6cu

uint32_t nds_host_442f2(uint32_t slot, uint32_t rec, const StockIo *io) {
    uint32_t r = fs_ab_stock_preset_load_factory(slot, rec, io);
    uint32_t current = r8(io, PRESET_CURRENT) | (uint32_t)r8(io, PRESET_CURRENT + 1) << 8;
    if (current == slot) gp50_fs_ab_active_replaced();
    return r;
}

/* Returns 1 when staged and published to the flash-store object, 0 when refused (object unchanged). */
uint32_t nds_host_4965a(uint32_t rec, uint32_t index, uint32_t n, const StockIo *io) {
    uint32_t obj = io_r32(io, FLASH_STORE);
    if (r8(io, obj + 0xc)) return 0;                              /* earlier write still pending: keep its buffer */
    uint32_t buf = STOCK_CALL(io, FLASH_ALLOC, 0x1000);
    if (!buf) return 0;
    zero(io, buf, 0x1000);
    uint32_t sector = ((index + 0x5dc) << 10) & ~0xfffu;
    if (STOCK_CALL(io, FLASH_READ, sector, buf, 0x1000, 10)
        || !gp50_fs_ab_stage_record(buf + ((index & 3) << 10), rec, n, io)) {
        STOCK_CALL(io, FLASH_RELEASE, buf);
        return 0;
    }
    io_w32(io, obj + 4, buf); io_w32(io, obj + 8, sector);
    return 1;
}

/* 0 = queued; 0xffffff01 index out of range (stock); 0xffffff02 refused (nothing queued). */
uint32_t nds_host_49772(uint32_t rec, uint32_t index, uint32_t n, const StockIo *io) {
    if (index >= 100) return 0xffffff01u;
    if (!STOCK_CALL(io, 0x4965a, rec, index, n)) return 0xffffff02u;
    w8(io, io_r32(io, FLASH_STORE) + 0xc, 1);
    return 0;
}

/* As stock, but waits only for a queued write and returns the request result (stock: always 0). */
uint32_t nds_host_4468a(uint32_t slot, uint32_t rec, const StockIo *io) {
    uint32_t r = STOCK_CALL(io, 0x49772, rec, r8(io, PRESET_MAP + slot), 0x1aa);
    if (r) return r;
    do STOCK_CALL(io, 0x5cb88, 10); while (STOCK_CALL0(io, FLASH_BUSY));
    return 0;
}
