#!/usr/bin/env python3
"""Compose an offline, unreviewed component image without address/linker edits.
Components must already reside inside the package; use --component-root for a
parent directory containing component folders. Never accesses or installs a device.
"""
import argparse,copy,json,re
from pathlib import Path
from nds_ui.cli import load_cfg
from nds_ui.components import discover,ComponentError
from build_component_draft import main as compose,R

def configure(ident,mod,version,roots,platform=None):
 if not re.fullmatch(r'[a-z][a-z0-9_]{2,47}',ident):raise ValueError('id: use 3-48 lowercase letters/digits/underscores')
 if isinstance(mod,bool) or not isinstance(mod,int) or not 98<=mod<=999:raise ValueError('mod: use an unused number 98-999')
 # N1.1.0x was exhausted by 2026-11-05; P1.1.0x continues the series (ui_theme: only the first and last characters are free).
 if not re.fullmatch(r'[A-Z]1\.1\.0[A-Za-z0-9]',version):raise ValueError('version: expected X1.1.0y (the stock settings migration reads the 1.1.0)')
 cfg=copy.deepcopy(load_cfg((platform or {}).get('base_config','editor_drum_fix')));relative=[]
 if platform:cfg.update({k:platform[k] for k in('parent','container_parent','catalog_ext')})
 for value in roots:
  root=Path(value).resolve()
  if not root.is_relative_to(R):raise ValueError('component root must be inside this package: '+str(root))
  relative.append(str(root.relative_to(R)))
 components=discover([R/p for p in relative],R)
 if not components:raise ValueError('no components found: roots contain */component.json')
 cfg.update(id=ident,mod=mod,version=version,component_roots=relative,
  name=f'NOT_RELEASED_MOD{mod:03d}_{ident.upper()}.bin',
  filename=f'NOT_RELEASED_MOD{mod:03d}_{ident.upper()}.bin',output='work/custom_images/'+ident,
  summary=('Author-supplied components; UNREVIEWED offline image' +
           ('; ABI3 feature components' if any(c['abi']==3 for c in components) else
            '; experimental ABI2 volatile state' if any(c['abi']==2 for c in components) else '; ABI1 stateless')))
 if any(c['abi']==3 for c in components) and 'GP50_FEATURES=1' not in cfg.get('c_defines',[]):
  cfg['c_defines']=[*cfg.get('c_defines',[]),'GP50_FEATURES=1']   # ABI 3: platform hooks call the feature dispatcher
 for c in components:   # one switch per SDK feature, so the platform can retire the code a feature replaces
  flag='GP50_FEATURE_'+c['id'].upper()+'=1'
  if c['abi']==3 and flag not in cfg['c_defines']:cfg['c_defines']=[*cfg['c_defines'],flag]
 if any(c['abi']==3 for c in components) and 'diagnostics_c' in cfg.get('features',()) and 'GP50_LOAD_BRIDGE=1' not in cfg['c_defines']:
  cfg['c_defines']=[*cfg['c_defines'],'GP50_LOAD_BRIDGE=1']   # gp50_load_get reads the 12 50 load bridge
 if any(c['abi']==3 and c.get('menu') for c in components) and 'GP50_FEATURES_MENU=1' not in cfg['c_defines']:
  cfg['c_defines']=[*cfg['c_defines'],'GP50_FEATURES_MENU=1']   # the Global settings feature tile
 if any(c['abi']==3 for c in components) and not any(c['abi']==2 for c in components):
  # RAM arena taken from the heap: what the features declare (+8 gate words each, 16 platform), 8-aligned, in 256s.
  from nds_ui.component_ram import FEATURES_BYTES
  need=FEATURES_BYTES+sum((c['resources']['state_bytes']+8+7)//8*8 for c in components if c['abi']==3)
  cfg['component_state_arena_bytes']=min(4096,(need+255)//256*256)
 cfg['stock_theme']=True   # stock blue UI: the parent's MOD005 pink colour loads go back to stock bytes
 cfg['b_placement']={'ledger':f'work/{ident}/b_placement/committed.json'}
 return cfg,components

def validate_output_identity(cfg):
 # A private author receipt owns an output. Research/candidate directories and
 # configs predate this receipt and must never become author outputs by accident.
 work=R/'work'/cfg['id'];snapshot=work/'author_config.json'
 config=R/'scripts/nds_ui/images'/(cfg['id']+'.json')
 output=R/cfg['output'] if 'output' in cfg else None
 if not snapshot.exists() and (work.exists() or config.exists() or output and output.exists()):
  raise ValueError('id already belongs to existing project outputs; choose another id')
 if snapshot.exists():
  if json.loads(snapshot.read_text())!=cfg or config.exists() and json.loads(config.read_text())!=cfg:
   raise ValueError('id already belongs to a different config; choose another id')

def compose_config(cfg):
 # Share output identity protection with the staged package driver.
 validate_output_identity(cfg)
 work=R/'work'/cfg['id'];snapshot=work/'author_config.json'
 work.mkdir(parents=True,exist_ok=True);snapshot.write_text(json.dumps(cfg,indent=2)+'\n')
 return compose(cfg)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--id',required=True);p.add_argument('--mod',required=True,type=int);p.add_argument('--version',required=True)
 p.add_argument('--component-root',action='append',required=True)
 p.add_argument('--check',action='store_true',help='validate declarations and print config without building')
 a=p.parse_args()
 try:
  cfg,components=configure(a.id,a.mod,a.version,a.component_root)
  validate_output_identity(cfg)
 except (ValueError,ComponentError)as e:p.error(str(e))
 if a.check:print(json.dumps(dict(status='validated_not_built',config=cfg,components=[c['id']for c in components]),indent=2));return
 try:compose_config(cfg)
 except ValueError as e:p.error(str(e))
if __name__=='__main__':main()
