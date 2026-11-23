"""Frozen-image checking must not regenerate artifacts or bypass review."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT)]
from nds_ui import tests


class FrozenImageCheck(unittest.TestCase):
    def test_rejected_image_stops_before_preparing_or_running(self):
        with patch('nds_ui.review.review', side_effect=ValueError('bad image')), \
             patch.object(tests, '_prepare') as prepare, \
             patch.object(tests, 'run_ghidra') as run:
            with self.assertRaisesRegex(ValueError, 'bad image'):
                tests.tier_c({}, verify_only=True)
            prepare.assert_not_called()
            run.assert_not_called()

    def test_normal_full_check_still_prepares(self):
        with patch.object(tests, '_prepare', side_effect=ValueError('prepare')), \
             patch('nds_ui.review.review') as review:
            with self.assertRaisesRegex(ValueError, 'prepare'):
                tests.tier_c({})
            review.assert_not_called()


if __name__ == '__main__':
    unittest.main()
