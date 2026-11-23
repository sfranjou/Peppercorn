#ifndef GP50_COMPONENT_H
#define GP50_COMPONENT_H
#include <stdint.h>
#include "ui.h"
typedef uint32_t (*gp50_component_status_fn)(char *, uint32_t);
/* SDK ABI 1: stateless application-task callbacks. No allocation, blocking,
 * recursion, flash writes, interrupt handlers or writable globals. Init runs
 * before interrupts; it may not use GUI, host transport or other task services.
 * Tick runs after GUI receive/service. Host callbacks run in normal dispatch.
 * Each callback's declared resource limits require independent linked review.
 * GET writes a schema byte plus payload, returns count (zero means refusal).
 * SET returns status 0 success / 1 refusal; input is borrowed for this call.
 */
typedef struct {
    uint32_t selector, set_bytes, max_reply_bytes;
    void (*init)(void);
    void (*tick)(void);
    uint32_t (*get)(uint8_t *, uint32_t);
    uint32_t (*set)(const uint8_t *, uint32_t);
} gp50_component_descriptor;
void gp50_components_init(void);
void gp50_components_tick(void);
uint32_t gp50_components_has(uint32_t selector);
uint32_t gp50_components_read(uint32_t selector, uint8_t *out, uint32_t capacity);
uint32_t gp50_components_write(uint32_t selector, const uint8_t *args, uint32_t length);
/* Framework editor adapter; no LVGL handles cross the component boundary. */
uint32_t gp50_components_editor_status(char *out, uint32_t capacity);
#endif
