#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "nds_transport.h"
typedef struct lv_obj {int unused;} lv_obj_t;
static uint32_t test_assign,tick,state[40],restores,base_calls,draws,requests,warning;
static gp50_capture_nds_state capture;
static char visible[64];static uint8_t frame[24];static int available=1;
#define GP50_CAPTURE_NATIVE_EDITOR
#define CAPTURE_STATE (&capture)
#define GP50_MOD026_ASSIGN_STATE ((uintptr_t)&test_assign)
#define GP50_TICK_COUNTER ((uintptr_t)&tick)
#define ST state
enum {S_WARN=35};
static void mod026_restore_ctx(void *ctx) {(void)ctx;restores++;visible[0]=0;}
static int gp50_gr_editor_tick_base(uint8_t *ctx,void *msg) {
 (void)ctx;(void)msg;base_calls++;state[S_WARN]=warning;
 if(warning)strcpy(visible,"CPU HIGH");
 if(test_assign)strcpy(visible,"ASSIGN");return 17;
}
static uint32_t enable_mask,icon_shown,icon_calls,current_capture_slot=13;
static uint32_t capture_enable_mask(void){return enable_mask;}
static int effect_ordinal(uint32_t slot){assert(slot==1 || slot==9);return slot==9 ? (int)current_capture_slot : 2;}
static lv_obj_t *lv_obj_get_child(lv_obj_t *p,uint32_t idx){assert(p==(lv_obj_t *)(uintptr_t)0x4000 && idx==2);return (lv_obj_t *)(uintptr_t)0x5000;}
static void capture_icon_visible(lv_obj_t *p,uint32_t show){assert(p==(lv_obj_t *)(uintptr_t)0x5000);icon_shown=show;icon_calls++;}
#ifdef GP50_COMPONENTS
#define GR_ORDINAL 2
static uint32_t ui_requests,ui_available;

