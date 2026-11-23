/* One overlay in its group's execution slot. SLOT_BASE and SLOT_SIZE come from the build
 * script (analysis/firmware/DSP_LOADER.md slot table). The payload (.text/.rodata/.data) is
 * copied by the loader; .bss follows inside the slot, which the loader has cleared. */
MEMORY { SLOT (rwx) : ORIGIN = SLOT_BASE, LENGTH = SLOT_SIZE }
SECTIONS {
  .payload : {
    __payload_start = .;
    KEEP(*(.text.gp50_init)) KEEP(*(.text.gp50_process))
    *(.text .text.*) *(.rodata .rodata.*) *(.data .data.*)
    . = ALIGN(4);
    __payload_end = .;
  } > SLOT
  .bss (NOLOAD) : { __bss_start = .; *(.bss .bss.* COMMON) . = ALIGN(4); __bss_end = .; } > SLOT
  /DISCARD/ : { *(.ARM.exidx*) *(.ARM.extab*) *(.comment) *(.ARM.attributes) *(.note*) }
}
