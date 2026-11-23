/* MOD085+: public notification/select adapters. Existing tables remain per-call safe.
 * Admission is linked explicitly, because redirecting 475d8 bypasses its old
 * interior call-site hook at475de. Configuration requires refuse_c. */
#include "remaining_chains_target.c"
/* Share the notification service constants with their C implementation, allowing
 * GCC to specialize direct wrappers without duplicating out-of-line callbacks. */
#include "../../../firmware/reconstructed/nds/host_notify.c"
extern uint32_t nds_adm_select_apply(uint32_t, uint32_t);
static uint32_t admit_select(void *context, uint32_t group, uint32_t ordinal) {
    (void)context;
    return nds_adm_select_apply(group, ordinal);
}
static const ApplyServices APPLY = {&SELECT, &LINK, admit_select, 0};
uint32_t nds_chain_40a42(uint32_t a, uint32_t ignored, uint32_t ctx) {
    (void)ignored; return notify_block_state(a, ctx, &NOTIFY);
}
uint32_t nds_chain_40bbc(uint32_t a, uint32_t b, uint32_t ctx) {
    return notify_two_words(a, b, ctx, &NOTIFY);
}
uint32_t nds_chain_40be8(uint32_t a, uint32_t b, uint32_t ctx) {
    return notify_combined_word(a, b, ctx, &NOTIFY);
}
uint32_t nds_chain_40c10(uint32_t index, uint32_t ignored, uint32_t ctx) {
    (void)ignored; return notify_name(index, ctx, &NOTIFY);
}
uint32_t nds_chain_40c42(uint32_t a, uint32_t ignored, uint32_t ctx) {
    (void)ignored; return notify_one_word(a, ctx, &NOTIFY);
}
uint32_t nds_chain_413f8(uint32_t ignored, uint32_t ctx) {
    (void)ignored; return notify_slot(ctx, &IO, &NOTIFY);
}
uint32_t nds_chain_4145e(uint32_t ptr, uint32_t ctx) {
    return notify_level(ptr, ctx, &IO, &NOTIFY);
}
uint32_t nds_chain_4206a(uint32_t ignored0, uint32_t ignored1, uint32_t ctx) {
    (void)ignored0; (void)ignored1; return notify_chain(ctx, &IO, &NOTIFY);
}
uint32_t nds_chain_420a0(uint32_t group, uint32_t ordinal, uint32_t ctx) {
    return notify_effect_selected(group, ordinal, ctx, &IO, &NOTIFY);
}
uint32_t nds_chain_420d4(uint32_t group, uint32_t parameter, uint32_t ctx) {
    return notify_parameter_changed(group, parameter, ctx, &IO, &NOTIFY);
}
uint32_t nds_chain_42120(uint32_t ignored0, uint32_t ignored1, uint32_t ctx) {
    (void)ignored0; (void)ignored1; return notify_preset_words(ctx, &IO, &NOTIFY);
}
uint32_t nds_chain_427d2(uint32_t ctx) { return notify_dirty_frame(ctx, &IO, &NOTIFY); }
uint32_t nds_chain_452a8(void) { return notify_order_address(); }
uint32_t nds_chain_4578e(uint32_t index) { return notify_preset_word(index, &IO); }
uint32_t nds_chain_45958(void) { return notify_dirty_value(&IO); }
float nds_chain_47602(uint32_t group, uint32_t parameter) {
    return notify_parameter_value(group, parameter, &IO);
}
uint32_t nds_chain_45382(uint32_t group) { return select_current_ordinal(group, &IO); }
uint32_t nds_chain_453ba(void) { return select_cab_link_enabled(&IO); }
uint32_t nds_chain_46bf4(uint32_t group, uint32_t id) { return select_lookup_ordinal(group, id, &IO); }
uint32_t nds_chain_46bfc(void) { return select_cab_link_enabled(&IO); }
uint32_t nds_chain_475d0(uint32_t group) { return select_current_ordinal(group, &IO); }
uint32_t nds_chain_475d8(uint32_t group, uint32_t ordinal) {
    return effect_select_apply(group, ordinal, &IO, &APPLY);
}
uint32_t nds_chain_430b8(uint32_t payload) { return host_effect_select(payload, &IO, &APPLY); }
