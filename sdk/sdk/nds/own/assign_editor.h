#ifndef GP50_NDS_ASSIGN_EDITOR_H
#define GP50_NDS_ASSIGN_EDITOR_H
#include <stdint.h>
#include "stock_io.h"
#include "assign_store.h"
/* MOD026 editor-side knob assignment (assembly work/ui_assignment_v2): in the effect editor (window 4),
 * DRUM starts assignment, the parameter knob picks the source parameter, DRUM confirms, a Stomp knob picks the
 * destination, DRUM commits (v3 assign_commit). Phase in ASSIGN_STATE+0: 0 idle, 1 source, 2 destination, 3 assigned;
 * +4 group, +8 parameter, +12 destination knob (255 = none), +16 candidate group, +20 preset, +24 model ordinal.
 * The window open/close wrappers (0x16e000/0x16e01c) replay stock prologues and stay assembly. */
#ifdef GP50_CATALOG_DIRECT
/* Texts as in MOD054's flash (0x16eb90.. ; MOD029 changed prompt 3 from v2's "Assigned! EXIT to leave"). */
#ifdef GP50_FS_AB   /* A/B footswitch assignment (phase 10 = wait for B on footswitch dest-3, 11 = damaged data) */
static const char *const ASSIGN_PROMPT[9] = { 0, "Turn parameter knob", "Turn destination knob", "Assigned; SAVE preset",
                                              "Selected; DRUM next", "Selected; DRUM saves", "Set B, FS1 again",
                                              "Set B, FS2 again", "Bad data: reset FS" };
#define ASSIGN_PROMPT_LAST 8u
#else
static const char *const ASSIGN_PROMPT[6] = { 0, "Turn parameter knob", "Turn destination knob", "Assigned; SAVE preset",
                                              "Selected; DRUM next", "Selected; DRUM saves" };
#endif
#define PROMPT_TEXT(n) ((uint32_t)(uintptr_t)ASSIGN_PROMPT[n])
uint32_t assign_commit(uint32_t context, uint32_t event, const StockIo *io);
#define COMMIT_CALL(io, ctx, ev) assign_commit((ctx), (ev), (io))
#else
#define PROMPT_TEXT(n) ((n) == 1 ? 0x16eb90u : (n) == 2 ? 0x16eba4u : (n) == 3 ? 0x16ebbau : (n) == 4 ? 0x16ebd2u : 0x16ebe6u)
#define COMMIT_CALL(io, ctx, ev) STOCK_CALL((io), 0x16eec4, (ctx), (ev))   /* host: v3 commit as linked in MOD054 */
#endif
#define EDIT_GROUP 0x90u     /* ctx + 0x90: selected block index; ctx + 0x80 + block: its group */
#define EDIT_HEADER 0xe0u    /* ctx + 0xe0: header label */
uint32_t assign_set_text(uint32_t label, uint32_t text, const StockIo *io);          /* 0x16e52c: set only if changed */
uint32_t assign_restore(uint32_t ctx, const StockIo *io);                            /* 0x16e39c */
uint32_t assign_render(uint32_t ctx, uint32_t prompt, const StockIo *io);            /* 0x16e46c */
uint32_t assign_render_current(uint32_t ctx, const StockIo *io);                     /* 0x16e3f4 */
uint32_t assign_editor_hold(uint32_t ctx, const StockIo *io);                               /* 0x16e034: 0 consume, 1 pass */
uint32_t assign_editor_back(uint32_t ctx, uint32_t event, const StockIo *io);        /* 0x16e06c */
uint32_t assign_editor_drum(uint32_t ctx, uint32_t event, const StockIo *io);        /* 0x16e0d8: 0 consumed, 1 pass */
uint32_t assign_editor_encoder(uint32_t ctx, uint32_t event, const StockIo *io);     /* 0x16e1e2 */
uint32_t assign_para(uint32_t ctx, uint32_t event, const StockIo *io);               /* 0x16e302 */
uint32_t assign_page(uint32_t ctx, uint32_t event, const StockIo *io);               /* 0x16e360 */
#endif
