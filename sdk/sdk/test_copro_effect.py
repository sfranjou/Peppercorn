"""Offline checks of the coprocessor-effect SDK path and of the first DST-group effect, Hard Clip.

  python3 -B -m unittest sdk.test_copro_effect        (from the project root)

Nothing here contacts the pedal. What each class establishes, and with what kind of evidence:
  Build        the record carries the assembled program as its secondary payload; sizes, IDs.
  Frame        sdk/copro/frame.py accepts our program and refuses broken ones; the frame words
               are the ones found in the stock DST programs of region g.
  Program      the program in the STRICT simulator (hardware-executed forms only) against a
               float32 reference; bypass; write footprint; step count.
  ArmHalf      the built ARM payload in the project's Thumb/VFP interpreter: cells written.
  Chain        our program followed by stock programs. Strict up to the CAB slot base with a
               bypassed stock AMP; the rest (stock EQ) needs Sim(static=True) and a one-word
               stand-in for the CAB program, so that part is NOT hardware-confirmed semantics.
"""
import json
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
for p in (ROOT,ROOT/'sdk'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
import build_effect                                    # noqa: E402
from run_effect import OverlayRunner,PARAMS,RAM        # noqa: E402
from protocol import copro_isa as isa,copro_sim as cs  # noqa: E402
from protocol.overlay_image import parse_overlay,parse_descriptor,parse_container  # noqa: E402
from sdk.copro import asm,frame                         # noqa: E402
from sdk.copro.test_soft_gain import vector,stock_eq_words  # noqa: E402

EFFECT=ROOT/'sdk/effects/hard_clip'
OUT=ROOT/'work/sdk_build/hard_clip'
STOCK_G=ROOT/'work/v110/decoded_g.bin'
INSTALLED_E=ROOT/'work/custom_images/mod008_afterglow/regions/decoded_e.bin'
fb=asm.fbits
ff=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]
r32=lambda x:struct.unpack('<f',struct.pack('<f',x))[0]


