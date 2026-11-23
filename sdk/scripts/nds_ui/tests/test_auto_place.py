import unittest
from nds_ui.auto_place import allocate, from_link_map, spans


def obj(name, size):
    return dict(object=name+'.o', source='sdk/'+name+'.c', required=size)


class AutoPlaceTests(unittest.TestCase):
    def test_allocation_stability_growth_and_fallback(self):
        pool=[(0x1000,0x1100),(0x2000,0x2080)]
        objects=[obj('a',100),obj('b',80),obj('c',40)]
        first=allocate(objects,pool)
        again=allocate(objects+[obj('d',20)],pool,first['allocations'])
        self.assertEqual(again['retained_objects'],3)
        for old in first['allocations']:
            now=next(x for x in again['allocations'] if x['object']==old['object'])
            self.assertEqual((now['address'],now['end']),(old['address'],old['end']))
        grown=allocate([obj('a',300),obj('b',80),obj('c',40)],pool,first['allocations'])
        self.assertEqual(grown['fallback_b'],['a.o'])
        self.assertEqual(grown['retained_objects'],2)
        self.assertEqual(allocate(list(reversed(objects)),pool),first)
        self.assertEqual(sum(x['end']-x['address'] for x in first['free_ranges'])+first['reserved_bytes'],384)
        self.assertEqual(len(spans(first)),3)

    def test_reject_unsafe_ledger_and_pools(self):
        for pools in ([(0,16),(8,24)],[(1,16)],[(16,0)]):
            with self.assertRaises(ValueError): allocate([obj('a',4)],pools)
        first=allocate([obj('a',16)],[(0x1000,0x1040)])['allocations']
        for bad in ([dict(first[0],address=0x800)],first+first,[dict(first[0],end=0x1044)]):
            with self.assertRaises(ValueError): allocate([obj('a',16)],[(0x1000,0x1040)],bad)

    def test_live_map_excludes_discarded_and_catalog(self):
        text=''' .text.dead 0x0 0x50 /tmp/a.o
Linker script and memory map
.text 0x00178000 0x10
 .text.live
                0x00178000 0x10 /tmp/a.o
 .rodata.table 0x00178010 0x8 /tmp/a.o
.catalog_ext 0x001a4000 0x20
 .rodata.ext_desc_x 0x001a4000 0x20 /tmp/a.o
'''
        result=from_link_map(text,['sdk/a.c'],{'/tmp/a.o':{'.text.live':2,'.rodata.table':4}},[(0x1000,0x1040)])
        self.assertEqual(result['allocations'][0]['required'],33)
        self.assertEqual(result['reserved_bytes'],36)

if __name__=='__main__': unittest.main()


class CatalogGrowthTests(unittest.TestCase):
    def test_growth_releases_overlapping_code_reservation(self):
        pool=[(0x1000,0x1100)]
        first=allocate([obj('a',32),obj('b',32)],pool)
        grown=allocate([obj('a',32),obj('b',32)],pool,first['allocations'],[(0xff0,0x1020)])
        self.assertEqual(grown['capacity_bytes'],224)
        self.assertEqual(grown['retained_objects'],1)
        self.assertTrue(all(x['address'] >= 0x1020 for x in grown['allocations']))
        self.assertEqual(next(x for x in grown['allocations'] if x['object']=='b.o')['address'],0x1020)

    def test_catalog_map_subtracted_automatically(self):
        text='Linker script and memory map\n.catalog_ext 0xff0 0x30\n.text 0x3000 0x10\n .text.f 0x3000 0x10 a.o\n'
        report=from_link_map(text,['sdk/a.c'],{'a.o':{'.text.f':4}},[(0x1000,0x1100)])
        self.assertEqual(report['capacity_bytes'],224)
        self.assertEqual(report['allocations'][0]['address'],0x1020)


class UnmergedSizingTests(unittest.TestCase):
    def test_shared_strings_reserve_input_sizes_including_zero_map(self):
        text = 'Linker script and memory map\n.text 0x3000 0x10\n .text.f 0x3000 0x10 a.o\n.rodata 0x3010 0x4\n .rodata.str1.4 0x3010 0x4 a.o\n .rodata.str1.1 0x3014 0x0 a.o\n'
        report = from_link_map(text,['sdk/a.c'],{'a.o':{}},[(0x1000,0x1100)],
                               section_sizes={'a.o':{'.text.f':16,'.rodata.str1.4':80,'.rodata.str1.1':32}})
        self.assertEqual(report['allocations'][0]['required'],140)
        self.assertEqual(report['reserved_bytes'],140)
