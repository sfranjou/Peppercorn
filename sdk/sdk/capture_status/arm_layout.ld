ENTRY(gp50_capture_early)
gp50_capture_stock_alloc = 0x4635;
gp50_capture_stock_free = 0x4693;
gp50_stock_reply = 0x8d11;
gp50_capture_stock_lookup = 0x6f35;
gp50_capture_stock_main = 0x942b;
gp50_capture_stock_tuner = 0x11255;
gp50_capture_init_continue = 0x6589;
gp50_capture_loader_continue = 0x532d;
gp50_capture_store_continue = 0x7a1d;
gp50_capture_delete_continue = 0x6f87;
gp50_capture_metadata_continue = 0x70e7;
gp50_capture_dispatch_done = 0x64ed;
gp50_capture_previous_gate = 0x11931;
gp50_capture_stock_erase_ram = 0x4c4f;
gp50_capture_stock_program_ram = 0x4c63;
SECTIONS {
 .capture_aux 0x11b1c : { KEEP(*(.text.capture_results)) *(.text.gp50_capture_arm_request) *(.text.gp50_capture_arm_dispatch) *(.text.gp50_capture_arm_boot) *(.text.gp50_capture_arm_write_fault) *(.text.gp50_capture_arm_startup) *arm_lifecycle.o(.text* .rodata*) *(.text.gp50_capture_record_preflight) *(.text.gp50_capture_arm_copy) *(.text.gp50_capture_arm_begin) *(.text.gp50_capture_arm_bypass) }
 .capture 0x106a0 : { *(.text.capture_hooks) KEEP(*(.text.gp50_capture_overlay_call)) *(.text*) *(.rodata*) }
 .data : { *(.data*) }
 .bss : { *(.bss*) *(COMMON) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
ASSERT(ADDR(.capture)+SIZEOF(.capture)<=0x10ffc,"capture code exceeds first reservation")
ASSERT(SIZEOF(.data)==0 && SIZEOF(.bss)==0,"resident capture has no static data")

ASSERT(ADDR(.capture_aux)+SIZEOF(.capture_aux)<=0x11ffc,"capture auxiliary exceeds second reservation")
