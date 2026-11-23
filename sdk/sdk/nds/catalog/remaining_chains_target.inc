/* Next-batch adapters; NOT included in a released or reviewed image yet.
 * Include after chains_target.c in the same translation unit, so the existing
 * target IO/PARAM/NOTIFY tables remain shared and reentrant. Do not compile this
 * file as a separate translation unit or manufacture another service table.
 * These are the stock public signatures in the reconstructed headers. Actual
 * entry redirections and composed caller checks remain required before release.
 * No new command/feature: existing parameter/selection/notification behavior.
 */
uint32_t nds_chain_43a62(uint32_t group, uint32_t parameter) {
    return parameter_storage_index(group, parameter, &IO);
}
void nds_chain_43ac0(uint32_t group, uint32_t parameter, float value) {
    parameter_store(group, parameter, value, &IO);
}
void nds_chain_43d52(uint32_t value) {
    preset_mark_dirty((uint8_t)value, &IO);
}
uint32_t nds_chain_43a32(uint32_t group, uint32_t ordinal) {
    return effect_parameter_count(group, ordinal, &IO);
}
void nds_chain_45396(uint32_t group, uint32_t ordinal) {
    effect_record_selection(group, ordinal, &IO);
}
uint32_t nds_chain_43a80(uint32_t group, uint32_t storage) {
    return parameter_visible_index(group, storage, &IO);
}
uint32_t nds_chain_476e4(uint32_t group, uint32_t parameter,
                         float value, uint32_t notify) {
    return effect_parameter_apply(group, parameter, value, notify, &IO, &PARAM);
}
uint32_t nds_chain_427f8(void) {
    return host_notify_dirty(&IO, &NOTIFY);
}
/* The compared effect-link C already performs these private operations inline.
 * Expose the original leaf entries for any retained callers in a later batch.
 * The stored-parameter accessor consumes a storage slot, not a visible index.
 */
uint32_t nds_chain_44cb8(void) {
    return CATALOG_READ8(&IO.catalog.memory, LINK_BLOCKED_MODE);
}
uint32_t nds_chain_46fa2(void) {
    return nds_chain_44cb8();
}
uint32_t nds_chain_45744(uint32_t group) {
    return group < 10 ? CATALOG_READ8(&IO.catalog.memory, ORDINAL_CACHE + group) : 0;
}
uint32_t nds_chain_45944(uint32_t group) {
    /* GP-0xf68 + 0xb = 0x200106fb = PARAMETER_VALUES. The constant already
     * includes the stock final +0xb; do not add it a second time. */
    return PARAMETER_VALUES + 32u * group;
}
float nds_chain_456cc(uint32_t group, uint32_t slot) {
    uint32_t address = PARAMETER_VALUES + 4u * (8u * group + slot);
    union { uint32_t bits; float value; } result = {.bits = 0};
    for (uint32_t i = 0; i < 4; ++i)
        result.bits |= (uint32_t)CATALOG_READ8(&IO.catalog.memory, address + i) << (8u * i);
    return result.value;
}
