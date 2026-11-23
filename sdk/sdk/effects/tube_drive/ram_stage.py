#!/usr/bin/env python3
"""RAM stage for Tube Drive: the shipped active path run from RAM under the probe's watchdog,
before any image exists. Offline builder only - prints / writes the probe write list; it never
contacts the pedal.

Host: a stock DST effect with the standard frame (nine of the ten, not Plustortion), e.g. Sora
Fuzz as in scripts/copro_hardclip_stage.py. Its word 6 (first word of the active path) is
replaced by `jump BODY`; the body is our active path placed at PC 0x400 (stock DST programs end
at or below PC 0x223; the loader zeroes the whole slot) and ends with the stock `jump 0x500`.

Cells: NOT the shipped D[0x194..0x1a0] - those belong to the host effect, whose ARM half may
rewrite some of them every block. The stage uses D[0x300..0x30c], above every cell a stock DST
overlay addresses (highest D[0x274]) and below the AMP group's first cell D[0x398]. The body is
the shipped one re-assembled with these cell numbers and at PC 0x400, so the words differ from
the shipped program only in direct cell addresses and branch targets (asserted by the tests).

Probe order (the undo log holds 24 entries; uncommitted writes are undone by the watchdog):
  1. preconditions (reads): word 0x1006 = host stock word 6; body area reads 0; cells read and
     recorded (expected 0)
  2. body words in groups of at most 20 writes, COMMIT after each group (inert: nothing jumps
     there yet); read the body back once
  3. the 13 cells, then the patch word LAST (14 logged writes). UNDO or the watchdog restores
     cells and patch and leaves the inert body, which the next DST load erases.
  4. to change a setting while the patch is live write single cells (each is one more logged
     write; at most 8 more before the log is full - UNDO and repeat step 3 for a new set).
The ENABLE cell D[0x193] is the host's and is driven by its ARM half (host block on/off).

  python3 -B sdk/effects/tube_drive/ram_stage.py [--setting neutral|knobs] [--gain 50 --tone 50 --vol 50] [--out FILE.json]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from sdk.copro import asm  # noqa: E402


def _load(name):
    spec=importlib.util.spec_from_file_location('tube_drive_'+name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


program=_load('program');model=_load('model')
BODY=0x400
PATCH_PC=6
CELL_BASE=0x300
C=program.cell_map(CELL_BASE)
GROUP=20                    # body writes per COMMIT


def body():
    return asm.assemble(program.active_body(C),BODY)


def neutral(drive=1.0,level=1.0,tone_a=1.0):
    """Biquad as a wire (b0 = 1), tone coefficient 1 (z follows x), ramps already at their targets:
    the output is level * f(drive * x) with f(x) = x - x^3/3 clamped - the static curve alone."""
    b=model.bits
    return dict(HP_B0=b(1.0),HP_B1=0,HP_B2=0,HP_A1=0,HP_A2=0,HP_S1=0,HP_S2=0,DRIVE_TGT=b(drive),DRIVE_CUR=b(drive),TONE_A=b(tone_a),TONE_Z=0,LEVEL_TGT=b(level),LEVEL_CUR=b(level))


def knobs(gain,tone,vol):
    c=model.init_cells(gain,tone,vol);c.pop('ENABLE');return c


def phases(values,host_word6=None):
    b=body();groups=[b[i:i+GROUP] for i in range(0,len(b),GROUP)]
    return dict(
        preconditions=dict(read_equal={f'{0x1000+PATCH_PC:#06x}':(f'{host_word6:#010x}' if host_word6 is not None else 'host stock word 6')},
                           read_zero=[f'{0x1000+BODY+i:#06x}' for i in range(len(b))],read_and_record=[f'{C[k]:#06x}' for k in program.CELL_NAMES]),
        body_groups_commit_after_each=[[[f'{0x1000+BODY+GROUP*g+i:#06x}',f'{w:#010x}'] for i,w in enumerate(ws)] for g,ws in enumerate(groups)],
        logged_writes=[[f'{C[k]:#06x}',f'{values[k]:#010x}'] for k in program.CELL_NAMES]+[[f'{0x1000+PATCH_PC:#06x}',f'{asm.isa.jump(BODY):#010x}']],
        cells={k:f'{C[k]:#06x}' for k in program.CELL_NAMES},
        undo='probe UNDO restores the patch word and the thirteen cells; the body stays (inert) until the next DST load')


def main():
    ap=argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--setting',choices=('neutral','knobs'),default='neutral')
    ap.add_argument('--gain',type=float,default=50.0);ap.add_argument('--tone',type=float,default=50.0);ap.add_argument('--vol',type=float,default=50.0)
    ap.add_argument('--drive',type=float,default=1.0);ap.add_argument('--level',type=float,default=1.0)
    ap.add_argument('--out',type=Path)
    a=ap.parse_args();p=phases(neutral(a.drive,a.level) if a.setting=='neutral' else knobs(a.gain,a.tone,a.vol))
    p['setting']=dict(vars(a),out=None)
    print(asm.listing(body(),BODY));print(json.dumps({k:v for k,v in p.items() if k!='body_groups_commit_after_each'},indent=1))
    if a.out:a.out.write_text(json.dumps(p,indent=1)+'\n')


if __name__=='__main__':main()
