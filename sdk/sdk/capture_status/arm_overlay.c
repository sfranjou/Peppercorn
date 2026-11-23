#include "arm_overlay.h"
void gp50_capture_arm_overlay(gp50_capture_arm *a,uint32_t event,
 gp50_capture_overlay_context *c,uint32_t address) {
 if(event==GP50_CAPTURE_PREPARE) {
  c->owned=0;
  c->generation=gp50_capture_arm_input(a,address,&c->extent);
  c->run=0;c->kind=GP50_CAPTURE_UNKNOWN;c->state=GP50_CAPTURE_REJECTED;
  c->error=GP50_CAPTURE_E_CONTEXT;c->bypassed=0;
  if(!c->generation)return;
  gp50_capture_record_check check=gp50_capture_record_preflight(
   (const uint8_t *)c->record,c->extent);
  c->extent=check.bytes;
  c->kind=check.kind;c->state=check.state;c->error=check.error;c->run=check.run;
 } else if(event==GP50_CAPTURE_COMPLETE) {
  (void)gp50_capture_arm_finish(a,c->generation,c->kind,c->state,c->error);
 } else if(event==GP50_CAPTURE_PROCESS) {
  if(c->error)(void)gp50_capture_arm_watchdog(a,c->generation,c->error);
  else (void)gp50_capture_arm_bypass(a,c->generation,c->bypassed);
 }
}
