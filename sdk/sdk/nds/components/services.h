#ifndef GP50_COMPONENT_SERVICES_H
#define GP50_COMPONENT_SERVICES_H
#include <stdint.h>
/* Component service API v1, experimental integrated NDS SDK.
 * Available in init, tick, GET and SET. No allocation, transport or GUI work.
 * Boot-relative milliseconds, modulo 2^32 (wraps after about 49.7 days).
 * Read once per scheduling decision. A tick callback is a service opportunity;
 * its frequency is not a clock. State/persistence addresses are never exposed.
 */
uint32_t gp50_sdk_millis(void);
/* Unsigned subtraction handles a wrap when the real interval is < 2^32 ms.
 * Stored timestamps are volatile boot-local state; discard them on reboot.
 */
static inline uint32_t gp50_sdk_elapsed_ms(uint32_t now, uint32_t then) {
    return now - then;
}
#endif