def load_module(name):
    import importlib.util
    spec=importlib.util.spec_from_file_location('hard_clip_'+name,EFFECT/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


program=load_module('program');model=load_module('model');C=program.CELLS
_manifest=None


def manifest():
    global _manifest
    if _manifest is None:_manifest=build_effect.build(EFFECT,OUT)
    return _manifest


def words():
    manifest();b=(OUT/'secondary.bin').read_bytes();return list(struct.unpack(f'<{len(b)//4}I',b))


def stock_programs(group):
    g=parse_container(STOCK_G.read_bytes())
    for blob in g.groups[group]:
        s=parse_overlay(blob).secondary;yield list(struct.unpack(f'<{len(s)//4}I',s))


def new_sim(samples,gain,limit,level,enable=1,static=False):
    sim=cs.Sim(static=static);sim.load_program(0,words())
    for k,v in (('ENABLE',enable),('GAIN',fb(gain)),('LIMIT',fb(limit)),('NLIMIT',fb(-limit)),('LEVEL',fb(level))):sim.write(C[k],v)
    for i,b in enumerate(samples):sim.write(0x13+i,b)
    return sim


class Build(unittest.TestCase):
    def test_record_carries_program_and_fits(self):
        m=manifest();o=parse_overlay((OUT/'record.bin').read_bytes())
        self.assertEqual(o.primary,(OUT/'payload.bin').read_bytes());self.assertEqual(o.secondary,(OUT/'secondary.bin').read_bytes())
        self.assertEqual(list(struct.unpack(f'<{len(o.secondary)//4}I',o.secondary)),asm.assemble(program.SOURCE,0))
        self.assertEqual(m['slot_base'],'0x10003800');self.assertLessEqual(m['payload_bytes']+m['state_bytes'],0x1000)
        self.assertEqual(m['secondary_bytes'],4*25);self.assertLessEqual(m['secondary_bytes'],0x1400)
        self.assertEqual(m['copro']['non_x_words'],[]);self.assertEqual(m['copro']['destination'],'0x28004000')
        for cb in (o.init_callback,o.process_callback):self.assertTrue(0x10003800<=cb&~1<0x10003800+len(o.primary) and cb&1)
        # Same record layout as the stock DST records: six words, prefix, primary, secondary, nothing else.
        stock=parse_overlay(parse_container(STOCK_G.read_bytes()).groups[2][5])   # La Charger: the 16-byte prefix
        self.assertEqual(o.prefix,stock.prefix)

    def test_descriptor_follows_dst_conventions(self):
        manifest();d=parse_descriptor((OUT/'descriptor.bin').read_bytes())
        self.assertEqual((d.name,d.type_name,[p.name for p in d.parameters]),('Hard Clip','Distortion',['Gain','VOL']))
        self.assertEqual(d.public_id,0x0300007e)
        for path in (ROOT/'work/v110/decoded_e.bin',INSTALLED_E):
            cat=parse_container(path.read_bytes()[0x10000:]);ids=[parse_descriptor(b).public_id for g in cat.groups[:10] for b in g]
            self.assertNotIn(d.public_id,ids)
            dst=[parse_descriptor(b) for b in cat.groups[2]]
            self.assertEqual({x.public_id>>24 for x in dst},{3});self.assertEqual({x.word1 for x in dst},{0xffffffff})
            self.assertEqual({x.count_word>>8 for x in dst},{d.count_word>>8})
            self.assertLessEqual(len(d.name),max(len(x.name) for x in dst));self.assertIn(d.type_name,{x.type_name for x in dst})
            # Stock DST parameter records: knob 0 on the first parameter, 255 on the rest, flags 0, display 21, 0..100 step 1.
            sora=next(x for x in dst if x.name=='Sora Fuzz')
            strip=lambda ps:[(p.minimum_bits,p.maximum_bits,p.step_bits,p.default_bits,p.storage_index,p.knob,p.flags,p.display_code,p.lead) for p in ps]
            self.assertEqual(strip(d.parameters),strip(sora.parameters))

    def test_existing_effects_are_unaffected_and_group_rules_hold(self):
        # A DST effect without a program, or a program in an ARM-only group, is refused.
        import tempfile,shutil
        with tempfile.TemporaryDirectory() as t:
            t=Path(t);shutil.copytree(EFFECT,t/'e');meta=json.loads((t/'e/effect.json').read_text());del meta['copro'];(t/'e/effect.json').write_text(json.dumps(meta))
            with self.assertRaises(SystemExit):build_effect.build(t/'e',t/'o')
            meta=json.loads((EFFECT/'effect.json').read_text());meta['group']=6;(t/'e/effect.json').write_text(json.dumps(meta))
            with self.assertRaises(SystemExit):build_effect.build(t/'e',t/'o2')


class Frame(unittest.TestCase):
    def test_stock_dst_programs_share_the_frame(self):
        progs=list(stock_programs(2));self.assertEqual(len(progs),10);at_zero=0
        for w in progs:
            self.assertEqual(tuple(w[:2]),frame.STOCK_DST_ENTRY[:2])
            i=next(k for k in range(len(w)) if tuple(w[k:k+3])==frame.STOCK_DST_ENTRY[2:]);at_zero+=i==2
            t=w[i+3];self.assertEqual(t>>16,0xa008);self.assertEqual(w[t&0xfff],0xa0080500);self.assertEqual(w[(t&0xfff)-1],0xa0080500)
            flow=frame.scan(w,0);self.assertEqual(flow['exits'],['0x500'])
            self.assertEqual([k for k,x in enumerate(w) if x>>16==0xa008 and x&0xfff>=len(w)],[(t&0xfff)-1,t&0xfff])
        self.assertEqual(at_zero,9)                                   # Plustortion does four cell copies before the test
        for x in frame.STOCK_DST_ENTRY+(0xa0080500,):self.assertEqual(isa.decode(x)[1],'X')

    def test_no_stock_stage_reads_a_register_left_by_the_previous_one(self):
        # Static dataflow (limits in sdk/copro/frame.py); none of the flagged reads is at a slot entry.
        flagged={}
        for group,base in ((2,0),(3,0x500),(4,0xb00),(5,0xe00),(9,0x500)):
            for i,w in enumerate(stock_programs(group)):
                f=frame.scan(w,base)
                if f['read_before_write']:flagged[(group,i)]=f['read_before_write']
        # 2026-10-20 (i_fft_*): `eRS6/7` program loads and `aR06 6ttt` calls are now decoded. N->S is no longer
        # flagged; the scan now follows the r14 6-flavour calls of DST 0/5 and AMP 7/8 into their subroutines,
        # where state stores read r2 on some call path (callee writes ignored: conservative). None at an entry.
        self.assertEqual(set(flagged),{(2,4),(2,0),(2,5),(3,7),(3,8)})
        # Plustortion's old flags (0x00e/0x00f/0x011, after its then-unknown `eRS7` loads) are resolved.
        self.assertFalse({'0x00e','0x00f','0x011'}&set(flagged[(2,4)]))
        entries={2:0,3:0x500}
        for (g,i),reads in flagged.items():self.assertNotIn(f'{entries[g]:#05x}',reads)

    def test_checker_accepts_ours_and_refuses_broken_programs(self):
        w=words();r=frame.check(2,w);self.assertEqual((r['words'],r['non_x_words'],r['dataflow']['exits']),(25,[],['0x500']))
        def bad(edit,why):
            v=list(w);edit(v)
            with self.assertRaises(frame.FrameError,msg=why):frame.check(2,v)
        bad(lambda v:v.__setitem__(0x17,0xa00e0000),'end word in the DST slot')
        bad(lambda v:v.__setitem__(0x17,0xa0080b00),'exit to another slot')
        bad(lambda v:v.__setitem__(0x18,0xf0000000|4<<16),'bypass exit replaced: falls off the end')
        bad(lambda v:v.__setitem__(2,0x75060194),'wrong flag cell')
        bad(lambda v:v.__setitem__(0xb,0xf8940000),'reads r9 before any write')
        bad(lambda v:v.__setitem__(0xb,0x58000398),'reads an AMP cell')
        bad(lambda v:v.__setitem__(0xb,0x20080000),'block primitive')
        bad(lambda v:v.__setitem__(0x16,0xa1040019),'loop target outside')
        bad(lambda v:v.extend([0xa0080500]),'unreachable word')
        bad(lambda v:v.extend([0xa0080500]*0x500),'too long')
        self.assertEqual(frame.check(2,w,allowed_non_x=[0x20080000])['non_x_words'],[])


class Program(unittest.TestCase):
    CASES=((0.7,0.25,1.0),(1.0,64.0,1.0),(13.25,0.05,1.0),(50.0,0.05,4.0),(2.0,1.0,0.36),(0.3333,0.001,0.0),(1.0,0.05,1.0))

    def test_active_path_matches_float32_reference(self):
        for gain,limit,level in self.CASES:
            samples=vector(0.25,0.7);sim=new_sim(samples,gain,limit,level)
            self.assertEqual(sim.run(0,stop=(0x500,)),'stop');self.assertEqual(sim.pc,0x500)
            got=[sim.read(0x13+i) for i in range(64)];self.assertEqual(got,program.reference(samples,gain,limit,level),(gain,limit,level))
            for b,g in zip(samples,got):
                self.assertEqual(ff(g),r32(max(-r32(limit),min(r32(limit),r32(ff(b)*r32(gain))))*r32(level)))
            # Footprint: D[0x10], the window and nothing else; cells only read.
            self.assertEqual([i for i,v in enumerate(sim.d) if v is not None],[0x10]+list(range(0x13,0x53))+sorted(C.values()))
            self.assertEqual(sim.read(0x10),0);self.assertEqual([sim.read(C[k]) for k in ('ENABLE','GAIN')],[1,fb(gain)])
            self.assertLessEqual(sim.steps,5+6+64*11+1);self.assertGreaterEqual(sim.steps,5+6+64*9+1)

    def test_unity_setting_is_bit_transparent_below_the_limit(self):
        samples=[fb(x) for x in (0.0499,-0.0499,0.05,-0.05,1e-3,-3e-2)]+vector(0.25,0.7)[:58]
        sim=new_sim(samples,1.0,0.05,1.0);sim.run(0,stop=(0x500,))
        for b,g in zip(samples,[sim.read(0x13+i) for i in range(64)]):
            if abs(ff(b))<=r32(0.05):self.assertEqual(g&0x7fffffff or 0,b&0x7fffffff or 0);self.assertEqual(ff(g),ff(b))
            else:self.assertEqual(abs(ff(g)),r32(0.05))

    def test_bypass_leaves_the_window_untouched(self):
        for flag in (0,2,0x100):                       # bit 0 clear: executed on the pedal with these three values (d1 follow-up)
            samples=vector();sim=new_sim(samples,50.0,0.05,4.0,enable=flag)
            self.assertEqual(sim.run(0,stop=(0x500,)),'stop')
            self.assertEqual([sim.read(0x13+i) for i in range(64)],samples);self.assertEqual(sim.steps,7)
            self.assertEqual([pc for pc,_ in self._trace(samples,flag)],[0,1,2,3,4,5,0x18])

    def _trace(self,samples,flag):
        sim=new_sim(samples,1.0,1.0,1.0,enable=flag);sim.trace=[];sim.run(0,stop=(0x500,));return sim.trace

    def test_every_executed_word_is_a_hardware_executed_form(self):
        sim=new_sim(vector(),13.25,0.05,1.0);sim.trace=[];sim.run(0,stop=(0x500,))       # strict simulator: would raise otherwise
        self.assertEqual({isa.decode(w)[1] for _,w in sim.trace},{'X'})
        self.assertEqual({pc for pc,_ in sim.trace},set(range(0x18))-{5})                    # the clamps both fire and both idle in this vector

    def test_non_finite_or_denormal_input_is_outside_what_was_observed(self):
        for bad in (0x7f800000,0x7fc00000):
            samples=vector();samples[3]=bad
            with self.assertRaises(cs.UnconfirmedInstruction):new_sim(samples,1.0,1.0,1.0).run(0,stop=(0x500,))


class ArmHalf(unittest.TestCase):
    def runner(self):
        manifest();self.cop=bytearray(0x8100);return OverlayRunner.from_build(OUT,extra=[(0x28000000,self.cop)])

    def cells(self):
        return {k:struct.unpack_from('<I',self.cop,4*v)[0] for k,v in C.items()}

    def test_init_and_process_write_exactly_the_cells(self):
        for gain,vol in ((50.0,50.0),(0.0,50.0),(100.0,100.0),(1.0,0.0),(37.0,73.0)):
            p=[gain,vol]+[0.0]*6;r=self.runner();r.init(p)
            self.assertEqual(self.cells(),model.cells(gain,vol,enable=0),(gain,vol))
            for enable,want in ((1,1),(0,0),(0xff,1),(2,1)):
                frames=[(0.01*i,-0.02*i) for i in range(64)];out=r.process(frames,p,enable=enable)
                self.assertEqual([(fb(a),fb(b)) for a,b in out],[(fb(a),fb(b)) for a,b in frames])          # samples untouched
                self.assertEqual(self.cells(),model.cells(gain,vol,enable=want),(gain,vol,enable))
            touched=[i//4 for i in range(0,len(self.cop),4) if self.cop[i:i+4]!=b'\0\0\0\0']
            self.assertTrue(set(touched)<=set(C.values()))                                               # nothing else in the coprocessor window
            self.assertEqual(r.cpu.body_written,set())
        self.assertLess(max(r.process_steps),40)

    def test_cell_values(self):
        c=model.cells(0.0,50.0);self.assertEqual((c['GAIN'],c['LEVEL']),(0x3f800000,0x3f800000))     # exactly 1.0: transparent setting
        self.assertEqual((c['LIMIT'],c['NLIMIT']),(0x3d4ccccd,0xbd4ccccd))
        self.assertAlmostEqual(ff(model.cells(100.0,100.0)['GAIN']),50.0,places=4);self.assertAlmostEqual(ff(model.cells(100.0,100.0)['LEVEL']),4.0,places=5)
        self.assertAlmostEqual(ff(model.cells(50.0,50.0)['GAIN']),13.25,places=4)

    def test_arm_cells_drive_the_program(self):
        samples=[fb(0.06*(i-32)/32) for i in range(64)]
        for gain,vol in ((0.0,50.0),(50.0,50.0),(100.0,25.0)):
            p=[gain,vol]+[0.0]*6;r=self.runner();r.init(p);r.process([(0.0,0.0)]*64,p,enable=1)
            sim=cs.Sim();sim.load_program(0,words())
            for k,v in self.cells().items():sim.write(C[k],v)
            for i,b in enumerate(samples):sim.write(0x13+i,b)
            sim.run(0,stop=(0x500,));c=model.cells(gain,vol)
            want=program.reference(samples,ff(c['GAIN']),ff(c['LIMIT']),ff(c['LEVEL']))
            self.assertEqual([sim.read(0x13+i) for i in range(64)],want)
            if gain==0.0:self.assertEqual(want,[b if abs(ff(b))<=r32(0.05) else fb(r32(0.05) if ff(b)>0 else -r32(0.05)) for b in samples])


class Chain(unittest.TestCase):
    GAIN,LIMIT,LEVEL=13.25,0.05,1.0

    def test_strict_through_bypassed_stock_amps_to_the_cab_slot(self):
        """Hardware-executed forms only: our program, then each stock AMP program with its flag
        cell D[0x398] = 0, must arrive at PC 0xb00 with the window as we left it. Registers are
        erased at the slot boundary, so an AMP program relying on DST leftovers would raise."""
        samples=vector(0.05,13.25);want=program.reference(samples,self.GAIN,self.LIMIT,self.LEVEL);ran=skipped=0
        for amp in stock_programs(3):
            sim=new_sim(samples,self.GAIN,self.LIMIT,self.LEVEL);sim.load_program(0x500,amp);sim.write(0x398,0)
            self.assertEqual(sim.run(0,stop=(0x500,)),'stop');sim.reset_registers()
            try:self.assertEqual(sim.run(0x500,stop=(0xb00,)),'stop')
            except (cs.UnconfirmedInstruction,cs.UndefinedValue):skipped+=1;continue       # three AMPs start with state words the decoder does not know
            ran+=1;self.assertEqual([sim.read(0x13+i) for i in range(64)],want)
        self.assertEqual((ran,skipped),(29,3))

    def test_static_to_the_end_of_block_through_the_stock_eq(self):
        """NOT hardware-confirmed semantics: Sim(static=True) (end word, block copy/multiply) and a
        one-word stand-in `jump 0xe00` for the CAB program (its bypass test `960a00ae` and its
        convolver use forms nobody executed). Shows the chain reaches the end word and that the
        output windows carry our result through pass-through EQ biquads."""
        samples=vector(0.05,13.25);sim=new_sim(samples,self.GAIN,self.LIMIT,self.LEVEL,static=True)
        sim.load_program(0x500,next(stock_programs(3)));sim.write(0x398,0)                 # Tweedy, bypassed
        sim.write(0x1000+0xb00,isa.jump(0xe00));sim.load_program(0xe00,stock_eq_words());sim.write(0xf9c,1)
        for k in range(5):
            for j,v in enumerate((1.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,0.0,0.0)):sim.write(0xf9d+10*k+j,fb(v))
        sim.write(0xfcf,fb(0.75));sim.write(0xfd0,fb(0.75))
        self.assertEqual(sim.run(0),'end')
        ours=[ff(b) for b in program.reference(samples,self.GAIN,self.LIMIT,self.LEVEL)]
        for base in (0x93,0xd3):
            out=[ff(sim.read(base+i)) for i in range(64)]
            self.assertLess(max(abs(o-0.75*y) for o,y in zip(out,ours)),1e-5)
        self.assertLess(sim.steps,8000)


class RamStage(unittest.TestCase):
    """Stage A (sdk/effects/hard_clip/ram_stage.py): our body reached from a stock DST program's frame."""
    def test_patch_on_every_standard_stock_dst_program(self):
        stage=load_module('ram_stage');samples=vector(0.05,13.25);hosts=0
        for stock in stock_programs(2):
            if tuple(stock[:5])!=frame.STOCK_DST_ENTRY:continue                           # Plustortion
            hosts+=1;self.assertLess(len(stock),stage.BODY);ph=stage.phases(13.25,0.05,1.0,stock[6])
            self.assertEqual(len(ph['logged_writes']),5);self.assertEqual(ph['logged_writes'][-1],['0x1006','0xa0080400'])
            for flag,want in ((1,program.reference(samples,13.25,0.05,1.0)),(0,samples)):
                sim=cs.Sim();sim.load_program(0,stock+[0]*(0x500-len(stock)))
                self.assertEqual(sim.read(int(next(iter(ph['preconditions']['read_equal'])),16)),stock[6])
                for i in ph['preconditions']['read_zero']:self.assertEqual(sim.read(int(i,16)),0)
                for i,v in ph['body_writes_then_commit']+ph['logged_writes']:sim.write(int(i,16),int(v,16))
                sim.write(C['ENABLE'],flag)
                for i,b in enumerate(samples):sim.write(0x13+i,b)
                sim.trace=[];self.assertEqual(sim.run(0,stop=(0x500,)),'stop')              # strict simulator
                self.assertEqual([sim.read(0x13+i) for i in range(64)],want)
                self.assertEqual({pc for pc,_ in sim.trace},({0,1,2,3,4,6}|set(range(stage.BODY,stage.BODY+18))) if flag else {0,1,2,3,4,5,stock[5]&0xfff})
        self.assertEqual(hosts,9)
        w=words();b=stage.body();self.assertEqual(len(b),18);self.assertEqual(b[:-2],w[6:0x16]);self.assertEqual(b[-2:],[0xa1040406,0xa0080500])


if __name__=='__main__':unittest.main()
