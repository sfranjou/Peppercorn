/* GP-50 V1.1.0: ARM-side access to the DSP coprocessor's data cells, for effects in a group
 * that owns a coprocessor program slot (first supported: DST, group 2).
 * Evidence: analysis/firmware/COPRO_EFFECTS.md, DSP_COPROCESSOR.md.
 *
 * Data word n ("D[n]") is the 32-bit word at 0x28000000 + 4n. Cells hold raw 32-bit values;
 * audio and parameters are IEEE float32. The coprocessor program reads them during the block
 * that starts after all process callbacks returned.
 *
 * Contract for a DST-group overlay (what every stock DST overlay does):
 *  - init:    write 0 to the group's enable cell first, then give EVERY cell the program reads
 *             a valid value (the loader clears the program slot, not the data cells);
 *  - process: called for every block, enabled or not; write the parameter cells, then write
 *             the enable cell: 1 when *enable != 0, else 0. Do not touch the sample buffer:
 *             the audio of this group is processed by the coprocessor program.
 *  - only cells inside the group's range (build_effect.py checks literal addresses).
 * Cell numbers come from the effect's program module through the generated "copro_cells.h".
 */
#ifndef GP50_COPRO_H
#define GP50_COPRO_H
#include <stdint.h>

#define GP50_COPRO_DATA_BASE 0x28000000u
#define GP50_COPRO_F(cell) (*(volatile float *)(GP50_COPRO_DATA_BASE + 4u * (cell)))
#define GP50_COPRO_U(cell) (*(volatile uint32_t *)(GP50_COPRO_DATA_BASE + 4u * (cell)))
#endif
