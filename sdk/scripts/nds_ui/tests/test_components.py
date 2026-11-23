import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from nds_ui.components import ComponentError, discover, registry_header, callback_header

class ComponentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.folder=self.root/'parts'/'example'
        self.folder.mkdir(parents=True)
        self.m=dict(abi=1,id='demo',sources=['demo_main.c'],
            callbacks=dict(init='demo_init',tick='demo_tick',get='demo_get',set='demo_set'),
            host=dict(selector=0x76,set_bytes=2,max_reply_bytes=4),
            resources=dict(state_bytes=0,stack_bytes=32,tick_us=10))
        (self.folder/'demo_main.c').write_text('/* test fixture */')
        self.write()
    def write(self): (self.folder/'component.json').write_text(json.dumps(self.m))
    def discover(self): return discover([self.root/'parts'],self.root)
    def test_deterministic_and_hash_bound(self):
        first=self.discover();self.assertEqual(first,self.discover())
        self.assertEqual(first[0]['sources'],['parts/example/demo_main.c'])
        self.assertEqual(len(first[0]['inputs']),2)
        (self.folder/'demo_main.c').write_text('/* changed */')
        self.assertNotEqual(first,self.discover())
    def test_invalid_contracts_rejected(self):
        original=copy.deepcopy(self.m)
        changes=[('abi',4),('abi',True),('id','../oops'),('sources',[]),('sources',['../escape.c']),
            ('sources',['demo_main.c','demo_main.c']),('extra',1)]
        changes += [('callbacks',{**original['callbacks'],'get':name}) for name in (None,'foreign_name')]
        changes += [('host',{**original['host'],field:value}) for field,value in
                    [('selector',0x75),('selector',0x7f),('selector',True),('set_bytes',25),('max_reply_bytes',0)]]
        changes += [('resources',{**original['resources'],field:value}) for field,value in
                    [('state_bytes',4),('stack_bytes',513),('tick_us',0),('tick_us',1001)]]
        for key,value in changes:
            with self.subTest(key=key,value=value):
                self.m=copy.deepcopy(original);self.m[key]=value;self.write()
                with self.assertRaises(ComponentError):self.discover()
    def test_duplicates_and_symlinks(self):
        other=self.root/'parts'/'other';other.mkdir()
        (other/'component.json').write_text(json.dumps(self.m))
        (other/'demo_main.c').write_text('')
        with self.assertRaisesRegex(ComponentError,'duplicate component id'):self.discover()
        self.m['id']='different';self.m['sources']=['different_main.c']
        self.m['callbacks']={k:('different_'+k) for k in self.m['callbacks']}
        (other/'component.json').write_text(json.dumps(self.m))
        (other/'different_main.c').write_text('')
        with self.assertRaisesRegex(ComponentError,'duplicate host selector'):self.discover()
        (other/'component.json').unlink()
        (self.folder/'demo_main.c').unlink();(self.root/'outside.c').write_text('')
        (self.folder/'demo_main.c').symlink_to(self.root/'outside.c')
        with self.assertRaisesRegex(ComponentError,'outside component'):self.discover()
    def test_duplicate_json_keys_and_empty_registry(self):
        (self.folder/'component.json').write_text('{"abi":1,"abi":1}')
        with self.assertRaisesRegex(ComponentError,'duplicate manifest key'):self.discover()
        with self.assertRaises(ComponentError):registry_header([])
    def test_declared_callback_signatures_are_compile_checked(self):
        header=self.root/'component_callbacks.h'
        header.write_text(callback_header(self.discover()))
        source=self.root/'wrong.c'
        source.write_text('void demo_get(void) {}\n')
        result=subprocess.run(['cc','-std=c11','-Werror','-I',str(ROOT/'sdk/nds'),
            '-include',str(header),'-c',str(source),'-o',str(self.root/'wrong.o')],
            capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('demo_get',result.stderr)
        source.write_text('uint32_t demo_get(uint8_t *p,uint32_t n) { return n; }\n')
        subprocess.run(['cc','-std=c11','-Werror','-I',str(ROOT/'sdk/nds'),'-include',str(header),
            '-c',str(source),'-o',str(self.root/'right.o')],check=True,capture_output=True)

    def test_native_registration_lifecycle_lengths_and_refusals(self):
        cs=self.discover();(self.root/'component_registry.h').write_text(registry_header(cs))
        test=self.root/'test.c';test.write_text('''
#include <assert.h>
#include "components/component.h"
static unsigned init_calls,ticks,writes;
void demo_init(void){init_calls++;}
void demo_tick(void){ticks++;}
uint32_t demo_get(uint8_t *b,uint32_t n){assert(n==4);b[0]=1;return 1;}
uint32_t demo_set(const uint8_t *b,uint32_t n){assert(n==2);writes++;return b[0];}
int main(void){
 uint8_t b[4]={0};gp50_components_init();gp50_components_tick();gp50_components_tick();
 assert(init_calls==1&&ticks==2);assert(gp50_components_has(0x76)&&!gp50_components_has(0x75));
 assert(!gp50_components_read(0x75,b,4));assert(!gp50_components_read(0x76,b,3));
 assert(gp50_components_read(0x76,b,4)==1&&b[0]==1);b[0]=0;
 assert(gp50_components_write(0x75,b,2)==1&&writes==0);
 assert(gp50_components_write(0x76,b,1)==1&&writes==0);
 assert(gp50_components_write(0x76,b,2)==0&&writes==1);b[0]=42;
 assert(gp50_components_write(0x76,b,2)==1&&writes==2);return 0;
}
''')
        binary=self.root/'test'
        subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(self.root),'-I',str(ROOT/'sdk/nds'),
            str(ROOT/'sdk/nds/components/components_registry.c'),str(test),'-o',str(binary)],check=True,capture_output=True)
        subprocess.run([str(binary)],check=True)

if __name__=='__main__':unittest.main()
