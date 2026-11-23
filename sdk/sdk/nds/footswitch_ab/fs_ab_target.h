#ifndef GP50_FS_AB_TARGET_H
#define GP50_FS_AB_TARGET_H
#include <stdint.h>
#include "../own/stock_io.h"
/* A/B footswitch target glue (fs_ab_target.c). FS_AB_STATE: 48 bytes reserved right after the capture cache
 * [0x2001f4a0,0x2001f580); runtime state is 36 bytes (gp50_fs_ab_state). */
#define FS_AB_STATE 0x2001f580u
void gp50_fs_ab_reset(void);
uint32_t gp50_fs_ab_preset_read(uint32_t buffer, uint32_t index, uint32_t length, const StockIo *io);
void gp50_fs_ab_active_replaced(void);
uint32_t gp50_fs_ab_stage_record(uint32_t destination, uint32_t source, uint32_t length, const StockIo *io);
void gp50_fs_ab_press(uint32_t index);
uint32_t gp50_fs_ab_metadata_fault(void);
uint32_t gp50_fs_ab_read_frame(uint8_t *out);
uint32_t gp50_fs_ab_command(const uint8_t *message, uint32_t length);
void nds_adm_footswitch(uint32_t index);
/* On-pedal feedback and reset (fs_ab_ui.c). Message area: FS_AB_STATE + 36 (12 bytes of the 48 reserved). */
enum { FS_AB_MSG_NONE = 6, FS_AB_MSG_READY = 1, FS_AB_MSG_STALE = 2, FS_AB_MSG_INVALID = 3, FS_AB_MSG_CLEARED = 4, FS_AB_MSG_ALL = 5 };
#define KNOB_VALID(k) (0x2001f3f0u + 32u + 16u * (k))   /* ASSIGN_STATE + 32 + 16 k: live knob binding valid word */
void gp50_fs_ab_note(uint32_t kind, uint32_t index);
uint32_t gp50_fs_ab_reset_press(uint32_t index);
uint32_t gp50_fs_ab_home(uint8_t *ctx);   /* CPU-admission gate + stock toggle (sdk/nds/ui/refuse.c) */
#endif
