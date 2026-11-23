.syntax unified
.cpu cortex-m4
.thumb
/* Successor-only hooks. Original bodies/continuations are fixed by the linker;
 * the component builder must pin every displaced byte before applying them. */
.section .text.capture_hooks,"ax",%progbits
.macro func name
.global \name
.thumb_func
\name:
.endm
/* Reset vector's SystemInit literal points here. Clear readiness before stock
 * SystemInit can enable IRQs; full reset occurs after scatter/heap startup. */
func gp50_capture_early
    ldr r0,=0x20003d04
    mov.w r1,#0
    str r1,[r0]
    str r1,[r0,#4]
    dsb sy
    ldr r0,=0x8ef5
    bx r0
func gp50_capture_boot_hook
    push {r0-r4,lr}
    mrs r4,APSR
    bl gp50_capture_arm_boot
    msr APSR_nzcvq,r4
    pop {r0-r4,lr}
    b.w gp50_capture_stock_main
/* BL at shared lookup site; r4 retains stock group throughout 0x6584. */
func gp50_capture_lookup_hook
    mov r1,r4
    b.w gp50_capture_lookup_call
/* Before group init (including fallback) and before replacing the RAM overlay. */
func gp50_capture_init_hook
    push {r0-r4,lr}
    mrs r4,APSR
    bl gp50_capture_retire_group
    msr APSR_nzcvq,r4
    pop {r0-r4,lr}
    push {r2,r3,r4,lr}
    mov r4,r0
    b.w gp50_capture_init_continue
func gp50_capture_loader_hook
    push {r0-r4,lr}
    mrs r4,APSR
    bl gp50_capture_retire_group
    msr APSR_nzcvq,r4
    pop {r0-r4,lr}
    push {r4,r5,r6,lr}
    mov r6,r0
    b.w gp50_capture_loader_continue
func gp50_capture_tuner_hook
    push {r0-r4,lr}
    mrs r4,APSR
    bl gp50_capture_retire_all
    msr APSR_nzcvq,r4
    pop {r0-r4,lr}
    b.w gp50_capture_stock_tuner
/* Four-argument AAPCS functions, with no stack arguments on the traced roots.
 * Keep the original body's frame/return behavior by BL into relocated prefix.
 * Return value r0 survives leave; callee-saved registers unwind normally. */
.macro writer name,body
func \name
    push {r0-r4,lr}
    bl gp50_capture_writer_enter
    pop {r0-r3}
    bl \body
    mov r4,r0
    bl gp50_capture_writer_leave
    mov r0,r4
    pop {r4,pc}
.endm
writer gp50_capture_store_hook,.Lstore
writer gp50_capture_delete_hook,.Ldelete
writer gp50_capture_metadata_hook,.Lmetadata
.Lstore:
    push {r3,r4,r5,lr}
    mov r4,r3
    b.w gp50_capture_store_continue
.Ldelete:
    mov r1,r0
    mov.w r0,#-1
    b.w gp50_capture_delete_continue
.Lmetadata:
    push {r4,lr}
    mov.w r2,#-1
    b.w gp50_capture_metadata_continue
func gp50_capture_dispatch_hook
    push {r0-r3,r7,lr}
    mrs r7,APSR
    cmp r5,#12
    blo .Lprevious
    ldrb r0,[r4,#3]
    cmp r0,#1
    bne .Lprevious
    add r0,r4,#4
    sub r1,r5,#4
    bl gp50_capture_arm_dispatch
    cmp r0,#0
    beq .Lprevious
    msr APSR_nzcvq,r7
    pop {r0-r3,r7,lr}
    b.w gp50_capture_dispatch_done
.Lprevious:
    msr APSR_nzcvq,r7
    pop {r0-r3,r7,lr}
    b.w gp50_capture_previous_gate
.ltorg
/* The stock wrappers keep PRIMASK masked across these two RAM calls and
 * mapping is restored by the original veneer before it returns. Inspect any
 * nonzero result before the caller can restore PRIMASK. Keep its exact r0.
 * This reports failures; it does not establish physical NOR idle semantics. */
.section .text.capture_results,"ax",%progbits
/* Erase result (2026-11-08): the stock sector erase returns -1 when its status-poll iteration limit expires, which
 * is normal for a slow NOR erase that then completes. No stock caller of 0x7b30 tests r0 (all seven call sites), and
 * the following program call first waits for flash idle. Treating it as a fault latched every capture upload into
 * "capture unavailable until power cycle" (MOD145 hardware, 2026-11-08). Match stock: return r0 unchanged, no fault.
 * Program results (checked by stock 0x7b6c) still fault; a bad erase also fails program or the per-record checks. */
func gp50_capture_erase_result
    push {r4,lr}
    bl gp50_capture_stock_erase_ram
    pop {r4,pc}
func gp50_capture_program_result
    push {r4,lr}
    bl gp50_capture_stock_program_ram
.Lwrite_result:
    mov r4,r0
    cbz r0,.Lwrite_ok
    ldr r0,=0x20003ce8
    bl gp50_capture_arm_write_fault
.Lwrite_ok:
    mov r0,r4
    pop {r4,pc}
.ltorg
.section .note.GNU-stack,"",%progbits
