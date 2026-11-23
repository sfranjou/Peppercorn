/* Pedal build of the effect chains (item 9, MOD052; analysis/firmware/NDS_PARAMETER_SET.md): parameter set and range
 * helpers, effect selection into the preset, effect state to the ARM (link commands 5/7/1), host parameter set `11 48`
 * and the USB host notification dispatcher. Thin wrappers with the stock entry signatures (hard float: values in fs0)
 * over the compared sources (chain_*.c). Each stock entry is patched to `j` its wrapper.
 * Calls leaving the chains go to the stock addresses, as the stock code does, so every hook another feature placed
 * there still applies (0x466fe, 0x4305e are themselves redirected here). Stays stock on purpose: 0x430b8 (`11 47`
 * parser), because its select path 0x475d8 holds the admission hook (refuse_c, 0x475de). */
#include <stdint.h>
#include "chain_module.h"
#include "../../../firmware/reconstructed/nds/host_param.h"
#include "../../../firmware/reconstructed/nds/host_notify.h"
#include "../../../firmware/reconstructed/nds/slot_table.h"

typedef uint32_t (*stock_u0_t)(void);
typedef uint32_t (*stock_u1_t)(uint32_t);
typedef uint32_t (*stock_u2_t)(uint32_t, uint32_t);
typedef uint32_t (*stock_u3_t)(uint32_t, uint32_t, uint32_t);
typedef uint32_t (*stock_send_t)(const uint8_t *, uint32_t, uint32_t);
typedef uint32_t (*stock_produce_t)(uint32_t, const uint8_t *, uint32_t, uint32_t);
typedef void (*stock_name_t)(uint32_t, uint8_t *, uint32_t);
typedef void (*stock_f1_t)(float);
typedef void (*stock_v0_t)(void);
#define STOCK(type, addr) ((type)(uintptr_t)(addr))
#define NOTIFY_TABLE 0x140b18u   /* 0x4305e handler table (kinds 0..), handlers take (a, b) with a2 = 1 */

/* GCC clears the zero-initialised message buffers with memset; freestanding, so it is ours (byte loop, kept a loop). */
__attribute__((optimize("no-tree-loop-distribute-patterns"))) void *memset(void *d, int v, unsigned int n) {
    uint8_t *p = d; while (n--) *p++ = (uint8_t)v; return d;
}

/* Catalog services as in catalog_target.c: groups 4/9 through the stock slot-table entries (redirected to slot_table.c). */
static uint32_t cab_count(void *c) { (void)c; return STOCK(stock_u0_t, 0x199de)(); }
static uint32_t ns_count(void *c) { (void)c; return STOCK(stock_u0_t, 0x19d90)(); }
static uint32_t cab_public_id(void *c, uint32_t i) { (void)c; return STOCK(stock_u1_t, 0x199e2)(i); }
static uint32_t ns_public_id(void *c, uint32_t i) { (void)c; return STOCK(stock_u1_t, 0x19d96)(i); }
static uint32_t cab_ordinal(void *c, uint32_t id) { (void)c; return STOCK(stock_u1_t, 0x19c5c)(id); }
static uint32_t ns_ordinal(void *c, uint32_t id) { (void)c; return STOCK(stock_u1_t, 0x1a014)(id); }
static uint32_t cab_field(void *c, uint32_t i, uint32_t k) { (void)c; return slot_field(&SLOT_TABLE_CAB, i, k); }
static uint32_t ns_field(void *c, uint32_t i, uint32_t k) { (void)c; return slot_field(&SLOT_TABLE_NS, i, k); }

/* scratch 0: the parameter record buffer is in the using function's frame, as in the stock code (these entries run in
 * more than one task: UI, USB host), so one constant table serves every call. */
static const ParameterIo IO = {{{0, 0, 0}, 0, cab_count, ns_count, cab_public_id, ns_public_id, cab_ordinal, ns_ordinal}, 0, cab_field, ns_field};

