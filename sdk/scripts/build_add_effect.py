#!/usr/bin/env python3
"""Add one SDK-built effect to an existing image as a new last entry of its group. Offline.

Appends the effect's overlay record to region g and its descriptor to the region-e catalog,
optionally sets the on-screen version text, and changes nothing else: every existing record
and descriptor must stay byte-identical, regions c and f identical, region b identical apart
from the version text, region e's length unchanged. Reports whether region g crosses a 4 KiB
boundary. Never installs.

  build_add_effect.py --base IMAGE.bin --effect work/sdk_build/NAME --out work/custom_images/DIR \
      --name FILE.bin [--version-text X1.1.0Y]
  build_add_effect.py --verify work/custom_images/DIR

Own-catalog images (MOD051+, item 9 phase C; analysis/firmware/NDS_EFFECT_CATALOG.md section 7): with --own-catalog
only region g changes. The descriptor must already be in sdk/nds/catalog/extension.json (scripts/build_catalog_ext.py
--add-effect DIR) at exactly the ordinal the new g record gets; region e stays stock + declared assets; afterwards g's
group counts must equal the logical catalog's. The NDS side (catalog data in b) is then built by scripts/nds_ui with
this image as parent.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from firmware_verify import decode,require,sha
import htfw_pack
import ui_theme
from protocol.overlay_image import parse_container,build_container,parse_overlay,parse_descriptor

ROOT=Path(__file__).resolve().parent.parent
CATALOG=0x10000
EXTERNAL_CATALOG=(0x14000,0x16000)   # nds_ui catalog_storage: immutable own descriptor arrays in E


def _catalog_ext():
    import importlib.util
    spec=importlib.util.spec_from_file_location('build_catalog_ext',ROOT/'scripts/build_catalog_ext.py');x=importlib.util.module_from_spec(spec);spec.loader.exec_module(x);return x


def build(base,effect_dir,version_text,own_catalog=None,stock_e=None,source_dir=None,external_catalog=False):
    """own_catalog: path of the extension.json describing the logical catalog (own-catalog mode), else None.
    external_catalog: the base keeps descriptors in E storage; the NDS composer replaces them, so ignore that window."""
    manifest=json.loads((effect_dir/'manifest.json').read_text())
    record=(effect_dir/'record.bin').read_bytes();descriptor=(effect_dir/'descriptor.bin').read_bytes()
    require(sha(record)==manifest['sha256']['record.bin'] and sha(descriptor)==manifest['sha256']['descriptor.bin'],'SDK outputs differ from their manifest')
    for name,expected in manifest['sha256'].items():
        if name.startswith('author_effect/'):
            require(source_dir is not None, 'external author inputs require --source-dir')
            source_root=Path(source_dir).resolve();source=(source_root/name[len('author_effect/'):]).resolve()
            require(source.is_relative_to(source_root), 'author source escapes --source-dir')
            require(sha(source.read_bytes())==expected,f'SDK source changed since build: {name}')
        elif '/' in name:require(sha((ROOT/name).read_bytes())==expected,f'SDK source changed since build: {name}')
    group=manifest['effect']['group'];new=parse_descriptor(descriptor);overlay=parse_overlay(record)
    base_regions,_=decode(base);base_map={rid:data for rid,_,data in base_regions}
    g_old=base_map['g'];e_old=base_map['e']
    if own_catalog:
        X=_catalog_ext();ext=json.loads(Path(own_catalog).read_text());stock=X.stock_e(stock_e);X.check(ext,stock)
        e_expected=X.image_e(ext,stock)
        if external_catalog:
            lo,hi=EXTERNAL_CATALOG;e_old=e_old[:lo]+e_expected[lo:hi]+e_old[hi:]
        require(e_old==e_expected,'own-catalog mode: base e is not stock + declared assets')
        e_view=X.logical(ext,stock)   # the catalog the NDS serves (stock e + extension), descriptor already added
    gc=parse_container(g_old);ec=parse_container((e_view if own_catalog else e_old)[CATALOG:])
    require(build_container(gc)==g_old and build_container(ec)==(e_view if own_catalog else e_old)[CATALOG:],'containers do not round-trip')
    old_records=gc.records();old_descriptors=ec.records()
    ids=[parse_descriptor(b).public_id for b in ec.groups[group]]
    replace=ids.index(new.public_id) if new.public_id in ids else None   # same ID in the same group: replace that entry in place
    require(sum(new.public_id==parse_descriptor(b).public_id for b in old_descriptors)==(replace is not None),'public ID already used in another group')
    if own_catalog:
        # the extension already holds the descriptor: as the new last entry of its group (one more than g), or in place
        if len(ec.groups[group])==len(gc.groups[group])+1:
            require(ids[-1]==new.public_id and ec.groups[group][-1]==descriptor,'own-catalog mode: descriptor is not the last appended entry of its group in extension.json')
            replace=None;ec.groups[group].pop();ids.pop()   # compare counts against the catalog before this effect
        else:
            require(replace is not None and ec.groups[group][replace]==descriptor,'own-catalog mode: descriptor not in extension.json (run build_catalog_ext.py --add-effect)')
    require([len(x) for x in gc.groups[:10]]==[len(x) for x in ec.groups[:10]],'g/e ordinals differ in the base image')
    if own_catalog:
        if replace is None:gc.groups[group].append(record);position=sum(len(x) for x in gc.groups[:group+1])-1
        else:position=sum(len(x) for x in gc.groups[:group])+replace;gc.groups[group][replace]=record;old_records=old_records[:position]+old_records[position+1:]
        g_new=build_container(gc);records=parse_container(g_new).records()
        require(records[:position]+records[position+1:]==old_records and records[position]==record,'stock g records changed')
        require([len(x) for x in parse_container(g_new).groups[:10]]==[len(x) for x in parse_container(e_view[CATALOG:]).groups[:10]],'g counts differ from the logical catalog')
        b_new,theme=(ui_theme.apply(base_map['b'],version_text=version_text) if version_text else (base_map['b'],dict(changed=[])))
        require(len(b_new)==len(base_map['b']) and len(theme['changed'])<=1,'region b changed beyond the version text')
        regions=[(rid,dest,{'g':g_new,'b':b_new}.get(rid,data)) for rid,dest,data in base_regions]
        header,template=htfw_pack.parse_template(base);require(template==[(rid,dest) for rid,dest,_ in regions],'template identity mismatch')
        image=htfw_pack.build(header,regions,compressed=True);actual,report=decode(image);require(actual==regions,'independent decode differs from desired regions')
        for rid,_,data in actual:
            if rid in 'cef':require(data==base_map[rid],f'{rid} changed')
        report.update(added_effect=dict(name=new.name,public_id=f'0x{new.public_id:08x}',group=group,ordinal=len(gc.groups[group])-1 if replace is None else replace,replaced_existing_entry=replace is not None,
                record_bytes=len(record),record_sha256=sha(record),catalog='own (sdk/nds/catalog/extension.json)'),
            g_change=dict(old_size=len(g_old),new_size=len(g_new),growth=len(g_new)-len(g_old),crosses_4k_boundary=-(-len(g_old)//0x1000)!=-(-len(g_new)//0x1000),stock_records_byte_identical=True),
            e_change=dict(unchanged=True,own_catalog=True),b_change=dict(version_text=version_text,sites_changed=len(theme['changed'])),regions_identical_to_base=['c','e','f'])
        return image,regions,report
    if replace is None:
        position=sum(len(x) for x in gc.groups[:group+1]);gc.groups[group].append(record);ec.groups[group].append(descriptor)
        epos=position
        others=lambda items,i:items[:i]+items[i+1:]
    else:
        position=epos=sum(len(x) for x in gc.groups[:group])+replace;gc.groups[group][replace]=record;ec.groups[group][replace]=descriptor
        old_records=old_records[:position]+old_records[position+1:];old_descriptors=old_descriptors[:epos]+old_descriptors[epos+1:]
        others=lambda items,i:items[:i]+items[i+1:]
    g_new=build_container(gc);records=parse_container(g_new).records()
    require(others(records,position)==old_records and records[position]==record,'stock g records changed')
    grown=build_container(ec);extra=len(grown)-(len(e_old)-CATALOG)
    require(extra>=0 and (extra>0 or replace is not None) and ec.trailing[:extra]==b'\xff'*extra,'catalog would overwrite non-fill bytes')
    e_new=e_old[:CATALOG]+grown[:len(grown)-len(ec.trailing)]+ec.trailing[extra:] if extra else e_old[:CATALOG]+grown
    require(len(e_new)==len(e_old) and e_new[:CATALOG]==e_old[:CATALOG],'region e outside the catalog changed')
    descs=parse_container(e_new[CATALOG:]).records()
    require(others(descs,epos)==old_descriptors and descs[epos]==descriptor,'stock descriptors changed')
    b_new,theme=(ui_theme.apply(base_map['b'],version_text=version_text) if version_text else (base_map['b'],dict(changed=[])))
    require(len(b_new)==len(base_map['b']) and len(theme['changed'])<=1,'region b changed beyond the version text')
    new_map={'g':g_new,'e':e_new,'b':b_new}
    regions=[(rid,dest,new_map.get(rid,data)) for rid,dest,data in base_regions]
    header,template=htfw_pack.parse_template(base)
    require(template==[(rid,dest) for rid,dest,_ in regions],'template identity mismatch')
    image=htfw_pack.build(header,regions,compressed=True)
    actual,report=decode(image);require(actual==regions,'independent decode differs from desired regions')
    mutable={4,5,*range(8,12),*range(0x24,0x28)}
    require(all(image[i]==base[i] for i in range(0x38) if i not in mutable),'unexpected header metadata change')
    for rid,_,data in actual:
        if rid in 'cf':require(data==base_map[rid],f'{rid} changed')
    report.update(added_effect=dict(name=new.name,type=new.type_name,public_id=f'0x{new.public_id:08x}',group=group,ordinal=len(gc.groups[group])-1 if replace is None else replace,replaced_existing_entry=replace is not None,
            parameters=[p.name for p in new.parameters],record_bytes=len(record),descriptor_bytes=len(descriptor),payload_bytes=len(overlay.primary),secondary_bytes=len(overlay.secondary),
            state_bytes=manifest['state_bytes'],slot_bytes_free=manifest['slot_bytes_free'],record_sha256=sha(record)),
        g_change=dict(old_size=len(g_old),new_size=len(g_new),growth=len(g_new)-len(g_old),sectors_4k=[-(-len(g_old)//0x1000),-(-len(g_new)//0x1000)],
            crosses_4k_boundary=-(-len(g_old)//0x1000)!=-(-len(g_new)//0x1000),stock_records_byte_identical=True),
        e_change=dict(region_size_unchanged=True,fill_bytes_consumed=extra,stock_descriptors_byte_identical=True),
        b_change=dict(version_text=version_text,sites_changed=len(theme['changed'])),regions_identical_to_base=['c','f'])
    return image,regions,report


def main():
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--base',type=Path);p.add_argument('--effect',type=Path);p.add_argument('--out',type=Path);p.add_argument('--name');p.add_argument('--version-text')
    p.add_argument('--verify',type=Path)
    p.add_argument('--stock-e',type=Path,help='explicit decoded stock catalog for own-catalog mode')
    p.add_argument('--source-dir',type=Path,help='external effect source folder recorded as author_effect/')
    p.add_argument('--lzo-library',type=Path,help='existing liblzo2 for encoding and independent decoding')
    p.add_argument('--own-catalog',nargs='?',const=str(ROOT/'sdk/nds/catalog/extension.json'),help='own-catalog mode (optional extension.json path)')
    a=p.parse_args()
    def configure_library(path):
        if path is not None:
            import firmware_verify
            firmware_verify.LZO=str(path)
            htfw_pack.LIBRARY=str(path)
    configure_library(a.lzo_library)
    if a.verify:
        m=json.loads((a.verify/'manifest.json').read_text())
        configure_library(a.lzo_library or m.get('lzo_library'))
        image,_,_=build((ROOT/m['base_image']).read_bytes(),ROOT/m['effect_build'],m['b_change']['version_text'],m.get('own_catalog'),m.get('stock_e'),m.get('source_dir'))
        require(sha((ROOT/m['base_image']).read_bytes())==m['base_sha256'] and sha(image)==m['image_sha256']==sha((ROOT/m['image']).read_bytes()),'rebuilt image differs from the stored one')
        print('verified',m['image'],m['image_sha256']);return 0
    if not (a.base and a.effect and a.out and a.name):p.error('--base, --effect, --out and --name are required')
    if a.out.exists():p.error('output directory exists; choose a new one')
    if Path(a.name).name != a.name or a.name in ('.','..'):p.error('--name must be a plain filename')
    base=a.base.read_bytes();image,regions,report=build(base,a.effect.resolve(),a.version_text,a.own_catalog,a.stock_e,a.source_dir)
    for key in ('stock_e','source_dir','lzo_library'):
        value=getattr(a,key)
        if value is not None:report[key]=str(value.resolve())
    if a.own_catalog:report['own_catalog']=a.own_catalog
    out=a.out.resolve();out.mkdir(parents=True);(out/'regions').mkdir()
    for rid,_,data in regions:(out/'regions'/f'decoded_{rid}.bin').write_bytes(data)
    (out/a.name).write_bytes(image)
    display=lambda q:str(q.resolve().relative_to(ROOT)) if q.resolve().is_relative_to(ROOT) else str(q.resolve())
    report.update(status='BUILT AND VERIFIED OFFLINE; NOT INSTALLED',image=display(out/a.name),image_sha256=sha(image),
        base_image=display(a.base),base_sha256=sha(base),effect_build=display(a.effect),
        source_hashes={str(q.relative_to(ROOT)):sha(q.read_bytes()) for q in [Path(__file__).resolve(),ROOT/'scripts/ui_theme.py',ROOT/'scripts/firmware_verify.py',ROOT/'scripts/htfw_pack.py',ROOT/'protocol/overlay_image.py',ROOT/'sdk/build_effect.py']},
        authorization='')
    (out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('image','image_sha256','added_effect','g_change','e_change','b_change')},indent=1))
    return 0
if __name__=='__main__':sys.exit(main())
