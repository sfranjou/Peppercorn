"""Tube Drive: coprocessor program for the DST slot (PC 0). Pure data; assembled by sdk/build_effect.py.

Per block, when the enable cell has bit 0 set (all in place on the left window D[0x13..0x52]):

  1 drive    ramp:  step = (DRIVE_TGT - DRIVE_CUR) * K;  64 x { cur += step; scratch[i] = cur }
             DRIVE_CUR = cur;  window *= scratch                       (block multiply 2007)
  2 high-pass biquad, transposed direct form II, state in two cells kept across blocks:
             y = b0*x + s1;  s1 = (b1*x - a1*y) + s2;  s2 = b2*x - a2*y
  3 soft clip  x = clamp(x, -1, +1)                                   (stock subtract / flag-skip / move idiom)
             scratch = x*x; scratch = x*scratch; scratch *= -1/3      (block multiply x2, block scale 2008)
             window  = scratch + x                                     (block add 2003)  ->  x - x^3/3
  4 tone     one-pole low-pass, state in one cell:  z = z + (x - z)*a;  out = z
  5 level    same ramp as 1 with LEVEL_TGT / LEVEL_CUR, window *= scratch

then `jump 0x500`. Bypassed: `jump 0x500`, window and all cells untouched.

Stage 1/5 are the stock idiom word for word in structure (Sora Fuzz PC 0x00f..0x020: targets
written by the ARM half, ramp constant 0x396dc66d = 1/4410 per sample, ramp into the scratch
buffer D[0x113..0x152], block multiply with r8 = scratch, r9 = r11 = window), except that the
running value is kept in a register and stored once after the loop, and that every arithmetic
word has a destination distinct from its operands (the rule of sdk/copro/asm.py: only that
operand pattern was run in our own experiments; stock code uses in-place forms every block).

Registers are all loaded before use in every stage. No call, so r14 is never used. Every word
is a form executed on the pedal (see analysis/firmware/COPRO_CAPABILITIES.md for the operand
patterns that are new).
"""
RAMP_K_BITS=0x396dc66d      # stock smoothing constant (Sora Fuzz PC 0x011/0x012), about 1/4410 per sample
NEXT_SLOT=0x500
WINDOW,SCRATCH,FRAMES=0x13,0x113,0x40
ALLOWED_NON_X=[]            # no static-only word is needed

CELL_NAMES=('HP_B0','HP_B1','HP_B2','HP_A1','HP_A2','HP_S1','HP_S2','DRIVE_TGT','DRIVE_CUR','TONE_A','TONE_Z','LEVEL_TGT','LEVEL_CUR')


def cell_map(first):
    """Cell layout with the thirteen parameter/state cells starting at data word `first`."""
    return dict(ENABLE=0x193,**{k:first+i for i,k in enumerate(CELL_NAMES)})


CELLS=cell_map(0x194)       # shipped layout: directly after the group's enable cell, as in stock DST effects
STATE_CELLS=('HP_S1','HP_S2','DRIVE_CUR','TONE_Z','LEVEL_CUR')     # written by the program; everything else is only read


def _ramp_and_multiply(C,target,current,label):
    return [
        ('load',0,C[target]),
        ('load',1,C[current]),
        ('const',2,RAMP_K_BITS),
        ('fsub',3,0,1),                # target - current
        ('fmul',4,2,3),                # per-sample step for this block
        ('li',5,SCRATCH),
        ('li',7,FRAMES),
        label+':',
        ('fadd',6,1,4),
        ('mov',1,6),
        ('store_inc',5,6),
        ('loop',7,label),
        ('store',1,C[current]),
        ('li',8,SCRATCH),              # the four words stock uses before its block multiply
        ('li',9,WINDOW),
        ('li',10,FRAMES),
        ('li',11,WINDOW),
        ('block','mul'),               # window[i] = scratch[i] * window[i]
    ]


