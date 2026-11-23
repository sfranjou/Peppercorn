/* Hard-float helper for the on-pedal A/B assignment (fs_ab_ui.c): current value of (group, parameter) as binary32 bits,
 * through the same stock getter the press adapter uses (0x4555a, result in fs0). Region E. */
#define GP50_CATALOG_DIRECT 1
#include <stdint.h>
#include "../own/stock_io.h"
uint32_t gp50_fs_ab_value(uint32_t group, uint32_t parameter) {
    static const StockIo direct;
    return STOCK_CALL_RF2(&direct, 0x4555a, group, parameter);
}
