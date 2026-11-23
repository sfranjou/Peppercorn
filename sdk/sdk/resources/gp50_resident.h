#ifndef GP50_RESIDENT_H
#define GP50_RESIDENT_H
/* Resident lease adapter: binds managed-tail leases to effect-group lifetimes.
 * Offline component. Not installed in any firmware image. See
 * analysis/firmware/RESIDENT_RESOURCES.md for the intended stock call boundaries
 * (5328 group load, 8fe8 builtin clear-all, 53b4 init, 53d0 process).
 *
 * All mutating calls require a caller-proved quiescent boundary (no processing
 * callback running or able to start) and external serialization. The adapter
 * never touches pool memory; only effects do, through gp50_tail.h. */
#include "gp50_resources.h"

#define GP50_RES_GROUPS 11u
#define GP50_REQ_MAGIC UINT32_C(0x51523547) /* "G5RQ" little-endian */
#define GP50_REQ_ABI 1u
#define GP50_REQ_FLAG_REQUIRED 1u /* informative: effect cannot run without tail */
#define GP50_REQ_KNOWN_FLAGS GP50_REQ_FLAG_REQUIRED
#define GP50_REQ_MAX_ALIGNMENT 4096u

/* Effect-supplied, read-only requirements record. */
typedef struct {
 uint32_t magic, abi, struct_bytes, flags, tail_bytes, tail_alignment;
} gp50_requirements;

typedef enum {
 GP50_LEASE_EMPTY = 0,   /* no effect loaded / retired */
 GP50_LEASE_STOCK = 1,   /* effect loaded without requirements record */
 GP50_LEASE_GRANTED = 2, /* address/bytes valid for this generation */
 GP50_LEASE_DENIED = 3   /* requirements present but not granted, see reason */
} gp50_lease_state;

typedef enum {
 GP50_DENY_NONE = 0, GP50_DENY_DESCRIPTOR = 1, GP50_DENY_FULL = 2,
 GP50_DENY_EXHAUSTED = 3, GP50_DENY_INIT_FAILED = 4
} gp50_deny_reason;

/* Published per-group view, internal SRAM, read by effects. Word order is ABI. */
typedef struct {
 uint32_t address, bytes, generation;
 uint8_t abi, state, reason, slot;
} gp50_lease_view;

/* signature/complement identify an initialized adapter: effects on firmware
 * without the adapter read ordinary stock heap bytes at this address and must
 * fall back. Both words are written last in init and never change afterwards. */
#define GP50_RESIDENT_SIGNATURE UINT32_C(0x52353047) /* "G05R" */
typedef struct {
 uint32_t signature, complement;
 gp50_rm rm;
 gp50_lease_view view[GP50_RES_GROUPS];
 uint32_t transitions; /* monotonic count of published changes, diagnostics */
} gp50_resident;

typedef enum { GP50_RES_OK, GP50_RES_INVALID, GP50_RES_BUSY } gp50_res_result;

/* Proposed resident placement: low end of the stock heap (512B carve, see
 * work/resource_transactions/heap_carve_verification.json). Not applied. */
#define GP50_RESIDENT_BASE UINT32_C(0x20003ae8)
#define GP50_RESIDENT_VIEW_OFFSET 108u
#define GP50_RESIDENT_VIEW(group) (GP50_RESIDENT_BASE+GP50_RESIDENT_VIEW_OFFSET+16u*(group))

/* g overlay record carriage: the requirements follow the 16-byte stock stub in
 * the record prefix (never copied by loader 5328), so word0 must be >= 64.
 * Stock V1.1.0/MOD030 records have word0 32..40 and never contain the magic. */
#define GP50_REQ_RECORD_OFFSET 40u
#define GP50_REQ_RECORD_MIN_WORD0 64u
/* Returns the requirements inside an aligned record, or 0 for a stock record. */
const gp50_requirements *gp50_requirements_from_record(const uint32_t *record);

/* Boot only, before any effect load. */
void gp50_resident_init(gp50_resident *);
/* Group (re)load boundary: retires the group's previous lease unconditionally,
 * then grants per req (NULL = stock effect). Load cannot be refused by the
 * adapter; denial is published in the view instead. */
gp50_res_result gp50_resident_load(gp50_resident *, uint32_t group,
 const gp50_requirements *req, uint32_t quiescent);
/* Effect init reported failure: retire its fresh lease, publish INIT_FAILED. */
gp50_res_result gp50_resident_init_failed(gp50_resident *, uint32_t group, uint32_t quiescent);
/* Group slot cleared without a replacement. */
gp50_res_result gp50_resident_unload(gp50_resident *, uint32_t group, uint32_t quiescent);
/* Builtin tuner/any clear-all of execution slots. */
gp50_res_result gp50_resident_retire_all(gp50_resident *, uint32_t quiescent);
/* Processing bracket around the dispatcher's whole chain. */
gp50_res_result gp50_resident_processing_enter(gp50_resident *);
gp50_res_result gp50_resident_processing_leave(gp50_resident *);
/* Diagnostic: handle for a granted group, for gp50_rm accessors. */
gp50_res_result gp50_resident_handle(const gp50_resident *, uint32_t group, gp50_rm_handle *);
#endif
