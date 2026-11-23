#ifndef GP50_NDS_STOCK_IO_H
#define GP50_NDS_STOCK_IO_H
#include <stdint.h>
#include "catalog_accessors.h"
/* Generic interface for readable C that calls into stock code (item 9, 2026-10-22; scripts/nds_generic_study.py):
 * memory through the catalog memory interface, every stock routine through one call service with its address, so the
 * host comparison records the same (address, arguments) as the original-instruction study stubs. On the pedal
 * (GP50_CATALOG_DIRECT) a stock call is a direct call to the address. Arguments are words; STOCK_CALL_F passes one word
 * and one float (fs0). */
typedef struct {
    CatalogIo memory;
    void *context;
    uint32_t (*call)(void *, uint32_t address, uint32_t argc, const uint32_t *argv);
    uint32_t (*scratch)(void *, uint32_t size);   /* host only: target-address scratch for LOCAL_BUFFER */
    uint32_t (*call_f)(void *, uint32_t address, uint32_t a0, uint32_t fs0_bits);   /* host only: (a0, fs0) call */
    uint32_t (*call_f3)(void *, uint32_t address, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t fs0_bits);   /* host only */
} StockIo;
#define IO_R8(io, a) CATALOG_READ8(&(io)->memory.memory, (a))
#define IO_W8(io, a, v) CATALOG_WRITE8(&(io)->memory, (a), (v))
#ifdef GP50_CATALOG_DIRECT
typedef uint32_t (*stock_fn_t)();   /* unprototyped: the stock routines take words in a0.. */
#define STOCK_CALL(io, address, ...) ((void)(io), ((stock_fn_t)(uintptr_t)(address))(__VA_ARGS__))
#define STOCK_CALL0(io, address) ((void)(io), ((stock_fn_t)(uintptr_t)(address))())
/* Stack buffer a stock callee fills or reads: a local array on the pedal, a scratch block in emulated memory on the host
 * (the comparison records pointers into the stack/scratch window as "local"). */
#define LOCAL_BUFFER(io, name, size) uint32_t name##_words[((size) + 3) / 4]; uint32_t name = ((void)(io), (uint32_t)(uintptr_t)name##_words)
static inline uint32_t stock_call_f(const void *io, uint32_t address, uint32_t a0, uint32_t bits) {   /* a0 + float in fs0 */
    union { uint32_t u; float f; } x = {.u = bits}; (void)io; return ((uint32_t (*)(uint32_t, float))(uintptr_t)address)(a0, x.f);
}
#define STOCK_CALL_F(io, address, a0, bits) stock_call_f((io), (address), (a0), (bits))
static inline uint32_t stock_call_f0(const void *io, uint32_t address, uint32_t bits) {   /* float in fs0 only */
    union { uint32_t u; float f; } x = {.u = bits}; (void)io; return ((uint32_t (*)(float))(uintptr_t)address)(x.f);
}
#define STOCK_CALL_F0(io, address, bits) stock_call_f0((io), (address), (bits))
static inline uint32_t stock_call_rf(const void *io, uint32_t address) {   /* no arguments, float result in fs0 */
    union { float f; uint32_t u; } x = {.f = ((float (*)(void))(uintptr_t)address)()}; (void)io; return x.u;
}
#define STOCK_CALL_RF(io, address) stock_call_rf((io), (address))
static inline uint32_t stock_call_f3(const void *io, uint32_t address, uint32_t a0, uint32_t a1, uint32_t a2, uint32_t bits) {   /* a0..a2 + fs0 */
    union { uint32_t u; float f; } x = {.u = bits}; (void)io;
    return ((uint32_t (*)(uint32_t, uint32_t, uint32_t, float))(uintptr_t)address)(a0, a1, a2, x.f);
}
#define STOCK_CALL_F3(io, address, a0, a1, a2, bits) stock_call_f3((io), (address), (a0), (a1), (a2), (bits))
static inline uint32_t stock_call_rf2(const void *io, uint32_t address, uint32_t a0, uint32_t a1) {   /* two words, float result */
    union { float f; uint32_t u; } x = {.f = ((float (*)(uint32_t, uint32_t))(uintptr_t)address)(a0, a1)}; (void)io; return x.u;
}
#define STOCK_CALL_RF2(io, address, a0, a1) stock_call_rf2((io), (address), (a0), (a1))
#else
#define LOCAL_BUFFER(io, name, size) uint32_t name = (io)->scratch((io)->context, (size))
#define STOCK_CALL_F(io, address, a0, bits) ((io)->call_f((io)->context, (address), (a0), (bits)))
#define STOCK_CALL_F0(io, address, bits) ((io)->call_f((io)->context, (address), 0xf0f0f0f0u, (bits)))   /* marker: no word argument */
#define STOCK_CALL_RF(io, address) STOCK_CALL0((io), (address))   /* host: the stub's return value is the fs0 bits */
#define STOCK_CALL_F3(io, address, a0, a1, a2, bits) ((io)->call_f3((io)->context, (address), (a0), (a1), (a2), (bits)))
#define STOCK_CALL_RF2(io, address, a0, a1) STOCK_CALL((io), (address), (a0), (a1))   /* host: stub value = fs0 bits */
#define STOCK_CALL(io, address, ...) \
    ((io)->call((io)->context, (address), sizeof((uint32_t[]){__VA_ARGS__}) / 4, (const uint32_t[]){__VA_ARGS__}))
#define STOCK_CALL0(io, address) ((io)->call((io)->context, (address), 0, 0))
#endif
static inline uint32_t io_r16(const StockIo *io, uint32_t a) { return IO_R8(io, a) | (uint32_t)IO_R8(io, a + 1) << 8; }
static inline uint32_t io_r32(const StockIo *io, uint32_t a) { return io_r16(io, a) | io_r16(io, a + 2) << 16; }
static inline void io_w16(const StockIo *io, uint32_t a, uint32_t v) { IO_W8(io, a, (uint8_t)v); IO_W8(io, a + 1, (uint8_t)(v >> 8)); }
static inline void io_w32(const StockIo *io, uint32_t a, uint32_t v) { io_w16(io, a, v); io_w16(io, a + 2, v >> 16); }
#endif
