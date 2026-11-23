#ifndef GP50_RESOURCES_H
#define GP50_RESOURCES_H
#include <stdint.h>
#define GP50_RM_SLOTS 6u
#define GP50_RM_BASE UINT32_C(0x290d7580)
#define GP50_RM_END UINT32_C(0x290fffb0)
#define GP50_RM_BYTES (GP50_RM_END-GP50_RM_BASE)
typedef enum { GP50_RM_OK, GP50_RM_INVALID, GP50_RM_BUSY, GP50_RM_FULL,
 GP50_RM_STALE, GP50_RM_UNSUPPORTED, GP50_RM_EXHAUSTED } gp50_rm_result;
typedef enum { GP50_RM_MANAGED_TAIL, GP50_RM_STOCK_LOOPER } gp50_rm_backend;
typedef struct { uint32_t owner, generation, slot; } gp50_rm_handle;
typedef struct { uint32_t owner, generation, address, bytes; } gp50_rm_slot;
/* Caller-owned internal SRAM, never place this metadata in external RAM. */
typedef struct { gp50_rm_slot slots[GP50_RM_SLOTS]; uint32_t processing; } gp50_rm;
/* Initialize once per manager lifetime, with no outstanding handles. External
 * serialization required; this API is neither interrupt-safe nor a lock. */
void gp50_rm_init(gp50_rm *m);
gp50_rm_result gp50_rm_acquire(gp50_rm *, gp50_rm_backend, uint32_t owner,
 uint32_t bytes, uint32_t alignment, gp50_rm_handle *);
gp50_rm_result gp50_rm_release(gp50_rm *, gp50_rm_handle);
gp50_rm_result gp50_rm_info(const gp50_rm *, gp50_rm_handle, uint32_t *address, uint32_t *bytes);
gp50_rm_result gp50_rm_processing_enter(gp50_rm *);
gp50_rm_result gp50_rm_processing_leave(gp50_rm *);
/* Only these accessors touch external memory: aligned volatile halfwords.
 * Offset is in bytes; reads/writes are allowed within processing scopes. */
gp50_rm_result gp50_rm_read16(const gp50_rm *, gp50_rm_handle, uint32_t offset, uint16_t *);
gp50_rm_result gp50_rm_write16(const gp50_rm *, gp50_rm_handle, uint32_t offset, uint16_t);
#endif
