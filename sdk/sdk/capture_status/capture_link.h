#ifndef GP50_CAPTURE_LINK_H
#define GP50_CAPTURE_LINK_H
#include "capture_status.h"
/* Proposed dedicated schema3 of 60f0; leaves schema2 load/lease/meter unchanged.
 * Inner messages only: stock framing/checksum are outside this component.
 * Hook/queue admission and descriptor ownership are NOT supplied here. */
#define GP50_CAPTURE_LINK_REQUEST_BYTES 16u
#define GP50_CAPTURE_LINK_REPLY_BYTES 32u
int gp50_capture_link_request(uint32_t token,uint8_t out[16]);
int gp50_capture_link_reply(const uint8_t *request,uint32_t bytes,
 const gp50_capture_snapshot *,uint8_t out[32]);
int gp50_capture_link_receive(gp50_capture_cache *,const uint8_t *reply,
 uint32_t bytes,uint32_t now_ms);
#endif
