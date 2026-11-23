"""Build and bind the paired resident/overlay capture player in an isolated SDK.

This is a platform extension: its resident hooks and fixed reservations are pinned
by release_binding.json. It is not an effect with permission to edit arbitrary RAM.
No previous capture ELF, record, generated header or project script is consumed.
"""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEMS = ('capture_status', 'capture_record', 'arm_producer', 'arm_overlay',
         'arm_private', 'capture_link', 'arm_runtime', 'arm_lifecycle')
sha = lambda data: hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def run(command):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True)
    require(result.returncode == 0, result.stdout + result.stderr)
    return result.stdout


def symbols(elf, arm):
    return {s[2]: int(s[0], 16) for line in run([arm/'arm-none-eabi-nm', elf]).splitlines()
            if len(s := line.split()) == 3}


def build(out, clang, arm, stock_g):
    from sdk.build_effect import CFLAGS, SLOTS, build_copro
    from protocol.overlay_image import Overlay, build_overlay, parse_overlay
    out.mkdir(parents=True, exist_ok=True)
    source = ROOT/'sdk/capture_status'
    binding = json.loads((source/'release_binding.json').read_text())
    objects = []
    for name in STEMS:
        obj = out/(name+'.o')
        run([clang, '--target=arm-none-eabi', '-mcpu=cortex-m4', '-mthumb',
             '-mfloat-abi=soft', '-Oz', '-ffreestanding', '-fno-builtin',
             '-ffunction-sections', '-fdata-sections', '-fno-unwind-tables',
             '-fno-asynchronous-unwind-tables', '-fstack-usage', '-Wall', '-Wextra',
             '-Werror', '-MMD', '-MF', out/(name+'.d'), '-c', source/(name+'.c'), '-o', obj])
        objects.append(obj)
    obj = out/'hooks.o'
    run([arm/'arm-none-eabi-as', source/'arm_hooks.S', '-o', obj])
    objects.append(obj)
    elf = out/'capture.elf'
    run([arm/'arm-none-eabi-ld', '--gc-sections', '--no-undefined', '-T',
         source/'arm_layout.ld', '-Map', out/'capture.map', '-o', elf, *objects])
    syms = symbols(elf, arm)
    sections = []
    for reservation in binding['reservations']:
        name = reservation['section']
        path = out/(name+'.bin')
        run([arm/'arm-none-eabi-objcopy', '-O', 'binary', '--only-section=.'+name, elf, path])
        data = path.read_bytes()
        require(len(data) <= reservation['end']-reservation['start'], 'capture reservation overflow')
        sections.append(dict(reservation, size=len(data), output_sha256=sha(data)))
    (out/'capture.lst').write_text(run([arm/'arm-none-eabi-objdump', '-d', elf]))
    # Assemble the actual installed hook bytes against this build's resident symbols.
    hooks = []
    for i, hook in enumerate(binding['hooks']):
        assembly = hook['assembly']
        if '{early_word}' in assembly:
            assembly = assembly.replace('{early_word}', f"{syms['gp50_capture_early']|1:#x}")
        for name, address in syms.items():
            assembly = assembly.replace('{'+name+'}', f'{address:#x}')
        asm = out/f'hook_{i}.S'
        asm.write_text('.syntax unified\n.thumb\n.cpu cortex-m4\n.text\n.global start\n.thumb_func\nstart:\n'+assembly+'\n')
        obj = asm.with_suffix('.o'); linked = asm.with_suffix('.elf'); binary = asm.with_suffix('.bin')
        run([arm/'arm-none-eabi-as', asm, '-o', obj])
        run([arm/'arm-none-eabi-ld', '--just-symbols='+str(elf), '-Ttext', hex(hook['address']), '-e', 'start', obj, '-o', linked])
        run([arm/'arm-none-eabi-objcopy', '-O', 'binary', linked, binary])
        data = binary.read_bytes()
        require(len(data) == len(bytes.fromhex(hook['before'])), 'hook width changed')
        hooks.append(dict(hook, after=data.hex()))
    # SDK assembly produces both exclusive kernels and the matching ARM cell header.
    meta_dir = ROOT/'sdk/effects/ns_capture_v7'
    secondary, copro, _, _ = build_copro(meta_dir, json.loads((meta_dir/'effect.json').read_text()), out, stock_g)
    obj = out/'effect.o'; overlay_elf = out/'effect.elf'
    run([clang, *CFLAGS, '-Oz', '-fstack-usage', '-MMD', '-MF', out/'effect.d',
         '-I', ROOT/'sdk/include', '-I', out, '-c', ROOT/'sdk/effects/ns_capture_v8/ns_capture.c', '-o', obj])
    base, size = SLOTS[9]
    gate = syms['gp50_capture_overlay_call'] | 1
    run([arm/'arm-none-eabi-ld', f'--defsym=SLOT_BASE={base:#x}', f'--defsym=SLOT_SIZE={size:#x}',
         f'--defsym=gp50_capture_overlay_call={gate:#x}', '-T', ROOT/'sdk/overlay.ld',
         '--gc-sections', '--no-undefined', '-Map', out/'effect.map', '-o', overlay_elf, obj])
    osyms = symbols(overlay_elf, arm)
    require(osyms['__bss_end'] <= base+size, 'capture overlay overflow')
    payload = out/'payload.bin'
    run([arm/'arm-none-eabi-objcopy', '-O', 'binary', '--only-section=.payload', overlay_elf, payload])
    (out/'effect.lst').write_text(run([arm/'arm-none-eabi-objdump', '-d', overlay_elf]))
    # Same SDK standard 16-byte Thumb trampoline prefix as build_effect.
    from sdk.build_effect import stock_overlay_prefix
    prefix = stock_overlay_prefix(stock_g)
    record = Overlay(osyms['ns_capture_init']|1, osyms['ns_capture_process']|1,
                     prefix, payload.read_bytes(), secondary)
    encoded = build_overlay(record)
    require(parse_overlay(encoded) == record, 'capture record round trip')
    (out/'record.bin').write_bytes(encoded)
    dependencies = set()
    for dep in out.glob('*.d'):
        for token in dep.read_text().replace(chr(92)+chr(10), ' ').split(':', 1)[1].split():
            path = Path(token).resolve()
            require(path.is_relative_to(ROOT), 'undeclared capture compiler input: '+str(path))
            dependencies.add(str(path.relative_to(ROOT)))
    report = dict(compiler_dependencies=sorted(dependencies), status='built_from_sdk_source', symbols=syms, overlay_symbols=osyms,
                  resident_gate=hex(gate), base=sections[0]['start'], end=sections[0]['start']+sections[0]['size'],
                  aux_base=sections[1]['start'], aux_end=sections[1]['start']+sections[1]['size'],
                  reservations=sections, hooks=hooks, copro=copro, overlay_spare_bytes=base+size-osyms['__bss_end'],
                  record_sha256=sha(encoded), elf_sha256=sha(elf.read_bytes()),
                  overlay_elf_sha256=sha(overlay_elf.read_bytes()), parent_c_sha256=binding['parent_c_sha256'])
    (out/'build.json').write_text(json.dumps(report, indent=2)+'\n')
    return report


