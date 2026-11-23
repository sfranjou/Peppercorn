/* A/B footswitch on-pedal feedback and the pedal-side reset (MOD089 draft; region E).
 *
 * Feedback: a press notes a message (kind, switch, tick); the home refresh router (via nds_refuse_home, first in every
 * DRUM mode) shows it in the home title for FS_AB_SHOW ticks, formatting the text once per message, then gives the title
 * back as the CPU-refusal message does (preset name in display mode 0, the router's own text otherwise).
 *   READY       "<parameter name> <value>" (stock name 0x43a44, value text 0x43d36 as on the edit page)
 *   STALE       "FS1 RE-ASSIGN"  (block holds another effect now)
 *   INVALID     "FS1 BAD DATA"   (damaged assignment data blocks the switch)
 *   CLEARED     "FS1 CLEARED"    (reset mode + footswitch)
 *   ALL         "ASSIGN CLEARED" (reset mode + footswitch on damaged data: all knob/foot mappings dropped)
 * Labels clip at about 13 characters (name 7 + space + value).
 *
 * Reset: MOD029's "Reset knob" mode (hold DRUM in Stomp mode; prompt now "Reset knob/FS") also takes a footswitch press:
 * it clears that switch's A/B assignment, or, when the preset's assignment data is damaged, clears every knob and foot
 * mapping and the save barrier (the pedal-side counterpart of host recovery). The press never toggles a block in this mode.
 * Assignment on the pedal, an extension of MOD026's editor flow: edit page, hold DRUM, turn the
 * parameter knob; instead of a Stomp knob press FS1/FS2 -> current value = A (phase 10, "Set B, FSn again"); knobs work
 * normally to dial B; the same footswitch again -> validated A/B binding (model, range, step, A != B) committed for the
 * current preset, preset marked modified, "Assigned; SAVE preset". Damaged assignment data -> phase 11 "Bad data: reset
 * FS". EXIT/DRUM cancel as before. While a phase is active the window's footswitch presses never step presets or toggle.
 * All of this runs in the GUI task (key handling and home refresh). */
#define GP50_CATALOG_DIRECT 1
#pragma GCC optimize("no-jump-tables")
#include "stock_api.h"
#include "fs_ab_target.h"
#include "../../footswitch_ab/host.h"
#include "../../footswitch_ab/stock_adapter.h"
#include "../own/assign_store.h"

#define MSG (FS_AB_STATE + 36u)     /* +0 tick, +4 kind, +5 switch, +6 sequence, +7 shown sequence */
#define FS_AB_SHOW 2000u
#define STOMP_MODE 0x46f20u         /* () -> 1 in Stomp mode */
#define NAME_TEXT 0x43a44u          /* (group, ordinal, parameter, buffer, size) */
#define VALUE_TEXT 0x43d36u         /* (group, parameter, buffer, size): stored value as on the edit page */
#define BLOCK_ORDINAL 0x475d0u
#define CURRENT_PRESET 0x471d6u
typedef uint32_t (*fn5)(uint32_t, uint32_t, uint32_t, uint32_t, uint32_t);
typedef uint32_t (*fn4)(uint32_t, uint32_t, uint32_t, uint32_t);
typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn0)(void);
#define CALL0(a) ((fn0)(uintptr_t)(a))()
#define B8(a) (*(volatile uint8_t *)(uintptr_t)(a))
#define W32(a) (*(volatile uint32_t *)(uintptr_t)(a))

static gp50_fs_ab_state *state(void) { return (gp50_fs_ab_state *)(uintptr_t)FS_AB_STATE; }

void gp50_fs_ab_note(uint32_t kind, uint32_t index) {
    W32(MSG) = W32(GP50_TICK_COUNTER);
    B8(MSG + 4) = (uint8_t)kind; B8(MSG + 5) = (uint8_t)index;
    B8(MSG + 6) = (uint8_t)(B8(MSG + 6) + 1);                     /* last: a new message */
}