def active_body(C):
    """The active path, from the first word after the frame up to and including the active exit."""
    return (_ramp_and_multiply(C,'DRIVE_TGT','DRIVE_CUR','drive_ramp')+[
        # --- 2: high-pass biquad (transposed direct form II) ---
        ('li',0,WINDOW),
        ('li',1,FRAMES),
        ('load',2,C['HP_B0']),
        ('load',3,C['HP_B1']),
        ('load',4,C['HP_B2']),
        ('load',5,C['HP_A1']),
        ('load',6,C['HP_A2']),
        ('load',7,C['HP_S1']),
        ('load',8,C['HP_S2']),
        'biquad:',
        ('load_ind',11,0),             # x
        ('fmul',9,11,2),               # b0*x
        ('fadd',10,9,7),               # y = b0*x + s1
        ('fmul',9,11,3),               # b1*x
        ('fmul',12,10,5),              # a1*y
        ('fsub',13,9,12),              # b1*x - a1*y
        ('fadd',7,13,8),               # s1 = (b1*x - a1*y) + s2
        ('fmul',9,11,4),               # b2*x
        ('fmul',12,10,6),              # a2*y
        ('fsub',8,9,12),               # s2 = b2*x - a2*y
        ('store_inc',0,10),
        ('loop',1,'biquad'),
        ('store',7,C['HP_S1']),
        ('store',8,C['HP_S2']),
        # --- 3: clamp to +-1, then x - x^3/3 with block words ---
        ('li',0,WINDOW),
        ('li',1,FRAMES),
        ('constf',3,1.0),
        ('constf',4,-1.0),
        'clamp:',
        ('load_ind',7,0),
        ('fsub',6,3,7),                # 1 - x: negative when x > 1
        ('run_next_if_negative',),
        ('mov',7,3),
        ('fsub',6,7,4),                # x - (-1): negative when x < -1
        ('run_next_if_negative',),
        ('mov',7,4),
        ('store_inc',0,7),
        ('loop',1,'clamp'),
        ('li',8,WINDOW),
        ('li',9,WINDOW),
        ('li',10,FRAMES),
        ('li',11,SCRATCH),
        ('block','mul'),               # scratch = x * x
        ('li',8,WINDOW),
        ('li',9,SCRATCH),
        ('li',10,FRAMES),
        ('li',11,SCRATCH),
        ('block','mul'),               # scratch = x * scratch          (in place, r9 = r11 as in stock)
        ('constf',8,-1.0/3.0),
        ('li',9,SCRATCH),
        ('li',10,FRAMES),
        ('li',11,SCRATCH),
        ('block','scale'),             # scratch = (-1/3) * scratch     (in place, as stock)
        ('li',8,SCRATCH),
        ('li',9,WINDOW),
        ('li',10,FRAMES),
        ('li',11,WINDOW),
        ('block','add'),               # window = scratch + window      (in place)
        # --- 4: tone, one-pole low-pass ---
        ('li',0,WINDOW),
        ('li',1,FRAMES),
        ('load',2,C['TONE_A']),
        ('load',3,C['TONE_Z']),
        'tone:',
        ('load_ind',4,0),
        ('fsub',5,4,3),                # x - z
        ('fmul',6,5,2),                # (x - z) * a
        ('fadd',7,3,6),                # z + (x - z) * a
        ('mov',3,7),
        ('store_inc',0,7),
        ('loop',1,'tone'),
        ('store',3,C['TONE_Z']),
        ]+_ramp_and_multiply(C,'LEVEL_TGT','LEVEL_CUR','level_ramp')+[
        ('jump',NEXT_SLOT),            # active exit
    ])


def source(C):
    return [
        ('li',0,0),                    # stock DST word 0
        ('store',0,0x10),              # stock DST word 1: D[0x10] = 0 (purpose unknown; every stock DST program does it)
        ('li',5,C['ENABLE']),
        ('load_ind',6,5),
        ('skip_if_bit0',6),            # enabled: skip the jump
        ('jump','bypass'),
    ]+active_body(C)+[
        'bypass:',
        ('jump',NEXT_SLOT),            # bypass exit
    ]


SOURCE=source(CELLS)