def bind(regions, report, out):
    """Replace only the pinned resident reservations, hooks and N->S record."""
    from protocol.overlay_image import parse_container, build_container, parse_overlay
    require(sha(regions['c']) == report['parent_c_sha256'], 'unsupported capture resident parent')
    c = bytearray(regions['c']); owned = set()
    for row in report['reservations']:
        lo, hi = row['start']-0x4000, row['end']-0x4000
        require(sha(c[lo:hi]) == row['sha256'], 'capture reservation provenance')
        data = (out/(row['section']+'.bin')).read_bytes()
        require(sha(data) == row['output_sha256'], 'capture section changed')
        c[lo:hi] = data+b'\xff'*(hi-lo-len(data)); owned.update(range(lo, hi))
    for row in report['hooks']:
        lo = row['address']-0x4000; before = bytes.fromhex(row['before']); after = bytes.fromhex(row['after'])
        require(c[lo:lo+len(before)] == before, 'capture hook provenance: '+row['name'])
        c[lo:lo+len(after)] = after; owned.update(range(lo, lo+len(after)))
    require(all(i in owned for i, (a, b) in enumerate(zip(regions['c'], c)) if a != b), 'capture changed unowned bytes')
    g = parse_container(regions['g']); encoded = (out/'record.bin').read_bytes()
    require(sha(encoded) == report['record_sha256'], 'capture record changed')
    require(parse_overlay(g.groups[9][0]).prefix == parse_overlay(encoded).prefix, 'capture prefix provenance')
    g.groups[9][0] = encoded
    return dict(regions, c=bytes(c), g=build_container(g))


