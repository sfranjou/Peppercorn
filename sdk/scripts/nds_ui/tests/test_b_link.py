import copy
import json
import tempfile
import unittest
from pathlib import Path
from nds_ui import b_link
from nds_ui.b_placement import plan

class BLinkTest(unittest.TestCase):
    def test_liveness_raw_strings_and_constraints(self):
        obj=Path('/a/unit.o');key=str(obj)
        # Includes a live string merged to size zero, and text beyond the target
        # limit in the initial unconstrained link. Neither may be lost.
        text='Linker script and memory map\n .text.f 0x200 0x10 /a/unit.o\n .text.g 0x300 0x8 /a/unit.o\n .rodata.s 0x310 0x0 /a/unit.o\n .rodata.e 0x190100 0x4 /a/unit.o\n'
        aligns={key:{'.text.f':2,'.text.g':2,'.rodata.s':4}}
        sizes={key:{'.text.f':16,'.text.g':8,'.rodata.s':12}}
        ledger,placed,clauses=b_link.propose(text,[obj],aligns,sizes,[(0x100,0x120,0x100)],0x200,0x240)
        self.assertEqual(len(ledger['allocations']),3)
        data=next(r for r in ledger['allocations'] if '.rodata' in r['id'])
        self.assertEqual(data['pool'],'tail');self.assertEqual(data['size'],12)
        repeat,_,_=b_link.propose(text,[obj],aligns,sizes,[(0x100,0x120,0x100)],0x200,0x240,ledger)
        self.assertEqual(repeat['retained'],3);self.assertIn('ASSERT',clauses)

    def test_data_cannot_spill_into_holes(self):
        with self.assertRaisesRegex(ValueError,'B placement exhausted'):
            plan([dict(id='data',size=20,align=4,pools=['tail'])],
                 [dict(id='hole',start=0,end=100),dict(id='tail',start=200,end=208)])
        old=plan([dict(id='a',size=8,align=2)], [dict(id='hole',start=0,end=16),dict(id='tail',start=32,end=48)])
        moved=plan([dict(id='a',size=8,align=2,pools=['tail'])],old['pools'],old)
        self.assertEqual(moved['allocations'][0]['pool'],'tail')

    def test_commit_and_tampered_prior_artifact(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);artifact=root/'image';artifact.write_bytes(b'validated example')
            path=root/'ledger.json';p=plan([], [dict(id='tail',start=0,end=32)])
            saved=copy.deepcopy(p)
            b_link.commit(path,p,[artifact],root)
            self.assertEqual(saved,p);self.assertEqual(b_link.load_previous(path,root)['schema'],1)
            prior=path.read_bytes();artifact.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,'validated artifact changed'):b_link.load_previous(path,root)
            self.assertEqual(path.read_bytes(),prior)
            with self.assertRaisesRegex(ValueError,'needs validation'):b_link.commit(path,p,[],root)
            self.assertEqual(path.read_bytes(),prior)
