#ifndef GP50_CAPTURE_STATUS_H
#define GP50_CAPTURE_STATUS_H
#include <stdint.h>
/* Offline component for a future candidate. No fixed memory address, hooks or
 * synchronization are implied. All operations require external serialization.
 * Read schema 1 describes the ACTIVE record only, never an inactive slot. */
#define GP50_CAPTURE_FEATURE_BIT 6u
#define GP50_CAPTURE_REPLY_BYTES 24u
#define GP50_CAPTURE_UNKNOWN_SLOT 255u
/* N->S slots 0..49 factory (IDs 41..90), 50..79 user (IDs 91..120). */
#define GP50_CAPTURE_SLOTS 80u
#define GP50_CAPTURE_STALE_MS 1000u
#define GP50_CAPTURE_NO_AGE UINT32_MAX

enum gp50_capture_kind { GP50_CAPTURE_UNKNOWN, GP50_CAPTURE_EMPTY,
 GP50_CAPTURE_VTSI, GP50_CAPTURE_GP5N, GP50_CAPTURE_GP5P, GP50_CAPTURE_GPTC };
enum gp50_capture_state { GP50_CAPTURE_UNAVAILABLE, GP50_CAPTURE_LOADING,
 GP50_CAPTURE_ACCEPTED, GP50_CAPTURE_REJECTED, GP50_CAPTURE_RUNTIME_ERROR,
 GP50_CAPTURE_UNSUPPORTED, GP50_CAPTURE_RETIRED };
enum gp50_capture_freshness { GP50_CAPTURE_NO_SAMPLE, GP50_CAPTURE_FRESH,
 GP50_CAPTURE_STALE };
enum { GP50_CAPTURE_BYPASSED=1u, GP50_CAPTURE_SLOT_KNOWN=2u,
 GP50_CAPTURE_FALLBACK=4u };
/* Slot is the selected N->S content slot, NOT proof its stored bytes played.
 * FALLBACK must be set if the loader selected another record. No record or
 * overlay pointer is retained. Errors are full 32-bit producer error codes. */
typedef struct {
 uint32_t generation, revision, error;
 uint8_t kind, state, slot, flags;
} gp50_capture_snapshot;
typedef struct {
 gp50_capture_snapshot snapshot;
 uint32_t request, received_tick, age_ms;
 uint8_t pending, valid;
} gp50_capture_cache;

void gp50_capture_reset(gp50_capture_snapshot *);
/* Generation/revision tokens saturate; they NEVER wrap and revive old work.
 * Begin returns 0 on invalid input or exhaustion, without changing state.
 * Successful begin invalidates prior status before content replacement. */
uint32_t gp50_capture_begin(gp50_capture_snapshot *, uint8_t selected_slot);
uint32_t gp50_capture_retire(gp50_capture_snapshot *);
/* Only a LOADING generation may finish init. Rejection requires a nonzero
 * error; unsupported/accepted/empty clear error. Disabled accepted != rejected. */
int gp50_capture_finish(gp50_capture_snapshot *, uint32_t generation,
 uint8_t kind, uint8_t state, uint32_t error, uint8_t fallback);
int gp50_capture_bypass(gp50_capture_snapshot *, uint32_t generation, uint8_t bypassed);
int gp50_capture_watchdog(gp50_capture_snapshot *, uint32_t generation, uint32_t error);
int gp50_capture_valid(const gp50_capture_snapshot *);
/* Exact 24-byte host frame. Does not read record bytes or private error cells. */
int gp50_capture_encode(const gp50_capture_snapshot *, uint8_t freshness,
 uint32_t age_ms, uint8_t out[GP50_CAPTURE_REPLY_BYTES]);
int gp50_capture_decode(const uint8_t *, uint32_t bytes,
 gp50_capture_snapshot *, uint8_t *freshness, uint32_t *age_ms);
void gp50_capture_cache_reset(gp50_capture_cache *);
/* One outstanding request; token saturates. Timeout must explicitly cancel.
 * An old/unsolicited reply cannot clear pending or change cache. */
uint32_t gp50_capture_request(gp50_capture_cache *);
void gp50_capture_cancel(gp50_capture_cache *, uint32_t request);
int gp50_capture_receive(gp50_capture_cache *, uint32_t request,
 const gp50_capture_snapshot *, uint32_t now_ms);
int gp50_capture_cached_frame(gp50_capture_cache *, uint32_t now_ms,
 uint8_t out[GP50_CAPTURE_REPLY_BYTES]);
#endif
