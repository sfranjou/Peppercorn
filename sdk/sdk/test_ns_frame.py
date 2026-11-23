"""N->S (group 9) slot rules: a minimal own program passes, the stock program's entry differs (documented)."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;sys.path[:0]=[str(ROOT),str(ROOT/'sdk')]
from copro import frame
from protocol import copro_isa as isa
from protocol.overlay_image import parse_container,parse_overlay
G=ROOT/'work/custom_images/mod046_reload_veneer/regions/decoded_g.bin'


class NSFrameTests(unittest.TestCase):
    def test_minimal_program_passes(self):
        entry=frame.SLOTS[9]['entry']
        words=list(entry)+[isa.jump(0x505),isa.jump(0xe00),isa.jump(0xe00)]
        frame.check(9,words)

    def test_program_must_end_before_eq(self):
        entry=frame.SLOTS[9]['entry']
        words=list(entry)+[isa.jump(0x505),isa.jump(0xe00)]+[isa.jump(0xe00)]*(0x900-5)
        with self.assertRaises(frame.FrameError):frame.check(9,words)

    def test_stock_record_matches_slot(self):
        o=parse_overlay(parse_container(G.read_bytes()).groups[9][0]);s=frame.SLOTS[9]
        self.assertLessEqual(len(o.primary),s['primary_bytes']);self.assertLessEqual(len(o.secondary),s['capacity_bytes'])
        self.assertTrue(s['primary_base']<=o.init_callback-1<s['primary_base']+len(o.primary))


if __name__=='__main__':unittest.main()
