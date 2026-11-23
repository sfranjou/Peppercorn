/* 41f34 target adapter. Reject decode/parse/allocation failures before sector writes.
 * Existing identity-write protocol and stock storage services are retained. */
#define GP50_CATALOG_DIRECT 1
#include "../own/stock_io.h"
static uint32_t hex_digit(uint32_t c) {
    if (c >= '0' && c <= '9') return c - '0';
    if (c >= 'a' && c <= 'f') return c - 'a' + 10;
    if (c >= 'A' && c <= 'F') return c - 'A' + 10;
    return 16;
}
uint32_t nds_remaining_41f34(uint32_t packet) {
    uint32_t encoded_length = io_r32(0, packet);
    /* The decoded string has at least 17 prefix bytes and a nonempty number.
     * Decoder appends a NUL; its allocation/transform ownership remains stock. */
    if (!encoded_length || encoded_length > 500) return 1;
    uint32_t key_length = IO_R8((const StockIo *)0, packet+4);
    if (!key_length || key_length > 127 || encoded_length <= key_length ||
        encoded_length - key_length - 1 < 18) return 1;
    uint32_t decoded = STOCK_CALL(0, 0x172e2, packet + 4, encoded_length);
    if (!decoded) return 1;
    uint32_t status = 1;
    for (uint32_t i = 0; i < 18; ++i)
        if (!IO_R8((const StockIo *)0, decoded + i)) goto cleanup;
    uint32_t identity[2] = {0, 0}; char text[17];
    STOCK_CALL(0, 0x5e08a, (uint32_t)(uintptr_t)identity);
    for (uint32_t i = 0; i < 8; ++i) {
        uint32_t byte = identity[i / 4] >> ((i % 4) * 8) & 255;
        text[14-i*2] = IO_R8((const StockIo *)0, 0x140a60 + (byte >> 4));
        text[15-i*2] = IO_R8((const StockIo *)0, 0x140a60 + (byte & 15));
    }
    text[16] = 0;
    if (STOCK_CALL(0, 0xd0e20, (uint32_t)(uintptr_t)text, packet+5, 16)) goto cleanup;
    uint32_t parsed = 0, digits = 0;
    for (; digits < 5; ++digits) {
        uint32_t c = IO_R8((const StockIo *)0, decoded+17+digits);
        if (!c) break;
        uint32_t digit = hex_digit(c);
        if (digit == 16) goto cleanup;
        parsed = (parsed << 4) | digit;
    }
    if (!digits) goto cleanup;
    uint32_t buffer = STOCK_CALL(0, 0x5cfb0, 0x400);
    if (!buffer) goto cleanup;
    STOCK_CALL(0, 0x10f9e, 0x1e0000, buffer, 0x400, 10);
    uint32_t count = STOCK_CALL0(0, 0x171fa);
    STOCK_CALL(0, 0x17200, buffer, count, parsed);
    STOCK_CALL(0, 0x11648, 0x1e0000, 0x1000);
    STOCK_CALL(0, 0x11160, 0x1e0000, buffer, 0x400, 1000);
    STOCK_CALL(0, 0x15ea4, parsed);
    uint32_t stored = STOCK_CALL0(0, 0x46d0a), limit = STOCK_CALL0(0, 0x15e9e);
    if ((int32_t)stored < (int32_t)limit)
        STOCK_CALL(0, 0x15f38, STOCK_CALL0(0, 0x46d0a));
    else STOCK_CALL(0, 0x46d12, 0);
    STOCK_CALL(0, 0x17842, 0x10, 9, 0, 0);
    STOCK_CALL(0, 0x5cfd8, buffer);
    status = 0;
cleanup:
    STOCK_CALL(0, 0x5cfd8, decoded);
    return status;
}
