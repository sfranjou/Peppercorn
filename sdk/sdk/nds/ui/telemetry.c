/* Telemetry transport in C (MOD030 schema 2 + MOD033 lease cache; behaviour identical to the
 * MOD037 assembly, proved by the unchanged service/receive/host/GUI oracle cases and routing).
 * Entries keep their asm names: `gui` (GUI tick wrapper), `service` (admits one coalesced 0x60f0
 * request), `host` (read-class 0x51 reply builder, entry 12 of `read_table`). The receive
 * validator `nds_receive(count)` is entered from a small asm stub that preserves the stock
 * receiver's registers and tail-jumps back. All tick-difference and range compares are unsigned
 * like the asm (NDS32 slt/slti are unsigned); the progress test is signed like its bltz. */
#include <stdint.h>
#include "stock_api.h"
#include "telemetry_table.h"
#ifdef GP50_COMPONENTS
#include "components/component.h"
#endif

#define ST ((volatile uint32_t *)NDS_UI_STATE)
#define LEG ((volatile uint32_t *)NDS_UI_LEGACY)
#define W32(a) (*(volatile uint32_t *)(a))
enum { S_REQUESTED = 0, S_PENDING = 1, S_VALID = 2, S_TIMEOUT = 3, S_SENT = 4, S_RX_TICK = 5, S_RX_COUNT = 6,
       S_SENT_VALID = 7, S_FIELDS = 8, S_PROGRESS = 17, S_ADMIT_TICK = 18, S_ADMIT_VALID = 19, S_LAST_KIND = 20,
       S_FAST = 23, S_LEASE = 24, S_LEASE_VALID = 33 };
enum { L_REQUESTED = 0, L_PENDING = 1, L_TIMEOUT = 3, L_SENT = 4, L_SENT_VALID = 9 };

void service(void) {
 irq_guard_enter();
 uint32_t now = W32(GP50_TICK_COUNTER);
 /* Only own software pending timeouts; never release the descriptor on timeout. */
 if (ST[S_PENDING] && now - ST[S_SENT] >= 1000u) { ST[S_PENDING] = 0; ST[S_TIMEOUT] = 1; }
 if (LEG[L_PENDING] && now - LEG[L_SENT] >= 500u) { LEG[L_PENDING] = 0; LEG[L_TIMEOUT] = 1; }
 if (ST[S_PENDING] || LEG[L_PENDING]) goto out;
 if (ST[S_ADMIT_VALID] && now - ST[S_ADMIT_TICK] < (ST[S_FAST] ? 100u : 500u)) goto out;
 const volatile uint8_t *tx = (const volatile uint8_t *)GP50_LINK_TX_STATE;
 if (tx[16]) goto out;
 const volatile uint16_t *q = (const volatile uint16_t *)GP50_LINK_QUEUE_COUNTERS;
 uint32_t p = q[0];
 if (p != q[1] || p >= 12u) goto out;
 uint32_t ext;
 if (ST[S_REQUESTED] && (!LEG[L_REQUESTED] || !ST[S_LAST_KIND])) ext = 1;
 else if (LEG[L_REQUESTED]) ext = 0;
 else goto out;
 volatile uint32_t *a = ext ? ST : LEG;
 uint32_t old_sent = a[S_SENT];
 a[S_PENDING] = 1; a[S_SENT] = now;
 int r;
 if (ext) {
  uint32_t msg[3] = {0x000c60f0u, 2u, 0u};    /* u16 0x60f0, u16 12, u32 schema 2, u32 0 */
  r = link_queue_produce(1, msg, 12, 0);
 } else r = legacy_load_send();
 if (r) { a[S_PENDING] = 0; a[S_SENT] = old_sent; goto out; }
 a[S_REQUESTED] = 0; a[S_TIMEOUT] = 0;
 if (ext) ST[S_SENT_VALID] = 1; else LEG[L_SENT_VALID] = 1;
 ST[S_ADMIT_TICK] = now; ST[S_ADMIT_VALID] = 1; ST[S_LAST_KIND] = ext;
out:
 irq_guard_leave();
}

int gui(void) {
 int r = gui_link_receive_tick();
 service();
#ifdef GP50_COMPONENTS
 gp50_components_tick();
#endif
 return r;
}

