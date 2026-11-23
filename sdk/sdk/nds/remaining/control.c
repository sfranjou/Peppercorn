/* Final-image integration source; focused synthetic studies in REMAINING_CONTROL_TARGET_DRAFT.md. */
#include <stdint.h>

/* Signature inferred from 49d92. External declarations require linker symbols bound to
 * unhooked stock addresses, verified in the final link map and disassembly. */
extern uint32_t stock_queue_receive(uint32_t queue, uint16_t *event, uint32_t timeout);
extern void stock_audio_notification(void);

/* Initialize the otherwise indeterminate first event. The real non-null queue
 * wrapper clears this halfword before receiving; the null-queue early return
 * leaves it unchanged. Queue construction specifies two-byte items. */
__attribute__((noreturn)) void draft_audio_task(void)
{
    uint16_t event = 0;
    for (;;) {
        uint32_t object = *(volatile uint32_t *)(uintptr_t)0x20004b98u;
        uint32_t queue = *(volatile uint32_t *)(uintptr_t)(object + 4u);
        (void)stock_queue_receive(queue, &event, 10u);
        if (event == 2u)
            stock_audio_notification();
    }
}

/* Fatal routine is expected not to return. Guard the return case with a terminal
 * loop instead of falling into unrelated stock code. Requires a conscious change
 * decision and stock fatal routine ABI verification before integration. */
extern void stock_fatal(uint32_t file, uint32_t line, uint32_t expr, uint32_t detail);
__attribute__((noreturn)) void draft_power_assert(void)
{
    stock_fatal(0xd432cu, 0xfbu, 0xd44b4u, 0x168234u);
    for (;;) { __asm__ volatile ("" ::: "memory"); }
}
__attribute__((noreturn)) void draft_protocol_assert(void)
{
    stock_fatal(0x140a78u, 0xaf9u, 0x140ad4u, 0x140aa8u);
    for (;;) { __asm__ volatile ("" ::: "memory"); }
}
