#!/usr/bin/env python3
"""The tier-b reviewer must reject undeclared edits. Builds mutated containers in a temp
directory from the reproduced MOD037 regions (never written to work/custom_images)."""
import json,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from nds_ui import review
from nds_ui.cli import load_cfg
from firmware_verify import decode
import htfw_pack
def mutated(cfg,edit):
    img=(ROOT/cfg['output']/cfg['name']).read_bytes();regs,_=decode(img);b=bytearray({r:v for r,_,v in regs}['b']);edit(b)
    head,_=htfw_pack.parse_template(img);return htfw_pack.build(head,[(r,d,bytes(b) if r=='b' else v) for r,d,v in regs],compressed=True)
def main():
    cfg=load_cfg('mod037');results={}
    assert review.review(cfg)['status']=='pass'
    cases={'undeclared stock byte':lambda b:b.__setitem__(0x1000,b[0x1000]^1),
           'segment byte':lambda b:b.__setitem__(0x160010,b[0x160010]^1),
           'hook target':lambda b:b.__setitem__(0x27b3c-0x10000+3,b[0x27b3c-0x10000+3]^2),
           'version text':lambda b:b.__setitem__(0x130f3a,ord('z'))}
    with tempfile.TemporaryDirectory() as d:
        for name,edit in cases.items():
            p=Path(d)/'m.bin';p.write_bytes(mutated(cfg,edit))
            try:review.review(cfg,p);results[name]='ACCEPTED (bad)'
            except ValueError as e:results[name]='rejected: '+str(e)[:70]
    print(json.dumps(results,indent=1))
    return 0 if all(v.startswith('rejected') for v in results.values()) else 1
if __name__=='__main__':sys.exit(main())
