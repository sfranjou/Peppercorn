#include "persistence.h"
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
int gp50_fs_ab_load(uint8_t owner,const uint8_t *stock,size_t sn,
                    const uint8_t *tail,size_t tn,gp50_fs_ab_state *state,
                    gp50_gpam_maps *maps) {
    if(!state || !maps) return GP50_FS_LOAD_BLOCKED;
    gp50_fs_ab_state next={.owner=owner<100?owner:255,.blocked_mask=3,.metadata_fault=1};
    gp50_gpam_maps decoded={0};int r=GP50_FS_LOAD_BLOCKED;
    if(owner>=100 || !stock || sn!=426 || get32(stock)!=0x15aa5 || !tail || tn!=64) goto done;
    /* Only blank tails establish an ordinary stock preset. Treat other unknown
     * data as damaged, including a GPAM record with a corrupted magic word. */
    if(get32(tail)!=0x4d415047) {
        unsigned zero=1,erased=1;
        for(unsigned i=0;i<64;i++){if(tail[i])zero=0;if(tail[i]!=255)erased=0;}
        if(zero || erased){next.blocked_mask=0;next.metadata_fault=0;r=GP50_FS_LOAD_NONE;}
        goto done;
    }
    r=gp50_gpam_decode(tail,tn,stock,sn,&decoded);
    if(!r) {r=GP50_FS_LOAD_BLOCKED;goto done;}
    next.binding[0]=decoded.foot[0];next.binding[1]=decoded.foot[1];next.blocked_mask=decoded.blocked_mask;next.metadata_fault=0;
done:
    *state=next;*maps=decoded;return r;
}
int gp50_fs_ab_save(const gp50_fs_ab_state *state,uint8_t owner,
                    const gp50_gpam_knob knobs[3],const uint8_t *stock,size_t sn,
                    uint8_t *tail,size_t capacity) {
    if(!state || !knobs || owner>=100 || state->owner!=owner || state->blocked_mask>3 || state->metadata_fault) return 0;
    if(!stock || sn!=426 || get32(stock)!=0x15aa5) return 0;
    gp50_gpam_maps maps={.blocked_mask=state->blocked_mask};
    /* Match existing knob save policy: omit maps for models no longer selected.
     * Stale feet instead remain explicitly blocked across save/load, so a model
     * change cannot turn a parameter press into a stock block action. */
    for(unsigned i=0;i<3;i++) {
        maps.knob[i]=knobs[i];
        if(knobs[i].valid==1 && knobs[i].group<10 && !knobs[i].reserved &&
           knobs[i].parameter<8 && knobs[i].model!=get32(stock+38+4*knobs[i].group))
            maps.knob[i]=(gp50_gpam_knob){0};
    }
    for(unsigned i=0;i<2;i++) {
        const gp50_fs_ab_binding *b=&state->binding[i];
        maps.foot[i]=*b;
        if(b->valid==1 && b->group<10 && b->parameter<8 && !b->flags &&
           b->model!=get32(stock+38+4*b->group)) {
            maps.foot[i]=(gp50_fs_ab_binding){0};maps.blocked_mask|=(uint8_t)(1u<<i);
        }
    }
    return gp50_gpam_encode(tail,capacity,stock,sn,&maps);
}
int gp50_fs_ab_stage(const gp50_fs_ab_state *state,uint8_t owner,
                    const gp50_gpam_knob knobs[3],const uint8_t *stock,size_t sn,
                    uint8_t *destination,size_t capacity) {
    uint8_t tail[64];
    uintptr_t d=(uintptr_t)destination,s=(uintptr_t)stock;
    if(!destination || capacity<576 ||
       (d>s && d-s<sn) || (s>d && s-d<576) ||
       !gp50_fs_ab_save(state,owner,knobs,stock,sn,tail,sizeof tail)) return 0;
    for(unsigned i=0;i<426;i++) destination[i]=stock[i];
    for(unsigned i=0;i<64;i++) destination[512+i]=tail[i];
    return 1;
}
