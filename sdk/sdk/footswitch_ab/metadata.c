#include "metadata.h"
static uint32_t get32(const uint8_t *p) {
    return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static void put32(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24);
}
uint32_t gp50_gpam_crc(const uint8_t *p,size_t n) {
    uint32_t c=0xffffffffu;
    while(n--) { c^=*p++; for(unsigned j=0;j<8;j++) c=(c>>1)^((c&1)?0xedb88320u:0); }
    return ~c;
}
static int any(const uint8_t *p,size_t n) { while(n--) if(*p++) return 1; return 0; }
/* V1's three reserved knob words plus its final eight reserved bytes. Model
 * identity is reconstructed from the exact CRC-bound stock record, not omitted
 * from live state. Two compact nine-byte records leave two reserved bytes. */
static const uint8_t extra_offset[20]={24,25,26,27,36,37,38,39,48,49,50,51,52,53,54,55,56,57,58,59};
static int structural(void *ctx,uint8_t g,uint8_t p,uint32_t m,uint32_t v) {
    (void)ctx;(void)g;(void)p;(void)m;(void)v;return 1;
}
static int stock_ok(const uint8_t *p,size_t n) { return p && n==426 && get32(p)==0x15aa5u; }
static int maps_ok(const gp50_gpam_maps *m,const uint8_t *s) {
    if(m->blocked_mask>3) return 0;
    for(unsigned k=0;k<3;k++) {
        const gp50_gpam_knob *b=&m->knob[k];
        if(!b->valid) { if(b->group||b->parameter||b->reserved||b->model) return 0; }
        else if(b->valid!=1 || b->group>=10 || b->parameter>=8 || b->reserved ||
                b->model!=get32(s+38+4*b->group)) return 0;
    }
    for(unsigned k=0;k<2;k++) {
        const gp50_fs_ab_binding *b=&m->foot[k]; gp50_fs_ab_binding tmp;
        if(!b->valid) { if(b->group||b->parameter||b->flags||b->model||b->a||b->b) return 0; }
        else if((m->blocked_mask&(1u<<k)) || b->valid!=1 || b->flags || b->group>=10 ||
                b->model!=get32(s+38+4*b->group) ||
                gp50_fs_ab_make(&tmp,b->group,b->parameter,b->model,b->a,b->b,structural,0)!=GP50_FS_AB_READY) return 0;
    }
    return 1;
}
int gp50_gpam_decode(const uint8_t *t,size_t n,const uint8_t *s,size_t sn,gp50_gpam_maps *out) {
    if(!t || !out || !stock_ok(s,sn) || n<64 || get32(t)!=0x4d415047u) return 0;
    uint32_t version=get32(t+4); size_t bytes;
    if(version==0x00400001u) bytes=64;
    else if(version==0x00400002u) bytes=64;
    else return 0;
    if(n<bytes || get32(t+8)!=gp50_gpam_crc(s,sn) || get32(t+12) ||
       get32(t+bytes-4)!=gp50_gpam_crc(t,bytes-4)) return 0;
    gp50_gpam_maps m={0};
    for(unsigned k=0;k<3;k++) {
        const uint8_t *p=t+16+12*k;
        m.knob[k]=(gp50_gpam_knob){p[0],p[1],p[2],p[3],get32(p+4)};
        if(version==0x00400001u && get32(p+8)) return 0;
    }
    if(version==0x00400001u) { if(any(t+52,8)) return 0; }
    else {
        uint8_t extra[20];for(unsigned i=0;i<20;i++) extra[i]=t[extra_offset[i]];
        if(extra[18]>3 || extra[19]) return 0;
        m.blocked_mask=extra[18];
        for(unsigned k=0;k<2;k++) {
            const uint8_t *p=extra+9*k;
            if(!(p[0]&0x80)) { if(any(p,9)) return 0;continue; }
            uint8_t group=(p[0]>>3)&15,parameter=p[0]&7;
            if(group>=10) return 0;
            m.foot[k]=(gp50_fs_ab_binding){1,group,parameter,0,get32(s+38+4*group),get32(p+1),get32(p+5)};
        }
    }
    if(!maps_ok(&m,s)) return 0;
    *out=m; return version==0x00400001u?1:2;
}
int gp50_gpam_encode(uint8_t *t,size_t n,const uint8_t *s,size_t sn,const gp50_gpam_maps *m) {
    if(!t || !m || n<64 || !stock_ok(s,sn) || !maps_ok(m,s)) return 0;
    uint8_t b[64]={0},extra[20]={0}; put32(b,0x4d415047u);put32(b+4,0x00400002u);put32(b+8,gp50_gpam_crc(s,sn));
    for(unsigned k=0;k<3;k++) {
        uint8_t *p=b+16+12*k;const gp50_gpam_knob *v=&m->knob[k];
        p[0]=v->valid;p[1]=v->group;p[2]=v->parameter;put32(p+4,v->model);
    }
    for(unsigned k=0;k<2;k++) {
        uint8_t *p=extra+9*k;const gp50_fs_ab_binding *v=&m->foot[k];
        if(v->valid) {p[0]=(uint8_t)(0x80|(v->group<<3)|v->parameter);put32(p+1,v->a);put32(p+5,v->b);}
    }
    extra[18]=m->blocked_mask;
    for(unsigned i=0;i<20;i++) b[extra_offset[i]]=extra[i];
    put32(b+60,gp50_gpam_crc(b,60)); for(unsigned i=0;i<64;i++) t[i]=b[i];
    return 1;
}
