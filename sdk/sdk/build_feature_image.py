#!/usr/bin/env python3
"""Build an ABI1 feature image from a staged SDK and user-supplied stock. Offline only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sha = lambda data: hashlib.sha256(data).hexdigest()


def add_effects(effects, inputs, platform, stock_g, stock_e, clang, arm_bin):
    """Author ARM effects -> catalog extension + header + container parent. Placement is automatic."""
    import subprocess
    import build_add_effect
    import build_catalog_ext as catalog
    ext = json.loads((ROOT/platform['catalog_ext']['extension']).read_text())
    container = (ROOT/platform['container_parent']['image']).read_bytes()
    stock = catalog.stock_e(stock_e)
    for index, source in enumerate(effects):
        out = inputs/('effect_%02d' % index)
        subprocess.run([sys.executable, str(ROOT/'sdk/build_effect.py'), str(source), '--out', str(out),
                        '--stock-g', str(stock_g), '--clang', clang, '--arm-bin', str(arm_bin)], check=True)
        built = json.loads((out/'manifest.json').read_text())
        blob = (out/'descriptor.bin').read_bytes()
        effect = built['effect']
        group = effect['group']
        if 'stock_ordinal' in effect:
            ordinal = effect['stock_ordinal']
            stock_group = catalog.groups(stock)[group]
            active_group = catalog.resolve(ext, stock)[group]
            if (type(ordinal) is not int or not 0 <= ordinal < len(stock_group)
                    or blob != stock_group[ordinal] or blob != active_group[ordinal]):
                raise ValueError(f'{source.name}: replacement must match the active stock descriptor')
        else:
            ext['entries'].append(catalog.entry('append', group, blob, 'author effect '+source.name))
        catalog.check(ext, stock)
        header, text = catalog.header(ext)
        (inputs/'extension.json').write_text(text)
        (inputs/'catalog_ext_author.h').write_text(header)
        container, _, _ = build_add_effect.build(container, out, None, own_catalog=str(inputs/'extension.json'),
                                                 stock_e=stock_e, source_dir=source, external_catalog=True)
    (inputs/'container_parent.bin').write_bytes(container)
    relative = lambda path: str(path.relative_to(ROOT))
    return dict(container_parent=dict(image=relative(inputs/'container_parent.bin'), sha256=sha(container)),
                catalog_ext=dict(extension=relative(inputs/'extension.json'), sha256=sha(text.encode()),
                                 header=relative(inputs/'catalog_ext_author.h')))


def add_boot_gif(source, inputs, platform):
    """Author boot GIF -> asset-bearing catalog extension and parents. The stock animation stays the default."""
    import boot_gif
    import build_catalog_ext as catalog
    import firmware_verify
    import htfw_pack
    data = source.read_bytes()
    facts = boot_gif.validate(data)
    (inputs/'boot.gif').write_bytes(data)
    relative = lambda path: str(path.relative_to(ROOT))
    ext = json.loads((ROOT/platform['catalog_ext']['extension']).read_text())
    if ext['e_assets']:
        raise ValueError('platform catalog already declares an E asset')
    ext['e_assets'] = [dict(name='author boot GIF', offset=hex(boot_gif.E_OFFSET), length=len(data),
                            source=relative(inputs/'boot.gif'), sha256=sha(data))]
    header, text = catalog.header(ext)
    (inputs/'extension.json').write_text(text)
    (inputs/'catalog_ext_author.h').write_text(header)
    selected = dict(catalog_ext=dict(extension=relative(inputs/'extension.json'), sha256=sha(text.encode()),
                                     header=relative(inputs/'catalog_ext_author.h')))
    for key in ('parent', 'container_parent'):
        raw = (ROOT/platform[key]['image']).read_bytes()
        regions, report = firmware_verify.decode(raw)
        firmware_verify.require(report['all_region_crcs_ok'], 'platform parent CRCs')
        at = boot_gif.DESCRIPTOR_OFFSET
        changed = []
        for rid, dest, region in regions:
            if rid == 'b':
                firmware_verify.require(region[at:at+12] == boot_gif.STOCK_DESCRIPTOR, 'stock boot descriptor')
                region = region[:at]+boot_gif.descriptor(len(data))+region[at+12:]
            elif rid == 'e':
                lo = boot_gif.E_OFFSET
                firmware_verify.require(region[lo:lo+len(data)] == b'\xff'*len(data), 'boot GIF destination erased')
                region = region[:lo]+data+region[lo+len(data):]
            changed.append((rid, dest, region))
        header_bytes, _ = htfw_pack.parse_template(raw)
        built = htfw_pack.build(header_bytes, changed, compressed=True)
        path = inputs/(key+'_boot.bin')
        path.write_bytes(built)
        selected[key] = dict(platform[key], image=relative(path), sha256=sha(built))
    return selected, facts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', required=True, type=Path)
    parser.add_argument('--toolchain-prefix', required=True, type=Path)
    parser.add_argument('--lzo-library', required=True, type=Path)
    parser.add_argument('--id', required=True)
    parser.add_argument('--mod', required=True, type=int)
    parser.add_argument('--version', required=True)
    parser.add_argument('--component-root', action='append', required=True,
                        help='package-relative parent directory containing component folders')
    parser.add_argument('--effect', action='append', default=[], type=Path,
                        help='author ARM effect directory (effect.json + C); repeat for several')
    parser.add_argument('--clang', default='clang', help='Clang executable for --effect')
    parser.add_argument('--boot-gif', type=Path, help='optional %dx%d boot animation; default keeps the stock one' % (144, 28))
    parser.add_argument('--arm-bin', type=Path, help='arm-none-eabi binutils directory, required with --effect')
    parser.add_argument('--forbid-project', type=Path,
                        help='acceptance check: reject undeclared reads of this authoring tree')
    parser.add_argument('--capture-player', choices=('latest',), help='build paired VTSI/GPTC resident and fused IR512 player from SDK source')
    parser.add_argument('--exclude-effect', action='append', default=[], type=lambda value: int(value, 0), help='omit an SDK extension effect by public ID')
    parser.add_argument('--admission-table', help='CPU-admission cost table version (sdk/telemetry/nds/admission_costs.py RUNS); default: the base config\'s')
    parser.add_argument('--admission-estimate-override', action='append', default=[],
                        metavar='EFFECT', help='use the SDK cost estimate for a rebuilt measured effect')
    args = parser.parse_args()
    if not args.arm_bin or not args.capture_player:
        parser.error('this platform needs --arm-bin and --capture-player latest')
    manifest = json.loads((ROOT/'package_manifest.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('kind') != 'feature_sdk':
        parser.error('requires a staged feature SDK proposal')
    for name, digest in manifest['files'].items():
        if sha((ROOT/name).read_bytes()) != digest:
            parser.error('package input mismatch: '+name)
    effects = [path.resolve() for path in args.effect]
    if effects and not args.arm_bin:
        parser.error('--effect requires --arm-bin')
    for path in effects:
        if not (path/'effect.json').is_file():
            parser.error('effect directory has no effect.json: '+str(path))
    tool = args.toolchain_prefix.resolve()
    for name in ('gcc', 'ld', 'nm', 'objcopy', 'objdump', 'as', 'readelf'):
        if not (tool/'bin'/('nds32le-elf-'+name)).is_file():
            parser.error('missing compiler tool: nds32le-elf-'+name)
    library = args.lzo_library.resolve()
    if not library.is_file():
        parser.error('LZO library does not exist')
    link = ROOT/'tools/nds32/prefix'
    if (link.exists() or link.is_symlink()) and link.resolve() != tool:
        parser.error('toolchain prefix collision')
    sys.path[:0] = [str(ROOT/'scripts'), str(ROOT)]
    import firmware_verify
    import htfw_pack
    firmware_verify.LZO = str(library)
    htfw_pack.LIBRARY = str(library)
    from sdk.telemetry.nds import admission_costs
    admission_costs.use_measurements(ROOT/'sdk/telemetry/nds/measurements.json')
    from compose_component_image import configure, validate_output_identity, compose_config
    roots = [str((ROOT/p).resolve()) for p in args.component_root]
    platform = json.loads((ROOT/'sdk/nds/platform.json').read_text())
    if platform.get('schema') != 1 or sha((ROOT/'base_seeds.json.zlib').read_bytes()) != platform['seed_sha256']:
        parser.error('platform selection does not match the packaged seeds')
    cfg, components = configure(args.id, args.mod, args.version, roots, platform)
    if any(c['abi'] not in (1, 3) for c in components):
        parser.error('supported component ABIs: 1 (stateless) and 3 (feature components, gp50.h)')
    cfg['identity_registry'] = 'sdk/nds/image_identities.json'
    validate_output_identity(cfg)
    # Reject collisions before preparing any firmware-derived inputs.
    from nds_ui.image import check_unique
    check_unique(cfg)
    raw = args.stock.read_bytes()
    seeds = json.loads(zlib.decompress((ROOT/'base_seeds.json.zlib').read_bytes()))
    if sha(raw) != seeds['stock_sha256']:
        parser.error('unsupported stock SHA-256; requires original GP-50 V1.1.0')
    decoded, stock_report = firmware_verify.decode(raw)
    firmware_verify.require(stock_report['all_region_crcs_ok'], 'stock region CRCs')
    regions = {key: data for key, _, data in decoded}
    derived = {name: raw for name in seeds['stock_paths']}
    from sdk.tone_core.stock_capture_filter import lpf_header
    derived['sdk/tone_core/stock_capture_lpf.h'] = lpf_header(regions['g'])
    for seed in seeds['seeds']:
        if 'region' in seed:
            data = regions[seed['region']]
        else:
            changed = {}
            for key, patch in seed['patches'].items():
                data = bytearray(regions[key][:patch['length']])
                data += b'\xff' * max(0, patch['length']-len(data))
                for op in (patch['ops'] if 'ops' in patch else patch['runs']):
                    offset = op[0]
                    if len(op) == 2:
                        part = bytes.fromhex(op[1])
                    else:  # schema 2: [offset, "copy", source_region, source_offset, length] from the user's stock
                        firmware_verify.require(len(op) == 5 and op[1] == 'copy', 'platform seed op')
                        _, _, name, source, count = op
                        firmware_verify.require(name in regions and 0 <= source and 0 < count
                                                and source+count <= len(regions[name]), 'platform seed copy bounds')
                        part = regions[name][source:source+count]
                    firmware_verify.require(0 <= offset <= len(data)-len(part), 'platform seed patch bounds')
                    data[offset:offset+len(part)] = part
                firmware_verify.require(sha(data) == patch['sha256'], 'platform region identity: '+key)
                changed[key] = bytes(data)
            if 'header_ops' in seed:   # container header: the user's stock bytes + the packed differences
                header = bytearray(seed['header_length'])
                for op in seed['header_ops']:
                    if len(op) == 2:
                        part = bytes.fromhex(op[1])
                    else:
                        firmware_verify.require(len(op) == 5 and op[1] == 'copy' and op[2] == 'stock'
                                                and 0 <= op[3] and op[3]+op[4] <= len(raw), 'platform header op')
                        part = raw[op[3]:op[3]+op[4]]
                    firmware_verify.require(0 <= op[0] <= len(header)-len(part), 'platform header bounds')
                    header[op[0]:op[0]+len(part)] = part
                firmware_verify.require(sha(header) == seed['header_sha256'], 'platform header identity')
                header = bytes(header)
            else:
                header = bytes.fromhex(seed['header'])
            data = htfw_pack.build(header,
                                  [(k, d, changed[k]) for k, d in seed['records']], compressed=True)
        firmware_verify.require(sha(data) == seed['sha256'], 'derived platform identity: '+seed['path'])
        derived[seed['path']] = data
    # Catalog extension: rebuilt from the user's stock region e + our bytes (no stock catalog records ship).
    packed_path = ROOT/'sdk/nds/catalog/extension.packed.json'
    if packed_path.exists():
        import catalog_ext_pack
        ext_text, header_text = catalog_ext_pack.unpack(json.loads(packed_path.read_text()), regions['e'])
        derived['sdk/nds/catalog/extension.json'] = ext_text.encode()
        derived['sdk/nds/catalog/catalog_ext_data.h'] = header_text.encode()
    # Validate every destination before writing any: an existing different file is
    # evidence/user data, never an invitation to overwrite it.
    for name, data in derived.items():
        target = ROOT/name
        if target.exists() and target.read_bytes() != data:
            parser.error('derived input collision: '+name)
    for name, data in derived.items():
        target = ROOT/name
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('xb') as handle:
                handle.write(data)
    if not link.exists():
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(tool, target_is_directory=True)
    forbidden = args.forbid_project.resolve() if args.forbid_project else None
    if forbidden:
        def guard(event, values):
            if event == 'open' and isinstance(values[0], (str, bytes)):
                path = Path(os.fsdecode(values[0])).resolve()
                if path.is_relative_to(forbidden) and not path.is_relative_to(ROOT) and not path.is_relative_to(tool):
                    raise RuntimeError('undeclared authoring-tree read: '+str(path))
        sys.addaudithook(guard)
    boot = None
    inputs = ROOT/'work/author_inputs'/cfg['id']
    if args.capture_player or args.exclude_effect:
        if args.capture_player and not args.arm_bin:
            parser.error('--capture-player requires --arm-bin')
        from sdk.build_capture import select_platform
        selected = select_platform(platform, inputs, regions, args.clang,
                                   args.arm_bin.resolve() if args.arm_bin else None,
                                   capture=bool(args.capture_player), excluded=args.exclude_effect)
        platform = dict(platform, **selected)
        cfg.update(selected)
    if args.boot_gif:
        inputs.mkdir(parents=True, exist_ok=True)
        try:
            selected, boot = add_boot_gif(args.boot_gif.resolve(), inputs, platform)
        except ValueError as error:
            parser.error(str(error))
        platform = dict(platform, **selected)
        cfg.update(selected)
    if effects:
        inputs.mkdir(parents=True, exist_ok=True)
        (inputs/'stock_g.bin').write_bytes(regions['g'])
        selected = add_effects(effects, inputs, platform, inputs/'stock_g.bin', ROOT/'work/v110/decoded_e.bin',
                               args.clang, args.arm_bin.resolve())
        platform = dict(platform, **selected)
        cfg.update(selected)
    from sdk.build_stock_gr import bind_container
    cfg['container_parent'] = bind_container(
        ROOT, platform['container_parent'], inputs/'stock_gr',
        args.clang, args.arm_bin.resolve())
    from nds_ui import build
    from nds_ui.features import legacy_ui_c
    # Same window tables; only the boot descriptor/asset differ from the research reference.
    legacy_ui_c.MOD054 = (platform['table_reference']['image'], platform['table_reference']['sha256'])
    firmware_verify.require(legacy_ui_c.pinned_mod054() is not None, 'platform table reference')
    build.C_FLAGS += ['-MMD']
    if args.admission_table:
        from sdk.telemetry.nds import admission_costs as admission_versions
        if args.admission_table not in admission_versions.RUNS:parser.error('unknown admission table '+args.admission_table)
        cfg['admission_table'] = args.admission_table
    if args.admission_estimate_override:
        from sdk.telemetry.nds import sdk_estimates
        estimates = {row['effect'] for row in sdk_estimates.load()}
        if (set(args.admission_estimate_override) - estimates
                or set(args.admission_estimate_override) - {path.name for path in effects}):
            parser.error('admission overrides require a selected effect and matching SDK estimate')
        cfg['admission_estimate_overrides'] = args.admission_estimate_override
    compose_config(cfg)
    deps = set()
    for path in (ROOT/'work/nds_ui'/cfg['id']/'c').rglob('*.d'):
        text = path.read_text().replace(chr(92)+chr(10), ' ')
        for token in text.split(':', 1)[1].split():
            path = Path(token)
            path = path.resolve() if path.is_absolute() else (ROOT/path).resolve()
            if not path.is_relative_to(ROOT) and not path.is_relative_to(tool):
                raise RuntimeError('undeclared compiler input: '+str(path))
            deps.add(str(path))
    if not deps:
        raise RuntimeError('missing compiler dependency evidence')
    for name, digest in manifest['files'].items():
        if sha((ROOT/name).read_bytes()) != digest:
            raise RuntimeError('package input changed during build: '+name)
    latest = json.loads((ROOT/'work'/cfg['id']/'latest.json').read_text())
    result = dict(status='built_not_hardware_qualified', image_id=cfg['id'],
                  image_sha256=latest['image_sha256'], folder=latest['folder'],
                  stock_sha256=sha(raw), source_files=len(manifest['files']), platform=platform['name'],
                  compiler_dependencies=sorted(deps),
                  components=[c['id'] for c in components],
                  effects=[str(path) for path in effects], boot_gif=boot,
                  capture_player=args.capture_player, excluded_effects=args.exclude_effect,
                  lzo_library_sha256=sha(library.read_bytes()),
                  limits=manifest['limits'])
    (ROOT/'work'/cfg['id']/'sdk_build_result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'compiler_dependencies'}, indent=2))


if __name__ == '__main__':
    main()
