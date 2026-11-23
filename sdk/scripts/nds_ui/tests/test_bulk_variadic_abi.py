import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from prepare_application_bulk import needs_hard_float

class VariadicAbi(unittest.TestCase):
    def test_header_format_wrapper(self):
        self.assertTrue(needs_hard_float('lv_label_set_text_fmt1(label, fmt, tempo);'))

    def test_direct_variadic(self):
        self.assertTrue(needs_hard_float('STOCK_CALL_VA(io, address, label, fmt, value);'))

    def test_ordinary_integer(self):
        self.assertFalse(needs_hard_float('uint32_t count = STOCK_CALL(io, 0x10000, index);'))

    def test_real_failing_source(self):
        source=Path(__file__).resolve().parents[3]/'firmware/reconstructed/nds/ui_effect_set_build.c'
        self.assertTrue(needs_hard_float(source.read_text()))

if __name__=='__main__':unittest.main()
