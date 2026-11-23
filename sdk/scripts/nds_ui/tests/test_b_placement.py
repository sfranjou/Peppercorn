import copy
import unittest
from nds_ui.b_placement import plan

P=[dict(id='hole',start=0x100,end=0x120),dict(id='tail',start=0x200,end=0x240)]
def item(name,size,align=2):return dict(id=name,size=size,align=align)
def by_id(ledger):return {x['id']:x for x in ledger['allocations']}

class BPlacementTest(unittest.TestCase):
    def test_repeat_reorder_add_remove_and_grow(self):
        items=[item('a',16),item('b',24),item('c',8)]
        first=plan(items,P);saved=copy.deepcopy(first)
        self.assertEqual(plan(list(reversed(items)),P,first),dict(first,retained=3))
        added=plan(items+[item('d',6,4)],P,first)
        for k in ('a','b','c'):self.assertEqual(by_id(first)[k],by_id(added)[k])
        grown=plan([item('a',30),item('b',24),item('d',6,4)],P,added)
        self.assertNotEqual(by_id(first)['a']['address'],by_id(grown)['a']['address'])
        self.assertEqual(by_id(first)['b'],by_id(grown)['b'])
        self.assertNotIn('c',by_id(grown));self.assertEqual(first,saved)

    def test_slack_alignment_and_pool_relocation(self):
        ledger=plan([item('a',16)],P)
        ledger['allocations'][0]['capacity']=20
        grown=plan([item('a',18,8)],P,ledger)
        self.assertEqual(grown['retained'],1);self.assertEqual(grown['allocations'][0]['capacity'],20)
        moved=plan([item('a',18)],P[1:],grown)
        self.assertEqual(moved['retained'],0);self.assertEqual(moved['allocations'][0]['pool'],'tail')

    def test_ledger_rejection(self):
        ledger=plan([item('a',8),item('b',8)],P)
        for mutation in ('schema','overlap','alignment','outside','duplicate'):
            bad=copy.deepcopy(ledger)
            if mutation=='schema':bad['schema']=999
            if mutation=='overlap':bad['allocations'][1]['address']=bad['allocations'][0]['address']
            if mutation=='alignment':bad['allocations'][0]['align']=3
            if mutation=='outside':bad['allocations'][0]['address']=0
            if mutation=='duplicate':bad['allocations'].append(dict(bad['allocations'][0]))
            for repack in (False,True):
                with self.subTest(mutation=mutation,repack=repack),self.assertRaises(ValueError):
                    plan([item('a',8)],P,bad,repack=repack)

    def test_fragmentation_explicit_repack_and_atomic_failure(self):
        pools=[dict(id='p',start=0,end=32)]
        old=plan([item(k,8)for k in 'abcd'],pools);saved=copy.deepcopy(old)
        with self.assertRaisesRegex(ValueError,'free 16, largest span 8'):
            plan([item('a',8),item('c',8),item('new',16)],pools,old)
        repacked=plan([item('a',8),item('c',8),item('new',16)],pools,old,repack=True)
        self.assertEqual(repacked['free_bytes'],0);self.assertEqual(old,saved)
        with self.assertRaisesRegex(ValueError,'exhausted'):plan([item('x',100)],pools,old)
        self.assertEqual(old,saved)

    def test_invalid_inputs_and_alignment_padding(self):
        for items,pools in [([item('a',0)],P),([item('a',4,3)],P),([item('a',4),item('a',4)],P),
                            ([item('a',4)],P+[P[0]]),([item('a',4)],[dict(id='x',start=0,end=10),dict(id='y',start=8,end=20)])]:
            with self.assertRaises(ValueError):plan(items,pools)
        out=plan([item('a',8,16)],[dict(id='x',start=3,end=24)])
        self.assertEqual(out['allocations'][0]['address'],16)
        self.assertEqual(out['free_bytes'],13)
