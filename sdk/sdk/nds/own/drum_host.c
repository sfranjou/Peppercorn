/* Own selector 75, schema 1. Exact SET: schema, playing 0/1, window 0/1/255.
 * Window 255 leaves navigation unchanged; 0 closes only an open drum window.
 * No toggle operation: retries cannot invert playback twice. */
#include "drum_host.h"
uint32_t drum_host_get(uint32_t length,uint32_t ctx,const StockIo *io) {
    if(length!=2) return 1;
    LOCAL_BUFFER(io,f,5);
    IO_W8(io,f,0x12); IO_W8(io,f+1,0x75); IO_W8(io,f+2,1);
    IO_W8(io,f+3,STOCK_CALL0(io,0x470c8)!=0);
    IO_W8(io,f+4,STOCK_CALL0(io,0x17742)==7);
    STOCK_CALL(io,0x40942,f,5,ctx); return 1;
}
uint32_t drum_host_set(uint32_t args,uint32_t length,uint32_t *status,const StockIo *io) {
    *status=1;
    if(length!=3 || IO_R8(io,args)!=1 || IO_R8(io,args+1)>1) return 1;
    uint32_t w=IO_R8(io,args+2);
    if(w!=0 && w!=1 && w!=255) return 1;
    STOCK_CALL(io,0x470c0,IO_R8(io,args+1));
    if(w==1) STOCK_CALL(io,0x176a6,7,0);
    else if(w==0 && STOCK_CALL0(io,0x17742)==7) STOCK_CALL(io,0x176a6,3,0);
    *status=0; return 1;
}
