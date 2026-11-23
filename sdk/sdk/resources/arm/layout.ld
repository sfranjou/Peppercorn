ENTRY(gp50_loader_tail)
SECTIONS {
 .patch_heap 0x4604 : { *(.patch_heap) }
 .patch_loader 0x5392 : { *(.patch_loader) }
 .patch_tuner 0x8fea : { *(.patch_tuner) }
 .resident 0x11240 : { *(.text.resident_hooks) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
ASSERT(ADDR(.resident)+SIZEOF(.resident)<=0x11ffc,"Resident code exceeds the existing c append sector")
ASSERT(SIZEOF(.patch_loader)==6,"loader patch size")
ASSERT(SIZEOF(.patch_tuner)==4,"tuner patch size")
ASSERT(SIZEOF(.patch_heap)==4,"heap literal size")
ASSERT(SIZEOF(.data)==0 && SIZEOF(.bss)==0,"Resident code must not have initialized or static data")
