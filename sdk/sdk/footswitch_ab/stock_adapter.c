#include "stock_adapter.h"
#include "endpoint.h"
#define PRESET_IDS 0x200106d3u
int gp50_fs_ab_stock_validate(void *ctx,uint8_t g,uint8_t p,uint32_t model,uint32_t value) {
    const StockIo *io=ctx;
    if(!io || g>=10 || p>=8 || p>=STOCK_CALL(io,0x46c2a,g) || io_r32(io,PRESET_IDS+4*g)!=model) return 0;
    uint32_t lo=STOCK_CALL_RF2(io,0x43b2c,g,p),hi=STOCK_CALL_RF2(io,0x43ba6,g,p);
    uint32_t step=STOCK_CALL_RF2(io,0x43c20,g,p);
    return gp50_fs_ab_endpoint(value,lo,hi,step);
}
int gp50_fs_ab_stock_press(uint32_t index,const gp50_fs_ab_state *state,const StockIo *io) {
    if(!io || !state || index>=2) return GP50_FS_AB_INVALID;
    if(state->owner!=STOCK_CALL0(io,0x471d6)) return GP50_FS_AB_STALE;
    if(state->blocked_mask>3 || (state->blocked_mask&(1u<<index))) return GP50_FS_AB_INVALID;
    const gp50_fs_ab_binding *b=&state->binding[index];uint32_t next=0;
    if(!b->valid) return gp50_fs_ab_next(b,0,0,gp50_fs_ab_stock_validate,(void *)io,&next);
    if(b->group>=10 || b->parameter>=8) return GP50_FS_AB_INVALID;
    uint32_t model=io_r32(io,PRESET_IDS+4*b->group);
    if(model!=b->model) return GP50_FS_AB_STALE;
    if(b->parameter>=STOCK_CALL(io,0x46c2a,b->group)) return GP50_FS_AB_STALE;
    uint32_t current=STOCK_CALL_RF2(io,0x4555a,b->group,b->parameter);
    int r=gp50_fs_ab_next(b,model,current,gp50_fs_ab_stock_validate,(void *)io,&next);
    if(r!=GP50_FS_AB_READY) return r;
    /* Defensive ownership check in addition to the required caller context. */
    if(state->owner!=STOCK_CALL0(io,0x471d6)) return GP50_FS_AB_STALE;
    uint32_t companion=STOCK_CALL_F3(io,0x4557e,b->group,b->parameter,1,next);
    STOCK_CALL(io,0x4305e,4,b->group,b->parameter);
    if(companion==0xffff) STOCK_CALL(io,0x46750,b->group,b->parameter);
    else {
        STOCK_CALL(io,0x4305e,9,1,0);
        STOCK_CALL(io,0x466ac,b->group,companion&0xff);
        STOCK_CALL(io,0x47696,4);
    }
    return GP50_FS_AB_READY;
}
