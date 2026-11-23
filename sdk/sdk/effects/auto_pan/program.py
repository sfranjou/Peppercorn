"""Auto Pan: own coprocessor program for the EQ slot (PC 0xe00, last stage). Pure data.

Mono in (left input window D[0x13..]) -> stereo out: per sample
    gl += DGL; gr += DGR; D[0x93+i] = x * gl; D[0xd3+i] = x * gr
with gl, gr starting at GL, GR (written by the ARM each block: the previous block's end gains and
the per-sample steps toward this block's targets, so the ramp is continuous). Bypassed: the
stock EQ bypass, input copied to both outputs with block copies. Every path ends in the end word.
Frame rules: sdk/copro/frame.py check_eq. Cells are free EQ cells (no stock EQ program here).
"""
CELLS=dict(ENABLE=0xf9c,GL=0xf9d,DGL=0xf9e,GR=0xf9f,DGR=0xfa0)
ALLOWED_NON_X=[]

SOURCE=[
    ('li',5,CELLS['ENABLE']),
    ('load_ind',6,5),
    ('skip_if_bit0',6),
    ('jump','bypass'),
    ('li',0,0x13),                 # input pointer
    ('li',1,0x93),                 # left output pointer
    ('li',2,0xd3),                 # right output pointer
    ('li',3,0x40),                 # 64 samples
    ('load',4,CELLS['GL']),
    ('load',7,CELLS['DGL']),
    ('load',8,CELLS['GR']),
    ('load',9,CELLS['DGR']),
    'sample:',
    ('load_inc',10,0),             # x
    ('fadd',11,4,7),('mov',4,11),  # gl += dgl
    ('fmul',12,10,4),
    ('store_inc',1,12),            # left
    ('fadd',11,8,9),('mov',8,11),  # gr += dgr
    ('fmul',12,10,8),
    ('store_inc',2,12),            # right
    ('loop',3,'sample'),
    ('end',),
    'bypass:',
    ('li',9,0x13),('li',10,0x40),('li',11,0x93),('block','copy'),
    ('li',9,0x13),('li',10,0x40),('li',11,0xd3),('block','copy'),
    ('end',),
]
