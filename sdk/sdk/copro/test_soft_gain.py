"""Offline checks of the P1 soft-gain coprocessor program in the simulator.

  python3 -B -m unittest sdk.copro.test_soft_gain        (from the project root)
"""
import json
from pathlib import Path
import re
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from protocol import copro_isa as isa,copro_sim as cs  # noqa: E402
from sdk.copro import asm,soft_gain as sg               # noqa: E402

fb=asm.fbits
ff=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]
r32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]


def vector(limit=0.25,gain=0.7):
    """64 float32 samples: ramp through and beyond the limit both ways, exact edges, zeros, tiny and awkward values."""
    xs=[(-1.0+i/23.5) for i in range(48)]
    xs+=[0.0,-0.0,limit/gain,-limit/gain,limit,-limit,1e-20,-1e-20,0.1,-0.1,1/3,-1/3,0.9999999,-0.9999999,3.0,-3.0]
    assert len(xs)==64
    return [fb(x) for x in xs]


def stock_eq_words():
    words=[]
    for line in (ROOT/'work/coprocessor/disasm/g5_04_Mess_EQ.txt').read_text().splitlines():
        m=re.match(r'^([0-9a-f]{4})  ([0-9a-f]{8})  ',line)
        if m:
            assert int(m[1],16)==0xe00+len(words);words.append(int(m[2],16))
    assert len(words)==0x5d and words[0]==sg.DISPLACED
    return words


def install(sim,gain,limit,samples):
    for index,value in sg.writes(gain,limit):sim.write(index,value)
    for i,b in enumerate(samples):sim.write(sg.IN_LEFT+i,b)


class ProgramShape(unittest.TestCase):
    def test_words_budget_and_confirmed_forms(self):
        words=sg.program();w=sg.writes()
        self.assertEqual(len(words),17);self.assertEqual(len(w),21);self.assertLessEqual(len(w)+1,sg.MAX_WRITES)
        self.assertEqual(words[-2:],[0x75060f9c,0xae0a4000]);self.assertEqual(w[-1],(0x1e00,0xae064f80))
        self.assertEqual([i for i,_ in w],[0xf00,0xf01,0xf02]+list(range(0x1f80,0x1f91))+[0x1e00])
        for word in words+[w[-1][1]]:self.assertEqual(isa.decode(word)[1],'X',f'{word:#010x}')
        self.assertEqual([f'{x:08x}' for x in words],
            ['70060013','71060040','52000f00','53000f01','54000f02','e6020000','86260007','c37f0006','9f0a3c01','f7340000',
             'c74f0006','9f0a3c01','f7440000','e0750000','a1040f85','75060f9c','ae0a4000'])
        # Registers written: r0..r4, r6, r7 (and r5 by the displaced instruction, r14/r15 implicitly).
        written=set()
        for word in words:
            text=isa.decode(word)[0];m=re.match(r'r(\d+)(\.hi|\.lo)? [+\-*]?=',text)
            if m:written.add(int(m[1]))
            if 'D[r0++]' in text or text.startswith('loop r'):written.add(int(re.search(r'r(\d+)',text)[1]))
        self.assertEqual(written,{0,1,2,3,4,5,6,7})

    def test_assembler_refuses_unconfirmed_shapes(self):
        for bad in ([('fmul',6,6,2)],[('li',14,1)],[('fadd',1,2,3),('run_next_if_negative',),('mov',1,2)],[('word',0x20090000,'block')],[('word',0x823c0004,'open')]):
            with self.assertRaises(asm.AsmError):asm.assemble(bad,0xf80)

    def test_batch_file_matches_builder(self):
        path=ROOT/'work/copro_experiments/batches/p1_soft_gain.json';b=json.loads(path.read_text())
        self.assertEqual(b,sg.batch());e=b[0]
        self.assertEqual(len(e['harness'])+len(e['variants']),22);self.assertEqual(e['harness'][-1],['0x1e00','0xae064f80'])
        self.assertEqual(e['test_index'],'0x0f00');self.assertEqual(e['variants'],[['gain_0.5','0x3f000000']])
        # Same shape rules as scripts/copro_experiment.validate (not imported: that module pulls in the device session).
        self.assertLessEqual(len(e['reads']),16)
        for i,v in e['harness']:self.assertTrue(0<=int(i,16)<0x2000 and 0<=int(v,16)<=0xffffffff)


