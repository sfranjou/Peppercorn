#include "services.h"
#include "stock_api.h"
/* Only the platform adapter knows the firmware clock location. Aligned u32
 * loads on this single-core target give a clock sample, not a multi-field
 * snapshot or a synchronization primitive for component state.
 */
uint32_t gp50_sdk_millis(void) {
    return *(volatile uint32_t *)GP50_TICK_COUNTER;
}
