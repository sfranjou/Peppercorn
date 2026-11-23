/* Successor adapters. Typed variadic prototypes put arguments on the stock
 * variadic stack. Original residual-context studies remain unchanged.
 * Failed address conversions intentionally produce zero, never local residue.
 */
#define GP50_CATALOG_DIRECT 1
#include "../own/stock_io.h"
typedef int (*scan_fn)(const char *, const char *, ...);
typedef int (*print_fn)(const char *, ...);
uint32_t nds_remaining_14bf6(uint32_t input) {
    uint8_t output[6] = {0};
    char field[3] = {0};
    for (uint32_t i = 0; i < 6; ++i) {
        unsigned int parsed = 0;
        field[0] = *(const volatile char *)(uintptr_t)(input + i * 3);
        field[1] = *(const volatile char *)(uintptr_t)(input + i * 3 + 1);
        if (((scan_fn)(uintptr_t)0xd0d50)(field, (const char *)0xd3c1c, &parsed) == 1)
            output[i] = (uint8_t)parsed;
    }
    return STOCK_CALL(0, 0x14b92, (uint32_t)(uintptr_t)output);
}
uint32_t nds_remaining_14fd6(uint32_t index) {
    uint32_t count = *(const volatile uint8_t *)0x20008a82;
    if (index >= count) {
        ((print_fn)(uintptr_t)0xd0c9c)((const char *)0xd3ce0, index, count);
        return 1;
    }
    uint32_t item = io_r32(0, 0x20008a84) + index * 44;
    uint32_t value = STOCK_CALL(0, 0x93658, item + 2, IO_R8((const StockIo *)0, item));
    ((print_fn)(uintptr_t)0xd0c9c)((const char *)0xd3d04, value);
    return 0;
}
