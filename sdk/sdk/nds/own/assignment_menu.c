/* Explicit editor clearing, MOD096. Reuses the old home-reset scratch words;
 * enabled only by GP50_ASSIGNMENT_MENU. No parameter writes or flash operations.
 * All input goes through the generated window-4 wrappers before stock handlers.
 */
#include "assignment_menu.h"
#define PHASE ASSIGN_STATE
#define OWNER (ASSIGN_STATE+20)
#define DEST (ASSIGN_STATE+12)
#define ROOT (ASSIGN_META+12)
#define MODEL (ASSIGN_META+16)
#define BLOCKED (ASSIGN_META+20)
#define FS 0x2001f580u
#define KNOB(k) (ASSIGN_STATE+32+16*(k))
static const uint32_t snapshot[4]={ASSIGN_STATE+4,ASSIGN_STATE+8,ASSIGN_STATE+16,ASSIGN_STATE+24};
static uint32_t fault(const StockIo *io) { return IO_R8(io,FS)==io_r32(io,OWNER) && IO_R8(io,FS+2); }
static uint32_t binding(uint32_t d) { return d<3?KNOB(d):FS+4+16*(d-3); }
static uint32_t live_owner(uint32_t d,const StockIo *io) { return d<3?io_r32(io,ASSIGN_STATE+80):IO_R8(io,FS); }
static uint32_t group(uint32_t d,const StockIo *io) { return d<3?io_r32(io,binding(d)+4):IO_R8(io,binding(d)+1); }
static uint32_t parameter(uint32_t d,const StockIo *io) { return d<3?io_r32(io,binding(d)+8):IO_R8(io,binding(d)+2); }
static uint32_t valid(uint32_t ctx,const StockIo *io) {
    return STOCK_CALL0(io,0x471d6)==io_r32(io,OWNER) && io_r32(io,ctx+EDIT_HEADER)==io_r32(io,ROOT);
}
static uint32_t current_model(uint32_t g,const StockIo *io) { return g<10?io_r32(io,PRESET_IDS+4*g):0; }
static void put(uint32_t out,uint32_t *n,const char *s,const StockIo *io) {
    while(*s && *n<126) IO_W8(io,out+(*n)++,(uint8_t)*s++);
}
static void render(uint32_t ctx,const StockIo *io) {
    LOCAL_BUFFER(io,text,128); uint32_t n=0,p=io_r32(io,PHASE),d=io_r32(io,DEST);
    if(p==ASSIGN_MENU) {
        put(text,&n,d==0?"> Assign control\n":"  Assign control\n",io);
        put(text,&n,d==1?"> Clear assignment\n":"  Clear assignment\n",io);
        if(fault(io)) put(text,&n,d==2?"> Clear all (bad data)\n":"  Clear all (bad data)\n",io);
        put(text,&n,"PARA: select\nEXIT: cancel",io);
    } else if(p==ASSIGN_PICK) put(text,&n,"Clear assignment\nTurn Stomp knob\nor press FS A/B\nEXIT: cancel",io);
    else if(p==ASSIGN_DONE) put(text,&n,"Assignment cleared\nSAVE preset\nEXIT: close",io);
    else if(p==ASSIGN_RECOVER) put(text,&n,"Clear ALL assignments?\nKnobs and FS A/B\nPARA: clear all\nEXIT: cancel",io);
    else if(p==ASSIGN_CHANGED) put(text,&n,"Assignment changed\nPlease select again\nEXIT: close",io);
    else {
        put(text,&n,d<3?"Stomp knob ":"Footswitch ",io);
        IO_W8(io,text+n++,(uint8_t)(d<3?'1'+d:'A'+d-3));
        if(p==ASSIGN_EMPTY) put(text,&n,"\nNot assigned\nEXIT: close",io);
        else {
            uint32_t g=group(d,io),param=parameter(d,io);
            put(text,&n,"\n",io);
            /* Bounds and model checks precede name lookup. Stale bindings can be
             * cleared, but never resolve a parameter through an unrelated model. */
            uint32_t model=g>=10?0:(d<3?STOCK_CALL(io,0x475d0,g):current_model(g,io));
            uint32_t saved=d<3?io_r32(io,binding(d)+12):io_r32(io,binding(d)+4);
            if(g<10 && model==saved && param<STOCK_CALL(io,0x46c2a,g)) {
                static const char *const names[]={"NR","PRE","DST","AMP","CAB","EQ","MOD","DLY","RVB","NS"};
                put(text,&n,names[g],io); put(text,&n,": ",io);
                LOCAL_BUFFER(io,name,24);
                STOCK_CALL(io,0x43a44,g,STOCK_CALL(io,0x475d0,g),param,name,24);
                IO_W8(io,name+23,0);
                for(uint32_t i=0;i<23 && IO_R8(io,name+i) && n<90;i++) IO_W8(io,text+n++,IO_R8(io,name+i));
            } else put(text,&n,"Stale / blocked binding",io);
            put(text,&n,"\nPARA: clear\nEXIT: cancel",io);
        }
    }
    IO_W8(io,text+n,0);
    uint32_t h=io_r32(io,ctx+EDIT_HEADER);
    STOCK_CALL(io,0x2a46a,h,0,0); STOCK_CALL(io,0x2a4ce,h,160,128);
    assign_set_text(h,text,io); STOCK_CALL(io,0x293fc,h,1);
}
static void phase(uint32_t ctx,uint32_t p,const StockIo *io) { io_w32(io,PHASE,p); render(ctx,io); }
static void pick(uint32_t ctx,uint32_t d,const StockIo *io) {
    if(fault(io)) { phase(ctx,ASSIGN_CHANGED,io); return; } /* recovery must be explicitly selected */
    io_w32(io,DEST,d);
    uint32_t a=binding(d),present=d<3?io_r32(io,a):IO_R8(io,a);
    if(d>=3 && IO_R8(io,FS+1)&(1u<<(d-3))) present=1;
    if(live_owner(d,io)!=io_r32(io,OWNER) || !present) { phase(ctx,ASSIGN_EMPTY,io); return; }
    for(uint32_t i=0;i<4;i++) io_w32(io,snapshot[i],io_r32(io,a+4*i));
    io_w32(io,MODEL,current_model(group(d,io),io));
    io_w32(io,BLOCKED,IO_R8(io,FS+1));
    phase(ctx,ASSIGN_CONFIRM,io);
}
static uint32_t unchanged(uint32_t d,const StockIo *io) {
    if(fault(io) || live_owner(d,io)!=io_r32(io,OWNER)) return 0;
    for(uint32_t i=0;i<4;i++) if(io_r32(io,snapshot[i])!=io_r32(io,binding(d)+4*i)) return 0;
    return current_model(group(d,io),io)==io_r32(io,MODEL) && (d<3 || IO_R8(io,FS+1)==io_r32(io,BLOCKED));
}
static void confirm(uint32_t ctx,const StockIo *io) {
    uint32_t p=io_r32(io,PHASE),d=io_r32(io,DEST),ok=0;
    STOCK_CALL0(io,0x5c0e2);
    if(valid(ctx,io)) {
        if(p==ASSIGN_RECOVER && fault(io)) {
            for(uint32_t k=0;k<3;k++) io_w32(io,KNOB(k),0);
            io_w32(io,ASSIGN_STATE+80,io_r32(io,OWNER));
            for(uint32_t i=0;i<36;i++) IO_W8(io,FS+i,0);
            IO_W8(io,FS,(uint8_t)io_r32(io,OWNER)); ok=1;
        } else if(p==ASSIGN_CONFIRM && d<5 && unchanged(d,io)) {
            if(d<3) io_w32(io,binding(d),0);
            else { for(uint32_t i=0;i<16;i++) IO_W8(io,binding(d)+i,0);
                   IO_W8(io,FS+1,IO_R8(io,FS+1)&~(1u<<(d-3))); }
            ok=1;
        }
    }
    STOCK_CALL0(io,0x5c102);
    /* Legacy pedal glue routes this call through own_assign_modified: stock
     * dirty notice plus 12 71. Footswitch clients re-read 12 74 after dirty. */
    if(ok) STOCK_CALL(io,0x43d52,1);
    phase(ctx,ok?ASSIGN_DONE:ASSIGN_CHANGED,io);
}
uint32_t assignment_tick(uint32_t ctx,const StockIo *io) {
    if(io_r32(io,PHASE)<ASSIGN_MENU) return 0;
    if(!valid(ctx,io)) { io_w32(io,PHASE,0); assign_restore(ctx,io); return 1; }
    if(io_r32(io,PHASE)==ASSIGN_CONFIRM && !unchanged(io_r32(io,DEST),io)) io_w32(io,PHASE,ASSIGN_CHANGED);
    render(ctx,io); return 1;
}
uint32_t assignment_input(uint32_t ctx,uint32_t event,const StockIo *io) {
    uint32_t e=io_r32(io,event),p=io_r32(io,PHASE);
    /* Match home playback access while editing. Assignment prompts retain their
     * existing event ownership, so a short press cannot act behind a modal. */
    if(!p && e==0x30602) {
        STOCK_CALL(io,0x470c0,STOCK_CALL0(io,0x470c8)==0); return 1;
    }
    if(!p && e==0x40602) {
        io_w32(io,OWNER,STOCK_CALL0(io,0x471d6)); io_w32(io,ROOT,io_r32(io,ctx+EDIT_HEADER));
        if(!io_r32(io,ROOT)) return 1;
        io_w32(io,DEST,0); phase(ctx,ASSIGN_MENU,io); return 1;
    }
    if(p<ASSIGN_MENU) return 0;
    if(!valid(ctx,io)) { io_w32(io,PHASE,0); assign_restore(ctx,io); return 1; }
    if(e==0x30302) { io_w32(io,PHASE,0); assign_restore(ctx,io); return 1; }
    if(p==ASSIGN_MENU && e==3 && io_r32(io,event+4)) {
        uint32_t d=io_r32(io,DEST),max=fault(io)?2:1;
        d=(int32_t)io_r32(io,event+4)>0?(d>=max?0:d+1):(d==0?max:d-1);
        io_w32(io,DEST,d); render(ctx,io);
    } else if(e==0x30202) { /* PARA press, separate from rotation */
        if(p==ASSIGN_MENU) {
            uint32_t d=io_r32(io,DEST);
            if(d==0 && !fault(io)) {
                io_w32(io,ASSIGN_STATE+4,255); io_w32(io,ASSIGN_STATE+8,255); io_w32(io,DEST,255);
                io_w32(io,PHASE,1); assign_render(ctx,1,io);
            } else if(d==1 && !fault(io)) phase(ctx,ASSIGN_PICK,io);
            else if(d==2 && fault(io)) phase(ctx,ASSIGN_RECOVER,io);
        } else if(p==ASSIGN_CONFIRM || p==ASSIGN_RECOVER) confirm(ctx,io);
    } else if(p==ASSIGN_PICK) {
        if((e==0x103 || e==0x203 || e==0x303) && io_r32(io,event+4)) pick(ctx,(e>>8)-1,io);
        else if(e==0x10002 || e==0x10102) pick(ctx,e==0x10002?3:4,io);
    }
    return 1; /* consume every other input/refresh: no underlying control action */
}
