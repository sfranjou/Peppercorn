"""Offline checks of Tube Drive (sdk/effects/tube_drive), the second DST-group coprocessor effect.

  python3 -B -m unittest sdk.test_tube_drive        (from the project root)

Nothing here contacts the pedal. Kinds of evidence:
  Build     record/descriptor shape, unused ID, frame checker, every word an executed form.
  Program   the program in the STRICT simulator (hardware-executed forms only, refuses denormal
            results and anything unobserved) against model.py bit for bit, several blocks in a
            row with the state cells carried by the simulator's memory.
  Model     model.py against plain double-precision mathematics (filter responses, curve), and
            the long silent tail where the strict simulator cannot follow (denormals).
  ArmHalf   the built ARM payload in the project's Thumb/VFP interpreter: cells written.
  Chain     our program followed by each bypassed stock AMP program, strict.
  RamStage  the RAM-stage write list applied to every standard stock DST program, strict.
"""
import cmath
import json
import math
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
for p in (ROOT,ROOT/'sdk'):
    if str(p) not in sys.path:sys.path.insert(0,str(p))
import build_effect                                    # noqa: E402
from run_effect import OverlayRunner                    # noqa: E402
from protocol import copro_isa as isa,copro_sim as cs  # noqa: E402
from protocol.overlay_image import parse_overlay,parse_descriptor,parse_container  # noqa: E402
from sdk.copro import asm,frame                         # noqa: E402

EFFECT=ROOT/'sdk/effects/tube_drive'
OUT=ROOT/'work/sdk_build/tube_drive'
STOCK_G=ROOT/'work/v110/decoded_g.bin'
CATALOGS=(ROOT/'work/v110/decoded_e.bin',ROOT/'work/custom_images/mod009_candidate_hard_clip/regions/decoded_e.bin')
fb=asm.fbits
ff=lambda b:struct.unpack('<f',struct.pack('<I',b))[0]
denormal=lambda b:b&0x7f800000==0 and b&0x007fffff!=0


