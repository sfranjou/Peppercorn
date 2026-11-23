/* Successor host integration; frozen implementation stays included unchanged.
 * Use only with boot-reset capture storage and the paired ARM schema3 runtime.
 * This translation unit replaces own_commands.c in a capture-enabled candidate. */
#ifndef GP50_CAPTURE_NATIVE_COMMANDS
#define OWN_FEATURES (OWN_FEATURE_LOAD | OWN_FEATURE_GPTC | OWN_FEATURE_KNOB_ASSIGN | OWN_FEATURE_TAP_SAFE | (1u << 6))
#define own_get gp50_own_get_base
#include "../nds/host_layer/own_commands.c"
#undef own_get
#endif
#include "nds_transport.h"
#include "capture_host.h"
uint32_t own_get(uint32_t sel,uint32_t length,uint32_t ctx,const StockIo *io) {
 if(sel!=0x72)return gp50_own_get_base(sel,length,ctx,io);
 if(length!=2)return 1;
 uint8_t bytes[GP50_CAPTURE_REPLY_BYTES];
 if(!gp50_capture_display_frame(bytes))return 1;
 LOCAL_BUFFER(io,f,GP50_CAPTURE_REPLY_BYTES);
 if(!f)return 1;
 for(uint32_t i=0;i<GP50_CAPTURE_REPLY_BYTES;i++)IO_W8(io,f+i,bytes[i]);
 STOCK_CALL(io,0x40942,f,GP50_CAPTURE_REPLY_BYTES,ctx);
 return 1;
}
