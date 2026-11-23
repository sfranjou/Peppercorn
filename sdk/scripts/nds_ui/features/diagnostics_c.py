"""Diagnostics block in C (MOD056+; analysis/firmware/NDS_CODE_ROOM.md section 8.3): our assembly of 0x16c6c0..0x16cb60
(MOD002/030 load bridge: GUI wrapper, sampler service, 0x6002 receive, `12 50` host reply; MOD007 USB send guard; MOD016
`11 15` main-memory peek) runs the readable source compared with it (firmware/reconstructed/nds/diagnostics.c,
scripts/study_nds_diagnostics.py) through the pedal build sdk/nds/diagnostics/diagnostics.c. With this feature nothing of
the old block is kept, so the segment base can drop to the stock end 0x16c6c0.

Stays assembly (byte-faithful copies of MOD055's instructions; only the PC-relative targets move):
- diag_dispatch_asm (MOD055 0x16c6e6): entered by `j` from telemetry_c's dispatch stub inside stock link_receive 0x46a0a
  (a5 = received command): 0x6002 -> diag_receive_asm, else `movi a0,0x7004; j 0x46aba` (the replaced stock compare);
- diag_receive_asm (MOD055 0x16c7f0): s0 = received count is link_receive's live register and the stub leaves with
  `j 0x46b7a` on link_receive's frame; a C function would return instead (its compared C models these as calls).
  It calls the C diag_finite (same contract as the assembly leaf: a0 in, a0 out; the C ABI preserves s0..s4).
Reach sites (scripts/nds_legacy_reach.py lo 0x16c6c0 on MOD055): 0x431dc `jal` (hook_diag_usb_guard), the `11 15` table
word 0x140c1c (hook_diag_peek_word), the stock read table word 0x140bc8 (hook_diag_host_word; dead since host_layer_c,
re-pointed so no stale pointer stays) and, inside our code, telemetry_c's dispatch `j` and host_layer_c's own_read_table
word (both switched to the new symbols for configs with this feature).
diag_gui / diag_service have no caller since MOD030 (telemetry's own GUI wrapper and service replaced them); they are
kept as C entries so the whole block is compared and available."""
from ..stock_api import API

NAME = 'diagnostics_c'
REQUIRES = ('telemetry', 'host_layer_c')
CONFLICTS = ()
ORACLES = ()
CASE_KINDS = ()
C_SOURCES = ('sdk/nds/diagnostics/diagnostics.c',)
C_ENTRIES = ('diag_gui', 'diag_service', 'diag_finite', 'diag_host', 'diag_putword', 'diag_usb_guard', 'diag_peek')
# MOD055 (and MOD002..MOD055) address -> replacement symbol / asm label (window of the old block for the image proof).
BLOCK = (0x16c6c0, 0x16cb60)
LEGACY = {0x16c6c0: 'diag_gui', 0x16c6e6: 'diag_dispatch_asm', 0x16c6f6: 'diag_service', 0x16c7f0: 'diag_receive_asm',
          0x16c930: 'diag_finite', 0x16c954: 'diag_host', 0x16ca6c: 'diag_putword', 0x16ca8a: 'diag_usb_guard', 0x16caa4: 'diag_peek'}


def enabled(cfg):
    return NAME in ((cfg or {}).get('features') or ())


