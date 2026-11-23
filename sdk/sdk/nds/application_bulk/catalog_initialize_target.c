/* Native adapter for the reconstructed catalog initialization routines.
 * Stock allocator entry 0x5cfc8 takes a byte count in a0 and returns a
 * 32-bit address in a0. The callbacks deliberately perform volatile native
 * memory accesses; there is no host-side address translation in the pedal
 * build. */
#include <stdint.h>
#include "../../../firmware/reconstructed/nds/catalog_initialize.h"

#define catalog_allocate bulk_init_allocate
#define catalog_initialize bulk_init_initialize
#include "../../../firmware/reconstructed/nds/catalog_initialize.c"
#undef catalog_initialize
#undef catalog_allocate

#ifdef GP50_CATALOG_HOST_TEST
extern uint32_t catalog_host_allocate(uint32_t bytes);
extern uint8_t catalog_host_read8(uint32_t address);
extern uint32_t catalog_host_read32(uint32_t address);
extern void catalog_host_write8(uint32_t address, uint8_t value);
extern void catalog_host_write32(uint32_t address, uint32_t value);
static uint32_t target_allocate(void *ctx, uint32_t bytes) {
    (void)ctx; return catalog_host_allocate(bytes);
}
static uint8_t target_read8(void *ctx, uint32_t address) {
    (void)ctx; return catalog_host_read8(address);
}
static uint32_t target_read32(void *ctx, uint32_t address) {
    (void)ctx; return catalog_host_read32(address);
}
static void target_write8(void *ctx, uint32_t address, uint8_t value) {
    (void)ctx; catalog_host_write8(address, value);
}
static void target_write32(void *ctx, uint32_t address, uint32_t value) {
    (void)ctx; catalog_host_write32(address, value);
}
#else
typedef uint32_t (*stock_allocate_fn)(uint32_t bytes);
static uint32_t target_allocate(void *ctx, uint32_t bytes) {
    (void)ctx;
    return ((stock_allocate_fn)(uintptr_t)0x5cfc8u)(bytes);
}
static uint8_t target_read8(void *ctx, uint32_t address) {
    (void)ctx; return *(volatile const uint8_t *)(uintptr_t)address;
}
static uint32_t target_read32(void *ctx, uint32_t address) {
    (void)ctx; return *(volatile const uint32_t *)(uintptr_t)address;
}
static void target_write8(void *ctx, uint32_t address, uint8_t value) {
    (void)ctx; *(volatile uint8_t *)(uintptr_t)address = value;
}
static void target_write32(void *ctx, uint32_t address, uint32_t value) {
    (void)ctx; *(volatile uint32_t *)(uintptr_t)address = value;
}
#endif

static const CatalogInitializeIo BULK_IO = {
    target_allocate, target_read8, target_read32,
    target_write8, target_write32, 0
};

/* Stock entry 0x196a8. Returns 1 on success, 0 on allocation failure. */
uint32_t nds_bulk_196a8(void) { return bulk_init_allocate(&BULK_IO); }

/* Stock entry 0x196d8. Returns 0 on success, 1 on allocation failure. */
uint32_t nds_bulk_196d8(uint32_t source) {
    return bulk_init_initialize(source, &BULK_IO);
}
