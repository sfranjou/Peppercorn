import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from nds_ui.image import classify_declared_preimage

class EntryPreimageTests(unittest.TestCase):
    def test_exact_and_negative_controls(self):
        cfg={'hook_preimages':{'0x10000':dict(parent='fc61fa2a',stock='fc61fa28',reason='count26')}}
        stock=bytes.fromhex('fc61fa28')
        self.assertIsNotNone(classify_declared_preimage(cfg,0x10000,bytes.fromhex('fc61fa2a'),stock))
        self.assertIsNone(classify_declared_preimage(cfg,0x10000,bytes.fromhex('fc61fa2b'),stock))
        self.assertIsNone(classify_declared_preimage(cfg,0x10000,bytes.fromhex('fc61fa2a'),bytes.fromhex('fc61fa29')))
        self.assertIsNone(classify_declared_preimage(cfg,0x10004,bytes.fromhex('fc61fa2a'),stock))
        self.assertIsNone(classify_declared_preimage({},0x10000,bytes.fromhex('fc61fa2a'),stock))
