#ifndef GP50_NDS_CATALOG_ACCESSORS_H
#define GP50_NDS_CATALOG_ACCESSORS_H
#include <stdint.h>
#include "catalog.h"
/* Remaining effect-catalog accessors and the public-ID bridges (item 9, analysis/firmware/NDS_EFFECT_CATALOG.md).
 * Groups 4 (CAB) and 9 (N->S) are served by the slot tables, reached through services. */
typedef struct {
 CatalogMemory memory;
 void (*write8)(void *,uint32_t,uint8_t);
 uint32_t (*cab_count)(void *);                 /* 199de */
 uint32_t (*ns_count)(void *);                  /* 19d90 */
 uint32_t (*cab_public_id)(void *,uint32_t);    /* 199e2 */
 uint32_t (*ns_public_id)(void *,uint32_t);     /* 19d96 */
 uint32_t (*cab_ordinal)(void *,uint32_t);      /* 19c5c */
 uint32_t (*ns_ordinal)(void *,uint32_t);       /* 1a014 */
} CatalogIo;
#ifdef GP50_CATALOG_DIRECT
#define CATALOG_WRITE8(io,a,v) ((void)(io),*(uint8_t *)(uintptr_t)(a)=(v))
#else
#define CATALOG_WRITE8(io,a,v) ((io)->write8((io)->memory.context,(a),(v)))
#endif
uint8_t catalog_group_total(const CatalogIo *);
uint32_t catalog_public_id_of(uint32_t,uint32_t,const CatalogIo *);
uint8_t catalog_descriptor_flag_byte(uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_descriptor_word4(uint32_t,uint32_t,const CatalogIo *);
uint8_t catalog_parameter_count(uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_parameter_index_of_slot(uint32_t,uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_parameter_record(uint32_t,uint32_t,uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_effect_name(uint32_t,uint32_t,uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_parameter_name(uint32_t,uint32_t,uint32_t,uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_bridge_count(uint32_t,const CatalogIo *);
uint32_t catalog_bridge_public_id(uint32_t,uint32_t,const CatalogIo *);
uint32_t catalog_bridge_ordinal(uint32_t,uint32_t,const CatalogIo *);
#endif
