/* Generated explicit public ABI adapters; require linked image review. */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include <stdint.h>
extern uint32_t diag_usb_guard(uint32_t,uint32_t);
#define PROTOCOL_USB_SEND(buffer,length,io) diag_usb_guard(buffer,length)
#include <stdint.h>
extern uint32_t diag_usb_guard(uint32_t,uint32_t);
#define PROTOCOL_USB_SEND(buffer,length,io) diag_usb_guard(buffer,length)
#include <stdint.h>
extern uint32_t diag_usb_guard(uint32_t,uint32_t);
#define PROTOCOL_USB_SEND(buffer,length,io) diag_usb_guard(buffer,length)
#include <stdint.h>
extern uint32_t diag_usb_guard(uint32_t,uint32_t);
#define PROTOCOL_USB_SEND(buffer,length,io) diag_usb_guard(buffer,length)
#include <stdint.h>
extern uint32_t diag_usb_guard(uint32_t,uint32_t);
#define PROTOCOL_USB_SEND(buffer,length,io) diag_usb_guard(buffer,length)
#include <stdint.h>
extern uint32_t diag_usb_guard(uint32_t,uint32_t);
#define PROTOCOL_USB_SEND(buffer,length,io) diag_usb_guard(buffer,length)
#define protocol_usb_send bulk_protocol_transport_protocol_usb_send
#define protocol_queue_push bulk_protocol_transport_protocol_queue_push
#define protocol_queue_consume bulk_protocol_transport_protocol_queue_consume
#define protocol_queue_reset bulk_protocol_transport_protocol_queue_reset
#define protocol_link_state bulk_protocol_transport_protocol_link_state
#define protocol_queue_init bulk_protocol_transport_protocol_queue_init
#include "../../../firmware/reconstructed/nds/protocol_transport.c"
uint32_t nds_bulk_431ba(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_protocol_transport_protocol_usb_send(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_431e8(uint32_t a0,uint32_t a1) {(void)a0;(void)a1;return bulk_protocol_transport_protocol_queue_push(a0,a1,(const StockIo *)0);}
uint32_t nds_bulk_43254(void) {return bulk_protocol_transport_protocol_queue_consume((const StockIo *)0);}
uint32_t nds_bulk_4328e(void) {return bulk_protocol_transport_protocol_queue_reset((const StockIo *)0);}
uint32_t nds_bulk_432ec(void) {return bulk_protocol_transport_protocol_link_state((const StockIo *)0);}
uint32_t nds_bulk_4334c(void) {return bulk_protocol_transport_protocol_queue_init((const StockIo *)0);}
