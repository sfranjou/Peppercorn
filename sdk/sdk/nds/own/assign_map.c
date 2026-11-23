/* Instruction-reviewed MOD026 assembly (work/ui_assignment_v2/source.nds: commit, valid_map, home_encoder, home_refresh,
 * editor_tick, home_tick; in MOD054's b, where home_refresh calls the MOD027 name helper and 0x293fc). Compared with the
 * original execution: work/firmware_source/nds_assign_map/verification.json. */
#include "assign_map.h"
#ifdef GP50_ASSIGNMENT_MENU
#include "assignment_menu.h"
#endif
#define PHASE (ASSIGN_STATE + 0)

uint32_t assign_publish(uint32_t ctx, uint32_t event, const StockIo *io) {
    (void)ctx; (void)event;
    uint32_t preset = STOCK_CALL0(io, 0x471d6);
    if (preset != io_r32(io, ASSIGN_STATE + 20)) return 0;           /* preset changed during assignment */
    if (preset != io_r32(io, ASSIGN_STATE + 80)) {                   /* first binding of this preset: drop old ones */
        io_w32(io, ASSIGN_STATE + 80, preset);
        io_w32(io, ASSIGN_STATE + 32, 0); io_w32(io, ASSIGN_STATE + 48, 0); io_w32(io, ASSIGN_STATE + 64, 0);
    }
    uint32_t group = io_r32(io, ASSIGN_STATE + 4);
    if (STOCK_CALL(io, 0x475d0, group) != io_r32(io, ASSIGN_STATE + 24)) return 0;   /* model changed */
    if (!(io_r32(io, ASSIGN_STATE + 8) < STOCK_CALL(io, 0x46c2a, io_r32(io, ASSIGN_STATE + 4)))) return 0;
    uint32_t knob = io_r32(io, ASSIGN_STATE + 12);
    if (knob >= 3) return 0;
    uint32_t m = ASSIGN_STATE + 32 + 16 * knob;
    io_w32(io, m, 0);                                                /* publish valid last */
    io_w32(io, m + 4, io_r32(io, ASSIGN_STATE + 4)); io_w32(io, m + 8, io_r32(io, ASSIGN_STATE + 8));
    io_w32(io, m + 12, io_r32(io, ASSIGN_STATE + 24)); io_w32(io, m, 1);
    return 1;
}

uint32_t assign_valid_map(uint32_t knob, const StockIo *io) {
    if (knob >= 3 || STOCK_CALL0(io, 0x46f20) != 1) return 0;
    uint32_t m = ASSIGN_STATE + 32 + 16 * knob;
    if (!io_r32(io, m)) return 0;
    if (STOCK_CALL0(io, 0x471d6) != io_r32(io, ASSIGN_STATE + 80)) {   /* bindings belong to another preset */
        io_w32(io, ASSIGN_STATE + 32, 0); io_w32(io, ASSIGN_STATE + 48, 0); io_w32(io, ASSIGN_STATE + 64, 0);
        return 0;
    }
    uint32_t group = io_r32(io, m + 4);
    if (group < 10 && STOCK_CALL(io, 0x475d0, group) == io_r32(io, m + 12)
        && io_r32(io, m + 8) < STOCK_CALL(io, 0x46c2a, io_r32(io, m + 4))) return m;
    io_w32(io, m, 0);                                                /* stale: invalidate */
    return 0;
}

#ifdef GP50_FEATURES
uint32_t gp50_features_knob(uint32_t index, int32_t steps);   /* SDK ABI 3 knob events (components/platform) */
#endif
uint32_t assign_home_knob(uint32_t ctx, uint32_t event, const StockIo *io) {
    uint32_t m = assign_valid_map(IO_R8(io, event + 1) - 1, io);
    if (m) { STOCK_CALL(io, 0x4772c, io_r32(io, m + 4), io_r32(io, m + 8), io_r32(io, event + 4)); return 0; }   /* knob nudge */
    uint32_t knob = IO_R8(io, event + 1);
#ifdef GP50_FEATURES   /* unassigned knob: SDK features first, then the stock Master / BPM / P-VOL */
    if (knob >= 1 && knob <= 3 && gp50_features_knob(knob - 1, (int32_t)io_r32(io, event + 4))) return 0;
#endif
    return STOCK_CALL(io, knob == 1 ? 0x218a0 : knob == 2 ? 0x21a38 : 0x21860, ctx, event);   /* stock Master / BPM / P-VOL */
}

