#!/usr/bin/env python3
"""Encoder vs Ghidra: every instruction Ghidra assembled for earlier images (spec.tsv paired
with assembled.tsv, and every patches.json hook) must encode identically. FPU rows (not
emitted by nds_ui) are counted as skipped."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'scripts'))
from nds_ui.asm import encode,AsmError
def vectors():
    for spec in sorted(ROOT.glob('work/*/spec.tsv')):
        asm=spec.with_name('assembled.tsv')
        if asm.exists():
            for a,b in zip(spec.read_text().splitlines(),asm.read_text().splitlines()):
                pc,_,text=a.split('\t',2);pc2,hx,_=b.split('\t',2);assert pc==pc2
                yield spec.parent.name,int(pc,16),text,hx
        p=spec.with_name('patches.json')
        if p.exists():
            for r in json.loads(p.read_text()):
                if 'new' in r and 'assembly' in r:yield spec.parent.name,int(r['address'],16),r['assembly'],r['new']
def main():
    ok=skip=0;bad=[]
    for where,pc,text,hx in vectors():
        if text.split()[0].startswith('f'):skip+=1;continue
        try:got=encode(pc,text).hex()
        except AsmError as e:got='ERR '+str(e)
        if got==hx:ok+=1
        else:bad.append((where,hex(pc),text,hx,got))
    for b in bad[:20]:print('MISMATCH',*b)
    print(json.dumps(dict(status='pass' if not bad else 'fail',matched=ok,mismatched=len(bad),skipped_fpu=skip)))
    return 1 if bad else 0
if __name__=='__main__':sys.exit(main())
