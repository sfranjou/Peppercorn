#ifndef GP50_FS_AB_ENDPOINT_H
#define GP50_FS_AB_ENDPOINT_H
#include <stdint.h>
/* An endpoint must be a fixed point of the existing parameter setter, which
 * rounds multiples of step about zero and then clamps to min/max. Dynamic Sync
 * ranges must be queried again on every press. No division for invalid step.
 * Compile this translation unit with the NDS32 hard-float ABI at integration. */
int gp50_fs_ab_endpoint(uint32_t value,uint32_t minimum,uint32_t maximum,uint32_t step);
#endif
