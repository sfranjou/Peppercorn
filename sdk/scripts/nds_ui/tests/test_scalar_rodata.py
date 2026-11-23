"""Exact scalar classification positive and fail-closed negative controls."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import nds_scalar_rodata as scalar


class ScalarRodataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name).resolve()
        self.idle, self.dump = 0x10200, 0x10400
        self.syms = [(self.idle, 12, 'CSWTCH.13', 'r'), (self.dump, 240, 'DUMP', 'r')]
        self.cb = bytearray(0x1000)
        self.cb[0x200:0x20c] = scalar.IDLE_BYTES
        self.cb[0x400:0x4f0] = scalar.DUMP_BYTES
        self.map = (f' .rodata.CSWTCH.13\n  0x{self.idle:x} 0xc {self.work}/component_state.o\n'
                    f' .rodata.DUMP 0x{self.dump:x} 0xf0 {self.work}/host_settings.o\n')
        self.write_map()

    def write_map(self):
        (self.work / 'link.map').write_text(self.map)

    def run_classifier(self):
        return scalar.scalar_rodata_words(bytes(self.cb), self.syms, self.work)

    def test_exact_layout_and_only_metadata_words(self):
        words = self.run_classifier()
        self.assertEqual(set(words), set(range(self.idle, self.idle + 12, 4)) |
                         set(range(self.dump, self.dump + 240, 8)))
        self.assertTrue(all(self.dump + offset not in words for offset in range(4, 240, 8)))

    def test_byte_mutations_reject_entire_affected_table(self):
        for offset in (0, 4, 8):
            with self.subTest(idle_offset=offset):
                self.cb[0x200 + offset] ^= 1
                self.assertFalse(any(x in self.run_classifier() for x in range(self.idle, self.idle + 12, 4)))
                self.cb[0x200 + offset] ^= 1
        for offset in (0, 4, 239):
            with self.subTest(dump_offset=offset):
                self.cb[0x400 + offset] ^= 1
                self.assertFalse(any(x in self.run_classifier() for x in range(self.dump, self.dump + 240, 8)))
                self.cb[0x400 + offset] ^= 1

    def test_wrong_symbol_size_type_or_duplicate_rejected(self):
        original = self.syms[:]
        for replacement in ((self.idle, 12, 'CSWTCH.12', 'r'), (self.idle, 8, 'CSWTCH.13', 'r'),
                            (self.idle, 12, 'CSWTCH.13', 'T')):
            self.syms[0] = replacement
            self.assertNotIn(self.idle, self.run_classifier())
        self.syms = original + [original[0]]
        self.assertNotIn(self.idle, self.run_classifier())

    def test_wrong_object_map_address_size_and_duplicate_rejected(self):
        original = self.map
        for changed in (original.replace('component_state.o', 'other.o'),
                        original.replace('0x10200', '0x10204'),
                        original.replace('0xc ', '0x8 '), original + original.splitlines()[0] + '\n' + original.splitlines()[1] + '\n'):
            self.map = changed
            self.write_map()
            self.assertNotIn(self.idle, self.run_classifier())
        self.map = original.replace('host_settings.o', 'other.o')
        self.write_map()
        self.assertNotIn(self.dump, self.run_classifier())

    def test_missing_map_and_wrong_symbol_offset_fail_closed(self):
        self.syms[1] = (self.dump + 4, 240, 'DUMP', 'r')
        self.assertNotIn(self.dump + 4, self.run_classifier())
        (self.work / 'link.map').unlink()
        self.assertEqual(self.run_classifier(), {})


class LegacyKeyTests(unittest.TestCase):
    def test_modal_keys_require_complete_exact_callback_table(self):
        import struct
        from unittest.mock import patch
        from nds_ui.features import legacy_ui_c as legacy
        reference = bytearray(0x170000)
        parent, candidate = bytearray(0x2000), bytearray(0x2000)
        pl, cl = {'assign_editor_hold': 0x11000}, {'assign_editor_hold': 0x11040}
        for name, source, count, dest in (('legacy_editor_table', 0x16ea20, 22, 0x10200),
                                           ('legacy_home_table', 0x16ff0c, 26, 0x10400)):
            pl[name] = cl[name] = dest
            for j in range(count):
                key = 0x2506 if j == 17 else (0x48002 if j == 16 else 0x2000+j)
                struct.pack_into('<II', reference, source-0x10000+j*8, key, 0x16e034)
                struct.pack_into('<II', parent, dest-0x10000+j*8, key, pl['assign_editor_hold'])
                callback = cl['assign_editor_hold']
                if name == 'legacy_editor_table' and key != 0x2506:
                    callback = cl[f'legacy_editor_input_{j}'] = 0x11100+j*4
                struct.pack_into('<II', candidate, dest-0x10000+j*8, key, callback)
        with patch.object(legacy, 'pinned_mod054', return_value=bytes(reference)):
            classify = lambda: scalar.legacy_table_key_words(candidate, cl, parent, pl)
            self.assertEqual(len(classify()), 48)
            self.assertNotIn(0x10204, classify())  # callback word is never exempted
            for offset in (0x200, 0x204, 0x280, 0x284):
                candidate[offset] ^= 1
                self.assertFalse(any(0x10200 <= a < 0x102b0 for a in classify()))
                candidate[offset] ^= 1
            cl.pop('legacy_editor_input_0')
            self.assertFalse(any(0x10200 <= a < 0x102b0 for a in classify()))


if __name__ == '__main__':
    unittest.main()
