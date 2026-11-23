ENTRY(gp50_normalizer_hook)
gp50_stock_reply = 0x8d11;
SECTIONS {
 .patch_startup 0x943e : { *(.patch_startup) }
 .patch_dispatch 0x6472 : { *(.patch_dispatch) }
 .patch_normalizer 0xe7ce : { *(.patch_normalizer) }
 .telemetry 0x11000 : { *(.text.hooks) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
ASSERT(SIZEOF(.telemetry)<0xffc,"Telemetry code exceeds reviewed append sector")
ASSERT(SIZEOF(.patch_startup)==4,"startup BL size")
ASSERT(SIZEOF(.patch_dispatch)==4,"dispatch BL size")
ASSERT(SIZEOF(.patch_normalizer)==10,"RAM veneer size")
