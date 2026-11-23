#!/usr/bin/env python3
"""Stage A for Hard Clip: the same program body run from RAM under the probe's watchdog,
before any image exists. Offline builder only - prints / writes the probe write list; it
never contacts the pedal.

Host: a stock DST effect whose program has the standard frame (words 0..5 = our words 0..5;
nine of the ten, not Plustortion). Its word 6 (first word of the active path) is replaced by
`jump BODY`; the body is our loop placed in the unused tail of the DST program slot and ends
with the stock `jump 0x500`. Executed path when enabled: stock words 0..5, the patch word,
our body - word for word the path of the shipped program except for the two jump targets.

Order of probe operations (each line of the output is one phase):
  1. read preconditions: word 0x1006 equals the host's stock word 6; words BODY.. read 0
  2. write the body (inert: nothing jumps to it), then COMMIT so the undo log is empty again
  3. write the four cells, then the patch word LAST (5 logged writes; the watchdog or an undo
     restores cells and patch, leaving only the inert body, which the next DST load erases)
Cells D[0x194..0x197] belong to the host effect's program (coefficients written once by its
init); they are restored by the undo. While the patch is live do not change the host effect's
parameters through the UI: its ARM code may rewrite those cells.

  python3 -B sdk/effects/hard_clip/ram_stage.py [--gain 1.0] [--limit 0.05] [--level 1.0] [--out FILE.json]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from sdk.copro import asm  # noqa: E402

_spec=importlib.util.spec_from_file_location('hard_clip_program',Path(__file__).with_name('program.py'));program=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(program)
BODY=0x400                  # stock DST programs end at or below PC 0x223; the loader zeroes the whole slot first
PATCH_PC=6
C=program.CELLS


def body():
    src=program.SOURCE;i=src.index(('li',0,0x13));j=src.index('bypass:')
    return asm.assemble(src[i:j],BODY)


def phases(gain=1.0,limit=0.05,level=1.0,host_word6=None):
    b=body()
    return dict(
        preconditions=dict(read_equal={f'{0x1000+PATCH_PC:#06x}':(f'{host_word6:#010x}' if host_word6 is not None else 'host stock word 6')},
                           read_zero=[f'{0x1000+BODY+i:#06x}' for i in range(len(b))]),
        body_writes_then_commit=[[f'{0x1000+BODY+i:#06x}',f'{w:#010x}'] for i,w in enumerate(b)],
        logged_writes=[[f'{C[k]:#06x}',f'{asm.fbits(v):#010x}'] for k,v in (('GAIN',gain),('LIMIT',limit),('NLIMIT',-limit),('LEVEL',level))]
                      +[[f'{0x1000+PATCH_PC:#06x}',f'{asm.isa.jump(BODY):#010x}']],
        undo='probe UNDO restores the patch word and the four cells')


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--gain',type=float,default=1.0);ap.add_argument('--limit',type=float,default=0.05);ap.add_argument('--level',type=float,default=1.0)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args();p=phases(a.gain,a.limit,a.level)
    print(asm.listing(body(),BODY));print(json.dumps(p,indent=1))
    if a.out:a.out.write_text(json.dumps(p,indent=1)+'\n')


if __name__=='__main__':main()
