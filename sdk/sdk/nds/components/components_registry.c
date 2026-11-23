#include "component_registry.h"
static const gp50_component_descriptor *find(uint32_t selector) {
    if(!selector) return 0;   /* ABI 3 features without a host section carry selector 0 */
    for(uint32_t i=0;i<GP50_COMPONENT_COUNT;i++)
        if(gp50_component_table[i].selector==selector) return &gp50_component_table[i];
    return 0;
}
void gp50_components_init(void) {
    for(uint32_t i=0;i<GP50_COMPONENT_COUNT;i++)
        if(gp50_component_table[i].init) gp50_component_table[i].init();
}
void gp50_components_tick(void) {
#if GP50_FEATURE_COUNT > 0
    gp50_features_service();   /* pending PRESET events before feature ticks */
#endif
    for(uint32_t i=0;i<GP50_COMPONENT_COUNT;i++)
        if(gp50_component_table[i].tick) gp50_component_table[i].tick();
}
uint32_t gp50_components_has(uint32_t selector) { return find(selector)!=0; }
uint32_t gp50_components_read(uint32_t selector,uint8_t *out,uint32_t capacity) {
    const gp50_component_descriptor *d=find(selector);
    if(!d || !out || capacity<d->max_reply_bytes) return 0;
    uint32_t n=d->get(out,d->max_reply_bytes);
    return n<=d->max_reply_bytes?n:0;
}
uint32_t gp50_components_write(uint32_t selector,const uint8_t *args,uint32_t length) {
    const gp50_component_descriptor *d=find(selector);
    if(!d || !d->set || !args || length!=d->set_bytes) return 1;
    return d->set(args,length)==0?0:1;
}
uint32_t gp50_components_editor_status(char *out, uint32_t capacity) {
    if (!out || capacity < GP50_COMPONENT_STATUS_CAPACITY) return 0;
    out[0] = 0;
#if GP50_COMPONENT_UI_COUNT > 0
    for (uint32_t i = 0; i < GP50_COMPONENT_UI_COUNT; i++) {
        for (uint32_t j = 0; j < GP50_COMPONENT_STATUS_CAPACITY; j++) out[j] = 0;
        uint32_t n = gp50_component_ui_table[i](out, GP50_COMPONENT_STATUS_CAPACITY);
        if (!n || n >= GP50_COMPONENT_STATUS_CAPACITY) continue;
        uint32_t valid = 1;
        for (uint32_t j = 0; j < n; j++)
            if ((uint8_t)out[j] < 32 || (uint8_t)out[j] > 126) valid = 0;
        if (!valid) continue;
        out[n] = 0;
        return n;
    }
    out[0] = 0;
#endif
    return 0;
}
