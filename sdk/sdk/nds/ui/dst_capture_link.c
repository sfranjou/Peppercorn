/* DST capture with the N->S block off: link filter (admission table v7, 2026-11-09). Separate object so the
 * refusal and admission objects keep their MOD149 layout; analysis/tone_capture/TWO_CAPTURES_20261108.md. */
#include <stdint.h>
#include "stock_api.h"
#include "refuse_table.h"     /* v7 constants only: admission_table.h would bring weak copies of the cost tables */

static uint32_t u32_at(const volatile uint8_t *p) {
 return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
#ifdef ADM_CAPTURE_FORCE
/* DST capture with the N->S block off (admission table v7, 2026-11-09). Our DSP capture program sits in the
 * AMP+CAB slots only while the ARM sees N->S enabled, so while the DST Capture is active and the user's N->S block is
 * off, the copies sent to the ARM say: N->S on, AMP and CAB off, N->S parameter 8 = ADM_CAPTURE_MAIN_OFF (the player
 * then plays the DST capture alone). The preset (mData) keeps the user's switches. Four stock producers' calls to
 * link_queue_produce (0x15480) come here: full config 0x463de, enable 0x466a2, mask 0x4666e, model 0x46746. */
static void put16(uint8_t *p, uint32_t v) { p[0] = (uint8_t)v; p[1] = (uint8_t)(v >> 8); }
static void put32(uint8_t *p, uint32_t v) { put16(p, v); put16(p + 2, v >> 16); }
static uint32_t lf_mask(void) { return u32_at((const volatile uint8_t *)GP50_MDATA_ENABLE_MASK); }
static uint32_t lf_dst_id(void) { return u32_at((const volatile uint8_t *)GP50_MDATA_ENABLE_MASK + GP50_MDATA_IDS_OFFSET + 8u); }
static uint32_t forced(uint32_t mask) {
 return (mask >> 2 & 1u) && lf_dst_id() == ADM_DST_CAPTURE_ID && !(mask >> 9 & 1u);
}
static uint32_t effective(uint32_t mask) { return forced(mask) ? (mask | 1u << 9) & ~(1u << 3 | 1u << 4) : mask; }
int gp50_link_filter(uint32_t channel, uint8_t *msg, uint32_t len, uint32_t zero) {
 uint32_t m = lf_mask(), f = forced(m), cmd = len >= 8u ? (uint32_t)msg[0] | (uint32_t)msg[1] << 8 : 0xffffu;
 uint32_t g = len >= 8u ? msg[4] : 0xffu;
 if (f && cmd == 0u && len >= 368u) { put16(msg + 10, effective(m)); put32(msg + 48 + 9 * 32 + 28, ADM_CAPTURE_MAIN_OFF); }
 if (f && cmd == 5u && len >= 40u && g == 9u) put32(msg + 8 + 28, ADM_CAPTURE_MAIN_OFF);
 if (f && cmd == 6u) put32(msg + 4, effective(m));
 int r = link_queue_produce(channel, msg, len, zero);
 /* A change that can enter or leave the forced state: send the effective mask and N->S parameter 8 again (both
  * idempotent; the player reloads only when parameter 8 changes meaning). */
 uint32_t follow = (cmd == 4u && (g == 2u || g == 3u || g == 4u || g == 9u)) || (cmd == 5u && g == 2u) || cmd == 6u;
 if (follow && (f || lf_dst_id() == ADM_DST_CAPTURE_ID || (cmd == 5u && g == 2u))) {
  uint32_t mk[2], p1[4];
  uint8_t *a = (uint8_t *)mk, *b = (uint8_t *)p1;
  for (uint32_t i = 0; i < 8u; i++) a[i] = 0;
  for (uint32_t i = 0; i < 16u; i++) b[i] = 0;
  put16(a, 6u); put16(a + 2, 8u); put32(a + 4, effective(m));
  if (cmd != 6u) link_queue_produce(channel, a, 8u, zero);
  put16(b, 1u); put16(b + 2, 16u); b[4] = 9u; b[5] = 7u; put32(b + 12, f ? ADM_CAPTURE_MAIN_OFF : 0u);
  link_queue_produce(channel, b, 16u, zero);
 }
 return r;
}
#endif
