#!/usr/bin/env python3
"""P1 "soft gain": first custom coprocessor program for the GP-50. Offline builder only.

What it does, once per 64-sample block, before the stock EQ program runs:
    for i in 0..63:  y = D[0x13+i] * D[GAIN]
                     if y > D[LIMIT]:  y = D[LIMIT]
                     if y < D[NLIMIT]: y = D[NLIMIT]        (NLIMIT holds -limit)
                     D[0x13+i] = y
The left input window is rewritten in place, so the stock EQ and its final copy to the output
windows carry the result onward (the chain is mono: both outputs are copied from D[0x13..]).

How it is reached: EQ program word 0 (`75060f9c`, r5 = #0xf9c) is replaced by a call to
PC 0xf80; the program ends with that displaced instruction and a return - the trampoline of
experiment t0_trampoline_002.

This script only builds the list of probe writes and a batch file for
scripts/copro_experiment.py. It never contacts the pedal.

  python3 -B sdk/copro/soft_gain.py                       write work/copro_experiments/batches/p1_soft_gain.json
  python3 -B sdk/copro/soft_gain.py --list                print listing and writes only
  python3 -B sdk/copro/soft_gain.py --gain 1.0 --limit 0.05 --variant-gain 2.0 --out FILE
"""
import argparse
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from sdk.copro import asm  # noqa: E402

BASE=0xf80                 # unused tail of the EQ program slot (EQ is 0x5d words at 0xe00)
CALL_SITE=0xe00            # EQ word 0
DISPLACED=0x75060f9c       # stock EQ word 0: r5 = #0xf9c
GAIN,LIMIT,NLIMIT=0xf00,0xf01,0xf02   # data cells shown to be free and stable (experiments used D[0xf00..0xf12])
IN_LEFT,BLOCK=0x13,0x40
MAX_WRITES=22              # scripts/copro_experiment.py: the probe's undo log holds 24

# Registers: r0 pointer, r1 counter, r2 gain, r3 +limit, r4 -limit, r6 sample, r7 result/scratch.
# r5 is set by the displaced instruction. r8..r13 are not touched; r14 is the call link.
SOURCE=[
    ('li',0,IN_LEFT),
    ('li',1,BLOCK),
    ('load',2,GAIN),
    ('load',3,LIMIT),
    ('load',4,NLIMIT),
    'sample:',
    ('load_ind',6,0),              # r6 = x
    ('fmul',7,6,2),                # r7 = x * gain
    ('fsub',6,3,7),                # r6 = limit - y      negative when y > limit
    ('run_next_if_negative',),
    ('mov',7,3),                   #   y = limit
    ('fsub',6,7,4),                # r6 = y - (-limit)   negative when y < -limit
    ('run_next_if_negative',),
    ('mov',7,4),                   #   y = -limit
    ('store_inc',0,7),             # D[r0++] = y
    ('loop',1,'sample'),
    ('word',DISPLACED,'instruction displaced from EQ word 0'),
    ('ret',),
]


def program():
    return asm.assemble(SOURCE,BASE)


def writes(gain=1.0,limit=64.0):
    """Probe writes (word index, value) in the order they must be applied: data cells, program, call patch last."""
    if not limit>0:raise ValueError('limit must be positive')
    out=[(GAIN,asm.fbits(gain)),(LIMIT,asm.fbits(limit)),(NLIMIT,asm.fbits(-limit))]
    out+=[(0x1000+BASE+i,w) for i,w in enumerate(program())]
    out.append((0x1000+CALL_SITE,asm.isa.call(BASE)))
    if len(out)>MAX_WRITES:raise ValueError(f'{len(out)} writes exceed the budget of {MAX_WRITES}')
    return out


def batch(gain=1.0,limit=64.0,variant_gains=(0.5,)):
    """Group-form batch: the harness installs the program with `gain`; each variant is one write to the gain cell."""
    harness=writes(gain,limit)
    if len(harness)+len(variant_gains)>MAX_WRITES:raise ValueError('harness + variants exceed the write budget')
    h=lambda v:f'{v:#010x}'
    return [dict(
        name='p1_soft_gain',
        note=(f'Custom program: left input window D[0x13..0x52] *= D[{GAIN:#x}], limited to +-D[{LIMIT:#x}] (D[{NLIMIT:#x}] = -limit); '
              f'called from EQ word 0, PC {BASE:#x}. Harness gain {gain}, limit {limit}; variants rewrite the gain cell. '
              'Preconditions: word 0x1e00 reads 0x75060f9c and words 0x1f80..0x1f90 read 0 before the run. '
              'The runner undoes everything at the end of the group; an audio measurement needs a hold between the variant write and the undo.'),
        harness=[[f'{i:#06x}',h(v)] for i,v in harness],
        test_index=f'{GAIN:#06x}',
        variants=[[f'gain_{g}',h(asm.fbits(g))] for g in variant_gains],
        reads=[f'{i:#06x}' for i in (GAIN,LIMIT,NLIMIT,0x1000+CALL_SITE,0x1000+BASE,0x1000+BASE+len(program())-1,IN_LEFT,0x93)])]


def reference(samples,gain,limit):
    """Plain float32 model of the program: list of float32 bit patterns in, list out."""
    import struct
    f=lambda b:struct.unpack('<f',struct.pack('<I',b))[0];r=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]
    g,lim=r(gain),r(limit);out=[]
    for b in samples:
        y=r(f(b)*g)
        if y>lim:y=lim
        if y<-lim:y=-lim
        out.append(struct.unpack('<I',struct.pack('<f',y))[0])
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--gain',type=float,default=1.0);ap.add_argument('--limit',type=float,default=64.0)
    ap.add_argument('--variant-gain',type=float,action='append');ap.add_argument('--list',action='store_true')
    ap.add_argument('--out',type=Path,default=ROOT/'work/copro_experiments/batches/p1_soft_gain.json')
    a=ap.parse_args();variants=tuple(a.variant_gain or (0.5,))
    b=batch(a.gain,a.limit,variants)
    print(asm.listing(program(),BASE))
    for i,v in writes(a.gain,a.limit):print(f'write {i:#06x} {v:#010x}')
    print(f'{len(writes(a.gain,a.limit))} harness writes + {len(variants)} variant write(s) of at most {MAX_WRITES}')
    if not a.list:
        a.out.write_text(json.dumps(b,indent=1)+'\n');print('wrote',a.out)


if __name__=='__main__':main()
