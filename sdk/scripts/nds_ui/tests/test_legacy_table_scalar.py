"""Legacy table keys require complete parent and candidate correspondence."""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import nds_scalar_rodata as scalar
from nds_ui.features import legacy_ui_c as legacy

class LegacyTableTests(unittest.TestCase):
    def setUp(self):
        self.reference = legacy.pinned_mod054()
        self.pb = bytearray((ROOT / 'work/custom_images/mod057_usb_guard_fix/regions/decoded_b.bin').read_bytes())
        self.cb = bytearray((ROOT / 'work/custom_images/mod079_bulk_application_c/regions/decoded_b.bin').read_bytes())
        self.pl = json.loads((ROOT / 'work/nds_ui/mod057/labels.json').read_text())
        self.cl = json.loads((ROOT / 'work/nds_ui/mod079/labels.json').read_text())
    def classify(self):
        return scalar.legacy_table_key_words(self.cb, self.cl, self.pb, self.pl)
    def test_exact_and_callbacks_excluded(self):
        words = self.classify()
        self.assertEqual(len(words), 48)
        for name, count in [('legacy_editor_table', 22), ('legacy_home_table', 26)]:
            for i in range(count):
                self.assertIn(self.cl[name]+8*i, words)
                self.assertNotIn(self.cl[name]+8*i+4, words)
    def test_key_and_callback_mutations_fail_affected_table(self):
        for buf, labels in ((self.pb, self.pl), (self.cb, self.cl)):
            for offset in (0, 4, 172):
                at = labels['legacy_editor_table'] - 0x10000 + offset
                buf[at] ^= 1
                words = self.classify()
                self.assertNotIn(self.cl['legacy_editor_table'], words)
                self.assertIn(self.cl['legacy_home_table'], words)
                buf[at] ^= 1
    def test_wrong_label_and_missing_reference_fail_closed(self):
        self.cl['assign_home_encoder'] += 4
        self.assertNotIn(self.cl['legacy_home_table'], self.classify())
        with patch.object(legacy, 'pinned_mod054', return_value=None):
            self.assertEqual(self.classify(), {})

if __name__ == '__main__': unittest.main()
