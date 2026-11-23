/* Own effect catalog (item 9 phase C, analysis/firmware/NDS_EFFECT_CATALOG.md section 7). Included by
 * catalog_target.c after the reconstructed stock catalog.c. Region e stays stock; our descriptors live in this
 * segment (catalog_ext_data.h, generated): appended ordinals after each group's stock entries, and overrides of stock
 * ordinals (same public ID). Stock ordinals without an override resolve exactly as before. */
#ifdef CATALOG_EXT_AUTHOR
#include "catalog_ext_author.h"     /* generated: the selected catalog plus author effects */
#else
#include "catalog_ext_data.h"
#endif

static inline __attribute__((always_inline)) const uint8_t *ext_override_of(uint32_t group, uint32_t ordinal) {
    for (uint32_t i = 0; i < EXT_OVERRIDES; i++)
        if (ext_override[i].group == group && ext_override[i].ordinal == ordinal) return ext_override[i].descriptor;
    return 0;
}
/* Our descriptor for (group, ordinal) after clamping, or 0 when the stock entry applies. */
static inline __attribute__((always_inline)) const uint8_t *own_entry(uint32_t group, uint32_t ordinal, const CatalogMemory *io) {
    uint32_t stock = catalog_group_count(group, io);             /* 0: no directory or invalid group */
    if (!stock) return 0;
    if (ordinal >= stock + ext_count[group]) ordinal = 0;        /* stock clamp, over the extended count */
    if (ordinal >= stock) return ext_append[group][ordinal - stock];
    return ext_override_of(group, ordinal);
}
uint32_t own_group_count(uint32_t group, const CatalogMemory *io) {
    uint32_t stock = catalog_group_count(group, io);
    return stock ? stock + ext_count[group] : 0;
}
uint32_t own_descriptor(uint32_t group, uint32_t ordinal, const CatalogMemory *io) {
    const uint8_t *own = own_entry(group, ordinal, io);
    return own ? (uint32_t)(uintptr_t)own : catalog_descriptor(group, ordinal, io);
}
uint32_t own_public_id_to_ordinal(uint32_t group, uint32_t public_id, const CatalogMemory *io) {
    uint32_t count = own_group_count(group, io);
    for (int32_t ordinal = 0; ordinal < (int32_t)count; ordinal++)
        if (CATALOG_READ32(io, own_descriptor(group, (uint32_t)ordinal, io)) == public_id) return (uint32_t)ordinal;
    return 0;
}
uint8_t own_parameter_slot(uint32_t group, uint32_t ordinal, uint32_t parameter, const CatalogMemory *io) {
    uint32_t d = own_descriptor(group, ordinal, io);
    if (d && parameter < CATALOG_READ8(io, d + 8)) return CATALOG_READ8(io, d + 0x24 + 24 * parameter);
    return 0;
}
float own_parameter_default(uint32_t group, uint32_t ordinal, uint32_t parameter, const CatalogMemory *io) {
    uint32_t d = own_descriptor(group, ordinal, io);
    if (d && parameter < CATALOG_READ8(io, d + 8)) {
        union { uint32_t bits; float value; } v = {.bits = CATALOG_READ32(io, d + 0x20 + 24 * parameter)}; return v.value;
    }
    return 1.0f; /* stock loads 1.0 from 0xd5894 for an invalid descriptor/index */
}