def section_stubs(c):
    """MOD055 0x16c6e6..0x16c6f6 and 0x16c7f0..0x16c930, instruction for instruction (registers by ABI name: r6..r10 =
    s0..s4); the five stock calls/jumps keep their absolute targets, the receive branch and the diag_finite calls are
    labels."""
    if 'remaining_application_c' in c.enabled:
        s = c.s
        s.label('diag_dispatch_asm')
        s.emit('movi a0,0x6002\nbeq a0,a5,@diag_receive_asm\nmovi a0,0x7004\nj 0x46aba')
        c.begin('diag_receive_asm')
        s.emit('mov55 a0,s0\njal @nds_remaining_diag_receive')
        c.end(tail=API.receive_continue)
        return
    s = c.s
    s.label('diag_dispatch_asm')
    s.emit('movi a0,0x6002\nbeq a0,a5,@diag_receive_asm\nmovi a0,0x7004\nj 0x46aba')
    s.label('diag_receive_asm')
    s.emit('addi sp,sp,-24\nswi s0,[sp + 0]\nswi s1,[sp + 4]\nswi s2,[sp + 8]\nswi s3,[sp + 12]\nswi s4,[sp + 16]\nswi lp,[sp + 20]'
           '\nmovi a0,0x10\nbne s0,a0,@diag_rx_end')
    s.address('s2', API.link_rx_frame)   # stock link receive buffer (DIAG_FRAME 0x20010928)
    for off, v in [(1, 0x10), (2, 0), (3, 1), (4, 2), (5, 0x60), (6, 0xc), (7, 0)]:
        s.emit(f'lbi a0,[s2 + {off}]\nmovi a1,{v:#x}\nbne a0,a1,@diag_rx_end')
    s.emit('lwi s3,[s2 + 8]\nlwi s4,[s2 + 12]\nmov55 a0,s3\njal @diag_finite\nbeqz a0,@diag_rx_end\nmov55 a0,s4\njal @diag_finite\nbeqz a0,@diag_rx_end')
    s.address('s1', 0x2001f3b0)   # DIAG_STATE
    s.emit(f'jal {API.irq_guard_enter:#x}')
    s.address('a0', API.tick_counter)
    s.emit('lwi a0,[a0 + 0]\nswi a0,[s1 + 20]\nswi s3,[s1 + 28]\nswi s4,[s1 + 32]\nlwi a0,[s1 + 24]\naddi a0,a0,1\nswi a0,[s1 + 24]\nmovi55 a0,1\nswi a0,[s1 + 8]')
    s.address('a0', API.link_tx_state)
    s.emit('lbi a1,[a0 + 16]\nbeqz a1,@diag_rx_unlock\nlhi a1,[a0 + 10]\nslti a1,a1,6\nbnez a1,@diag_rx_unlock\nlwi a0,[a0 + 4]\nbeqz a0,@diag_rx_unlock'
           '\nlbi a1,[a0 + 4]\nlbi a0,[a0 + 5]\nslli a0,a0,8\nor a0,a0,a1\nmovi a1,0x6002\nbne a0,a1,@diag_rx_unlock'
           f'\nmovi55 a0,0\nswi a0,[s1 + 4]\nswi a0,[s1 + 12]\njal {API.link_release_owned:#x}')
    s.label('diag_rx_unlock'); s.emit(f'jal {API.irq_guard_leave:#x}')
    s.label('diag_rx_end')
    s.emit('lwi s0,[sp + 0]\nlwi s1,[sp + 4]\nlwi s2,[sp + 8]\nlwi s3,[sp + 12]\nlwi s4,[sp + 16]\nlwi lp,[sp + 20]\naddi sp,sp,24'
           f'\nj {API.receive_continue:#x}')


CODE = {'stubs': section_stubs}
DATA = {}
HOOKS = {}


def patches(c):
    L = c.labels
    out = [(API.hook_diag_usb_guard, f'jal {L["diag_usb_guard"]:#x}', 'USB bulk send: MOD007 guard (C diag_usb_guard)'),
            (API.hook_diag_host_word, f'.word {L["diag_host"]:#x}', 'stock read table word (12 50): C diag_host (table unused since host_layer_c; no stale pointer)'),
            (API.hook_diag_peek_word, f'.word {L["diag_peek"]:#x}', 'set table word (11 15): MOD016 peek (C diag_peek)')]

    from ..stock_in_place import bulk_stems   # the call site lives in bulk protocol_transport: live again when that module runs as stock
    return [p for p in out if not ('application_bulk_c' in c.enabled and p[0] == API.hook_diag_usb_guard and 'protocol_transport' not in bulk_stems(c.cfg))]


def remap(labels):
    """MOD055 address -> candidate address (for the image proof)."""
    return {a: labels[n] for a, n in LEGACY.items()}
