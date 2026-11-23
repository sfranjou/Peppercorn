/* Coprocessor (DSP) part of the admission prediction, table v4+ (ADM_WITH_DSP; analysis/firmware/
 * COPRO_BUDGET.md). Included by admission.c and refuse.c after admission_table.h. Thousandths of the
 * DSP proxy (deadline measured ~1.025): base + enabled DST/AMP/EQ by id (unknown +ADM_DSP_UNKNOWN,
 * sets *unknown) + any cab + any N->S slot; N->S on replaces AMP and CAB. Group `og` uses id `oid`
 * (og >= 10: none). mData mask/ids unaligned: byte loads only. */
#ifndef ADM_DSP_H
#define ADM_DSP_H
#if ADM_WITH_DSP
static uint32_t adm_u32(const volatile uint8_t *p) {
 return (uint32_t)p[0] | (uint32_t)p[1] << 8 | (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}
static uint32_t adm_dsp_of(uint32_t mask, uint32_t og, uint32_t oid, uint32_t *unknown) {
 const volatile uint8_t *md = (const volatile uint8_t *)GP50_MDATA_ENABLE_MASK;
 uint32_t est = ADM_DSP_BASE, ntos = mask >> 9 & 1u;
 for (uint32_t k = 0; k < 3u; k++) {
  const struct adm_group *g = &adm_dsp_groups[k];
  if (!(mask >> g->group & 1u) || (ntos && g->group == 3u)) continue;
  uint32_t id = g->group == og ? oid : adm_u32(md + GP50_MDATA_IDS_OFFSET + 4u * g->group), i = 0;
  while (i < g->count && g->rows[i].id != id) i++;
  if (i < g->count) est += g->rows[i].cost;
  else { est += ADM_DSP_UNKNOWN; *unknown = 1; }
 }
 if ((mask >> 4 & 1u) && !ntos) est += ADM_DSP_CAB;
 if (ntos) est += ADM_DSP_NTOS;
 return est;
}
#endif
#endif
