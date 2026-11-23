#ifndef GP50_NDS_DIAGNOSTICS_H
#define GP50_NDS_DIAGNOSTICS_H
#include <stdint.h>
#include "stock_io.h"
/* Our diagnostics assembly still in MOD055's b at 0x16c6c0..0x16cb60 (features), ported to C
 * (analysis/firmware/APPLICATION_C_BURNDOWN.md): MOD002/MOD030 load bridge (sampler service, 0x6002 receive, `12 50`
 * host reply; sources scripts/load_bridge_source.py, work/load_measurement/implementation/), MOD007 USB send guard and
 * MOD016 main-memory peek (`11 15`). Compared with the MOD055 instructions by scripts/study_nds_diagnostics.py. */
#define DIAG_STATE 0x2001f3b0u   /* +0 enabled, +4 pending, +8 valid, +0xc timed out, +0x10 request tick, +0x14 reply tick,
                                  * +0x18 reply count, +0x1c/+0x20 the two reported floats (bits), +0x24 sent at least once */
#define DIAG_TICKS 0x20004ad0u   /* SysTick counter (0x174e8) */
#define DIAG_LINK 0x2000a4f4u    /* link sender descriptor: +4 frame pointer, +0xa queued length, +0x10 busy */
#define DIAG_QUEUE 0x20008cc0u   /* link producer queue: u16 producer, u16 consumer */
#define DIAG_FRAME 0x20010928u   /* receive buffer of the stock link receiver */
#define DIAG_USB_BUSY 0x20005deau   /* gp-0xb86e: byte set around the USB send (MOD007) */
uint32_t diag_gui(const StockIo *io);                                 /* 0x16c6c0: link tick 0x46a0a, then the service */
uint32_t diag_dispatch(uint32_t command, uint32_t count, const StockIo *io);   /* 0x16c6e6 (a5 = command, s0 = count) */
uint32_t diag_service(const StockIo *io);                             /* 0x16c6f6: time-out and 0x6002 request */
uint32_t diag_receive(uint32_t count, const StockIo *io);             /* 0x16c7f0 (s0 = count): 0x6002 report */
uint32_t diag_finite(uint32_t bits, const StockIo *io);               /* 0x16c930: 1 if the float bits are usable */
uint32_t diag_host(uint32_t context, const StockIo *io);              /* 0x16c954: `12 50` reply */
uint32_t diag_putword(uint32_t value, uint32_t destination, const StockIo *io);   /* 0x16ca6c: little-endian store */
uint32_t diag_usb_guard(uint32_t object, uint32_t length, const StockIo *io);          /* 0x16ca8a: 0x4cf34 with the busy byte set */
uint32_t diag_peek(uint32_t request, const StockIo *io);              /* 0x16caa4: `11 15` peek of 1..64 bytes */
#endif
