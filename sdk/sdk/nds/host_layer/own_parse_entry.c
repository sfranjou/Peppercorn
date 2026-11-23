/* stock_in_place (patching release): the host message parser 0x43374 runs as stock code. This entry wrapper claims our
 * own commands first, under the parser lock and with the same ACK the compiled parser sent (own_commands.c: 11/12 70-7x,
 * capture 72, the `12 51` telemetry route), then releases the lock; anything else runs the stock parser through its
 * prologue-replay tail (parse_stock_43374, host_layer_c CODE), which takes the lock itself. */
#include <stdint.h>

typedef uint32_t (*fn4_t)(uint32_t, uint32_t, uint32_t, uint32_t);
#define PARSE_LOCK_WORD (*(volatile uint32_t *)(uintptr_t)(0x20011658u - 0xb904u))
#define LOCK_TAKE ((fn4_t)(uintptr_t)0x5c4faU)
#define LOCK_GIVE ((fn4_t)(uintptr_t)0x5c306U)
#define ACK ((uint32_t (*)(uint32_t, uint32_t))(uintptr_t)0x408e8U)

uint32_t own_get(uint32_t sel, uint32_t length, uint32_t ctx, const void *io);
uint32_t own_set(uint32_t sel, uint32_t args, uint32_t args_length, uint32_t *status, const void *io);
uint32_t parse_stock_43374(uint32_t buffer, uint32_t length, uint32_t ctx);

uint32_t gp50_host_parse(uint32_t buffer, uint32_t length, uint32_t ctx) {
    uint8_t cls = *(volatile uint8_t *)(uintptr_t)buffer, sel = *(volatile uint8_t *)(uintptr_t)(buffer + 1);
    /* Our selectors: 11/12 70-7f and `12 51`. The stock parser has no handler for any of them (set: ACK 0, read: nothing),
     * so they are handled here completely, in the compiled parser's order; every other message enters the stock parser
     * untouched. */
    int ours = (cls == 0x11 || cls == 0x12) && ((sel & 0xf0) == 0x70 || (cls == 0x12 && sel == 0x51));
    if (!ours) return parse_stock_43374(buffer, length, ctx);
    LOCK_TAKE(PARSE_LOCK_WORD, 0, 0xffffffffu, 0);
    if (cls == 0x11) {
        uint32_t status = 0;
        own_set(sel, buffer + 2, (length - 2) & 0xffff, &status, 0);
        ACK(ctx, status);
    } else own_get(sel, length, ctx, 0);
    LOCK_GIVE(PARSE_LOCK_WORD, 0, 0, 0);
    return 0;
}
