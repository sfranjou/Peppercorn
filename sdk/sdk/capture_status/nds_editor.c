/* Successor-only small edit-page status. Base GR/admission/assignment behavior
 * runs first. No object allocation or ARM wait; cached frame + coalesced request.
 * CPU/refusal/assignment prompts win. Restore before leaving a capture strip.
 * This translation unit replaces gr_meter.c in a capture-enabled candidate. */
#ifndef GP50_CAPTURE_NATIVE_EDITOR
#define nds_gr_editor_tick gp50_gr_editor_tick_base
#include "../nds/ui/gr_meter.c"
#undef nds_gr_editor_tick
#endif
#include "nds_transport.h"
#ifdef GP50_COMPONENTS
#include "components/component.h"
#endif
#ifndef CAPTURE_STATE
#define CAPTURE_STATE ((gp50_capture_nds_state *)GP50_CAPTURE_NDS_BASE)
#endif
static char *capture_put(char *p,const char *s) {while(*s)*p++=*s++;return p;}
static void capture_short_text(const uint8_t frame[24],char out[32]) {
 gp50_capture_snapshot s;uint8_t fresh;uint32_t age;
 char *p=out;
 if(!gp50_capture_decode(frame,24,&s,&fresh,&age) || !fresh)p=capture_put(p,"CAPTURE --");
 else if(fresh==GP50_CAPTURE_STALE)p=capture_put(p,"CAPTURE OLD");
 else if(s.state==GP50_CAPTURE_LOADING)p=capture_put(p,"CAPTURE LOAD");
 else if(s.state==GP50_CAPTURE_RETIRED)p=capture_put(p,"CAPTURE NONE");
 else if(s.kind==GP50_CAPTURE_EMPTY)p=capture_put(p,"CAPTURE EMPTY");
 else {
  static const char *const names[]={"CAPTURE","EMPTY","SNAPTONE","GP5N","GP5P","LTTC"};
  p=capture_put(p,names[s.kind]);
  if(s.state==GP50_CAPTURE_ACCEPTED)p=capture_put(p,s.flags&GP50_CAPTURE_BYPASSED?" OFF":" OK");
  else if(s.error) {
   p=capture_put(p," ERR ");
   for(int i=7;i>=0;i--)*p++="0123456789abcdef"[(s.error>>(4u*(uint32_t)i))&15u];
  } else p=capture_put(p," UNSUPPORTED");
 }
 *p=0;
}
/* Stock editor marks AMP and CAB unavailable whenever N->S is on. The
 * current GPTC player instead owns CAB's convolution. Keep AMP restricted,
 * and clear CAB's mark only for a fresh, matching, accepted GPTC snapshot.
 * No record/flash reads, audio work, allocation, or blocking link requests. */
#ifndef GP50_CAPTURE_NATIVE_EDITOR
static uint32_t capture_enable_mask(void) {
 const volatile uint8_t *p=(const volatile uint8_t *)GP50_MDATA_ENABLE_MASK;
 return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;
}
static void capture_icon_visible(lv_obj_t *marker,uint32_t show) {
 /* Stock LVGL hidden flag helpers, the same calls as the stock row renderer. */
 if(show)strip_label_show(marker,1);
 else ((void (*)(lv_obj_t *,uint32_t))(uintptr_t)0x29858)(marker,1);
}
#endif
static void capture_cab_icon(uint8_t *ctx) {
 uint32_t row;
 for(row=0;row<10u;row++)if(ctx[0x80+row]==4u)break;
 if(row==10u)return;
 uint32_t image=*(uint32_t *)(void *)(ctx+0x54+4u*row);
 if(!image)return;
 uint8_t frame[24];gp50_capture_snapshot snap;uint8_t fresh;uint32_t age;
 uint32_t blocked=(capture_enable_mask()>>9)&1u;
 if(blocked && gp50_capture_display_frame(frame) &&
    gp50_capture_decode(frame,24,&snap,&fresh,&age) && fresh==GP50_CAPTURE_FRESH &&
    snap.kind==GP50_CAPTURE_GPTC && snap.state==GP50_CAPTURE_ACCEPTED &&
    snap.slot==(uint32_t)effect_ordinal(9) &&
    !(snap.flags&(GP50_CAPTURE_BYPASSED|GP50_CAPTURE_FALLBACK)))blocked=0;
 lv_obj_t *marker=lv_obj_get_child((lv_obj_t *)(uintptr_t)image,2);
 if(marker)capture_icon_visible(marker,blocked);
}
int nds_gr_editor_tick(uint8_t *ctx,void *msg) {
 if(CAPTURE_STATE->ready!=GP50_CAPTURE_NDS_READY ||
    CAPTURE_STATE->complement!=~GP50_CAPTURE_NDS_READY)return gp50_gr_editor_tick_base(ctx,msg);
 uint32_t idx=ctx[0x90];
 int selected=idx<10u && ctx[0x80+idx]==9u;
 int assign=*(volatile uint32_t *)GP50_MOD026_ASSIGN_STATE!=0;
#ifdef GP50_FEATURE_ASSIGNMENT
 assign|=gp50_features_editor_text_active()!=0;   /* an SDK feature's editor text owns the strip */
#endif
 lv_obj_t *label=*(lv_obj_t **)(ctx+0xe0);
 uint32_t wanted=selected && !assign ? (uint32_t)(uintptr_t)label : 0;
#ifdef GP50_COMPONENTS
#ifdef GP50_FEATURE_GR_METER   /* a feature meter strip shown on the last tick keeps the strip (one tick of lag) */
 int ordinary=idx<10u && !selected && !ST[S_SHOWN];
#else
 int ordinary=idx<10u && !selected &&
     !(ctx[0x80+idx]==1u && effect_ordinal(1)==GR_ORDINAL);
#endif
 if(ordinary && !assign && label && !((uintptr_t)label&1u))
  wanted=(uint32_t)(uintptr_t)label|1u;
#endif
 /* Identity only, never dereferenced. Low bit marks component text; only an
  * even label identity can be tagged. Deletion/creation remains stock-owned.
  * Mode changes restore before base rendering, so GR/prompts retain priority. */
 uint32_t previous=CAPTURE_STATE->reserved[0];
 if(previous && previous!=wanted) {
  CAPTURE_STATE->reserved[0]=0;mod026_restore_ctx(ctx);
 }
 int result=gp50_gr_editor_tick_base(ctx,msg);
 capture_cab_icon(ctx);
 if(!wanted || !label)return result;
 if(ST[S_WARN]) {CAPTURE_STATE->reserved[0]=0;return result;}
 uint32_t now=*(volatile uint32_t *)GP50_TICK_COUNTER;
 if(CAPTURE_STATE->reserved[0]==wanted && now-CAPTURE_STATE->reserved[1]<100u)return result;
 uint8_t frame[24];char text[32];
 if(selected) {
  if(!gp50_capture_display_frame(frame))return result;
  capture_short_text(frame,text);
 }
#ifdef GP50_COMPONENTS
 else if(!gp50_components_editor_status(text,sizeof text)) {
  if(CAPTURE_STATE->reserved[0])mod026_restore_ctx(ctx);
  CAPTURE_STATE->reserved[0]=0;return result;
 }
#endif
 lv_obj_set_pos(label,0,0);lv_obj_set_size(label,160,20);
 mod026_set_text(label,text);strip_label_show(label,1);
 CAPTURE_STATE->reserved[0]=wanted;
 CAPTURE_STATE->reserved[1]=now;
 return result;
}
