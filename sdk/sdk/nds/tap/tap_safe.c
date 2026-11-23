/* Owned tap-tempo implementation: intentional zero-interval guard.
 * Stock nonzero behavior is compared separately; not unconditional equivalence. */
#include "tap_safe.h"
uint32_t home_tap_safe(uint32_t dlg,uint32_t key,const StockIo *io){
 if(key!=IO_R8(io,0x20004a88)){IO_W8(io,0x20004a88,key);return dlg;}
 uint32_t now=STOCK_CALL0(io,0x174f4),result;
 if(IO_R8(io,dlg+0x15)==0){result=1;IO_W8(io,dlg+0x15,1);}
 else {
  uint32_t elapsed=now-io_r32(io,dlg+0x10);
  result=tap_safe_interval(elapsed,io);
 }
 io_w32(io,dlg+0x10,now);return result;
}

/* Shared on-pedal/remote interval policy; return is not a BPM confirmation. */
uint32_t tap_safe_interval(uint32_t elapsed,const StockIo *io){
 if (!elapsed) return 0;
 uint32_t result=60000u/elapsed;
 if(result>=30){
  if(result<40)result=40;
  else if(result>=261)result=260;
  result=STOCK_CALL(io,0x47302,result);
 }
 return result;
}
