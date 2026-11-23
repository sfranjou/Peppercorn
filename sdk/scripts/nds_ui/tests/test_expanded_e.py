import hashlib
import unittest
import struct
from pathlib import Path
from nds_ui import expanded_e as X, catalog_storage as C

CFG = dict(component_only=True, expanded_e='offline_0x3f000')


class ExpandedETest(unittest.TestCase):
    def test_prefix_and_precise_capacity(self):
        raw = bytearray(bytes(range(256)) * (X.STOCK_LENGTH // 256))
        struct.pack_into('<I', raw, 0x1b8000-X.BASE, 0)
        raw = bytes(raw)
        out = X.extend(CFG, raw)
        self.assertEqual(out[:len(raw)], raw)
        self.assertEqual(len(out)-len(raw), 72*1024)
        self.assertEqual(out[len(raw):], b'\xff' * (72*1024))
        self.assertIs(X.extend({}, raw), raw)
        self.assertEqual(X.BASE + (((len(out)+2)&~0xfff)+0x1000), X.SETTINGS)

    def test_explicit_draft_and_length_only(self):
        for cfg in (dict(expanded_e='offline_0x3f000'), dict(component_only=True, expanded_e='0x40000')):
            with self.assertRaises(ValueError): X.extend(cfg, b'\xff'*X.STOCK_LENGTH)
        for length in (X.STOCK_LENGTH-1, X.STOCK_LENGTH+1, X.EXPANDED_LENGTH):
            with self.assertRaises(ValueError): X.extend(CFG,b'\xff'*length)

    def test_growth_payload_requires_policy_and_rejects_boundary(self):
        raw = X.extend(CFG, b'\xff'*X.STOCK_LENGTH)
        def blob(addr):
            data=b'\x12\x34\x56\x78'
            return dict(region='e', address=addr, offset=addr-X.BASE, bytes=data, sha256=hashlib.sha256(data).hexdigest())
        b=blob(X.GROWTH_RANGE[0])
        with self.assertRaises(ValueError): C.apply(raw,[b])
        out=C.apply(raw,[b],CFG);self.assertEqual(out[X.STOCK_LENGTH:X.STOCK_LENGTH+4],b['bytes'])
        with self.assertRaises(ValueError): C.apply(raw,[blob(X.GROWTH_RANGE[1]-2)],CFG)
        with self.assertRaises(ValueError): C.apply(out,[b],CFG)
        with self.assertRaises(ValueError): C.apply(raw,[b,b],CFG)
        self.assertEqual(C.code_ranges(CFG)[-1],X.GROWTH_RANGE)
        self.assertNotIn(X.GROWTH_RANGE,C.code_ranges({}))

    def test_real_stock_pcm_conflict_rejected(self):
        root=Path(__file__).resolve().parents[3]
        raw=(root/'work/v110/decoded_e.bin').read_bytes()
        self.assertEqual(X.pcm_ranges(raw),[(0x1b8024,0x1bbca4),(0x1bbcfc,0x1bfa7c),
                                          (0x1bfa84,0x1c1684),(0x1c16b4,0x1c8bb4)])
        with self.assertRaisesRegex(ValueError,'stock PCM reads'):
            X.extend(CFG,raw)
        self.assertIs(X.extend({},raw),raw)

    def test_unknown_table_and_erase_only_conflict(self):
        raw=bytearray(b'\xff'*X.STOCK_LENGTH);table=0x1b8000-X.BASE
        struct.pack_into('<I',raw,table,5)
        with self.assertRaisesRegex(ValueError,'table count'):X.extend(CFG,bytes(raw))
        # Even an asset in the final erased-but-not-programmed sector is unsafe.
        struct.pack_into('<III',raw,table,1,0x1cf000-0x1b8000,2)
        with self.assertRaisesRegex(ValueError,'stock PCM reads'):X.extend(CFG,bytes(raw))
