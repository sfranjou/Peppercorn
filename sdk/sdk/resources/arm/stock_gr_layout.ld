stock_gr_continue = 0x53fa;
gp50_stock_reply = 0x8d11;
stock_gr_gate = 0x20003c14;
stock_gr_pre = 0x20003c20;
stock_gr_gate_generation = 0x20003b5c;
stock_gr_pre_generation = 0x20003b6c;
SECTIONS {
 .stock_gr_patch 0x53f4 : { *(.stock_gr_patch) }
 .stock_gr_take 0xfee8 : { *(.text.stock_gr_take) }
 .stock_gr_observer 0xff38 : { *(.stock_gr_observer) }
 .stock_gr_pack : { *(.text.stock_gr_reply) }
 .stock_gr_reply 0x11978 : { *(.text.gp50_lease_reply) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment*) *(.note*) }
}
ASSERT(SIZEOF(.stock_gr_patch) == 4, "stock meter hook width")
ASSERT(ADDR(.stock_gr_take)+SIZEOF(.stock_gr_take) <= 0xff34, "snapshot overflow")
ASSERT(ADDR(.stock_gr_pack)+SIZEOF(.stock_gr_pack) <= 0x10000, "observer and packet pack overflow")
ASSERT(ADDR(.stock_gr_reply)+SIZEOF(.stock_gr_reply) <= 0x11b1c, "reply overflow")
ASSERT(SIZEOF(.data)==0 && SIZEOF(.bss)==0, "no static data")
