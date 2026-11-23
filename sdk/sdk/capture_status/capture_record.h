#ifndef GP50_CAPTURE_RECORD_H
#define GP50_CAPTURE_RECORD_H
#include "capture_status.h"
/* These errors belong to our wrapper, distinct from GP5P validator errors. */
enum { GP50_CAPTURE_E_EXTENT=0x10001u, GP50_CAPTURE_E_SIZE=0x10002u,
 GP50_CAPTURE_E_FORMAT=0x10003u, GP50_CAPTURE_E_CONTEXT=0x10004u, GP50_CAPTURE_E_MEMORY=0x10005u };
typedef struct {
 uint32_t bytes, error;
 uint8_t kind, state, run, reserved;
} gp50_capture_record_check;
/* Caller supplies a stable readable extent from the synchronous lookup
 * transaction, never the record's own claimed length. Reads at most extent.
 * Does not validate DSP coefficients, program CRC, or execution acceptance. */
gp50_capture_record_check gp50_capture_record_preflight(const uint8_t *, uint32_t extent);
typedef struct { uint32_t base, bytes, stride, directories; } gp50_capture_geometry;
/* No dereference: classify aligned sector starts only under an explicit
 * no-writer transaction and exact initialized area geometry. */
uint32_t gp50_capture_record_extent(uint32_t pointer,
 const gp50_capture_geometry *factory, const gp50_capture_geometry *user,
 uint32_t read_transaction, uint8_t *fallback);
#endif