def load_module(name):
    import importlib.util
    spec=importlib.util.spec_from_file_location('tube_drive_'+name,EFFECT/f'{name}.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


program=load_module('program');model=load_module('model');stage=load_module('ram_stage');C=program.CELLS
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


# --- test signals: lists of 64-sample blocks (float32 bit patterns) -----------------------------

def blocks(fn,count):
    return [[fb(fn(64*b+i)) for i in range(64)] for b in range(count)]


def sweep(amplitude,count):          # sine sweep 100 Hz -> 8 kHz over the run
    n=64*count;phase=[0.0]
    for k in range(1,n):phase.append(phase[-1]+2*math.pi*(100.0*(80.0**(k/n)))/44100.0)
    return blocks(lambda k:amplitude*math.sin(phase[k]),count)


SIGNALS={
    'sweep_0.05':lambda n:sweep(0.05,n),
    'sweep_full_scale':lambda n:sweep(1.0,n),
    'impulse':lambda n:blocks(lambda k:0.06 if k==5 else 0.0,n),
    'silence':lambda n:blocks(lambda k:0.0,n),
    'square_full_scale':lambda n:blocks(lambda k:1.0 if (k//37)%2 else -1.0,n),
    'guitar_like':lambda n:blocks(lambda k:0.04*math.sin(2*math.pi*196*k/44100)+0.02*math.sin(2*math.pi*588*k/44100+1.0),n),
}
STEPS_MIN,STEPS_MAX=2637,2701     # simulator steps per active block: 2253..2317 scalar words + 6 block words of 64 elements
KNOBS=((50.0,50.0,50.0),(0.0,50.0,50.0),(100.0,100.0,100.0),(100.0,0.0,25.0),(37.0,73.0,61.0))


def new_sim(cells,prog=None,base=0):
    sim=cs.Sim();sim.load_program(base,words() if prog is None else prog)
    for k,v in cells.items():sim.write(C[k],v)
    return sim


def run_sim_block(sim,window,stop=(0x500,)):
    for i,b in enumerate(window):sim.write(0x13+i,b)
    sim.steps=0;sim.reset_registers()               # nothing survives between blocks except memory
    assert sim.run(0,stop=stop)=='stop' and sim.pc==0x500
    return [sim.read(0x13+i) for i in range(64)]


class Build(unittest.TestCase):
    def test_record_descriptor_and_frame(self):
        m=manifest();o=parse_overlay((OUT/'record.bin').read_bytes());w=words()
        self.assertEqual(o.secondary,(OUT/'secondary.bin').read_bytes());self.assertEqual(w,asm.assemble(program.SOURCE,0))
        self.assertEqual(m['copro']['non_x_words'],[]);self.assertEqual(m['copro']['destination'],'0x28004000')
        self.assertEqual(len(w),115);self.assertLessEqual(m['secondary_bytes'],0x1400);self.assertLessEqual(m['payload_bytes']+m['state_bytes'],0x1000)
        r=frame.check(2,w);self.assertEqual((r['non_x_words'],r['dataflow']['exits'],r['dataflow']['read_before_write']),([],['0x500'],{}))
        self.assertEqual({isa.decode(x)[1] for x in w},{'X'})
        self.assertEqual(tuple(w[:5]),frame.STOCK_DST_ENTRY);self.assertEqual(w[-2:],[0xa0080500,0xa0080500])
        # No call, return, end word; block words only the executed float forms multiply, scale, add.
        self.assertFalse([x for x in w if x>>24==0xae or x==0xa00e0000])
        self.assertEqual(sorted(x>>16&15 for x in w if x>>28==2),[3,7,7,7,7,8])
        # Direct cell operands: D[0x10] and our own thirteen cells, nothing else.
        self.assertEqual({x&0xffff for x in w if x>>28==5},{0x10}|{C[k] for k in program.CELL_NAMES})
        self.assertEqual(sorted(C.values()),list(range(0x193,0x1a1)))

    def test_descriptor_follows_dst_conventions(self):
        manifest();d=parse_descriptor((OUT/'descriptor.bin').read_bytes())
        self.assertEqual((d.name,d.type_name,[p.name for p in d.parameters]),('Tube Drive','OD',['Gain','Tone','VOL']))
        self.assertEqual(d.public_id,0x0300007d)
        for path in CATALOGS:
            cat=parse_container(path.read_bytes()[0x10000:]);ids=[parse_descriptor(b).public_id for g in cat.groups[:10] for b in g]
            self.assertNotIn(d.public_id,ids)
            dst=[parse_descriptor(b) for b in cat.groups[2]]
            self.assertLessEqual(len(d.name),max(len(x.name) for x in dst));self.assertIn(d.type_name,{x.type_name for x in dst})
            ref=next(x for x in dst if x.name=='Super OD')                      # stock three-knob Gain / Tone / VOL, defaults 50
            strip=lambda ps:[(p.name,p.minimum_bits,p.maximum_bits,p.step_bits,p.default_bits,p.storage_index,p.knob,p.flags,p.display_code,p.lead) for p in ps]
            self.assertEqual(strip(d.parameters),strip(ref.parameters))
            self.assertEqual((d.word1,d.count_word),(ref.word1,ref.count_word))


class Program(unittest.TestCase):
    BLOCKS=4

    def test_strict_simulator_equals_model_over_several_blocks(self):
        """Every signal x every knob set; the knobs change after block 1 so both ramps are moving."""
        compared=0;steps=set()
        for name,make in SIGNALS.items():
            for knobs in KNOBS:
                c=model.init_cells(*knobs);c['ENABLE']=1;sim=new_sim(c);then=KNOBS[(KNOBS.index(knobs)+1)%len(KNOBS)]
                for n,window in enumerate(make(self.BLOCKS)):
                    if n==1:
                        new=model.cells(*then);c.update(new)
                        for k,v in new.items():sim.write(C[k],v)
                    got=run_sim_block(sim,window);want=model.run_block(c,window)
                    self.assertEqual(got,want,(name,knobs,n))
                    self.assertEqual({k:sim.read(C[k]) for k in C},c,(name,knobs,n))            # state cells carried, parameters untouched
                    steps.add(sim.steps)
                    compared+=64
        self.assertEqual(compared,64*self.BLOCKS*len(SIGNALS)*len(KNOBS))
        # 7 or 8 words per sample in the clamp loop (at most one of the two moves runs); block words counted as 1 + 64
        self.assertEqual((min(steps),max(steps)),(STEPS_MIN,STEPS_MAX))

    def test_footprint_and_executed_words(self):
        c=model.init_cells(100.0,50.0,50.0);c['ENABLE']=1;sim=new_sim(c);sim.trace=[]
        run_sim_block(sim,SIGNALS['sweep_full_scale'](1)[0])
        self.assertEqual([i for i,v in enumerate(sim.d) if v is not None],[0x10]+list(range(0x13,0x53))+list(range(0x113,0x153))+sorted(C.values()))
        self.assertEqual({isa.decode(w)[1] for _,w in sim.trace},{'X'})
        self.assertEqual({pc for pc,_ in sim.trace},set(range(len(words())))-{5,len(words())-1})     # both clamps fire and idle; only the bypass words are not run

    def test_bypass_leaves_window_and_cells_untouched(self):
        for flag in (0,2,0x100):
            c=model.init_cells(50.0,50.0,50.0);c['ENABLE']=flag;sim=new_sim(c);window=SIGNALS['guitar_like'](1)[0]
            self.assertEqual(run_sim_block(sim,window),window);self.assertEqual(sim.steps,7)
            self.assertEqual({k:sim.read(C[k]) for k in C},c)

    def test_silence_stays_exact_zero(self):
        c=model.init_cells(100.0,100.0,100.0);c['ENABLE']=1;sim=new_sim(c)
        for window in SIGNALS['silence'](3):self.assertEqual(run_sim_block(sim,window),[0]*64)
        self.assertEqual([sim.read(C[k]) for k in ('HP_S1','HP_S2','TONE_Z')],[0,0,0])

    def test_non_finite_input_is_outside_what_was_observed(self):
        for bad in (0x7f800000,0x7fc00000):
            c=model.init_cells(50.0,50.0,50.0);c['ENABLE']=1;window=SIGNALS['guitar_like'](1)[0];window[3]=bad
            with self.assertRaises(cs.UnconfirmedInstruction):run_sim_block(new_sim(c),window)


class Model(unittest.TestCase):
    """model.py (float32, block structured) against double-precision mathematics."""
    def test_hp_design(self):
        w=2*math.pi*model.HP_FC/model.FS;alpha=math.sin(w)/(2*math.sqrt(0.5));a0=1+alpha;cw=math.cos(w)
        want=((1+cw)/2/a0,-(1+cw)/a0,(1+cw)/2/a0,-2*cw/a0,(1-alpha)/a0)
        for got,exact in zip((model.HP_B0,model.HP_B1,model.HP_B2,model.HP_A1,model.HP_A2),want):self.assertAlmostEqual(got,exact,delta=1.5e-7)
        def mag(f):
            z=cmath.exp(-1j*2*math.pi*f/model.FS)
            return abs((model.HP_B0+model.HP_B1*z+model.HP_B2*z*z)/(1+model.HP_A1*z+model.HP_A2*z*z))
        self.assertAlmostEqual(20*math.log10(mag(140.0)),-3.01,delta=0.05);self.assertLess(20*math.log10(mag(35.0)),-23.5);self.assertAlmostEqual(mag(5000.0),1.0,delta=1e-3)

    def test_stages_against_double_precision(self):
        """Neutral cells isolate each stage; several blocks, so block boundaries must be seamless."""
        n=6;sig=[0.3*math.sin(2*math.pi*440*k/44100)+0.2*math.sin(2*math.pi*90*k/44100) for k in range(64*n)]
        feed=[[fb(x) for x in sig[64*b:64*b+64]] for b in range(n)]
        # high-pass alone (drive 1, |x| small enough that the cubic is the only other change)
        c=stage.neutral();c.update(HP_B0=fb(model.HP_B0),HP_B1=fb(model.HP_B1),HP_B2=fb(model.HP_B2),HP_A1=fb(model.HP_A1),HP_A2=fb(model.HP_A2))
        hp=[];x1=x2=y1=y2=0.0
        for x in sig:                                   # direct form I in double precision, one run over the whole signal
            y=model.HP_B0*x+model.HP_B1*x1+model.HP_B2*x2-model.HP_A1*y1-model.HP_A2*y2;x2,x1,y2,y1=x1,x,y1,y;hp.append(y)
        got=[]
        for w in feed:
            st=[];model.run_block(c,w,st);got+=[ff(b) for b in st[1]]
        self.assertLess(max(abs(a-b) for a,b in zip(got,hp)),2e-5)
        # tone alone: z += a (x - z), a = 0.25
        c=stage.neutral(tone_a=0.25);z=0.0;lp=[];curve=[]
        for x in sig:
            y=model.transfer(x);curve.append(y);z+=0.25*(y-z);lp.append(z)
        got=[];mid=[]
        for w in feed:
            st=[];out=model.run_block(c,w,st);got+=[ff(b) for b in out];mid+=[ff(b) for b in st[2]]
        self.assertLess(max(abs(a-b) for a,b in zip(mid,curve)),1e-7);self.assertLess(max(abs(a-b) for a,b in zip(got,lp)),1e-6)

    def test_static_curve(self):
        for drive,level in ((1.0,1.0),(8.0,0.5),(150.0,0.1)):
            c=stage.neutral(drive,level);xs=[(i-32)/32*0.06 for i in range(64)]+[-1.0,1.0,0.5,-0.5]*16
            for k in (0,64):
                c2=dict(c);out=model.run_block(c2,[fb(x) for x in xs[k:k+64]])
                for x,b in zip(xs[k:k+64],out):
                    # tone a = 1 makes z = z + (x - z): equal to x within one rounding of the larger term
                    self.assertAlmostEqual(ff(b),level*model.transfer(drive*x),delta=2e-6*max(1.0,level))
        self.assertAlmostEqual(model.transfer(5.0),2/3);self.assertAlmostEqual(model.transfer(-1.0),-2/3);self.assertAlmostEqual(model.transfer(0.06),0.06-0.06**3/3)

    def test_ramp_time_constant_matches_stock(self):
        c=model.init_cells(0.0,50.0,50.0);c.update(model.cells(100.0,50.0,50.0));start,target=ff(c['DRIVE_CUR']),ff(c['DRIVE_TGT'])
        self.assertEqual((start,round(target,3)),(3.0,150.0))
        for n in range(69):model.run_block(c,[0]*64)                      # 69 blocks = 4416 samples = one time constant of 4410
        self.assertAlmostEqual((ff(c['DRIVE_CUR'])-start)/(target-start),1-math.exp(-1),delta=0.01)
        for n in range(2000):model.run_block(c,[0]*64)
        # the ramp stalls when K * (target - current) falls below half a unit of the current value: within 3e-4 relative (0.003 dB), as stock
        self.assertAlmostEqual(ff(c['DRIVE_CUR']),target,delta=target*3e-4)

    def test_silent_tail_reaches_denormals_only_in_filter_states(self):
        """After a note, digital silence: the IEEE model's filter states decay into the denormal
        range (the strict simulator refuses that; hardware behaviour is test plan item c). The
        ramps never do: the level target has a floor of 1e-6."""
        c=model.init_cells(50.0,50.0,0.0);c['ENABLE']=1;model.run_block(c,SIGNALS['guitar_like'](1)[0]);first=None
        for n in range(1,400):
            out=model.run_block(c,[0]*64)
            if first is None and any(denormal(c[k]) for k in ('HP_S1','HP_S2','TONE_Z')):first=n
            self.assertFalse(denormal(c['DRIVE_CUR']) or denormal(c['LEVEL_CUR']));self.assertFalse(any(b&0x7f800000==0x7f800000 for b in out))
        self.assertIsNotNone(first);self.assertGreater(first,60)        # well over 0.1 s of exact digital silence
        self.first_denormal_block=first
        self.assertEqual(ff(model.cells(50.0,50.0,0.0)['LEVEL_TGT']),model.LEVEL_FLOOR)
        sim=new_sim(dict(c))                                             # and the strict simulator indeed stops there
        with self.assertRaises(cs.UnconfirmedInstruction):
            for n in range(400):run_sim_block(sim,[0]*64)


class ArmHalf(unittest.TestCase):
    def runner(self):
        manifest();self.cop=bytearray(0x8100);return OverlayRunner.from_build(OUT,extra=[(0x28000000,self.cop)])

    def cells(self):
        return {k:struct.unpack_from('<I',self.cop,4*v)[0] for k,v in C.items()}

    def test_init_and_process_write_the_cells_of_the_model(self):
        for knobs in KNOBS+((0.0,0.0,0.0),(100.0,50.0,0.0)):
            p=list(knobs)+[0.0]*5;r=self.runner();r.init(p)
            self.assertEqual(self.cells(),model.init_cells(*knobs),knobs)
            # process must not disturb the state cells or the fixed coefficients: fill them with sentinels
            for i,k in enumerate(program.STATE_CELLS):struct.pack_into('<I',self.cop,4*C[k],0x12340000+i)
            for enable,want in ((1,1),(0,0),(0xff,1),(2,1)):
                frames=[(0.01*i,-0.02*i) for i in range(64)];out=r.process(frames,p,enable=enable)
                self.assertEqual([(fb(a),fb(b)) for a,b in out],[(fb(a),fb(b)) for a,b in frames])          # samples untouched
                want_cells=model.init_cells(*knobs);want_cells.update(model.cells(*knobs,enable=want))
                want_cells.update({k:0x12340000+i for i,k in enumerate(program.STATE_CELLS)})
                self.assertEqual(self.cells(),want_cells,(knobs,enable))
            touched={i//4 for i in range(0,len(self.cop),4) if self.cop[i:i+4]!=b'\0\0\0\0'}
            self.assertTrue(touched<=set(C.values()));self.assertEqual(r.cpu.body_written,set())
        self.assertLess(max(r.process_steps),60)

    def test_cell_values(self):
        c=model.init_cells(50.0,50.0,50.0)
        self.assertAlmostEqual(ff(c['DRIVE_TGT']),39.75,places=4);self.assertAlmostEqual(ff(c['TONE_A']),0.24,places=6)
        self.assertAlmostEqual(ff(c['LEVEL_TGT']),0.08+0.75/39.75+1e-6,places=6)
        lo,hi=model.init_cells(0.0,0.0,50.0),model.init_cells(100.0,100.0,100.0)
        self.assertEqual(ff(lo['DRIVE_TGT']),3.0);self.assertAlmostEqual(ff(hi['DRIVE_TGT']),150.0,places=3)
        self.assertAlmostEqual(ff(lo['TONE_A']),0.09,places=6);self.assertAlmostEqual(ff(hi['TONE_A']),0.69,places=6)
        self.assertAlmostEqual(ff(lo['DRIVE_TGT'])*ff(lo['LEVEL_TGT']),0.99,places=4)                   # Gain 0 / VOL 50: unity small-signal gain
        self.assertEqual(c['DRIVE_CUR'],c['DRIVE_TGT']);self.assertEqual(c['LEVEL_CUR'],c['LEVEL_TGT'])

    def test_arm_cells_drive_the_program(self):
        for knobs in ((0.0,50.0,50.0),(50.0,50.0,50.0),(100.0,25.0,80.0)):
            p=list(knobs)+[0.0]*5;r=self.runner();r.init(p);r.process([(0.0,0.0)]*64,p,enable=1)
            c=self.cells();self.assertEqual(c['ENABLE'],1);sim=new_sim(c);ref=dict(c)
            for window in SIGNALS['guitar_like'](2):self.assertEqual(run_sim_block(sim,window),model.run_block(ref,window))


class Chain(unittest.TestCase):
    def test_strict_through_bypassed_stock_amps_to_the_cab_slot(self):
        window=SIGNALS['guitar_like'](1)[0];c=model.init_cells(50.0,50.0,50.0);c['ENABLE']=1;want=model.run_block(dict(c),window);ran=skipped=0
        for amp in stock_programs(3):
            sim=new_sim(c);sim.load_program(0x500,amp);sim.write(0x398,0)
            self.assertEqual(run_sim_block(sim,window),want);sim.reset_registers()
            try:self.assertEqual(sim.run(0x500,stop=(0xb00,)),'stop')
            except (cs.UnconfirmedInstruction,cs.UndefinedValue):skipped+=1;continue       # three AMPs start with words the decoder does not know
            ran+=1;self.assertEqual([sim.read(0x13+i) for i in range(64)],want)
        self.assertEqual((ran,skipped),(29,3))


class RamStage(unittest.TestCase):
    def test_body_is_the_shipped_active_path_relocated(self):
        w=words();b=stage.body();self.assertEqual(len(b),len(w)-7);shipped=w[6:-1]
        delta=stage.CELL_BASE-0x194
        for i,(x,y) in enumerate(zip(b,shipped)):
            if y>>28==5:self.assertEqual(x,y+delta,i)                                   # direct cell operand moved
            elif y>>16&0xf0ff==0xa004:self.assertEqual(x,y-6+stage.BODY,i)              # loop target moved
            else:self.assertEqual(x,y,i)
        self.assertEqual(b[-1],0xa0080500)
        ph=stage.phases(stage.neutral());self.assertEqual(len(ph['logged_writes']),14);self.assertEqual(ph['logged_writes'][-1],['0x1006','0xa0080400'])
        self.assertTrue(all(len(g)<=20 for g in ph['body_groups_commit_after_each']));self.assertEqual(sum(len(g) for g in ph['body_groups_commit_after_each']),len(b))
        saved=json.loads((ROOT/'work/copro_effect/tube_drive_ram_stage.json').read_text());saved.pop('setting')
        self.assertEqual(saved,json.loads(json.dumps(ph)))
        # cells of the stage: above every stock DST cell, below the AMP cells
        scan=json.loads((ROOT/'work/copro_effect/frame_scan.json').read_text())
        top=max(int(v['direct_cell_range'][1],16) for k,v in scan.items() if k.startswith('g2_'))
        self.assertLess(top,stage.CELL_BASE);self.assertLess(max(stage.C.values()),0x398)

    def test_patch_on_every_standard_stock_dst_program(self):
        window=SIGNALS['guitar_like'](1)[0];hosts=0
        for values in (stage.neutral(),stage.neutral(8.0,0.5),stage.knobs(50.0,50.0,50.0)):
            for stock in stock_programs(2):
                if tuple(stock[:5])!=frame.STOCK_DST_ENTRY:continue                           # Plustortion
                hosts+=1;self.assertLess(len(stock),stage.BODY);ph=stage.phases(values,stock[6])
                for flag in (1,0):
                    sim=cs.Sim();sim.load_program(0,stock+[0]*(0x500-len(stock)))
                    for i in ph['preconditions']['read_zero']:self.assertEqual(sim.read(int(i,16)),0)
                    for i,v in [x for g in ph['body_groups_commit_after_each'] for x in g]+ph['logged_writes']:sim.write(int(i,16),int(v,16))
                    sim.write(0x193,flag);ref={k:values[k] for k in program.CELL_NAMES}
                    for i,b in enumerate(window):sim.write(0x13+i,b)
                    sim.trace=[];self.assertEqual(sim.run(0,stop=(0x500,)),'stop')              # strict simulator
                    got=[sim.read(0x13+i) for i in range(64)]
                    if flag:
                        self.assertEqual(got,model.run_block(ref,window));self.assertEqual({k:sim.read(stage.C[k]) for k in program.CELL_NAMES},ref)
                        clamp_moves={stage.BODY+i for i,x in enumerate(stage.body()) if x in (0xf7340000,0xf7440000)}   # idle: the test signal stays inside +-1
                        self.assertEqual(len(clamp_moves),2)
                        self.assertTrue({pc for pc,_ in sim.trace}|clamp_moves=={0,1,2,3,4,6}|set(range(stage.BODY,stage.BODY+len(stage.body()))))
                    else:
                        self.assertEqual(got,window);self.assertEqual({pc for pc,_ in sim.trace},{0,1,2,3,4,5,stock[5]&0xfff})
        self.assertEqual(hosts,27)


if __name__=='__main__':unittest.main()
