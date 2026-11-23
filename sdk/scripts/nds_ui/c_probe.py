"""Run sdk/nds/probe/probe.c (compiled by the local NDS32 GCC) through NDSCProbe.java in the
repaired Sleigh emulator. Vectors are computed here in Python. Usage:
  python3 scripts/nds_ui/c_probe.py"""
import json,random,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from nds_ui import tests
D=ROOT/'work/nds_c_probe';M=0xffffffff
def nm():
    tool=tests.ghidra_assets().parent.parent/'tools/nds32/prefix/bin/nds32le-elf-nm'
    return {l.split()[2]:int(l.split()[0],16) for l in subprocess.run([str(tool),str(D/'probe.elf')],capture_output=True,text=True).stdout.splitlines()}
def deep(a,b,c):
    leaf=lambda x:(x*3+1)&M;buf=[(leaf((a+i)&M)+b)&M for i in range(12)]
    s=sum(buf[i]*(i+1) for i in range(12))&M;return (s+leaf(c)+((a^b)*(b^c))-(a+c))&M
def s32(x):return x-(1<<32) if x>>31 else x
def main():
    sym=nm();rng=random.Random(0xc0de);calls=[];BUF=0x20018000
    for v in range(1000):
        t=(str(v)).encode();calls.append(dict(fn='fmt_pct',entry=hex(sym['fmt_pct']),args=[v,BUF],a0=BUF+len(t),mem=dict(addr=hex(BUF),hex=t.hex())))
    edge=[0,1,2,3,7,9,10,99,100,999,1000,0x7fffffff,0x80000000,0xfffffffe,M]
    pairs=[(a,b) for a in edge for b in edge if b]+[(rng.randrange(1<<32),rng.randrange(1,1<<32)) for _ in range(300)]+[(rng.randrange(1<<32),rng.randrange(1,1000)) for _ in range(300)]
    for a,b in pairs:
        calls+= [dict(fn='divq',entry=hex(sym['divq']),args=[a,b],a0=a//b),dict(fn='divm',entry=hex(sym['divm']),args=[a,b],a0=a%b),
                 dict(fn='divqm',entry=hex(sym['divqm']),args=[a,b],a0=((a//b)*1000+a%b)&M)]
        sa,sb=s32(a),s32(b)
        if not(sa==-2**31 and sb==-1):
            q=abs(sa)//abs(sb)*(1 if (sa<0)==(sb<0) else -1);calls+=[dict(fn='sdivq',entry=hex(sym['sdivq']),args=[a,b],a0=q&M),dict(fn='sdivm',entry=hex(sym['sdivm']),args=[a,b],a0=(sa-q*sb)&M)]
    for _ in range(200):
        a,b,c=(rng.randrange(1<<32) for _ in range(3));calls.append(dict(fn='deep',entry=hex(sym['deep']),args=[a,b,c],a0=deep(a,b,c)))
    (D/'vectors.json').write_text(json.dumps(dict(base='0x170000',leaf=hex(sym['leaf']),calls=calls))+'\n')
    t=time.time();rep=tests.run_ghidra(D,script='NDSCProbe.java');rep['seconds']=round(time.time()-t,1);print(json.dumps(rep,indent=1))
if __name__=='__main__':main()
