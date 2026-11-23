#ifndef GP50_NDS_CATALOG_H
#define GP50_NDS_CATALOG_H
#include <stdint.h>
typedef struct {
 uint8_t (*read8)(void *,uint32_t);
 uint32_t (*read32)(void *,uint32_t);
 void *context;
} CatalogMemory;
/* Host comparison builds read through CatalogMemory; the pedal build (GP50_CATALOG_DIRECT, item 9 phase B)
 * reduces the interface to plain loads so the accessors stay leaf functions with stock-like stack use. */
#ifdef GP50_CATALOG_DIRECT
#define CATALOG_READ8(io,a) ((void)(io),*(const uint8_t *)(uintptr_t)(a))
#define CATALOG_READ32(io,a) ((void)(io),*(const uint32_t *)(uintptr_t)(a))
#else
#define CATALOG_READ8(io,a) ((io)->read8((io)->context,(a)))
#define CATALOG_READ32(io,a) ((io)->read32((io)->context,(a)))
#endif
uint32_t catalog_descriptor(uint32_t,uint32_t,const CatalogMemory *);
uint32_t catalog_group_count(uint32_t,const CatalogMemory *);
uint32_t catalog_public_id_to_ordinal(uint32_t,uint32_t,const CatalogMemory *);
uint8_t catalog_parameter_slot(uint32_t,uint32_t,uint32_t,const CatalogMemory *);
float catalog_parameter_default(uint32_t,uint32_t,uint32_t,const CatalogMemory *);
#endif
