/* Retained MOD154 wrapper. After the original callback r0 is overwritten
 * and r1-r3 are reloaded by the stock continuation. */
.syntax unified
.cpu cortex-m4
.thumb

.section .stock_gr_patch,"ax",%progbits
    b.w stock_gr_observe

.section .stock_gr_observer,"ax",%progbits
.thumb_func
stock_gr_observe:
    ldr r4, [r4, #20]
    mov r1, r5
    blx r4
    mrs r3, APSR
    ldr r2, =0x10000091
    cmp r4, r2
    beq gate
    ldr r2, =0x10000c9d
    cmp r4, r2
    beq comp
    ldr r2, =0x10000cc9
    cmp r4, r2
    bne done
    ldr r2, =0x100021c8
    b pre
comp:
    ldr r2, =0x10001640
pre:
    ldr r1, =stock_gr_pre
    ldr r0, =stock_gr_pre_generation
    b snapshot
gate:
    ldr r2, =0x10000a6c
    ldr r1, =stock_gr_gate
    ldr r0, =stock_gr_gate_generation
snapshot:
    ldr r0, [r0]
    str r0, [r1, #4]
    movs r0, #0
    cmp r5, #64
    bne publish
    ldr r0, [sp]
    ldrb r0, [r0]
    cbz r0, publish
    ldr r0, [r2]
    str r0, [r1, #8]
    mov r0, r4
publish:
    str r0, [r1]
done:
    msr APSR_nzcvq, r3
    b.w stock_gr_continue
.ltorg
.section .note.GNU-stack,"",%progbits
