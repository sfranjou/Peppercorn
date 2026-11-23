"""Allocator boundaries and parent-preservation checks for in-container E spans."""
import copy
import hashlib
import unittest
from nds_ui import catalog_storage as E


def cfg():
    return dict(region_e_code=dict(spans=[
        dict(name=n, address=hex(a), end=hex(b), sources=[n+'.c'])
        for n, (a, b) in zip(('low', 'main', 'high'), E.CODE_RANGES)]))


def blob(a, raw=b'\x12\x34\x56\x78'):
    return dict(region='e', address=a, offset=a-E.FILE_BASE, bytes=raw,
                sha256=hashlib.sha256(raw).hexdigest())


class StorageTests(unittest.TestCase):
    def test_legacy_layout_and_named_spans(self):
        self.assertEqual(E.code_sections(dict(region_e_code=dict(address=hex(E.CODE_ADDRESS), end=hex(E.CODE_END), sources=['a.c']))), ['.e_text'])
        self.assertEqual(E.code_sections(cfg()), ['.e_text_low', '.e_text_main', '.e_text_high'])
        self.assertEqual(E.e_code_stems(cfg()), ['low', 'main', 'high'])

    def test_bad_configuration_rejected(self):
        base = cfg()
        bad = []
        for key, value in [('address', '0x19d9a4'), ('end', '0x1a0004'), ('name', 'low);bad'), ('sources', [])]:
            c = copy.deepcopy(base); c['region_e_code']['spans'][0][key] = value; bad.append(c)
        c = copy.deepcopy(base); c['region_e_code']['spans'][1]['sources'] = ['somewhere/low.c']; bad.append(c)
        c = copy.deepcopy(base); c['region_e_code']['spans'].append(c['region_e_code']['spans'][0]); bad.append(c)
        c = copy.deepcopy(base); c['region_e_code']['address'] = '0x1a6000'; bad.append(c)
        for c in bad:
            with self.subTest(c=c), self.assertRaises(ValueError): E.code_spans(c)

    def test_apply_preserves_assets_and_rejects_bad_payloads(self):
        parent = bytearray(b'\xff' * 0x2d000)
        parent[0x19600:0x19604] = b'ASST'
        payloads = [blob(a) for a, _ in E.CODE_RANGES]
        result = E.apply(bytes(parent), payloads)
        self.assertEqual(result[0x19600:0x19604], b'ASST')
        covered = {i for b in payloads for i in range(b['offset'], b['offset']+len(b['bytes']))}
        self.assertTrue(all(x == y for i, (x, y) in enumerate(zip(parent, result)) if i not in covered))
        cases = [[blob(0x1a9600)], [blob(0x1bd000)], [blob(E.CODE_RANGES[0][0]-4)],
                 [payloads[0], payloads[0]], [dict(payloads[0], sha256='bad')],
                 [dict(payloads[0], offset=0)], [blob(0x1a0000-2)], [blob(0x1a6000, b'')]]
        for bs in cases:
            with self.subTest(bs=bs), self.assertRaises(ValueError): E.apply(bytes(parent), bs)
        with self.assertRaises(ValueError): E.apply(result, payloads)
        with self.assertRaises(ValueError): E.apply(b'\xff'*0x1000, payloads)

if __name__ == '__main__': unittest.main()
