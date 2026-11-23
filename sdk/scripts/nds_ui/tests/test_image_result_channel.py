"""Public hard-float return checks must observe fs0 rather than scratch a0."""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from verify_nds_generic_image import normalise_row


class ResultChannelTests(unittest.TestCase):
    def test_float_ignores_scratch_but_detects_float_change(self):
        case = dict(entry=0x44a8a, result_fs0=True)
        mod = SimpleNamespace()
        a = dict(result=1, fs0=0x3f800000, steps=2, calls=[], observe=[])
        b = dict(a, result=99, steps=20)
        self.assertEqual(normalise_row(case, a, mod), normalise_row(case, b, mod))
        b['fs0'] ^= 1
        self.assertNotEqual(normalise_row(case, a, mod), normalise_row(case, b, mod))
        self.assertEqual(a['result'], 1)

    def test_float_state_and_calls_remain_observed(self):
        case = dict(entry=1, result_fs0=True)
        a = dict(result=0, fs0=0, calls=[], observe=['00'])
        for change in (dict(calls=[dict(addr='123', a=[1])]), dict(observe=['01'])):
            self.assertNotEqual(normalise_row(case, a, SimpleNamespace()),
                                normalise_row(case, dict(a, **change), SimpleNamespace()))

    def test_integer_result_remains_observed(self):
        case = dict(entry=1)
        self.assertNotEqual(normalise_row(case, dict(result=1, fs0=0), SimpleNamespace()),
                            normalise_row(case, dict(result=2, fs0=0), SimpleNamespace()))

    def test_missing_float_result_is_failure(self):
        with self.assertRaises(KeyError):
            normalise_row(dict(entry=1, result_fs0=True), dict(result=0), SimpleNamespace())


if __name__ == '__main__':
    unittest.main()
