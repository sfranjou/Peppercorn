ENTRY(gp50_dispatch_gate2)
gp50_stock_reply = 0x8d11;
SECTIONS {
 .patch_dispatch2 0x6472 : { *(.patch_dispatch2) }
 .lease 0x11930 : { *(.text.lease_hooks) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
ASSERT(ADDR(.lease)+SIZEOF(.lease)<=0x11ffc,"Lease reply exceeds the c append sector")
ASSERT(SIZEOF(.patch_dispatch2)==4,"dispatch BL size")
ASSERT(SIZEOF(.data)==0 && SIZEOF(.bss)==0,"no static data")