uint32_t gp50_components_editor_status(char *out,uint32_t capacity) {
 assert(capacity==32);ui_requests++;
 if(!ui_available)return 0;
 memcpy(out,"Counter 42",11);return 10;
}
#endif
static void lv_obj_set_pos(lv_obj_t *p,int x,int y){assert(p && x==0 && y==0);}
static void lv_obj_set_size(lv_obj_t *p,int x,int y){assert(p && x==160 && y==20);}
static void mod026_set_text(lv_obj_t *p,const char *s){assert(p);assert(strlen(s)<32);strcpy(visible,s);draws++;}
static void strip_label_show(lv_obj_t *p,uint32_t n){assert(p && n==1);}
int gp50_capture_display_frame(uint8_t out[24]){requests++;memcpy(out,frame,24);return available;}
#include "nds_editor.c"
static unsigned cases;
static uint8_t ctx[256] __attribute__((aligned(8)));
static void run(void){assert(nds_gr_editor_tick(ctx,0)==17);cases++;}
int main(void) {
 lv_obj_t *label=(lv_obj_t *)(uintptr_t)0x1000;
 capture.ready=GP50_CAPTURE_NDS_READY;capture.complement=~GP50_CAPTURE_NDS_READY;
 memcpy(ctx+0xe0,&label,sizeof label);ctx[0x90]=0;ctx[0x80]=9;
 gp50_capture_snapshot s;gp50_capture_reset(&s);assert(gp50_capture_encode(&s,0,UINT32_MAX,frame));
 run();assert(!strcmp(visible,"CAPTURE --"));
 unsigned d=draws;tick=99;run();assert(draws==d);tick=100;run();assert(draws==d+1);
 assert(gp50_capture_begin(&s,13));assert(gp50_capture_encode(&s,1,0,frame));tick+=100;run();assert(!strcmp(visible,"CAPTURE LOAD"));
 assert(gp50_capture_finish(&s,s.generation,GP50_CAPTURE_GPTC,GP50_CAPTURE_ACCEPTED,0,0));
 assert(gp50_capture_encode(&s,1,0,frame));tick+=100;run();assert(!strcmp(visible,"LTTC OK"));
 assert(gp50_capture_bypass(&s,s.generation,1));assert(gp50_capture_encode(&s,1,0,frame));tick+=100;run();assert(!strcmp(visible,"LTTC OFF"));
 assert(gp50_capture_watchdog(&s,s.generation,0xffffffffu));assert(gp50_capture_encode(&s,1,0,frame));tick+=100;run();assert(!strcmp(visible,"LTTC ERR ffffffff"));
 warning=1;run();assert(!strcmp(visible,"CPU HIGH"));d=draws;run();assert(draws==d);
 warning=0;tick+=100;run();assert(!strcmp(visible,"LTTC ERR ffffffff"));
 test_assign=1;unsigned r=restores;run();assert(restores==r+1 && !strcmp(visible,"ASSIGN"));
 test_assign=0;run();assert(!strcmp(visible,"LTTC ERR ffffffff"));
 ctx[0x80]=1;r=restores;run();assert(restores==r+1 && !visible[0]);
 ctx[0x80]=9;assert(gp50_capture_encode(&s,2,1000,frame));run();assert(!strcmp(visible,"CAPTURE OLD"));
 frame[0]^=1;tick+=100;run();assert(!strcmp(visible,"CAPTURE --"));
 label=0;memcpy(ctx+0xe0,&label,sizeof label);r=restores;run();assert(restores==r+1);
 label=(lv_obj_t *)(uintptr_t)0x2000;memcpy(ctx+0xe0,&label,sizeof label);available=0;d=draws;run();assert(draws==d);
 available=1;run();assert(draws==d+1);
#ifdef GP50_COMPONENTS
 /* Ordinary editor claims only a text strip; protected screens win. */
 ctx[0x80]=2;ui_available=1;unsigned u=ui_requests;r=restores;
 run();assert(!strcmp(visible,"Counter 42") && ui_requests==u+1 && restores==r+1);
 d=draws;u=ui_requests;run();assert(draws==d && ui_requests==u);
 tick+=100;run();assert(draws==d+1 && ui_requests==u+1);
 ui_available=0;tick+=100;r=restores;run();assert(!visible[0] && restores==r+1);
 ui_available=1;run();assert(!strcmp(visible,"Counter 42"));
 warning=1;u=ui_requests;run();assert(!strcmp(visible,"CPU HIGH") && ui_requests==u);
 warning=0;run();assert(!strcmp(visible,"Counter 42"));
 test_assign=1;u=ui_requests;run();assert(!strcmp(visible,"ASSIGN") && ui_requests==u);
 test_assign=0;run();assert(!strcmp(visible,"Counter 42"));
 ctx[0x80]=1;u=ui_requests;run();assert(!visible[0] && ui_requests==u); /* GR owns */
 ctx[0x80]=9;run();assert(!strcmp(visible,"CAPTURE --") && ui_requests==u);
 ctx[0x80]=2;run();assert(!strcmp(visible,"Counter 42"));
 label=(lv_obj_t *)(uintptr_t)0x3000;memcpy(ctx+0xe0,&label,sizeof label);
 r=restores;run();assert(!strcmp(visible,"Counter 42") && restores==r+1);
 label=0;memcpy(ctx+0xe0,&label,sizeof label);u=ui_requests;r=restores;
 run();assert(!visible[0] && restores==r+1 && ui_requests==u);
 label=(lv_obj_t *)(uintptr_t)0x3001;memcpy(ctx+0xe0,&label,sizeof label);
 run();assert(ui_requests==u); /* odd identity cannot be tagged */
 label=(lv_obj_t *)(uintptr_t)0x3000;memcpy(ctx+0xe0,&label,sizeof label);
 run();assert(!strcmp(visible,"Counter 42"));
 ctx[0x90]=255;u=ui_requests;run();assert(!visible[0] && ui_requests==u);
 ui_available=0;
#endif
 /* CAB mark: fresh current GPTC only, with AMP untouched; stale/mismatched
  * data must not claim a usable fused cabinet. */
 ctx[0x80]=9;ctx[0x81]=4;ctx[0x90]=0;
 uint32_t image=0x4000;memcpy(ctx+0x58,&image,4);enable_mask=1u<<9;
 gp50_capture_reset(&s);assert(gp50_capture_begin(&s,13));
 assert(gp50_capture_finish(&s,s.generation,GP50_CAPTURE_GPTC,GP50_CAPTURE_ACCEPTED,0,0));
 assert(gp50_capture_encode(&s,1,0,frame));run();assert(!icon_shown);
 current_capture_slot=14;run();assert(icon_shown);current_capture_slot=13;
 assert(gp50_capture_encode(&s,2,1000,frame));run();assert(icon_shown);
 assert(gp50_capture_encode(&s,1,0,frame));available=0;run();assert(icon_shown);available=1;
 s.kind=GP50_CAPTURE_VTSI;assert(gp50_capture_encode(&s,1,0,frame));run();assert(icon_shown);
 s.kind=GP50_CAPTURE_GPTC;s.flags=GP50_CAPTURE_SLOT_KNOWN|GP50_CAPTURE_BYPASSED;
 assert(gp50_capture_encode(&s,1,0,frame));run();assert(icon_shown);
 s.flags=GP50_CAPTURE_SLOT_KNOWN|GP50_CAPTURE_FALLBACK;assert(gp50_capture_encode(&s,1,0,frame));run();assert(icon_shown);
 s.flags=GP50_CAPTURE_SLOT_KNOWN;s.state=GP50_CAPTURE_RUNTIME_ERROR;s.error=1;
 assert(gp50_capture_encode(&s,1,0,frame));run();assert(icon_shown);
 enable_mask=0;run();assert(!icon_shown && icon_calls>=9);
 ctx[0x81]=0;memset(ctx+0x58,0,4);
 for(unsigned i=0;i<256;i++){ctx[0x90]=(uint8_t)i;tick+=100;run();}
 assert(base_calls==cases);printf("%u capture editor lifecycle cases passed\n",cases);
}
