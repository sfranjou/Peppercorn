/* Pedal build of firmware/reconstructed/nds/host_reply.c (see host_layer_module.h). The four routines that take the
 * ReplyServices table (transport 0x432a2, frame sender 0x40942, reply queue 0x15a1e, flush 0x15b18) are entered from
 * stock code with the stock arguments only: nds_host_<address> passes the pedal service table, whose entries call the
 * stock lock/tick/allocator/driver routines the original instructions call (same addresses, same arguments). */
#include "host_layer_module.h"
#include "../../../firmware/reconstructed/nds/host_reply.c"
static uint32_t svc_take(void *c, uint32_t lock, uint32_t a, uint32_t t, uint32_t b) { (void)c; return ((stock_fn_t)0x5c4fau)(lock, a, t, b); }
static uint32_t svc_give(void *c, uint32_t lock, uint32_t a, uint32_t b, uint32_t d) { (void)c; return ((stock_fn_t)0x5c306u)(lock, a, b, d); }
static uint32_t svc_now(void *c) { (void)c; return ((stock_fn_t)0x174f4u)(); }
static uint32_t svc_call(void *c, uint32_t f, uint32_t a0, uint32_t a1, uint32_t a2) { (void)c; return ((stock_fn_t)(uintptr_t)f)(a0, a1, a2); }
static uint32_t svc_alloc(void *c, uint32_t n) { (void)c; return ((stock_fn_t)0x5cfb0u)(n); }
static void svc_release(void *c, uint32_t a) { (void)c; ((stock_fn_t)0x5cfd8u)(a); }
static uint32_t svc_usb(void *c, uint32_t f, uint32_t n) { (void)c; return ((stock_fn_t)0x431bau)(f, n); }
static void svc_pause(void *c, uint32_t n) { (void)c; ((stock_fn_t)0x5cb88u)(n); }
static uint32_t svc_bt(void *c, uint32_t f, uint32_t n) { (void)c; return ((stock_fn_t)0x431e8u)(f, n); }
static const ReplyServices SVC = {0, svc_take, svc_give, svc_now, svc_call, svc_alloc, svc_release, svc_usb, svc_pause, svc_bt};
uint32_t nds_host_432a2(uint32_t out, uint32_t length, uint32_t ctx) { return hr_frame_transport(out, length, ctx, 0, &SVC); }
uint32_t nds_host_40942(uint32_t data, uint32_t length, uint32_t ctx) { return hr_frame_send(data, length, ctx, 0, &SVC); }
uint32_t nds_host_15a1e(uint32_t frame, uint32_t length, uint32_t ctx) { return hr_reply_queue(frame, length, ctx, 0, &SVC); }
uint32_t nds_host_15b18(void) { return hr_reply_flush(0, &SVC); }
