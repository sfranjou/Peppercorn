#include "components/component.h"
/* Private authoring example: schema 1, fixed answer 42; no lifecycle/state. */
uint32_t answer_get(uint8_t *out,uint32_t capacity) {
    if(capacity<2) return 0;
    out[0]=1;out[1]=42;return 2;
}
