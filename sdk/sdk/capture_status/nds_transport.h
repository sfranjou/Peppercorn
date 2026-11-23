#ifndef GP50_CAPTURE_NDS_TRANSPORT_H
#define GP50_CAPTURE_NDS_TRANSPORT_H
#include "capture_status.h"
/* Successor-only allocation. The builder must enlarge BOTH startup zero-end
 * and heap-start to 0x2001f580 before using this address. Not in MOD087. */
#define GP50_CAPTURE_NDS_BASE UINT32_C(0x2001f540)
#define GP50_CAPTURE_NDS_END UINT32_C(0x2001f580)
#define GP50_CAPTURE_NDS_READY UINT32_C(0x43504e31)
typedef struct {
 gp50_capture_cache cache;
 uint32_t sent_tick, requested, last_capture, timed_out;
 uint32_t ready, complement;
 uint32_t reserved[2];
} gp50_capture_nds_state;
_Static_assert(sizeof(gp50_capture_nds_state)==64,"capture reservation");
_Static_assert(GP50_CAPTURE_NDS_BASE+sizeof(gp50_capture_nds_state)==GP50_CAPTURE_NDS_END,"capture end");
/* Boot hook, before receiver/GUI/host scheduling; ordinary requests never reset
 * tokens. Caller must hold the same irq guard as telemetry. */
void gp50_capture_transport_reset(void);
void gp50_capture_refresh(void);
int gp50_capture_display_frame(uint8_t out[GP50_CAPTURE_REPLY_BYTES]);
#endif
