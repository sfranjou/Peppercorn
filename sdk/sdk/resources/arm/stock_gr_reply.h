#ifndef GP50_STOCK_GR_REPLY_H
#define GP50_STOCK_GR_REPLY_H

#include <stddef.h>

/* Follows the legacy 12-byte GR Comp mailbox in the resident carve. Each
 * slot is {callback, lease generation, float bits}. PendSV writes it and
 * foreground reads and clears the callback with interrupts masked. */
#define STOCK_GR_OFFSET 300u
_Static_assert(sizeof(gp50_resident) <= 288u, "resident overlaps meter mailboxes");
_Static_assert(STOCK_GR_OFFSET + 24u <= 512u, "stock meter exceeds resident carve");
_Static_assert(offsetof(gp50_resident, view[0].generation) == 116u, "Gate generation address");
_Static_assert(offsetof(gp50_resident, view[1].generation) == 132u, "PRE generation address");

__attribute__((noinline)) static uint32_t stock_gr_take(const volatile gp50_resident *resident,
                                                       unsigned group) {
 volatile uint32_t *slot = (volatile uint32_t *)(GP50_RESIDENT_BASE + STOCK_GR_OFFSET + 12u * group);
 uint32_t callback = slot[0];
 slot[0] = 0;
 if (!callback || slot[1] != resident->view[group].generation) return 0;
 return (callback << 16) | (slot[2] >> 16);
}

__attribute__((noinline)) static void stock_gr_reply(uint32_t *packet, const volatile gp50_resident *resident) {
 uint32_t sample = stock_gr_take(resident, 0);
 /* Store the high 16 float bits. Gate's linear coefficient is positive,
  * so bit 15 can mark a fresh Gate sample, including a coefficient of zero. */
 if (sample) packet[19] |= (0x8000u | sample) << 16;
 sample = stock_gr_take(resident, 1);
 /* Lease byte 33 bits 2-3 identify stock COMP or COMP4. For these models
  * bytes 30-31 carry the signed detector instead of legacy GR Comp cdb. */
 if (sample) {
  uint32_t kind = sample & (0x40u << 16) ? 2u : 1u;
  packet[18] = (packet[18] & 0xffffu) | (sample << 16);
  packet[19] = (packet[19] & 0xffff0000u) | (kind << 10) | 0x301u;
 }
}

#endif
