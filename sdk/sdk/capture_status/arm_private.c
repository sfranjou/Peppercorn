#include "arm_private.h"
void gp50_capture_private_prepare(gp50_capture_arm *a,
 gp50_capture_overlay_context *c,uint32_t address,gp50_capture_alloc allocate) {
 gp50_capture_arm_overlay(a,GP50_CAPTURE_PREPARE,c,address);
 c->owned=0;
 if(!c->run)return;
 /* Preflight sets extent to independently checked complete format length.
  * All supported formats are <=2696; keep an independent copy-loop cap. */
 if(!c->extent || c->extent>2696u) {
  c->run=0;c->state=GP50_CAPTURE_REJECTED;c->error=GP50_CAPTURE_E_EXTENT;return;
 }
 uint8_t *p=allocate?allocate(c->extent):0;
 if(!p) {
  c->run=0;c->state=GP50_CAPTURE_REJECTED;c->error=GP50_CAPTURE_E_MEMORY;return;
 }
 const volatile uint8_t *source=(const volatile uint8_t *)c->record;
 for(uint32_t i=0;i<c->extent;i++)p[i]=source[i];
 c->record=(uintptr_t)p;c->owned=(uintptr_t)p;
}
void gp50_capture_private_release(gp50_capture_overlay_context *c,gp50_capture_free release) {
 if(c->owned && release) {
  release((void *)c->owned);
  c->record=0;c->owned=0;c->run=0;
 }
}