uint32_t assign_home_refresh(uint32_t ctx, const StockIo *io) {
    uint32_t root = io_r32(io, ctx + 0x98);
    if (root != io_r32(io, ASSIGN_STATE + 88)) { io_w32(io, ASSIGN_STATE + 88, root); io_w32(io, ASSIGN_STATE + 92, 0); }
    uint32_t before = io_r32(io, ASSIGN_STATE + 92), mapped = 0;
    LOCAL_BUFFER(io, name, 16);
    LOCAL_BUFFER(io, value, 16);
    for (uint32_t k = 0; k < 3; k++) {
        uint32_t widget = io_r32(io, ctx + 0x98 + 4 * k), m = assign_valid_map(k, io);
        if (m) {                                                     /* assigned: parameter name and value */
            mapped |= 1u << k;
            NAME_CALL(io, io_r32(io, m + 4), io_r32(io, m + 8), name, 16);
            STOCK_CALL(io, 0x46c4a, io_r32(io, m + 4), io_r32(io, m + 8), value, 16);
            IO_W8(io, name + 15, 0); IO_W8(io, value + 15, 0);
            assign_set_text(STOCK_CALL(io, 0x2da52, STOCK_CALL(io, 0x2da52, widget, 0), 0), name, io);
            assign_set_text(STOCK_CALL(io, 0x2da52, widget, 2), value, io);
            STOCK_CALL(io, 0x293fc, STOCK_CALL(io, 0x2da52, widget, 1), 1);
        } else if (before & 1u << k) {                               /* just cleared: stock label and value */
            uint32_t text = STOCK_CALL(io, 0x15f0c, k + 12);
            assign_set_text(STOCK_CALL(io, 0x2da52, STOCK_CALL(io, 0x2da52, widget, 0), 0), text, io);
            STOCK_CALL(io, 0x293fc, STOCK_CALL(io, 0x2da52, widget, 1), 1);
            STOCK_CALL(io, k == 0 ? 0x21ac2 : k == 1 ? 0x219d0 : 0x21a8c, ctx, k == 0 ? 0 : 1);
        }
    }
    io_w32(io, ASSIGN_STATE + 92, mapped);
    return mapped;
}

#ifdef GP50_FEATURE_ASSIGNMENT
void gp50_features_screen_ctx(uint32_t screen, uint32_t ctx);
#endif
#ifdef GP50_FEATURE_AUTO_WAH
#include "../components/gp50.h"

int32_t gp50_features_expression_config(void);

static uint32_t expression_visibility(uint32_t obj, uint32_t visible, const StockIo *io) {
    if (!obj) return 0;
    uint32_t hidden = io_r32(io, obj + 0x1c) & 1u;
    if (hidden != visible) return 0;
    if (visible) STOCK_CALL(io, 0x293fc, obj, 1);
    else STOCK_CALL(io, 0x29858, obj, 1);
    return 1;
}

static void expression_page_count(uint32_t ctx, uint32_t pages, uint32_t rows, const StockIo *io) {
    if (IO_R8(io, ctx + 0xe5) == pages && IO_R8(io, ctx + 0xe6) == rows) return;
    IO_W8(io, ctx + 0xe5, pages);
    IO_W8(io, ctx + 0xe6, rows);
    uint32_t indicator = io_r32(io, ctx + 0xdc);
    if (indicator) STOCK_CALL(io, 0x27806, indicator, pages, IO_R8(io, ctx + 0xe4), 0);
}

static uint32_t expression_tile(uint32_t rows, const char *name, uint32_t maximum, const StockIo *io) {
    uint32_t tile = STOCK_CALL(io, 0x27498, rows, (uint32_t)(uintptr_t)name);
    if (tile) {
        STOCK_CALL(io, 0x27634, tile, 48, 20);
        STOCK_CALL(io, 0x276da, tile, 0, maximum);
    }
    return tile;
}