/* Receiver (CRC already checked by stock code): validate the whole 84-byte frame shape and the
 * semantic invariants before taking the guard; then cache fields + lease block atomically. */
void nds_receive(uint32_t count) {
 if (count != 84u) return;
 const volatile uint8_t *b = (const volatile uint8_t *)GP50_LINK_RX_FRAME;
 static const uint8_t head[7] = {84, 0, 1, 0xf0, 0x60, 80, 0};
 for (uint32_t i = 0; i < 7u; i++) if (b[1 + i] != head[i]) return;
 const volatile uint32_t *w = (const volatile uint32_t *)GP50_LINK_RX_FRAME;   /* word i = byte 4i */
 if (w[2] != 2u) return;
 uint32_t arm = w[3], flags = w[4];
 if (flags >= 16u) return;
 if (flags & 1u) { if (!(flags & 8u) || w[6] < w[5]) return; }
 else if (w[3] || w[5] || w[6] || w[11] || (flags & 8u)) return;
 if (flags & 2u) { if (w[8] < w[7]) return; }
 else if (w[7] || w[8] || w[9] || w[10]) return;
 if ((flags & 4u) && ((flags & 3u) != 3u || w[10] != arm)) return;
 if (flags & 8u) { if (!(flags & 1u) || w[11] != 64u) return; }
 else if (w[11]) return;
 irq_guard_enter();                                   /* held until the end (lease_guard in asm) */
 for (uint32_t i = 0; i < 9u; i++) ST[S_LEASE + i] = w[12 + i];
 ST[S_LEASE_VALID] = 1;
 uint32_t progress = 0;
 if (ST[S_VALID]) {
  int32_t d = (int32_t)(arm - ST[S_FIELDS]);
  progress = d == 0 ? 32u : d < 0 ? 64u : 0u;
 }
 ST[S_PROGRESS] = progress;
 ST[S_RX_TICK] = W32(GP50_TICK_COUNTER);
 for (uint32_t i = 0; i < 9u; i++) ST[S_FIELDS + i] = w[3 + i];
 ST[S_RX_COUNT] = ST[S_RX_COUNT] + 1u;
 ST[S_VALID] = 1;
 if (ST[S_PENDING]) {
  const volatile uint8_t *tx = (const volatile uint8_t *)GP50_LINK_TX_STATE;
  if (tx[16] && *(const volatile uint16_t *)(tx + 10) >= 16u) {
   uint32_t frame = *(const volatile uint32_t *)(tx + 4);
   if (frame && *(const volatile uint16_t *)(frame + 4) == 0x60f0u) { ST[S_PENDING] = 0; ST[S_TIMEOUT] = 0; link_release_owned(); }
  }
 }
 irq_guard_leave();
}

/* Host read-class reply 0x51: 48-byte status/cache snapshot; requests a refresh afterwards. */
void host(void *host_ctx) {
 uint32_t buf[12];
 irq_guard_enter();
 uint32_t status = ST[S_VALID] | ST[S_PENDING] << 1 | ST[S_REQUESTED] << 2 | ST[S_TIMEOUT] << 3;
 if (ST[S_VALID]) {
  status |= ST[S_PROGRESS];
  buf[1] = ST[S_RX_COUNT];
  uint32_t age = W32(GP50_TICK_COUNTER) - ST[S_RX_TICK];
  buf[2] = age;
  if (age >= 1000u) status |= 16u;
  for (uint32_t i = 0; i < 9u; i++) buf[3 + i] = ST[S_FIELDS + i];
 } else {
  buf[1] = 0;
  for (uint32_t i = 0; i < 9u; i++) buf[3 + i] = 0;
  buf[2] = 0xffffffffu;
 }
 ST[S_REQUESTED] = 1;
 irq_guard_leave();
 uint8_t *h = (uint8_t *)buf;
 h[0] = 0x12; h[1] = 0x51; h[2] = 1; h[3] = (uint8_t)status;
 host_reply_serialize(buf, 48, host_ctx);
}

/* Stock read-class table (12 builders, copied from the parent image) + entry 12 = host. */
const uint32_t read_table[13] = { HOST_READ_TABLE_STOCK, (uint32_t)host };
