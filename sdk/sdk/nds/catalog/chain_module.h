/* Shared prelude of the pedal builds of the effect chains (item 9, MOD052): the compared sources compiled with plain
 * loads/stores (GP50_CATALOG_DIRECT). With the own catalog (CATALOG_EXT, MOD051+) the two base-layer lookups that the
 * chains call directly resolve through the own catalog, as the catalog wrappers do (nds_cat_198a2, nds_cat_198f2);
 * same signatures, so the renamed prototypes in catalog.h match catalog_own.h. One file per module: the modules'
 * private helpers share names (r8, le32, ...). */
#ifndef GP50_CHAIN_MODULE_H
#define GP50_CHAIN_MODULE_H
#define GP50_CATALOG_DIRECT 1
/* No switch jump tables: GCC places them inside .text, which the C disassembly round-trip gate (tier a) refuses. */
#pragma GCC optimize("no-jump-tables")
#include "catalog_config.h"
#if CATALOG_EXT
#define catalog_parameter_slot own_parameter_slot
#define catalog_parameter_default own_parameter_default
#endif
#endif