/* 1 = this was a reset-mode press (handled, consumed). */
uint32_t gp50_fs_ab_reset_press(uint32_t index) {
    if (index >= 2 || !W32(ASSIGN_META + 8) || CALL0(STOMP_MODE) != 1) return 0;
    uint32_t owner = CALL0(CURRENT_PRESET);
    if (W32(ASSIGN_META + 16) != owner) return 0;                /* reset mode of another preset: stale, ignore */
    W32(ASSIGN_META + 8) = 0;                                    /* one action per reset mode, like a knob */
    irq_guard_enter();
    gp50_fs_ab_state s = *state();
    uint32_t kind = 0;
    if (s.owner == owner && s.metadata_fault) {
        W32(KNOB_VALID(0)) = 0; W32(KNOB_VALID(1)) = 0; W32(KNOB_VALID(2)) = 0;
        *state() = (gp50_fs_ab_state){.owner = (uint8_t)owner};
        kind = FS_AB_MSG_ALL;
    } else if (s.owner == owner && (s.binding[index].valid || s.blocked_mask & (1u << index))) {
        state()->binding[index] = (gp50_fs_ab_binding){0};
        state()->blocked_mask &= (uint8_t)~(1u << index);
        kind = FS_AB_MSG_CLEARED;
    }
    irq_guard_leave();
    if (kind) { ((fn1)(uintptr_t)0x43d52u)(1); gp50_fs_ab_note(kind, index); }
    else gp50_fs_ab_note(FS_AB_MSG_NONE, index);                  /* nothing assigned: just end the prompt */
    return 1;
}

static char *put(char *d, const char *s, char *end) { while (*s && d < end) *d++ = *s++; return d; }

static void message_text(char *text, uint32_t kind, uint32_t index) {
    char *d = text, *end = text + 15;
    if (kind == FS_AB_MSG_READY) {
        gp50_fs_ab_state s = *state();
        const gp50_fs_ab_binding *b = &s.binding[index];
        char name[8], value[8];
        name[0] = value[0] = 0;
        if (b->valid && b->group < 10) {
            ((fn5)(uintptr_t)NAME_TEXT)(b->group, ((fn1)(uintptr_t)BLOCK_ORDINAL)(b->group), b->parameter, (uint32_t)(uintptr_t)name, sizeof name);
            ((fn4)(uintptr_t)VALUE_TEXT)(b->group, b->parameter, (uint32_t)(uintptr_t)value, sizeof value);
        }
        name[7] = value[7] = 0;
        d = put(d, name, end); d = put(d, " ", end); d = put(d, value, end);
    } else if (kind == FS_AB_MSG_ALL) {
        d = put(d, "ASSIGN CLEARED", end);
    } else {
        d = put(d, index ? "FS2 " : "FS1 ", end);
        d = put(d, kind == FS_AB_MSG_STALE ? "RE-ASSIGN" : kind == FS_AB_MSG_INVALID ? "BAD DATA"
                 : kind == FS_AB_MSG_CLEARED ? "CLEARED" : "NOT SET", end);
    }
    *d = 0;
}

/* Home refresh (from nds_refuse_home): 1 = the title is ours this tick (router returns). */
uint32_t gp50_fs_ab_home(uint8_t *ctx) {
    lv_obj_t *label = *(lv_obj_t **)(ctx + 0x34);
    uint8_t seq = B8(MSG + 6), kind = B8(MSG + 4);
    if (kind && W32(GP50_TICK_COUNTER) - W32(MSG) < FS_AB_SHOW) {
        if (B8(MSG + 7) != seq) {
            char text[16];
            message_text(text, kind, B8(MSG + 5));
            mod026_set_text(label, text);
            B8(MSG + 7) = seq;
        }
        return 1;
    }
    if (!kind) return 0;
    B8(MSG + 4) = 0;                                             /* message over: give the title back */
    if (W32(GP50_MOD029_DISPLAY_MODE)) return 0;
    mod026_set_text(label, preset_name_text());
    return 1;
}

