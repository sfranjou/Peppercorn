#include "diagnostics.h"
/* NDS32 slti/slt compare unsigned (sltsi/slts are the signed forms): every compare here is unsigned.
 * Readable C of our diagnostics assembly in MOD055's b (see diagnostics.h). Stock routines: 0x5c0e2/0x5c102 critical
 * section enter/leave, 0x46262 the stock 0x6002 producer (12-byte load query to the ARM), 0x1573e release of the link
 * sender, 0x46b7a stock receiver continuation, 0x46aba stock receive compare tree (a0 = 0x7004 replayed), 0x46a0a link
 * tick, 0x40942 host reply sender (buffer, length, context), 0x4cf34 USB send. */

uint32_t diag_gui(const StockIo *io)
{
    uint32_t result = STOCK_CALL0(io, 0x46a0a);
    diag_service(io);
    return result;
}

uint32_t diag_dispatch(uint32_t command, uint32_t count, const StockIo *io)
{
    if (command == 0x6002) return diag_receive(count, io);
    return STOCK_CALL(io, 0x46aba, 0x7004);   /* the replaced `movi a0,0x7004`, then the stock compare tree */
}

uint32_t diag_service(const StockIo *io)
{
    STOCK_CALL0(io, 0x5c0e2);
    uint32_t now = io_r32(io, DIAG_TICKS);
    if (io_r32(io, DIAG_STATE + 4) && !(now - io_r32(io, DIAG_STATE + 0x10) < 500)) {   /* request timed out */
        io_w32(io, DIAG_STATE + 4, 0); io_w32(io, DIAG_STATE + 0xc, 1);
    }
    if (io_r32(io, DIAG_STATE) && !io_r32(io, DIAG_STATE + 4) && !IO_R8(io, DIAG_LINK + 0x10)) {   /* armed, idle sender */
        uint32_t producer = io_r16(io, DIAG_QUEUE), consumer = io_r16(io, DIAG_QUEUE + 2);
        if (producer == consumer && producer < 12) {   /* link queue empty */
            uint32_t last = io_r32(io, DIAG_STATE + 0x10), sent = io_r32(io, DIAG_STATE + 0x24);
            if (!sent || !(now - last < 100)) {   /* at most one request per 100 ticks */
                io_w32(io, DIAG_STATE + 4, 1); io_w32(io, DIAG_STATE + 0x10, now);
                if (STOCK_CALL0(io, 0x46262) == 0) {
                    io_w32(io, DIAG_STATE, 0); io_w32(io, DIAG_STATE + 0xc, 0); io_w32(io, DIAG_STATE + 0x24, 1);
                } else {   /* not queued: restore */
                    io_w32(io, DIAG_STATE + 4, 0); io_w32(io, DIAG_STATE + 0x10, last); io_w32(io, DIAG_STATE + 0x24, sent);
                }
            }
        }
    }
    return STOCK_CALL0(io, 0x5c102);
}

uint32_t diag_finite(uint32_t bits, const StockIo *io)
{
    (void)io;
    if ((bits >> 23 & 0xff) == 0xff) return 0;   /* inf / NaN */
    if ((int32_t)bits >= 0) return 1;
    return (bits << 1) == 0;                      /* negative: only -0.0 */
}

