"""Captures and fills must use decoded stack arguments where specified."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from verify_nds_generic_image import capture_harness


class CaptureHarness(unittest.TestCase):
    def test_stack_buffer(self):
        self.assertEqual(capture_harness({'stubs': [dict(argc=3, regs=2, capture=[[2, -100]])]}),
                         'NDSAbiCaptureStudy.java')

    def test_stack_length(self):
        self.assertEqual(capture_harness({'stubs': [dict(argc=4, regs=2, capture=[[0, 3]])]}),
                         'NDSAbiCaptureStudy.java')

    def test_stack_fill(self):
        self.assertEqual(capture_harness({'stubs': [dict(argc=3, regs=2, fill=2)]}),
                         'NDSAbiCaptureStudy.java')

    def test_register_capture_retains_old_harness(self):
        self.assertEqual(capture_harness({'stubs': [dict(argc=3, capture=[[2, -100]])]}),
                         'NDSGenericStudy.java')


if __name__ == '__main__':
    unittest.main()
