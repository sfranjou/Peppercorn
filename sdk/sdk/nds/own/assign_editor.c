/* Instruction-reviewed MOD026 assembly (work/ui_assignment_v2/source.nds: hold, back, drum, encoder, para, page, restore,
 * render_current, render, set_text; in MOD054's b). Compared with the original execution:
 * work/firmware_source/nds_assign_editor/verification.json. */
#include "assign_editor.h"
#define PHASE (ASSIGN_STATE + 0)

uint32_t assign_set_text(uint32_t label, uint32_t text, const StockIo *io) {
    uint32_t now = io_r32(io, label + 0x24);
    if (now) {
        for (uint32_t a = now, b = text;; a++, b++) {
            uint8_t x = IO_R8(io, a), y = IO_R8(io, b);
            if (x != y) break;
            if (!y) return label;                                 /* same text: no LVGL call */
        }
    }
    return STOCK_CALL(io, 0x3eea0, label, text);                  /* lv_label_set_text */
}

uint32_t assign_restore(uint32_t ctx, const StockIo *io) {
    uint32_t header = io_r32(io, ctx + EDIT_HEADER);
    if (header) { STOCK_CALL(io, 0x2a46a, header, 0, 0x57); STOCK_CALL(io, 0x2a4ce, header, 160, 41); }
    return STOCK_CALL(io, 0x1cb6c, ctx);                          /* stock header text */
}

uint32_t assign_render(uint32_t ctx, uint32_t prompt, const StockIo *io) {
    uint32_t header = io_r32(io, ctx + EDIT_HEADER);
    if (!header) return ctx;
    STOCK_CALL(io, 0x2a46a, header, 0, 0);
    STOCK_CALL(io, 0x2a4ce, header, 160, 20);
#ifdef ASSIGN_PROMPT_LAST
    assign_set_text(header, PROMPT_TEXT(prompt >= 1 && (prompt <= 4 || (prompt >= 6 && prompt <= ASSIGN_PROMPT_LAST)) ? prompt : 5), io);
#else
    assign_set_text(header, PROMPT_TEXT(prompt >= 1 && prompt <= 4 ? prompt : 5), io);
#endif
    return STOCK_CALL(io, 0x293fc, header, 1);
}

uint32_t assign_render_current(uint32_t ctx, const StockIo *io) {
    uint32_t phase = io_r32(io, PHASE);
    if (!phase) return 0;
    if (phase == 1) { if (io_r32(io, ASSIGN_STATE + 8) != 255) phase = 4; }
    else if (phase == 2 && io_r32(io, ASSIGN_STATE + 12) != 255) phase = 5;
#ifdef ASSIGN_PROMPT_LAST
    else if (phase == 10) phase = io_r32(io, ASSIGN_STATE + 12) == 4 ? 7 : 6;   /* footswitch 1/2 waits for B */
    else if (phase == 11) phase = 8;
#endif
    return assign_render(ctx, phase, io);
}

static uint32_t selected_group(uint32_t ctx, const StockIo *io) {   /* 10 = none */
    uint32_t block = IO_R8(io, ctx + EDIT_GROUP);
    if (block >= 10) return 10;
    uint32_t group = IO_R8(io, ctx + block + 0x80);
    return group < 10 ? group : 10;
}

uint32_t assign_editor_hold(uint32_t ctx, const StockIo *io) {
    if (io_r32(io, PHASE)) return 0;
    return selected_group(ctx, io) < 10 ? 0 : 1;
}

uint32_t assign_editor_back(uint32_t ctx, uint32_t event, const StockIo *io) {
    if (!io_r32(io, PHASE)) return STOCK_CALL(io, 0x1b9d8, ctx, event);   /* stock EXIT */
    io_w32(io, PHASE, 0);
    assign_restore(ctx, io);
    return 0;
}

static uint32_t set_phase(uint32_t ctx, uint32_t phase, const StockIo *io) {
    io_w32(io, PHASE, phase); assign_render(ctx, phase, io); return 0;
}

uint32_t assign_editor_drum(uint32_t ctx, uint32_t event, const StockIo *io) {
    (void)event;
    switch (io_r32(io, PHASE)) {
    case 0:                                                       /* start on the selected block */
        #ifdef GP50_ASSIGNMENT_MENU
        return 0; /* hold, via assignment_input, opens the explicit menu */
        #endif
        if (selected_group(ctx, io) >= 10) return 1;
        io_w32(io, ASSIGN_STATE + 4, 255); io_w32(io, ASSIGN_STATE + 8, 255); io_w32(io, ASSIGN_STATE + 12, 255);
        io_w32(io, ASSIGN_STATE + 20, STOCK_CALL0(io, 0x471d6));
        return set_phase(ctx, 1, io);
    case 1:
        if (io_r32(io, ASSIGN_STATE + 8) == 255) return 0;          /* no parameter yet */
        return set_phase(ctx, 2, io);
    case 2:
        if (io_r32(io, ASSIGN_STATE + 12) == 255) return 0;         /* no destination yet */
        if (COMMIT_CALL(io, ctx, 255)) return set_phase(ctx, 3, io);  /* second word: the 255 left in a1 (unused by commit) */
        io_w32(io, PHASE, 0); assign_restore(ctx, io); return 0;
    default:                                                      /* assigned: DRUM leaves */
        io_w32(io, PHASE, 0); assign_restore(ctx, io); return 0;
    }
}

uint32_t assign_editor_encoder(uint32_t ctx, uint32_t event, const StockIo *io) {
    uint32_t phase = io_r32(io, PHASE);
#ifdef ASSIGN_PROMPT_LAST
    if (!phase || phase == 10) return STOCK_CALL(io, 0x1c376, ctx, event);   /* idle, or footswitch B: knobs set the value */
#else
    if (!phase) return STOCK_CALL(io, 0x1c376, ctx, event);       /* stock knob/encoder callback */
#endif
    if (!io_r32(io, event + 4)) return 0;
    if (phase == 1) {                                             /* source: knob -> visible parameter on this page */
        uint32_t group = selected_group(ctx, io);
        if (group >= 10) return 0;
        io_w32(io, ASSIGN_STATE + 16, group);
        int32_t knob = IO_R8(io, event + 1), page = IO_R8(io, ctx + 0xe4), first = IO_R8(io, ctx + 0x30), parameter;
        if (page) parameter = knob + 3 * page - 3 - first;
        else { if (first || knob != 3) return 0; parameter = 0; }
        if (parameter < 0) return 0;
        if (!((uint32_t)parameter < STOCK_CALL(io, 0x46c2a, group))) return 0;
        io_w32(io, ASSIGN_STATE + 4, io_r32(io, ASSIGN_STATE + 16)); io_w32(io, ASSIGN_STATE + 8, (uint32_t)parameter);
        io_w32(io, ASSIGN_STATE + 24, STOCK_CALL(io, 0x475d0, group));
        assign_render(ctx, 4, io);
    } else if (phase == 2) {                                      /* destination: Stomp knob 1..3 -> 0..2 */
        io_w32(io, ASSIGN_STATE + 12, IO_R8(io, event + 1) - 1);
        assign_render(ctx, 5, io);
    }
    return 0;
}

uint32_t assign_para(uint32_t ctx, uint32_t event, const StockIo *io) {
    if (!io_r32(io, PHASE)) return STOCK_CALL(io, 0x1be7e, ctx, event);   /* stock encoder handler */
    return 0;
}

uint32_t assign_page(uint32_t ctx, uint32_t event, const StockIo *io) {
    STOCK_CALL(io, 0x1b912, ctx, event);                          /* stock page switch */
    assign_render_current(ctx, io);
    return 0;
}
