"""SDK checks: build conformance, interpreter execution of the built payload against the
bit-exact reference model, bypass behaviour, slot discipline and relative cost."""
import json
import math
from pathlib import Path
import struct
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'sdk'));sys.path.insert(0,str(ROOT/'sdk/effects/chop_trem'))
import build_effect            # noqa: E402
from run_effect import OverlayRunner  # noqa: E402
from model import ChopTremModel       # noqa: E402
from protocol.overlay_image import parse_overlay,parse_descriptor,parse_container  # noqa: E402

OUT=ROOT/'work/sdk_build/chop_trem'
bits=lambda v:struct.pack('<f',v)


class ChopTremTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=build_effect.build(ROOT/'sdk/effects/chop_trem',OUT)

    def signal(self,n):
        return [0.25*math.sin(2*math.pi*440*i/44100)+0.05*math.sin(2*math.pi*3111*i/44100) for i in range(n)]

    def test_record_and_descriptor_are_well_formed(self):
        o=parse_overlay((OUT/'record.bin').read_bytes());d=parse_descriptor((OUT/'descriptor.bin').read_bytes())
        self.assertEqual(len(o.secondary),0);self.assertEqual(o.primary,(OUT/'payload.bin').read_bytes())
        self.assertEqual((d.name,d.type_name,[p.name for p in d.parameters]),('Chop Trem','Tremolo',['Depth','Rate','VOL']))
        # The public ID must not collide with any stock catalog entry.
        cat=parse_container((ROOT/'work/v110/decoded_e.bin').read_bytes()[0x10000:])
        self.assertNotIn(d.public_id,[parse_descriptor(b).public_id for g in cat.groups[:10] for b in g])
        self.assertLess(self.manifest['payload_bytes']+self.manifest['state_bytes'],0x2000)

    def test_interpreter_matches_reference_model_bit_for_bit(self):
        for params in ([50.0,2.0,50.0],[100.0,10.0,100.0],[0.0,0.1,50.0],[37.0,7.3,12.0]):
            p=params+[0.0]*5;x=self.signal(64*120)
            r=OverlayRunner.from_build(OUT);r.init(p);got=r.run_mono(x,p)
            m=ChopTremModel();m.init(p);want=m.run_mono(x,p)
            self.assertEqual([bits(v) for v in got],[bits(v) for v in want],params)
            # Both output words carry the same sample.
            frames=r.process([(v,-v) for v in x[:64]],p)
            self.assertTrue(all(bits(l)==bits(rr) for l,rr in frames))

    def test_bypass_touches_nothing_and_state_stays_in_slot(self):
        p=[50.0,2.0,50.0]+[0.0]*5;r=OverlayRunner.from_build(OUT);r.init(p)
        frames=[(0.1*i,-0.2*i) for i in range(64)]
        self.assertEqual([(bits(a),bits(b)) for a,b in r.process(frames,p,enable=0)],[(bits(a),bits(b)) for a,b in frames])
        r.run_mono(self.signal(64*10),p)
        base=int(self.manifest['slot_base'],16);end=base+self.manifest['payload_bytes']
        self.assertEqual(r.cpu.body_written,set())                       # never writes its own code/constants
        self.assertGreaterEqual(r.cpu.wmin,end);self.assertLessEqual(r.cpu.wmax,end+self.manifest['state_bytes'])

    def test_behaviour_and_cost(self):
        p=[100.0,5.0,50.0]+[0.0]*5;r=OverlayRunner.from_build(OUT);r.init(p)
        y=r.run_mono([0.5]*44100,p)
        tail=y[22050:];self.assertAlmostEqual(max(tail),0.5,places=3);self.assertAlmostEqual(min(tail),0.0,places=3)
        crossings=sum(1 for a,b in zip(tail,tail[1:]) if (a<0.25)!=(b<0.25))
        self.assertEqual(crossings,5)                                    # 5 Hz square: 5 edges in half a second
        full=set(r.process_steps[:-1]);self.assertEqual(len(full),1)     # constant cost per full 64-frame block
        # Same interpreter, stock Sine Trem (measured on the pedal: ARM proxy +0.038 alone).
        g=parse_container((ROOT/'work/v110/decoded_g.bin').read_bytes());o=parse_overlay(g.groups[6][9])
        stock=OverlayRunner(o.primary,0x1000a000,0x2000,o.init_callback,o.process_callback)
        q=[50.0,0.5,50.0,0.0]+[0.0]*4;stock.init(q);stock.run_mono(self.signal(64*20),q)
        ours,theirs=full.pop(),max(stock.process_steps)
        self.assertLess(ours,theirs)                                     # cheaper than the stock tremolo
        (OUT/'cost.json').write_text(json.dumps(dict(instructions_per_64_frame_block=ours,stock_sine_trem_instructions_per_block=theirs,
            stock_sine_trem_measured_arm_proxy_delta=0.038,note='Instruction counts are not cycles; ratio is a rough guide only.'))+'\n')