/* ---- on-pedal assignment (edit window, MOD026 phases + 10/11) ---- */
#define PHASE (ASSIGN_STATE + 0)        /* +4 group, +8 parameter (255 none), +12 destination, +20 preset, +24 ordinal */
#define A_BITS (FS_AB_STATE + 44u)      /* value A while waiting for B (last 4 bytes of the 48 reserved) */
#define PRESET_IDS_U8 0x200106d3u
uint32_t gp50_fs_ab_value(uint32_t group, uint32_t parameter);   /* fs_ab_value.c (hard float) */
uint32_t assign_render(uint32_t ctx, uint32_t prompt, const StockIo *io);
static const StockIo ui_io;

static uint32_t u32_unaligned(uint32_t a) {
    return B8(a) | (uint32_t)B8(a + 1) << 8 | (uint32_t)B8(a + 2) << 16 | (uint32_t)B8(a + 3) << 24;
}

/* Footswitch event in the edit window (down = 1 press, 0 release). 1 = consumed by the assignment flow. */
#ifdef GP50_FEATURE_ASSIGNMENT
#include "../components/platform/gp50_features.h"
#endif
uint32_t gp50_fs_ab_editor_foot(uint32_t dlg, uint32_t fs, uint32_t down) {
#ifdef GP50_FEATURE_ASSIGNMENT   /* SDK assignment: a feature modal takes the editor's footswitch keys */
    (void)dlg;
    if (!gp50_features_editor_text_active()) return 0;            /* no modal: stock (the press reaches the hook once) */
    if (down && fs < 2) (void)gp50_features_footswitch(fs);
    return 1;
#endif
    uint32_t phase = W32(PHASE);
    if (!phase) return 0;                                         /* not assigning: stock window behaviour */
    if (!down || fs >= 2) return 1;                               /* releases and other keys: swallowed while assigning */
    uint32_t group = W32(ASSIGN_STATE + 4), parameter = W32(ASSIGN_STATE + 8), owner = CALL0(CURRENT_PRESET);
    if ((phase == 1 || phase == 2) && parameter != 255 && group < 10) {
        W32(A_BITS) = gp50_fs_ab_value(group, parameter);
        W32(ASSIGN_STATE + 12) = 3 + fs;                          /* destination 3/4 = FS1/FS2 (host numbering) */
        W32(PHASE) = 10;
        assign_render(dlg, fs ? 7 : 6, &ui_io);
        return 1;
    }
    if (phase != 10 || W32(ASSIGN_STATE + 12) != 3 + fs) return 1;   /* other switch, or nothing to do: ignore */
    gp50_fs_ab_binding b;
    uint32_t model = u32_unaligned(PRESET_IDS_U8 + 4 * group);
    if (gp50_fs_ab_make(&b, (uint8_t)group, (uint8_t)parameter, model, W32(A_BITS), gp50_fs_ab_value(group, parameter),
                        gp50_fs_ab_stock_validate, (void *)&ui_io) != GP50_FS_AB_READY) return 1;   /* A == B etc.: keep waiting */
    irq_guard_enter();
    gp50_fs_ab_state s = *state();
    uint32_t ok = 0;
    if (s.owner == owner && s.metadata_fault) ok = 0;
    else {
        if (s.owner != owner) s = (gp50_fs_ab_state){.owner = (uint8_t)owner};
        s.binding[fs] = b; s.blocked_mask &= (uint8_t)~(1u << fs);
        *state() = s; ok = 1;
    }
    irq_guard_leave();
    if (!ok) { W32(PHASE) = 11; assign_render(dlg, 8, &ui_io); return 1; }
    ((fn1)(uintptr_t)0x43d52u)(1);                                /* preset modified: SAVE persists the GPAM tail */
    W32(PHASE) = 3;
    assign_render(dlg, 3, &ui_io);
    return 1;
}
