#define GP50_CATALOG_DIRECT 1
#include "../../../firmware/reconstructed/nds/userdata_frame_packets.c"
/* Successor integration source: deterministic private packet storage.
 * Existing frame-explicit models retain original packet construction/order.
 * Local storage is initialized before populating it. See lifetime inventory.
 */
#include "../../../firmware/reconstructed/nds/userdata_frame_packets.h"
static void packet_zero(const StockIo *io, uint32_t address, uint32_t size) {
    for (uint32_t i = 0; i < size; ++i) IO_W8(io, address + i, 0);
}
uint32_t safe_userdata_46336(const StockIo *io) {
    LOCAL_BUFFER(io, frame, 16); packet_zero(io, frame, 16);
    return userdata_frame_46336(frame, io);
}
uint32_t safe_userdata_46366(const StockIo *io) {
    LOCAL_BUFFER(io, frame, 376); packet_zero(io, frame, 376);
    return userdata_frame_46366(frame, io);
}
uint32_t safe_userdata_464b2(const StockIo *io) {
    LOCAL_BUFFER(io, frame, 8); packet_zero(io, frame, 8);
    return userdata_frame_464b2(frame, io);
}
uint32_t safe_userdata_46678(uint32_t first, uint32_t second, const StockIo *io) {
    LOCAL_BUFFER(io, frame, 8); packet_zero(io, frame, 8);
    return userdata_frame_46678(first, second, frame, io);
}
uint32_t safe_userdata_467fe(const StockIo *io) {
    LOCAL_BUFFER(io, frame, 8); packet_zero(io, frame, 8);
    return userdata_frame_467fe(frame, io);
}
uint32_t safe_userdata_471de(uint32_t value, const StockIo *io) {
    STOCK_CALL(io, 0x45064, value);
    return 0; /* Observed caller ignores original uninitialized return. */
}

uint32_t nds_remaining_46336(void) { return safe_userdata_46336(0); }
uint32_t nds_remaining_46366(void) { return safe_userdata_46366(0); }
uint32_t nds_remaining_464b2(void) { return safe_userdata_464b2(0); }
uint32_t nds_remaining_467fe(void) { return safe_userdata_467fe(0); }
uint32_t nds_remaining_46678(uint32_t a, uint32_t b) { return safe_userdata_46678(a,b,0); }
uint32_t nds_remaining_471de(uint32_t a) { return safe_userdata_471de(a,0); }
