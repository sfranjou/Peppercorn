"""Shared-runner decodes added 2026-10-19 (UXTAB, USAT): exact results vs Python references."""
import struct,sys,unittest
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parent.parent),str(Path(__file__).resolve().parent)]
import run_effect
BASE=0x10000c00
def run(code,args):
    payload=code+bytes.fromhex('7047')                       # bx lr
    r=run_effect.OverlayRunner(payload+bytes(64),BASE,0x2c00,BASE,BASE)
    r.cpu.call(BASE,tuple(args));return r.cpu.r[0]
def t32(hw,hw2):return struct.pack('<HH',hw,hw2)
class Ops(unittest.TestCase):
    def test_usat(self):
        for v in (0,1,7,8,100,0xffffffff,0x80000000,0x7fffffff,3):
            for sat in (0,3,8,16,31):
                for sh,n in ((0,0),(0,2),(1,1),(1,4)):
                    hw=0xf380|sh<<5;hw2=(n>>2)<<12|(n&3)<<6|sat     # usat r0,#sat,r0,{lsl|asr} #n
                    s=v-(1<<32) if v&0x80000000 else v;s=s>>n if sh else s<<n
                    self.assertEqual(run(t32(hw,hw2),[v]),min(max(s,0),(1<<sat)-1),(v,sat,sh,n))
    def test_uxtab(self):
        for a in (0,5,0xffffffff):
            for b in (0x12345678,0xff,0x80000001):
                for rot in range(4):
                    hw2=0xf080|rot<<4|1                              # uxtab r0, r0, r1, ror #8*rot
                    x=((b>>8*rot)|(b<<(32-8*rot)))&0xffffffff if rot else b
                    self.assertEqual(run(t32(0xfa50,hw2),[a,b]),(a+(x&255))&0xffffffff)
    def test_ldr_str_imm8_writeback(self):
        BUF=0x20001200
        for pre in (0,1):
            for up in (0,1):
                for imm in (0,4,16,252):              # word-aligned so memory holds its own address
                    hw2=0x0900|pre<<10|up<<9|imm|5<<12              # rt=r5
                    start=BUF+0x200
                    r=run_effect.OverlayRunner(t32(0xf853,hw2)+t32(0xf843,hw2)+bytes.fromhex('2846'+'7047')+bytes(64),BASE,0x2c00,BASE,BASE)
                    for k in range(-300,300,4):r.cpu.w32(start+k,(start+k)&0xffffffff)
                    r.cpu.call(BASE,(0,0,0,start))                    # ldr r5,[r3,#±imm]{!}; str r5,[r3,#±imm]{!}; mov r0,r5
                    step=imm if up else -imm;a1=start+step if pre else start
                    self.assertEqual(r.cpu.r[0],a1);self.assertEqual(r.cpu.r[3],start+2*step)
                    self.assertEqual(r.cpu.r32((start+2*step) if pre else start+step),a1)
if __name__=='__main__':unittest.main()