def select_platform(platform, inputs, stock_regions, clang, arm, capture=False, excluded=()):
    """SDK-owned parent selection and catalog exclusion; never edits package inputs."""
    import firmware_verify as verify
    import htfw_pack
    import build_catalog_ext as catalog
    from protocol.overlay_image import parse_container, build_container, parse_descriptor
    inputs.mkdir(parents=True, exist_ok=True)
    ext = json.loads((ROOT/platform['catalog_ext']['extension']).read_text())
    logical = catalog.resolve(ext, stock_regions['e'])
    ids = set(excluded)
    custom = {int(row['public_id'], 16) for row in ext['entries']}
    require(ids <= custom, 'can exclude only SDK extension effects')
    removals = {group: [i for i, d in enumerate(rows) if parse_descriptor(d).public_id in ids]
                for group, rows in enumerate(logical)}
    ext['entries'] = [row for row in ext['entries'] if int(row['public_id'], 16) not in ids]
    catalog.check(ext, stock_regions['e'])
    header, text = catalog.header(ext)
    (inputs/'extension_selected.json').write_text(text)
    (inputs/'catalog_selected.h').write_text(header)
    relative = lambda path: str(path.relative_to(ROOT))
    selected = dict(catalog_ext=dict(extension=relative(inputs/'extension_selected.json'),
                    header=relative(inputs/'catalog_selected.h'), sha256=sha(text.encode())))
    out = inputs/'capture'
    report = None
    if capture:
        stock_g = inputs/'capture_stock_g.bin'; stock_g.write_bytes(stock_regions['g'])
        report = build(out, clang, arm, stock_g)
    seen = {}; capture_parents = 0; parents = []
    for key in ('parent', 'container_parent', 'table_reference'):
        source = platform[key]['image']
        if source in seen:
            selected[key] = dict(platform[key], **seen[source])
            continue
        raw = (ROOT/source).read_bytes()
        require(sha(raw) == platform[key]['sha256'], 'SDK parent identity')
        records, receipt = verify.decode(raw)
        require(receipt['all_region_crcs_ok'], 'SDK parent CRCs')
        old = {k: data for k, _, data in records}; new = dict(old)
        fused = bool(report and sha(old['c']) == report['parent_c_sha256'])
        if fused:
            new = bind(new, report, out); capture_parents += 1
        g = parse_container(new['g'])
        require([len(rows) for rows in g.groups[:10]] == [len(rows) for rows in logical], 'SDK catalog geometry')
        for group, indices in removals.items():
            for i in reversed(indices):
                del g.groups[group][i]
        new['g'] = build_container(g)
        header_bytes, _ = htfw_pack.parse_template(raw)
        encoded = htfw_pack.build(header_bytes, [(k, dest, new[k]) for k, dest, _ in records], compressed=True)
        require({k: data for k, _, data in verify.decode(encoded)[0]} == new, 'SDK selected parent round trip')
        target = inputs/(key+'_selected.bin'); target.write_bytes(encoded)
        seen[source] = dict(image=relative(target), sha256=sha(encoded))
        selected[key] = dict(platform[key], **seen[source])
        parents.append(dict(source=source, input_sha256=sha(raw), output_sha256=sha(encoded), fused_capture=fused,
                            changed_regions=[k for k in old if old[k] != new[k]]))
    if capture:
        require(capture_parents == 1, 'SDK platform needs exactly one supported capture resident parent')
        require(next(row for row in parents if row['source'] == platform['container_parent']['image'])['fused_capture'],
                'capture must be bound to the actual container parent')
    (inputs/'platform_selection.json').write_text(json.dumps(dict(status='pass', parents=parents,
        excluded_effects=sorted(ids), capture_build='capture/build.json' if capture else None), indent=2)+'\n')
    return selected
