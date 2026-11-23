"""Hard Clip: coprocessor program for the DST slot (PC 0). Pure data; assembled by sdk/build_effect.py.

Per block, when the enable cell has bit 0 set:
    for i in 0..63:  y = D[0x13+i] * D[GAIN]
                     if y > D[LIMIT]:  y = D[LIMIT]
                     if y < D[NLIMIT]: y = D[NLIMIT]        (NLIMIT holds -limit)
                     D[0x13+i] = y * D[LEVEL]
in place on the left input window, then `jump 0x500` to the AMP slot. Bypassed: `jump 0x500`
with the window untouched. Words 0..5 and both exits are the stock DST frame word for word
(analysis/firmware/COPRO_EFFECTS.md); the body is the clamp of sdk/copro/soft_gain.py, which
ran on the pedal, plus one multiply. Every word is a form executed on the pedal.

Registers: r0 pointer, r1 counter, r2 gain, r3 +limit, r4 -limit, r5/r6 frame, r6/r7 sample,
r8 level. No call, so r14 is never used.
"""
CELLS=dict(ENABLE=0x193,GAIN=0x194,LIMIT=0x195,NLIMIT=0x196,LEVEL=0x197)
NEXT_SLOT=0x500
ALLOWED_NON_X=[]            # no static-only word is needed

SOURCE=[
    ('li',0,0),                    # stock DST word 0
    ('store',0,0x10),              # stock DST word 1: D[0x10] = 0 (purpose unknown; every stock DST program does it)
    ('li',5,CELLS['ENABLE']),
    ('load_ind',6,5),
    ('skip_if_bit0',6),            # enabled: skip the jump
    ('jump','bypass'),
    ('li',0,0x13),
    ('li',1,0x40),
    ('load',2,CELLS['GAIN']),
    ('load',3,CELLS['LIMIT']),
    ('load',4,CELLS['NLIMIT']),
    ('load',8,CELLS['LEVEL']),
    'sample:',
    ('load_ind',6,0),              # r6 = x
    ('fmul',7,6,2),                # r7 = x * gain
    ('fsub',6,3,7),                # r6 = limit - y      negative when y > limit
    ('run_next_if_negative',),
    ('mov',7,3),                   #   y = limit
    ('fsub',6,7,4),                # r6 = y - (-limit)   negative when y < -limit
    ('run_next_if_negative',),
    ('mov',7,4),                   #   y = -limit
    ('fmul',6,7,8),                # r6 = y * level
    ('store_inc',0,6),             # D[r0++] = r6
    ('loop',1,'sample'),
    ('jump',NEXT_SLOT),            # active exit
    'bypass:',
    ('jump',NEXT_SLOT),            # bypass exit
]


def reference(samples,gain,limit,level):
    """Plain float32 model of the active path: float32 bit patterns in, bit patterns out."""
    import struct
    f=lambda b:struct.unpack('<f',struct.pack('<I',b))[0];r=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
    g,lim,lev=r(gain),r(limit),r(level);out=[]
    for b in samples:
        y=r(f(b)*g)
        if y>lim:y=lim
        if y<-lim:y=-lim
        out.append(struct.unpack('<I',struct.pack('<f',r(y*lev)))[0])
    return out
