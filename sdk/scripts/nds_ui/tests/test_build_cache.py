"""Cache rejection checks: stale keys, artifacts and corrupted receipts must rebuild."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from nds_ui import build_cache as cache


class BuildCacheTests(unittest.TestCase):
    def test_invalidation_and_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            obj = root / 'source.o'
            obj.write_bytes(b'object')
            receipt = root / 'cache.json'
            cache.save(receipt, 'source+headers+flags', 'payload', [obj])
            self.assertEqual(cache.load(receipt, 'source+headers+flags'), 'payload')
            self.assertIsNone(cache.load(receipt, 'changed-header'))
            obj.write_bytes(b'corrupt')
            self.assertIsNone(cache.load(receipt, 'source+headers+flags'))
            obj.write_bytes(b'object')
            with patch.dict(os.environ, NDS_UI_NO_CACHE='1'):
                self.assertIsNone(cache.load(receipt, 'source+headers+flags'))
            data = json.loads(receipt.read_text())
            data['value'] = 'corrupt'
            receipt.write_text(json.dumps(data))
            self.assertIsNone(cache.load(receipt, 'source+headers+flags'))
            receipt.write_text('{partial')
            self.assertIsNone(cache.load(receipt, 'source+headers+flags'))
            receipt.unlink()
            self.assertIsNone(cache.load(receipt, 'source+headers+flags'))


if __name__ == '__main__':
    unittest.main()