uint32_t diag_receive(uint32_t count, const StockIo *io)
{
    static const uint8_t head[7] = {0x10, 0x00, 0x01, 0x02, 0x60, 0x0c, 0x00};   /* frame bytes 1..7: 0x6002, length 12 */
    if (count != 16) return STOCK_CALL0(io, 0x46b7a);
    for (uint32_t i = 0; i < 7; i++)
        if (IO_R8(io, DIAG_FRAME + 1 + i) != head[i]) return STOCK_CALL0(io, 0x46b7a);
    uint32_t first = io_r32(io, DIAG_FRAME + 8), second = io_r32(io, DIAG_FRAME + 12);
    if (!diag_finite(first, io) || !diag_finite(second, io)) return STOCK_CALL0(io, 0x46b7a);
    STOCK_CALL0(io, 0x5c0e2);
    io_w32(io, DIAG_STATE + 0x14, io_r32(io, DIAG_TICKS));
    io_w32(io, DIAG_STATE + 0x1c, first); io_w32(io, DIAG_STATE + 0x20, second);
    io_w32(io, DIAG_STATE + 0x18, io_r32(io, DIAG_STATE + 0x18) + 1);
    io_w32(io, DIAG_STATE + 8, 1);
    if (IO_R8(io, DIAG_LINK + 0x10) && !(io_r16(io, DIAG_LINK + 0xa) < 6)) {   /* sender busy with a frame */
        uint32_t frame = io_r32(io, DIAG_LINK + 4);
        if (frame && io_r16(io, frame + 4) == 0x6002) {   /* our own query: release the sender */
            io_w32(io, DIAG_STATE + 4, 0); io_w32(io, DIAG_STATE + 0xc, 0);
            STOCK_CALL0(io, 0x1573e);
        }
    }
    STOCK_CALL0(io, 0x5c102);
    return STOCK_CALL0(io, 0x46b7a);
}

uint32_t diag_putword(uint32_t value, uint32_t destination, const StockIo *io)
{
    for (uint32_t i = 0; i < 4; i++) IO_W8(io, destination + i, (uint8_t)(value >> 8 * i));
    return value >> 24;
}

uint32_t diag_host(uint32_t context, const StockIo *io)
{
    STOCK_CALL0(io, 0x5c0e2);
    uint32_t valid = io_r32(io, DIAG_STATE + 8);
    uint32_t flags = valid | io_r32(io, DIAG_STATE + 4) << 1 | io_r32(io, DIAG_STATE) << 2 | io_r32(io, DIAG_STATE + 0xc) << 3;
    uint32_t count = 0, age = 0xffffffffu, first = 0, second = 0;
    if (valid) {
        count = io_r32(io, DIAG_STATE + 0x18); first = io_r32(io, DIAG_STATE + 0x1c); second = io_r32(io, DIAG_STATE + 0x20);
        age = io_r32(io, DIAG_TICKS) - io_r32(io, DIAG_STATE + 0x14);
        if (!(age < 1000)) flags |= 0x10;   /* stale */
    } else flags |= 0x10;
    io_w32(io, DIAG_STATE, 1);   /* arm the next request */
    STOCK_CALL0(io, 0x5c102);
    LOCAL_BUFFER(io, reply, 18);   /* 12 50 01 flags, u16 count, u32 age, u32 first, u32 second */
    IO_W8(io, reply, 0x12); IO_W8(io, reply + 1, 0x50); IO_W8(io, reply + 2, 1); IO_W8(io, reply + 3, (uint8_t)flags);
    io_w16(io, reply + 4, count);
    diag_putword(age, reply + 6, io); diag_putword(first, reply + 10, io); diag_putword(second, reply + 14, io);
    return STOCK_CALL(io, 0x40942, reply, 18, context);
}

/* USB sender 0x4cf34 requires both a0=buffer and a1=length. MOD056 lost a1. */
uint32_t diag_usb_guard(uint32_t object, uint32_t length, const StockIo *io)
{
    IO_W8(io, DIAG_USB_BUSY, 1);
    uint32_t result = STOCK_CALL(io, 0x4cf34, object, length);
    IO_W8(io, DIAG_USB_BUSY, 0);
    return result;
}

uint32_t diag_peek(uint32_t request, const StockIo *io)
{
    uint32_t address = io_r32(io, request), length = IO_R8(io, request + 4), end = address + length;
    /* flash/boot range only: end <= 0x200000 without wrap-around (unsigned compares as in the assembly) */
    if (length == 0 || length > 64 || end > 0x200000 || end < address) return request;
    LOCAL_BUFFER(io, reply, 72);   /* 12 15, u32 address, data */
    IO_W8(io, reply, 0x12); IO_W8(io, reply + 1, 0x15);
    for (uint32_t i = 0; i < 4; i++) IO_W8(io, reply + 2 + i, (uint8_t)(address >> 8 * i));
    for (uint32_t i = 0; i < length; i++) IO_W8(io, reply + 6 + i, IO_R8(io, address + i));
    return STOCK_CALL(io, 0x40942, reply, length + 6, 0);
}