static void expression_release_label(uint32_t tile, uint32_t ms, const StockIo *io) {
    LOCAL_BUFFER(io, value, 8);
    uint32_t length = 0;
    for (uint32_t place = 1000; place; place /= 10) {
        uint32_t digit = ms / place;
        ms %= place;
        if (digit || length || place == 1) IO_W8(io, value + length++, '0' + digit);
    }
    IO_W8(io, value + length++, ' ');
    IO_W8(io, value + length++, 'm');
    IO_W8(io, value + length++, 's');
    IO_W8(io, value + length, 0);
    uint32_t label = STOCK_CALL(io, 0x2da52, tile, 2);
    if (label) assign_set_text(label, value, io);
}

static void expression_tiles(uint32_t ctx, uint32_t last_page, const StockIo *io) {
    if (IO_R8(io, ctx + 0x90) != GP50_BLOCKS) return;
    uint32_t rows = io_r32(io, ctx + 0x28);
    if (!rows) return;
    uint32_t count = STOCK_CALL(io, 0x2da72, rows);
    if (count < 6 || count > 9) return;
    /* Stock rows are the header, two selectors, Min, Max and Pre/Post. */
    uint32_t position = STOCK_CALL(io, 0x2da52, rows, 5);
    uint32_t engage = count >= 7 ? STOCK_CALL(io, 0x2da52, rows, 6) : 0;
    uint32_t release = count >= 8 ? STOCK_CALL(io, 0x2da52, rows, 7) : 0;
    uint32_t spacer = count >= 9 ? STOCK_CALL(io, 0x2da52, rows, 8) : 0;
    uint32_t enabled = IO_R8(io, ctx + 0x94) == 1;
    uint32_t target = IO_R8(io, ctx + 0x95);
    uint32_t changed = expression_visibility(position, enabled && target == GP50_BLOCKS, io);
    if (!enabled || target >= GP50_BLOCKS) {
        changed |= expression_visibility(engage, 0, io);
        expression_visibility(release, 0, io);
        expression_visibility(spacer, 0, io);
        if (IO_R8(io, ctx + 0xe4) >= (enabled ? 2 : 1)) {
            IO_W8(io, ctx + 0xe4, enabled ? 1 : 0);
            changed = 1;
        }
        expression_page_count(ctx, enabled ? 2 : 1, 6, io);
        if (changed && IO_R8(io, ctx + 0xe4) == 1) {
            uint32_t first = STOCK_CALL(io, 0x2da52, rows, 3);
            if (first) STOCK_CALL(io, 0x2c204, first, 0);
        }
        return;
    }
    int32_t config = gp50_features_expression_config();
    if (config < 0 && count < 9) return;
    if (!engage) engage = expression_tile(rows, "Auto Engage", 1, io);
    if (engage && !release) release = expression_tile(rows, "Release", GP50_EXPRESSION_RELEASE_MAX, io);
    if (release && !spacer) {
        /* Keep a full final page so Release lines up with the left knob. */
        spacer = STOCK_CALL(io, 0x293e0, rows);
        if (spacer) {
            STOCK_CALL(io, 0x2d03e, spacer, 0, 0xfffff); /* stock LVGL all-styles selector */
            STOCK_CALL(io, 0x2a4ce, spacer, 100, 20);
        }
    }
    if (!engage || !release || !spacer) return;
    if (config >= 0) {
        uint32_t on = (uint32_t)config & 1u, ms = (uint32_t)config >> 1;
        if (count < 7 || STOCK_CALL(io, 0x276ca, engage) != on) {
            STOCK_CALL(io, 0x276b4, engage, on, 0);
            uint32_t label = STOCK_CALL(io, 0x2da52, engage, 2);
            if (label) assign_set_text(label, (uint32_t)(uintptr_t)(on ? "On" : "Off"), io);
        }
        if (count < 8 || STOCK_CALL(io, 0x276ca, release) != ms) {
            STOCK_CALL(io, 0x276b4, release, ms, 0);
            expression_release_label(release, ms, io);
        }
    }
    changed |= expression_visibility(engage, 1, io);
    changed |= expression_visibility(release, 1, io);
    changed |= expression_visibility(spacer, 1, io);
    expression_page_count(ctx, 3, 9, io);
    uint32_t page = IO_R8(io, ctx + 0xe4);
    if (page == 2 && (last_page != 2 || changed || count < 9)) {
        STOCK_CALL(io, 0x2c204, release, 0);
    } else if (page == 1 && (changed || count < 9)) {
        uint32_t first = STOCK_CALL(io, 0x2da52, rows, 3);
        if (first) STOCK_CALL(io, 0x2c204, first, 0);
    }
}
#endif

