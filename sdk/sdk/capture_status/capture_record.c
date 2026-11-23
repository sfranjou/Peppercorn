#include "capture_record.h"
static uint32_t rd32(const uint8_t *p) {
 return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static gp50_capture_record_check result(uint8_t kind,uint8_t state,uint32_t bytes,uint32_t error,uint8_t run) {
 gp50_capture_record_check c={bytes,error,kind,state,run,0};return c;
}
gp50_capture_record_check gp50_capture_record_preflight(const uint8_t *p,uint32_t extent) {
 uint8_t kind=GP50_CAPTURE_UNKNOWN;
 if(!p || extent<4u)return result(kind,GP50_CAPTURE_REJECTED,0,GP50_CAPTURE_E_EXTENT,0);
 uint32_t magic=rd32(p);
 if(!magic)return result(GP50_CAPTURE_EMPTY,GP50_CAPTURE_UNSUPPORTED,4,0,0);
 switch(magic) {
 case 0x49535456u:kind=GP50_CAPTURE_VTSI;break;
 case 0x43545047u:kind=GP50_CAPTURE_GPTC;break;
 case 0x4e355047u:return result(GP50_CAPTURE_GP5N,GP50_CAPTURE_REJECTED,4,GP50_CAPTURE_E_FORMAT,0);
 case 0x50355047u:return result(GP50_CAPTURE_GP5P,GP50_CAPTURE_REJECTED,4,GP50_CAPTURE_E_FORMAT,0);
 default:return result(kind,GP50_CAPTURE_UNSUPPORTED,4,0,0);
 }
 if(extent<2696u)goto short_record;
 return result(kind,GP50_CAPTURE_LOADING,2696u,0,1);
short_record:return result(kind,GP50_CAPTURE_REJECTED,0,GP50_CAPTURE_E_EXTENT,0);
}
uint32_t gp50_capture_record_extent(uint32_t p,const gp50_capture_geometry *b,
 const gp50_capture_geometry *c,uint32_t transaction,uint8_t *fallback) {
 *fallback=0;
 if(transaction!=1u)return 0;
 if(p==0x20002074u) {*fallback=1;return 2048;}
 if(b && b->base==0x122000u && b->bytes==0x36000u && b->stride==4096u && b->directories==3u &&
    p>=0x125000u && p<0x157000u && !(p&4095u))return 4096;
 if(c && c->base==0x158000u && c->bytes==0x78000u && c->stride==4096u && c->directories==3u &&
    p>=0x15b000u && p<0x1d0000u && !(p&4095u))return 4096;
 return 0;
}
