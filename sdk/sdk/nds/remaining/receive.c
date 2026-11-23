/* Instruction-reviewed 0x46a0a (GP 0x20011658). Compared with original execution:
 * work/firmware_source/nds_link_receive/verification.json. */
#define GP50_CATALOG_DIRECT 1
#include "../../../firmware/reconstructed/nds/link_receive.h"
#include "../own/diagnostics.h"
#ifndef REMAINING_RECEIVE_TEST
#define frame_crc8 nds_host_1540a
#endif
#include "../../../firmware/reconstructed/nds/host_reply.h"
#define ACK_DONE 0x1573eu       /* frame consumed / acknowledge */
#define ACK_RETRY 0x156d8u      /* request a resend */
#define PAYLOAD (LINK_RX + 8)

static uint32_t u16at(const StockIo *io, uint32_t a) { return IO_R8(io, a) | (uint32_t)IO_R8(io, a + 1) << 8; }

/* Telemetry remains a normal C call. Test builds bind a synthetic stub; production
 * must resolve the existing nds_receive symbol. */
#ifdef REMAINING_RECEIVE_TEST
static void telemetry_receive(uint32_t n) { ((void (*)(uint32_t))(uintptr_t)REMAINING_RECEIVE_TEST_ADDR)(n); }
#else
extern void nds_receive(uint32_t);
static void telemetry_receive(uint32_t n) { nds_receive(n); }
#endif
static int finite_nonnegative(uint32_t bits) {
    if (((bits >> 23) & 255u) == 255u) return 0;
    return (int32_t)bits >= 0 || (bits << 1) == 0;
}
/* Converts the former continuation jump into an ordinary return. The caller owns
 * housekeeping, including invalid diagnostics; the stock continuation skips the common acknowledgement. */
static void receive_diagnostics(uint32_t count, const StockIo *io) {
    static const uint8_t head[7]={0x10,0,1,2,0x60,0x0c,0};
    if (count != 16) return;
    for (uint32_t i=0;i<7;i++) if (IO_R8(io,DIAG_FRAME+1+i)!=head[i]) return;
    uint32_t first=io_r32(io,DIAG_FRAME+8), second=io_r32(io,DIAG_FRAME+12);
    if (!finite_nonnegative(first) || !finite_nonnegative(second)) return;
    STOCK_CALL0(io,0x5c0e2);
    io_w32(io,DIAG_STATE+0x14,io_r32(io,DIAG_TICKS));
    io_w32(io,DIAG_STATE+0x1c,first);io_w32(io,DIAG_STATE+0x20,second);
    io_w32(io,DIAG_STATE+0x18,io_r32(io,DIAG_STATE+0x18)+1);
    io_w32(io,DIAG_STATE+8,1);
    if (IO_R8(io,DIAG_LINK+0x10) && io_r16(io,DIAG_LINK+0xa)>=6) {
        uint32_t frame=io_r32(io,DIAG_LINK+4);
        if (frame && io_r16(io,frame+4)==0x6002) {
            io_w32(io,DIAG_STATE+4,0);io_w32(io,DIAG_STATE+0xc,0);
            STOCK_CALL0(io,ACK_DONE);
        }
    }
    STOCK_CALL0(io,0x5c102);
}

/* One pump step: take a frame from the link (0x1572c/0x15700), check it, run its handler; then the link housekeeping
 * (idle retry count up to 20, a pending resend when 0x469be reports 4, the hold-off countdown, 0x15548 when idle). */
static uint32_t receive_body(const StockIo *io) {
    if (STOCK_CALL0(io, 0x15754)) STOCK_CALL0(io, 0x15746);
    uint32_t size = STOCK_CALL0(io, 0x1572c);
    if (size) {
        STOCK_CALL0(io, 0x46990);
        size = STOCK_CALL(io, 0x15700, LINK_RX, size);
        if (!size) return 0;
        uint32_t length = u16at(io, LINK_RX + 1);
        if (length == 4) { STOCK_CALL0(io, IO_R8(io, LINK_RX + 3) == 0x14 ? ACK_DONE : ACK_RETRY); return size; }
        if (((length - 4) & 0xffff) >= 0x1fd) return 0;
        uint32_t crc = frame_crc8(LINK_RX + 4, length - 4, &io->memory), type = u16at(io, LINK_RX + 4), arg = u16at(io, LINK_RX + 6);
        if (IO_R8(io, LINK_RX) != crc) { STOCK_CALL0(io, type == 0x4001 || type == 0x5002 ? ACK_DONE : ACK_RETRY); return size; }
        int done = 1;   /* handlers after which the frame is acknowledged */
        switch (type) {
            case 0x6002: receive_diagnostics(size, io); done = 0; break;
            case 0x60f0: telemetry_receive(size); done = 0; break;
            case 0x6000: STOCK_CALL(io, 0x46904, PAYLOAD); break;
            case 0x7004: STOCK_CALL(io, 0x4261e, PAYLOAD, arg); break;
            case 0x7005: STOCK_CALL(io, 0x1a08c, PAYLOAD, arg); break;
            case 0x5002: STOCK_CALL(io, 0x46942, PAYLOAD, arg); break;
            case 0x4001: STOCK_CALL(io, 0x468be, PAYLOAD, IO_R8(io, LINK_RX + 6)); done = 0; break;
            case 0x2002: case 0x7002:   /* CAB / N->S slot info: store, acknowledge, echo to the host when it listens (state 4) */
                STOCK_CALL(io, type == 0x2002 ? 0x19c9a : 0x1a052, PAYLOAD, arg); STOCK_CALL0(io, ACK_DONE);
                if (STOCK_CALL0(io, 0x17742) == 4) STOCK_CALL(io, 0x17842, 6, type == 0x2002 ? 0x20 : 0x25, 0, 0);
                done = 0; break;
            default: break;
        }
        if (done) STOCK_CALL0(io, ACK_DONE);
    }
    uint32_t pending = STOCK_CALL0(io, 0x156d2);
    if (!pending && STOCK_CALL0(io, 0x1574e)) {
        uint32_t count = io_r32(io, LINK_RX_STATE + 4) + 1;
        if (count < 0x15) io_w32(io, LINK_RX_STATE + 4, count);
        else { io_w32(io, LINK_RX_STATE + 4, pending); STOCK_CALL0(io, ACK_DONE); }
    }
    if (STOCK_CALL0(io, 0x469be) == 4 && STOCK_CALL0(io, 0x156d2) == 1) { STOCK_CALL0(io, 0x4699c); STOCK_CALL0(io, ACK_RETRY); }
    uint32_t hold = io_r32(io, LINK_RX_STATE);
    if (hold) io_w32(io, LINK_RX_STATE, hold - 1);
    else if (!STOCK_CALL0(io, 0x1574e)) { io_w32(io, LINK_RX_STATE + 4, 0); STOCK_CALL0(io, 0x15548); }
    return size;
}

uint32_t nds_remaining_46a0a(void) { return receive_body((const StockIo *)0); }

void nds_remaining_diag_receive(uint32_t count) { receive_diagnostics(count, (const StockIo *)0); }