static void send_selection(void *c, uint32_t g, uint32_t o) { (void)c; STOCK(stock_u2_t, 0x466fe)(g, o); }
static void notify_host(void *c, uint32_t k, uint32_t a, uint32_t b) { (void)c; STOCK(stock_u3_t, 0x4305e)(k, a, b); }
static void ui_refresh(void *c, uint32_t a, uint32_t b, uint32_t d) { (void)c; STOCK(stock_u3_t, 0x47d68)(a, b, d); }
static const SelectServices SELECT = {0, send_selection, notify_host, ui_refresh};
static uint32_t produce(void *c, uint32_t ch, const uint8_t *m, uint32_t n, uint32_t f) { (void)c; return STOCK(stock_produce_t, 0x15480)(ch, m, n, f); }
static const LinkServices LINK = {0, produce};
static uint32_t run_mode(void *c, uint32_t v) { (void)c; return STOCK(stock_u1_t, 0x47696)(v); }
static const ParamServices PARAM = {&SELECT, &LINK, run_mode};

static uint32_t connection_state(void *c) { (void)c; return STOCK(stock_u0_t, 0x432ec)(); }
static uint32_t usb_mode(void *c) { (void)c; return STOCK(stock_u0_t, 0x55642)(); }
static uint32_t reply_queue(void *c, const uint8_t *f, uint32_t n, uint32_t x) { (void)c; return STOCK(stock_send_t, 0x15a1e)(f, n, x); }
static uint32_t serialize(void *c, const uint8_t *f, uint32_t n, uint32_t x) { (void)c; return STOCK(stock_send_t, 0x40942)(f, n, x); }
static uint32_t other_kind(void *c, uint32_t kind, uint32_t a, uint32_t b) {
    (void)c; return STOCK(stock_u3_t, ((const uint32_t *)(uintptr_t)NOTIFY_TABLE)[kind])(a, b, 1);
}
static void name_bytes(void *c, uint32_t a, uint8_t *d, uint32_t n) { (void)c; STOCK(stock_name_t, 0x451c4)(a, d, n); }
static uint32_t slot_mask(void *c, uint32_t n) { (void)c; return STOCK(stock_u2_t, 0x17212)(0x1e0000, n); }
/* Kind 11 level word, the stock sequence of 0x4145e: float in fs0 -> 0xd08fc (to double, fd0) -> 0xcc0a4 (rounds fd0)
 * -> 0xcf12c (fd0 to word, a0). Nothing may run between the calls (checked on the disassembly). */
static uint32_t fpu_word(void *c, uint32_t bits) {
    (void)c; union { uint32_t u; float f; } x = {.u = bits};
    STOCK(stock_f1_t, 0xd08fc)(x.f); STOCK(stock_v0_t, 0xcc0a4)(); return STOCK(stock_u0_t, 0xcf12c)();
}
static const NotifyServices NOTIFY = {0, connection_state, usb_mode, reply_queue, serialize, other_kind, name_bytes, slot_mask, fpu_word};

/* Parameter set path (0x4557e: a0 group, a1 visible index, a2 notify, fs0 value) and its range helpers (fs0 results). */
uint32_t nds_chain_4557e(uint32_t g, uint32_t p, float v, uint32_t notify) { return effect_parameter_set(g, p, v, notify, &IO); }
float nds_chain_43a9e(uint32_t g, uint32_t p) { return parameter_value(g, p, &IO); }
float nds_chain_43b2c(uint32_t g, uint32_t p) { return parameter_minimum(g, p, &IO); }
float nds_chain_43ba6(uint32_t g, uint32_t p) { return parameter_maximum(g, p, &IO); }
float nds_chain_43c20(uint32_t g, uint32_t p) { return parameter_step(g, p, &IO); }
/* Effect selection into the preset (0x453d0). */
uint32_t nds_chain_453d0(uint32_t g, uint32_t o) { return effect_select_into_preset(g, o, &IO, &SELECT); }
/* Effect state to the ARM: link commands 5 (0x466fe), 7 (0x466ac), 1 (0x46750). */
uint32_t nds_chain_466fe(uint32_t g, uint32_t o) { return effect_link_state(5, g, o, &IO, &LINK); }
uint32_t nds_chain_466ac(uint32_t g, uint32_t o) { return effect_link_state(7, g, o, &IO, &LINK); }
uint32_t nds_chain_46750(uint32_t g, uint32_t p) { return effect_link_parameter(g, p, &IO, &LINK); }
/* Host parameter set `11 48` (0x41dfe: a0 payload). */
uint32_t nds_chain_41dfe(uint32_t payload) { return host_parameter_set(payload, &IO, &PARAM); }
/* USB host notification dispatcher (0x4305e: a0 kind, a1 a, a2 b). */
uint32_t nds_chain_4305e(uint32_t kind, uint32_t a, uint32_t b) { return host_notify(kind, a, b, &IO, &NOTIFY); }
