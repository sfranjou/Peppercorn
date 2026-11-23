/* Experimental reset prefix. The stock tail at 0x4a070 retains CSR operations,
 * final service, PC-zero transfer and original return continuation. No device use. */
#include <stdint.h>
#define MMIO(a) (*(volatile uint32_t *)(uintptr_t)(a))
#define CALL0(a) ((uint32_t (*)(void))(uintptr_t)(a))()
#define CALL1(a,v) ((uint32_t (*)(uint32_t))(uintptr_t)(a))(v)
uint32_t reset_prefix_draft(uint32_t *a2_out) {
 MMIO(0x4000100c) = MMIO(0x4000100c) | 2u;
 MMIO(0x4000100c) = MMIO(0x4000100c) | 0x20u;
 uint32_t saved=MMIO(0x4000100c);
 (void)CALL1(0x6506e,0); (void)CALL0(0x57da4);
 uint32_t cache=CALL0(0x5ea54); (void)CALL1(0x5ea96,cache);
 (void)CALL0(0x5eaa0); (void)CALL0(0x639d6); (void)CALL0(0x639ea);
 MMIO(0x4000d100)=0;
 for(uint32_t a=0x4000d000;a!=0x4000d104;a+=4) MMIO(a)=0;
 MMIO(0x40022000)=(MMIO(0x40022000)&0xff880007u)|0x007ffff8u;
 uint32_t a2=MMIO(0x40022004)&0x80000800u;
 MMIO(0x40022004)=a2|0x7ffff7ffu;
 *a2_out=a2;
 return saved;
}

__asm__("/* entered by j at 49ff6. Stock frame stays live; C frame is unwound first. */\n.section .text.resetshim,\"ax\"\n.global reset_shim_draft\nreset_shim_draft:\n smw.adm $r6,[$sp],$r8,0x2\n addi $sp,$sp,-8\n mov55 $r0,$sp\n jal reset_prefix_draft\n lwi $r2,[$sp]\n sethi $r1,0x7ffff\n addi $r1,$r1,0x7ff\n or $r1,$r1,$r2\n addi $sp,$sp,8\n sethi $r5,0x4000d\n addi $r5,$r5,0x104\n mov55 $r7,$r0\n movi55 $r6,0\n j stock_reset_tail\n");