/* DST Capture Slot scroll restart. The stock tick refreshes a parameter value label in place
 * (0x1ba8c -> label text), so a long capture name keeps its running scroll; stock restarts the scroll only when it builds
 * the row (0x27498: long mode 3 = circular scroll through 0x3ef60). The tick caches the selected block's parameter values
 * at dlg+0xa8+4i (firmware/reconstructed/nds/ui_effect_tick.c), so a changed Slot (parameter 0) is seen without own
 * RAM: compare it around the stock tick and re-apply long mode 3 to the Slot row's value label (row child 3, label child
 * 2: ui_effect_rows.c), which restarts the scroll from the start. Only for block 2 holding DST Capture (0x0300007c). */
#define DST_SCROLL_NONE 0xffffffffu
static uint32_t dst_slot_cached(uint32_t dlg, const StockIo *io) {
    uint32_t group = IO_R8(io, dlg + 0x90);
    if (group >= 10u || IO_R8(io, dlg + 0x80 + group) != 2u) return DST_SCROLL_NONE;
    uint32_t id = 0;
    for (uint32_t i = 0; i < 4u; i++) id |= (uint32_t)IO_R8(io, 0x200106d3u + 8u + i) << (8u * i);   /* live model ID, block 2 */
    return id == 0x0300007cu ? io_r32(io, dlg + 0xa8) : DST_SCROLL_NONE;
}
static void dst_slot_scroll_restart(uint32_t dlg, uint32_t before, const StockIo *io) {
    uint32_t after = dst_slot_cached(dlg, io);
    if (before == DST_SCROLL_NONE || after == DST_SCROLL_NONE || after == before) return;
    uint32_t row = STOCK_CALL(io, 0x2da52, io_r32(io, dlg + 0x28), 3);
    uint32_t label = row ? STOCK_CALL(io, 0x2da52, row, 2) : 0;
    if (label) STOCK_CALL(io, 0x3ef60, label, 3);
}

uint32_t assign_editor_tick(uint32_t ctx, uint32_t event, const StockIo *io) {
#ifdef GP50_FEATURE_AUTO_WAH
    uint32_t last_page = IO_R8(io, 0x20004d9c);
#endif
    uint32_t dst_slot = dst_slot_cached(ctx, io);
    STOCK_CALL(io, 0x16e9ca, ctx, event);                            /* stock editor tick (prologue-replay stub) */
    dst_slot_scroll_restart(ctx, dst_slot, io);
#ifdef GP50_FEATURE_AUTO_WAH
    expression_tiles(ctx, last_page, io);
#endif
    #ifdef GP50_FEATURE_ASSIGNMENT                                   /* assignment is the SDK feature: context only */
    gp50_features_screen_ctx(1u, ctx); return 0;
    #endif
    #ifdef GP50_ASSIGNMENT_MENU
    if (assignment_tick(ctx, io)) return 0;
    #endif
    if (!io_r32(io, PHASE)) return 0;
    if (STOCK_CALL0(io, 0x471d6) == io_r32(io, ASSIGN_STATE + 20)) {
        uint32_t group = io_r32(io, ASSIGN_STATE + 4);
        if (group >= 10 || STOCK_CALL(io, 0x475d0, group) == io_r32(io, ASSIGN_STATE + 24)) { assign_render_current(ctx, io); return 0; }
    }
    io_w32(io, PHASE, 0);                                            /* preset or model changed: cancel */
    assign_restore(ctx, io);
    return 0;
}

uint32_t assign_home_tick(uint32_t ctx, uint32_t event, const StockIo *io) {
    STOCK_CALL(io, 0x16ea12, ctx, event);                            /* stock home tick (prologue-replay stub) */
    assign_home_refresh(ctx, io);
    return 0;
}
