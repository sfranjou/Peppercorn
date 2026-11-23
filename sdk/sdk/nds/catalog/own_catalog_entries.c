/* stock_in_place (patching release): the catalog accessors and slot tables run as stock code; only the three catalog
 * helpers are ours, so every stock accessor resolves through the own catalog (stock e + our extension). The own code
 * reaches the original helpers through prologue-replay tails (cat_stock_<entry>, catalog_c CODE), since the stock
 * entries themselves now jump here. */
#include <stdint.h>
#define GP50_CATALOG_DIRECT 1
#include "catalog_config.h"
#include "../own/catalog.h"   /* CatalogMemory type and the reader macros only */

uint32_t cat_stock_1966a(uint32_t group, uint32_t ordinal);
uint32_t cat_stock_19746(uint32_t group);
uint32_t catalog_descriptor(uint32_t group, uint32_t ordinal, const CatalogMemory *io) { (void)io; return cat_stock_1966a(group, ordinal); }
uint32_t catalog_group_count(uint32_t group, const CatalogMemory *io) { (void)io; return cat_stock_19746(group); }

#include "catalog_own.h"
static const CatalogMemory MEMORY = {0, 0, 0};
uint32_t nds_cat_1966a(uint32_t g, uint32_t o) { return own_descriptor(g, o, &MEMORY); }
uint32_t nds_cat_19746(uint32_t g) { return own_group_count(g, &MEMORY); }
uint32_t nds_cat_19782(uint32_t g, uint32_t id) { return own_public_id_to_ordinal(g, id, &MEMORY); }
uint32_t nds_cat_198a2(uint32_t g, uint32_t o, uint32_t p) { return own_parameter_slot(g, o, p, &MEMORY); }

/* Names: our descriptors keep their strings right after their own parameter records, which the stock directory formula
 * cannot reach, so both name entries stay ours (written for the own catalog; stock entries resolve as before). */
#define DIRECTORY 0x20004d94u
#define CATALOG 0x1a0000u
#define EFFECT_NAME_FALLBACK 0xd721cu
#define PARAMETER_NAME_FALLBACK 0x141dccu
static uint32_t word(uint32_t a) { const volatile uint8_t *p = (const volatile uint8_t *)(uintptr_t)a; return p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24; }
static void copy_name(uint32_t dst, uint32_t src, uint32_t size) {
    volatile uint8_t *d = (volatile uint8_t *)(uintptr_t)dst; const volatile uint8_t *s = (const volatile uint8_t *)(uintptr_t)src;
    if (!size) return;
    while (--size) { uint8_t c = *s++; *d++ = c; if (!c) return; }
    *d = 0;
}
static uint32_t name_pool(uint32_t g, uint32_t o, const uint8_t *d) {
    const uint8_t *own = own_entry(g, o, &MEMORY);
    uint32_t base = own ? (uint32_t)(uintptr_t)own : CATALOG + word(CATALOG + 4 + word(word(DIRECTORY) + 0x14 + 4 * g) + 4 * o);
    return base + 0x10 + 24u * d[8];
}
uint32_t nds_cat_197ca(uint32_t g, uint32_t o, uint32_t dst, uint32_t n) {
    const uint8_t *d = (const uint8_t *)(uintptr_t)own_descriptor(g, o, &MEMORY);
    if (!d) { copy_name(dst, EFFECT_NAME_FALLBACK, n); return 1; }
    copy_name(dst, name_pool(g, o, d) + (d[0xc] | d[0xd] << 8), n); return 0;
}
uint32_t nds_cat_1982e(uint32_t g, uint32_t o, uint32_t p, uint32_t dst, uint32_t n) {
    const uint8_t *d = (const uint8_t *)(uintptr_t)own_descriptor(g, o, &MEMORY);
    if (!d || p >= d[8]) { copy_name(dst, PARAMETER_NAME_FALLBACK, n); return 1; }
    const uint8_t *r = d + 0x12 + 24 * p; copy_name(dst, name_pool(g, o, d) + (r[0] | r[1] << 8), n); return 0;
}

/* By-name catalog services used by the effect chains: the stock accessor entries (stock code over our helpers). */
typedef struct CatalogIo CatalogIo;
typedef struct SlotTable SlotTable;
#define STOCK(type, a) ((type)(uintptr_t)(a))
uint32_t catalog_bridge_count(uint32_t g, const CatalogIo *io) { (void)io; return STOCK(uint32_t (*)(uint32_t), 0x43996)(g); }
uint32_t catalog_bridge_public_id(uint32_t g, uint32_t o, const CatalogIo *io) { (void)io; return STOCK(uint32_t (*)(uint32_t, uint32_t), 0x439b6)(g, o); }
uint32_t catalog_bridge_ordinal(uint32_t g, uint32_t id, const CatalogIo *io) { (void)io; return STOCK(uint32_t (*)(uint32_t, uint32_t), 0x439dc)(g, id); }
uint8_t catalog_descriptor_flag_byte(uint32_t g, uint32_t o, const CatalogIo *io) { (void)io; return (uint8_t)STOCK(uint32_t (*)(uint32_t, uint32_t), 0x19774)(g, o); }
uint32_t catalog_descriptor_word4(uint32_t g, uint32_t o, const CatalogIo *io) { (void)io; return STOCK(uint32_t (*)(uint32_t, uint32_t), 0x197ac)(g, o); }
uint8_t catalog_parameter_count(uint32_t g, uint32_t o, const CatalogIo *io) { (void)io; return (uint8_t)STOCK(uint32_t (*)(uint32_t, uint32_t), 0x197bc)(g, o); }
uint32_t catalog_parameter_index_of_slot(uint32_t g, uint32_t o, uint32_t s, const CatalogIo *io) { (void)io; return STOCK(uint32_t (*)(uint32_t, uint32_t, uint32_t), 0x198c4)(g, o, s); }
uint32_t catalog_parameter_record(uint32_t g, uint32_t o, uint32_t p, uint32_t out, const CatalogIo *io) { (void)io; return STOCK(uint32_t (*)(uint32_t, uint32_t, uint32_t, uint32_t), 0x1991e)(g, o, p, out); }
/* Slot-table identities for the chains' CAB / N->S field reads; the stock float entries return the field. */
const uint8_t SLOT_TABLE_CAB[4], SLOT_TABLE_NS[4];
uint32_t slot_field(const SlotTable *t, uint32_t i, uint32_t k) {
    union { float f; uint32_t u; } v;
    v.f = STOCK(float (*)(uint32_t, uint32_t), (const void *)t == (const void *)SLOT_TABLE_CAB ? 0x19c2eu : 0x19fe6u)(i, k);
    return v.u;
}

/* GCC clears zero-initialised buffers with memset; freestanding, so ours. Weak: chains_target.c provides the same
 * helper when the compiled chains are linked. */
__attribute__((weak, optimize("no-tree-loop-distribute-patterns"))) void *memset(void *d, int v, unsigned int n) {
    uint8_t *p = d; while (n--) *p++ = (uint8_t)v; return d;
}
