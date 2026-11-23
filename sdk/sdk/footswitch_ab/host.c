#include "host.h"
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static void put32(uint8_t *p,uint32_t v) { p[0]=v; p[1]=v>>8; p[2]=v>>16; p[3]=v>>24; }
static int equal(const gp50_fs_ab_binding *a,const gp50_fs_ab_binding *b) { return a->valid==b->valid && a->group==b->group && a->parameter==b->parameter && a->flags==b->flags && a->model==b->model && a->a==b->a && a->b==b->b; }
static int structural(void *ctx, uint8_t g, uint8_t p, uint32_t m, uint32_t v) { (void)ctx; (void)g; (void)p; (void)m; (void)v; return 1; }
static int state_ok(const gp50_fs_ab_state *s) {
    unsigned i; gp50_fs_ab_binding t, zero={0};
    if (!s || s->blocked_mask>3 || s->metadata_fault>1 || (s->owner>99 && s->owner!=255)) return 0;
    for(i=0;i<2;i++) { const gp50_fs_ab_binding *b=&s->binding[i];
        if (!b->valid) { if (!equal(b,&zero)) return 0; }
        else if(s->owner==255 || b->flags || gp50_fs_ab_make(&t,b->group,b->parameter,b->model,b->a,b->b,structural,0)!=GP50_FS_AB_READY || !equal(b,&t)) return 0;
    } return 1;
}
int gp50_fs_ab_host_read(const gp50_fs_ab_state *s,const uint8_t *m,size_t n,uint8_t *out,size_t cap,gp50_fs_ab_validator check,void *ctx) {
    unsigned i; (void)check; (void)ctx; if(!m || n!=2 || m[0]!=0x12 || m[1]!=0x74 || !out || cap<40 || !state_ok(s)) return 0;
    for(unsigned j=0;j<40;j++) out[j]=0;
    out[0]=0x12; out[1]=0x74; out[2]=1; out[3]=s->owner; out[4]=2; out[5]=s->blocked_mask | (s->metadata_fault?0x80:0);
    for(i=0;i<2;i++) { uint8_t *p=out+6+17*i; const gp50_fs_ab_binding *b=&s->binding[i]; p[0]=3+i; p[1]=b->valid; p[2]=b->group; p[3]=b->parameter; p[4]=b->flags; put32(p+5,b->model); put32(p+9,b->a); put32(p+13,b->b); } return 40;
}
int gp50_fs_ab_host_set(gp50_fs_ab_state *s,const uint8_t *m,size_t n,gp50_fs_ab_validator check,void *ctx,gp50_fs_ab_dirty dirty,void *dirty_ctx) {
    gp50_fs_ab_binding v={0}; unsigned i;
    if(!m || n!=20 || m[0]!=0x11 || m[1]!=0x74 || m[2]!=1 || m[3]<3 || m[3]>4 || !state_ok(s) || s->metadata_fault || s->owner==255 || m[6] || m[7]>99 || m[7]!=s->owner) return 0;
    i=m[3]-3;
    if(m[4]==255) { if(m[5] || get32(m+8) || get32(m+12) || get32(m+16)) return 0; }
    else if(gp50_fs_ab_make(&v,m[4],m[5],get32(m+8),get32(m+12),get32(m+16),check,ctx)!=GP50_FS_AB_READY) return 0;
    if(!equal(&s->binding[i],&v) || (s->blocked_mask&(1u<<i))) {
        s->binding[i]=v; s->blocked_mask&=(uint8_t)~(1u<<i);
        if(dirty) dirty(dirty_ctx);
    } return 1;
}
int gp50_fs_ab_host_recover(gp50_fs_ab_state *s,const uint8_t *m,size_t n,
    gp50_fs_ab_dirty clear_knobs,void *knobs_ctx,gp50_fs_ab_dirty dirty,void *dirty_ctx) {
    if(!m || n!=20 || !state_ok(s) || !s->metadata_fault || s->owner>=100 ||
       !clear_knobs || !dirty || m[0]!=0x11 || m[1]!=0x74 || m[2]!=1 ||
       m[3]!=255 || m[4]!=255 || m[5] || m[6]!=1 || m[7]!=s->owner ||
       get32(m+8) || get32(m+12) || get32(m+16)) return 0;
    gp50_fs_ab_state next={.owner=s->owner};
    clear_knobs(knobs_ctx);*s=next;dirty(dirty_ctx);
    return 1;
}
