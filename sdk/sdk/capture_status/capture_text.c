#include "capture_text.h"
typedef struct {char *p;uint32_t capacity,used;} writer;
static void append(writer *w,const char *s) {
 for(;*s;s++) {if(w->used+1u<w->capacity)w->p[w->used]=*s;w->used++;}
}
static void hex(writer *w,uint32_t value) {
 char h[9];const char *digits="0123456789abcdef";
 for(unsigned i=0;i<8;i++)h[i]=digits[(value>>(28u-i*4u))&15u];
 h[8]=0;append(w,h);
}
int gp50_capture_text(const gp50_capture_snapshot *s,uint8_t freshness,char *out,uint32_t capacity) {
 static const char *const kinds[]={"UNKNOWN","EMPTY","SNAPTONE","GP5N","GP5P","LTTC"};
 writer w={out,capacity,0};
 if(!gp50_capture_valid(s) || freshness>2 || (freshness==0)!=(s->state==GP50_CAPTURE_UNAVAILABLE))append(&w,"Capture status unavailable");
 else if(freshness==0)append(&w,"Capture status unavailable");
 else if(freshness==2)append(&w,"Capture status stale");
 else if(s->state==GP50_CAPTURE_LOADING)append(&w,"Loading capture");
 else if(s->state==GP50_CAPTURE_RETIRED)append(&w,"No active capture");
 else if(s->state==GP50_CAPTURE_UNSUPPORTED && s->kind==GP50_CAPTURE_EMPTY)append(&w,"Empty capture");
 else {
  append(&w,kinds[s->kind]);
  if(s->state==GP50_CAPTURE_ACCEPTED)append(&w,s->flags&GP50_CAPTURE_BYPASSED?" bypassed":" ready");
  else if(s->state==GP50_CAPTURE_REJECTED || s->state==GP50_CAPTURE_RUNTIME_ERROR) {
   append(&w,s->state==GP50_CAPTURE_REJECTED?" rejected: 0x":" runtime error: 0x");hex(&w,s->error);
  } else append(&w," unsupported");
  if(s->flags&GP50_CAPTURE_FALLBACK)append(&w," (fallback)");
 }
 if(capacity)out[w.used<capacity?w.used:capacity-1u]=0;
 return w.used<capacity;
}