class ProgramBehaviour(unittest.TestCase):
    def run_patch(self,gain,limit,samples):
        sim=cs.Sim();install(sim,gain,limit,samples)
        self.assertEqual(sim.run(0xe00,stop=(0xe01,)),'stop')
        return sim

    def test_matches_float32_reference(self):
        for gain,limit in ((0.7,0.25),(1.0,64.0),(0.5,64.0),(2.0,1.0),(0.3333,0.001),(-1.5,0.5)):
            samples=vector(0.25,0.7);sim=self.run_patch(gain,limit,samples)
            got=[sim.read(sg.IN_LEFT+i) for i in range(64)];want=sg.reference(samples,gain,limit)
            self.assertEqual(got,want,(gain,limit))
            # Independent statement of the same thing, in plain Python floats.
            for b,g in zip(samples,got):
                y=max(-r32(limit),min(r32(limit),r32(ff(b)*r32(gain))))
                self.assertEqual(ff(g),y)
            self.assertEqual(sim.r[5],0xf9c);self.assertEqual(sim.r[0],0x53);self.assertEqual(sim.r[1],0)
            self.assertEqual(sim.steps,1+5+64*10-self.skipped(samples,gain,limit)+2)   # call, setup, loop, tail
            # Nothing outside the left input window was written.
            self.assertEqual([i for i,v in enumerate(sim.d) if v is not None],list(range(0x13,0x53))+[0xf00,0xf01,0xf02])

    def skipped(self,samples,gain,limit):
        # Each sample skips one word per clamp that does not fire.
        n=0
        for b in samples:
            y=r32(ff(b)*r32(gain));n+=(0 if y>r32(limit) else 1)+(0 if min(y,r32(limit))<-r32(limit) else 1)
        return n

    def test_unity_gain_is_bit_transparent_and_limit_is_exact(self):
        samples=vector();sim=self.run_patch(1.0,64.0,samples)
        self.assertEqual([sim.read(0x13+i) for i in range(64)],samples)
        sim=self.run_patch(1.0,0.25,samples);out=[ff(sim.read(0x13+i)) for i in range(64)]
        self.assertEqual(max(out),0.25);self.assertEqual(min(out),-0.25)
        self.assertEqual([o for o,b in zip(out,samples) if abs(ff(b))<=0.25],[ff(b) for b in samples if abs(ff(b))<=0.25])

    def test_gain_change_is_one_data_write(self):
        samples=vector();sim=cs.Sim();install(sim,1.0,64.0,samples)
        sim.write(sg.GAIN,fb(0.5));sim.run(0xe00,stop=(0xe01,))
        self.assertEqual([sim.read(0x13+i) for i in range(64)],sg.reference(samples,0.5,64.0))

    def test_non_finite_input_is_refused_by_the_simulator(self):
        samples=vector();samples[5]=0x7f800000
        with self.assertRaises(cs.UnconfirmedInstruction):self.run_patch(1.0,1.0,samples)


class WithStockEq(unittest.TestCase):
    """Program followed by the stock EQ program (active path), using static-only forms.

    This part is not a hardware-confirmed simulation: it relies on Sim(static=True) readings of
    end-of-block, the two block primitives and the high-half AND, and on the single measured
    value of the approximate 1/sqrt at 1.0. It checks two things: (1) the stock EQ never reads
    a register the soft-gain program left behind, and (2) the processed window reaches both
    output windows with the arithmetic expected of pass-through biquads."""
    GAIN_OUT=0.75

    def build(self,samples,gain,limit):
        sim=cs.Sim(static=True);sim.load_program(0xe00,stock_eq_words());install(sim,gain,limit,samples)
        sim.write(0xf9c,1)                                   # EQ flag: 1 = the skip-if-1 at 0xe02 skips the jump to the bypass path (X)
        for k in range(5):
            for j,v in enumerate((1.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0)):sim.write(0xf9d+10*k+j,fb(v))   # b0 b1 b2 (1.0) a1 a2, four state words
        sim.write(0xfcf,fb(self.GAIN_OUT));sim.write(0xfd0,fb(self.GAIN_OUT))    # output level: target and current
        return sim

    def test_program_then_stock_eq(self):
        gain,limit=0.7,0.25;samples=vector(limit,gain);sim=self.build(samples,gain,limit)
        self.assertEqual(sim.run(0xe00,stop=(0xe01,)),'stop')
        # Forget every register the program used except r5: if stock code read one, the simulator would raise.
        for n in (0,1,2,3,4,6,7,15):sim.r[n]=None
        self.assertEqual(sim.run(0xe01),'end')
        # Reference: five biquads with b = (1, 0, 0), a = (0, 0), each scaled by rsqrt(1.0)^2 as
        # the stock routine does, then the output level. Every step rounded to float32.
        k=r32(ff(0x3f7fffb7)*ff(0x3f7fffb7));block=[ff(b) for b in sg.reference(samples,gain,limit)]
        for _ in range(5):
            x1=x2=y1=y2=0.0;out=[]
            for x in block:
                acc=r32(x*1.0);acc=r32(acc+r32(x1*0.0));acc=r32(acc+r32(x2*0.0))
                fb_sum=r32(y1*0.0);fb_sum=r32(fb_sum+r32(y2*0.0))
                y=r32(r32(acc-fb_sum)*k);x2,x1,y2,y1=x1,x,y1,y;out.append(y)
            block=out
        want=[fb(r32(r32(self.GAIN_OUT)*y)) for y in block]
        self.assertLess(max(abs(ff(w)-self.GAIN_OUT*ff(b)) for w,b in zip(want,sg.reference(samples,gain,limit))),1e-4)
        self.assertEqual([sim.read(0x93+i) for i in range(64)],want);self.assertEqual([sim.read(0xd3+i) for i in range(64)],want)

    def test_stock_eq_alone_runs_with_all_registers_undefined(self):
        samples=vector();sim=self.build(samples,1.0,64.0);sim.write(0x1e00,sg.DISPLACED)
        self.assertEqual(sim.run(0xe00),'end')              # r0..r13 start undefined: the EQ sets everything it reads

    def test_bypass_path_reads_only_registers_it_sets(self):
        # The condition that takes the jump at 0xe03 was never observed, so start at the bypass path directly.
        samples=vector();sim=self.build(samples,0.5,64.0)
        sim.run(0xe00,stop=(0xe01,))
        for n in range(16):sim.r[n]=None
        self.assertEqual(sim.run(0xe2e),'end')
        self.assertEqual([sim.read(0x93+i) for i in range(64)],sg.reference(samples,0.5,64.0))
        self.assertEqual([sim.read(0xd3+i) for i in range(64)],sg.reference(samples,0.5,64.0))


if __name__=='__main__':unittest.main()
