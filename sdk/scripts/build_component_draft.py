#!/usr/bin/env python3
"""Compose the MOD097 (stable B placement; no expanded E) draft: MOD088's container with only NDS regions B and E replaced
by the component_draft build. Never installs; output names say NOT_RELEASED.

cfg container_parent selects a reviewed derivation of MOD088 (SDK stock-boot platform); default stays MOD088.
Checks: MOD088 identity; regions C, F, G byte-identical to MOD088; E differs from MOD088 only inside the declared E code
payload (which was erased in MOD088) and nowhere else; independent decode/CRC of the packed container; header bytes
outside the length/CRC fields unchanged.
"""
import hashlib, json, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R / 'scripts'), str(R)]
from firmware_verify import decode, require
import htfw_pack
from nds_ui import build, image
from nds_ui.cli import image_lock, load_cfg

PARENT = R / 'work/custom_images/mod088_capture_status/GP-50_V1.1.0_MOD088_CaptureStatus.bin'
PARENT_SHA = '47e030d5a85e5e08c65361baa9de536189955b69a7cfeb407620171a9bec1c1d'
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def main(cfg=None):
    cfg = cfg or load_cfg('component_draft')
    work = R / 'work' / cfg['id']
    generated_dir = R / 'work/nds_ui' / cfg['id']
    require(cfg['component_only'], 'draft must stay component_only')
    selected = cfg.get('container_parent', dict(image=str(PARENT.relative_to(R)), sha256=PARENT_SHA))
    parent = (R / selected['image']).read_bytes()
    require(sha(parent) == selected['sha256'], 'container parent identity')
    with image_lock(cfg):
        nds_image, nds, generated = image.build_image(cfg, write=False, component_bundle=True)
        build.write_outputs(generated_dir, cfg, generated, cfg['parent']['label'])
    callback_resources = None
    if 'external_components_c' in cfg['features']:
        from nds_ui.component_stack import check_build
        callback_resources = check_build(generated_dir, R/'tools/nds32/prefix/bin/nds32le-elf-nm')
        work.mkdir(parents=True, exist_ok=True)
        (work/'callback_resources.json').write_text(json.dumps(callback_resources, indent=2)+'\n')
        require(callback_resources['status'] == 'pass',
                'component callback stack budget unresolved/exceeded; see '+str(work/'callback_resources.json'))
    regions, _ = decode(parent)
    old = {key: raw for key, _, raw in regions}
    new = {key: raw for key, _, raw in decode(nds_image)[0]}
    e_code = sorted((x for x in generated['external'] if x['section'] != '.catalog_ext'), key=lambda x: x['address'])
    require(bool(e_code), 'E code payloads')
    covered = set()
    if 'header' in cfg.get('catalog_ext', {}) or 'container_parent' in cfg:
        # A selected platform or author effects change the catalog; only its declared payload may replace the parent's.
        for x in generated['external']:
            if x['section'] == '.catalog_ext':
                require(new['e'][x['offset']:x['offset'] + len(x['bytes'])] == x['bytes'], 'E catalog placed')
                covered.update(range(x['offset'], x['offset'] + len(x['bytes'])))
    for x in e_code:
        lo_x, hi_x = x['offset'], x['offset'] + len(x['bytes'])
        require(old['e'][lo_x:hi_x] == b'\xff' * (hi_x - lo_x), 'E code destination erased in MOD088')
        require(new['e'][lo_x:hi_x] == x['bytes'], 'E payload placed')
        covered.update(range(lo_x, hi_x))
    lo = min(covered); hi = max(covered) + 1
    diff = [i for i, (x, y) in enumerate(zip(old['e'], new['e'])) if x != y]
    require(len(old['e']) == len(new['e']) and all(i in covered for i in diff), 'E changes only inside declared code/rodata payloads')
    replacements = dict(old, b=new['b'], e=new['e'])
    final = [(key, descriptor, replacements[key]) for key, descriptor, _ in regions]
    header, record_list = htfw_pack.parse_template(parent)
    require(record_list == [(key, descriptor) for key, descriptor, _ in final], 'container template')
    packed = htfw_pack.build(header, final, compressed=True)
    actual, _ = decode(packed)
    require(actual == final, 'independent decode/CRCs')
    mutable = {4, 5, *range(8, 12), *range(0x24, 0x28)}
    require(all(packed[i] == parent[i] for i in range(0x38) if i not in mutable), 'header outside length/CRC fields')
    identity = sha(packed)
    folder = work / identity[:16]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / cfg['name']).write_bytes(packed)
    for key, _, raw in final:
        (folder / f'decoded_{key}.bin').write_bytes(raw)
    b_diff = [i for i, (x, y) in enumerate(zip(old['b'], new['b'])) if x != y]
    inputs = {str(q.relative_to(R)): sha(q.read_bytes()) for root in ('scripts/nds_ui', 'sdk', 'firmware/reconstructed')
              for q in sorted((R / root).rglob('*')) if q.is_file() and q.suffix in ('.py', '.c', '.h', '.S', '.ld', '.json')}
    from nds_ui.compat import MAP_PATH
    inputs[MAP_PATH] = sha((R/MAP_PATH).read_bytes())
    inputs[str(Path(__file__).relative_to(R))] = sha(Path(__file__).read_bytes())
    manifest = dict(callback_resources=callback_resources, status='draft_not_reviewed', image_sha256=identity, inputs=inputs, nds=nds, version=cfg['version'], parent_sha256=selected['sha256'],
                    admission_table=json.loads((generated_dir / 'layout.json').read_text())['admission'].get('table'),
                    regions=[dict(id=k, bytes=len(v), sha256=sha(v), changed=k in ('b', 'e')) for k, _, v in final],
                    e_payload_ranges=[dict(section=x['section'], address=hex(x['address']), end=hex(x['address']+len(x['bytes']))) for x in e_code],
                    b_changed_bytes=len(b_diff), e_changed_range=[hex(lo + 0x190000), hex(hi + 0x190000)],
                    unchanged=['c', 'f', 'g'] if all(replacements[k] == old[k] for k in ('c', 'f', 'g')) else 'CHECK')
    # Retain exact source inputs independently of future workspace edits.
    snapshots=folder/'source_inputs'
    for source,digest in inputs.items():
        target=snapshots/source; target.parent.mkdir(parents=True,exist_ok=True)
        raw=(R/source).read_bytes(); require(sha(raw)==digest,'source changed during composition: '+source)
        target.write_bytes(raw)
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    # Review input view for the existing read-only regression tools (cfg output): image, decoded regions, ledger.
    view = R / cfg['output']; (view / 'regions').mkdir(parents=True, exist_ok=True)
    (view / cfg['name']).write_bytes(packed)
    for key, _, raw in final:
        (view / 'regions' / f'decoded_{key}.bin').write_bytes(raw)
    ledger = dict(nds); ledger.update(status=f"MOD{cfg['mod']:03d} DRAFT REVIEW INPUT; NOT APPROVED", image_sha256=identity, image_bytes=len(packed),
                                      regions=manifest['regions'], unchanged=['c', 'f', 'g'])
    (view / 'nds_ui_manifest.json').write_text(json.dumps(ledger, indent=2) + '\n')
    (work / 'latest.json').write_text(json.dumps(dict(folder=str(folder.relative_to(R)), image_sha256=identity), indent=2) + '\n')
    # Preserve immutable validation inputs before publishing a reusable ledger.
    import shutil
    from nds_b_sections import verify as verify_b
    from nds_e_sections import verify as verify_e
    from nds_ui import b_link
    linked=generated_dir/'c/linked'
    elf=linked/(build.c_artifact_name(generated['enabled'])+'.elf')
    # Use the actual combined C feature list, excluding assembly-only modules.
    cf=[f for f in generated['enabled'] if getattr(build.feature(f),'C_SOURCES',None) and build.has_c(f,cfg)]
    elf=linked/(build.c_artifact_name(cf)+'.elf')
    proposal=json.loads((linked/'b_placement.proposed.json').read_text())
    b_sections=verify_b(elf.read_bytes(),new['b'],proposal)
    e_sections=verify_e(elf.read_bytes(),new['e'])
    # A repeat build has the same image hash but different retention metadata.
    # Content-address evidence separately; never overwrite the previous ledger's
    # validation inputs before a new ledger has successfully committed.
    evidence=folder/'placement'/sha(json.dumps(proposal,sort_keys=True).encode())[:16]
    evidence.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(elf,evidence/'linked.elf')
    (evidence/'b_placement.json').write_text(json.dumps(proposal,indent=2)+'\n')
    receipt=evidence/'section_validation.json'
    receipt.write_text(json.dumps(dict(image_sha256=identity,b_sections=b_sections,e_sections=e_sections),indent=2)+'\n')
    b_link.commit(R/cfg['b_placement']['ledger'],proposal,[folder/cfg['name'],evidence/'linked.elf',evidence/'b_placement.json',receipt],R)
    ram_file=linked/'component_ram.proposed.json'
    ram=json.loads(ram_file.read_text()) if ram_file.exists() else None
    if ram is not None:
        from nds_ui.component_ram import ledger_path
        # Freeze the proposal used by this image before publishing reusable state.
        shutil.copyfile(ram_file,evidence/'component_ram.json')
        b_link.commit(ledger_path(cfg,R),ram['layout'],
                      [folder/cfg['name'],evidence/'component_ram.json',receipt],R)
    print(json.dumps(dict(image_sha256=identity,folder=str(folder.relative_to(R)),b_sections=len(b_sections),e_sections=len(e_sections),
        b_retained=proposal['retained'],b_allocations=len(proposal['allocations']),b_free_bytes=proposal['free_bytes'],b_largest_span=proposal['largest_free_span']),indent=2))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Build a named component image offline.')
    parser.add_argument('image', nargs='?', default='component_draft',
                        help='image configuration name (default: component_draft)')
    options = parser.parse_args()
    main(load_cfg(options.image))
