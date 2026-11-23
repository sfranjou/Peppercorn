#ifndef GP50_CAPTURE_TEXT_H
#define GP50_CAPTURE_TEXT_H
#include "capture_status.h"
/* Bounded text for a future on-pedal label; no LVGL ownership/hook implied.
 * Returns 1 when full text fits; always NUL terminates if capacity>0. */
int gp50_capture_text(const gp50_capture_snapshot *,uint8_t freshness,
 char *out,uint32_t capacity);
#endif
