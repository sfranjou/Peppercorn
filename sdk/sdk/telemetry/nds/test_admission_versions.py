#!/usr/bin/env python3
"""Admission table versions: v1/v2 pinned (images MOD036-MOD043 rebuild from them), v3 = v2 + SDK
estimates for unmeasured ids only, explicit per-image overrides, stale estimates refused."""
import hashlib, json, sys, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]; sys.path.insert(0, str(ROOT))
from sdk.telemetry.nds import admission_costs as AC, sdk_estimates as SE


def digest(t):
    return hashlib.sha256(json.dumps({str(g): r for g, r in t.items()}, sort_keys=True).encode()).hexdigest()[:16]


class Versions(unittest.TestCase):
    def tearDown(self):
        AC.ESTIMATES_JSON = SE.JSON; AC._CACHE.clear(); AC.use('v1')

    def test_pinned(self):
        AC.use('v1'); self.assertEqual(digest(AC.table()[0]), PIN['v1'])
        AC.use('v2'); self.assertEqual(digest(AC.table()[0]), PIN['v2'])

    def test_v3_fills_only_unmeasured(self):
        AC.use('v2'); v2 = AC.table()[0]
        est = json.loads(SE.JSON.read_text())
        est['effects'] = est['effects'] + [dict(effect='synthetic', group=6, public_id='0x04000077', estimate=42, instructions_mean=0, factor=1e-5, sources_sha256='')]
        f = Path(tempfile.mkdtemp()) / 'e.json'; f.write_text(json.dumps(est)); AC.ESTIMATES_JSON = f
        real_stale = SE.stale; SE.stale = lambda: []
        try:
            AC._CACHE.clear(); AC.use('v3'); t, prov = AC.table()
            self.assertEqual(dict(t[6])[0x04000077], 42); self.assertIn('sdk estimate', prov['6:0x04000077']['source'])
            for g in AC.ARM_GROUPS:                       # every measured row unchanged
                for i, c in v2[g]: self.assertEqual(dict(t[g])[i], c)
            AC.use('v3', ('afterglow_micro',)); t2 = AC.table()[0]
            e = next(x for x in est['effects'] if x['effect'] == 'afterglow_micro')
            self.assertEqual(dict(t2[7])[0x0b0000f0], e['estimate'])
        finally:
            SE.stale = real_stale

    def test_overrides_need_estimates(self):
        with self.assertRaises(ValueError): AC.use('v2', ('afterglow_micro',))

    def test_estimates_fresh(self):
        self.assertEqual(SE.stale(), [])


PIN = {'v1': '4267b439a05811da', 'v2': '117a682853d31e6a'}   # tables of MOD036-040 (v1) and MOD042-043 (v2)
if __name__ == '__main__':
    if '--pin' in sys.argv:
        for v in ('v1', 'v2'): AC.use(v); print(v, digest(AC.table()[0]))
        sys.exit(0)
    unittest.main()
