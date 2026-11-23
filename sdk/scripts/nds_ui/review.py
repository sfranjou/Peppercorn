"""Independent declared-diff review and routing check (tier b). Never flashes.

Works from the built container, the pinned parent and the generator outputs only (not from
image.py): every changed byte of b below the segment must lie in a declared hook site, the
paired BSS/heap bound words, or the version text; the segment must equal code.bin; c/e/f/g
identical; CRCs valid. Hook words are decoded with a separate bit-field decoder and must land
on generator labels. dispatch/read_route are interpreted over every command/selector."""
import json
from . import build
from .stock_api import API, check as api_check, check_c_link

ROOT = build.ROOT
VERSION_ROOM = 8


def _s(v, bits):
    return v - (1 << bits) if v >> (bits - 1) else v


def decode32(pc, w):
    """Minimal independent decoder for the opcodes the hook/routing checks need."""
    op = w >> 25; rt = w >> 20 & 31; ra = w >> 15 & 31
    if op == 0x24: return ('jal' if w >> 24 & 1 else 'j', pc + 2 * _s(w & 0xffffff, 24))
    if op == 0x22: return ('movi', rt, _s(w & 0xfffff, 20))
    if op == 0x23: return ('sethi', rt, (w & 0xfffff) << 12)
    if op == 0x2c: return ('ori', rt, ra, w & 0x7fff)
    if op == 0x26: return ('bne' if w >> 14 & 1 else 'beq', rt, ra, pc + 2 * _s(w & 0x3fff, 14))
    return ('?', w)


def interpret(code, base, entry, regs, stops=(), limit=40):
    """Run straight-line movi/beq/bne/j code inside the segment; return (exit pc, regs)."""
    pc = entry; regs = dict(regs)
    for _ in range(limit):
        if pc in stops or not base <= pc < base + len(code): return pc, regs
        w = int.from_bytes(code[pc - base:pc - base + 4], 'big'); ins = decode32(pc, w)
        if ins[0] == 'movi': regs[ins[1]] = ins[2] & 0xffffffff; pc += 4
        elif ins[0] in ('beq', 'bne'):
            eq = regs.get(ins[1]) == regs.get(ins[2]); pc = ins[3] if eq == (ins[0] == 'beq') else pc + 4
        elif ins[0] == 'j': pc = ins[1]
        else: raise ValueError(f'routing code uses unexpected instruction at {pc:#x}: {w:08x}')
    raise ValueError('routing step bound')


def routing(code, base, labels):
    """Same contract as the Ghidra routing study: 65536 commands, 5 lengths x 256 selectors."""
    n = 0; legacy = labels.get('diag_dispatch_asm', API.mod030_dispatch)   # MOD056+ (diagnostics_c): the dispatch stub is ours
    for cmd in range(65536):
        stop, _ = interpret(code, base, labels['dispatch'], {5: cmd}, stops={labels['receive'], legacy})
        want = labels['receive'] if cmd == 0x60f0 else legacy
        if stop != want: raise ValueError(f'dispatch {cmd:#x} -> {stop:#x}')
        n += 1
    if 'diag_dispatch_asm' in labels:   # and from there: 0x6002 -> own receive stub, everything else -> stock 0x46aba with a0 = 0x7004
        for cmd in range(65536):
            stop, r = interpret(code, base, labels['diag_dispatch_asm'], {5: cmd}, stops={labels['diag_receive_asm']})
            want = labels['diag_receive_asm'] if cmd == 0x6002 else 0x46aba
            if stop != want or (cmd != 0x6002 and r[0] != 0x7004) or r[5] != cmd: raise ValueError(f'diagnostics dispatch {cmd:#x} -> {stop:#x}')
            n += 1
    for ln in ((0, 1, 2, 3, 65535) if 'read_route' in labels else ()):   # MOD056+: the `12 51` route is C (host_layer_c, model-tested)
        for sel in range(256):
            stop, r = interpret(code, base, labels['read_route'], {0: sel, 7: ln, 15: 0x12345678})
            want = (API.read_route_table_index if ln == 2 else API.read_route_invalid) if sel == 0x51 else API.read_route_4f if sel == 0x4f else API.read_route_original
            if stop != want or r[15] != 0x12345678: raise ValueError(f'read route {sel:#x}/{ln}')
            if r[0] != (12 if sel == 0x51 and ln == 2 else sel): raise ValueError('read route a0')
            n += 1
    return n


def review(cfg, image_path=None):
    from firmware_verify import decode, require, sha
    from nds_hook_encoding import gp_add
    gen = ROOT / 'work/nds_ui' / cfg['id']
    labels = json.loads((gen / 'labels.json').read_text()); code = (gen / 'code.bin').read_bytes()
    patches = json.loads((gen / 'patches.json').read_text()); lay = json.loads((gen / 'layout.json').read_text())
    img = (image_path or ROOT / cfg['output'] / cfg['name']).read_bytes(); par = (ROOT / cfg['parent']['image']).read_bytes()
    require(sha(par) == cfg['parent']['sha256'], 'parent identity')
    act, ck = decode(img); bef, _ = decode(par); a = {r: v for r, _, v in act}; p = {r: v for r, _, v in bef}
    for r in 'cfg': require(a[r] == p[r], r + ' identical to parent')
    if cfg.get('region_e'):   # phase C: independent re-check of the whole-region rule (image.region_e)
        stock_e = (ROOT / 'work/v110/decoded_e.bin').read_bytes()
        require(cfg['region_e'] == 'stock_v110' and sha(stock_e) == '4f48cf8c1c7e691c8d1df1900491ffd3509eef1b767258ea49fa6f3e231d7d48', 'stock e identity')
        ext = json.loads((ROOT / cfg['catalog_ext']['extension']).read_text()); spans = []
        for x in ext.get('e_assets', []):
            o = int(x['offset'], 16); blob = (ROOT / x['source']).read_bytes()
            require(sha(blob) == x['sha256'] and a['e'][o:o + len(blob)] == blob, 'asset ' + x['name']); spans.append((o, o + len(blob)))
        external = json.loads((gen / 'external_data.json').read_text()) if cfg.get('catalog_descriptor_storage') else []
        if cfg.get('catalog_descriptor_storage'):
            require(cfg['catalog_descriptor_storage'] == 'region_e_1a4000' and len(external) == 1, 'exact external catalog mode/count')
        for x in external:
            o = int(x['offset'], 16); address = int(x['address'], 16); blob = bytes.fromhex(x['hex'])
            require(x['region'] == 'e' and address == 0x1a4000 and o == 0x14000 and 0 < len(blob) <= 0x2000, 'external catalog bounds')
            require(stock_e[o:o+len(blob)] == b'\xff' * len(blob), 'external catalog was erased')
            require(all(o+len(blob) <= lo or hi <= o for lo, hi in spans), 'external catalog excludes assets')
            require(sha(blob) == x['sha256'] and a['e'][o:o+len(blob)] == blob, 'external catalog bytes')
            spans.append((o,o+len(blob)))
        inside = lambda i: any(s <= i < e for s, e in spans)
        require(len(a['e']) == len(stock_e) and all(a['e'][i] == stock_e[i] for i in range(len(stock_e)) if not inside(i)), 'e = stock except declared assets')
        require(all(p['e'][i] == a['e'][i] for i in range(len(stock_e)) if not 0x10000 <= i < 0x20000), 'parent e differs from this e only in the catalog window')
        import importlib.util
        from protocol.overlay_image import parse_container
        spec = importlib.util.spec_from_file_location('build_catalog_ext', ROOT / 'scripts/build_catalog_ext.py'); X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)
        logical = X.resolve(ext, stock_e); g = parse_container(a['g'])
        require([len(g.groups[k]) for k in range(10)] == [len(logical[k]) for k in range(10)], 'g record counts equal the logical catalog counts (the NDS sends ordinals to the ARM)')
    else: require(a['e'] == p['e'], 'e identical to parent')
    seg = lay['base'] - 0x10000; require(a['b'][seg:] == code, 'segment equals generated code.bin')
    require(lay['code_sha256'] == sha(code), 'code.bin matches layout')
    sites = {}; hole_ranges = []
    if (gen / 'holes.json').exists():   # code room step 2: compiled C in dead stock bodies (generator output, checked byte for byte)
        for h in json.loads((gen / 'holes.json').read_text())['blobs']:
            o = int(h['address'], 16) - 0x10000; raw = bytes.fromhex(h['hex'])
            require(a['b'][o:o + len(raw)] == raw, 'hole bytes ' + h['address']); require(o + len(raw) <= int(h['end'], 16) - 0x10000, 'hole overflow ' + h['address'])
            for i in range(o, o + len(raw)): sites[i] = 'hole'
            hole_ranges.append((o + 0x10000, o + 0x10000 + len(raw)))
        stock_b0 = (ROOT / 'work/v110/decoded_b.bin').read_bytes()
        for r in json.loads((gen / 'holes.json').read_text()).get('restored', []):
            o = int(r, 16) - 0x10000; require(a['b'][o:o + 4] == stock_b0[o:o + 4], 'restored stock bytes ' + r)
            for i in range(o, o + 4): sites[i] = 'restore'
    for row in patches:
        o = int(row['address'], 16) - 0x10000
        for i in range(o, o + len(row['new']) // 2): sites[i] = 'hook'
        require(a['b'][o:o + len(row['new']) // 2].hex() == row['new'], 'hook bytes ' + row['address'])
        targets = set(labels.values())
        if row['assembly'].startswith('.word'):   # data word (MOD056 diagnostics_c table words): little-endian address of one of our symbols
            v = int.from_bytes(bytes.fromhex(row['new']), 'little'); require(v in targets and (lay['base'] <= v < lay['end'] or any(s <= v < e for s, e in hole_ranges)), f'data word {row["address"]} target not a generator label'); continue
        ins = decode32(o + 0x10000, int(row['new'], 16))
        if ins[0] in ('j', 'jal'): require(ins[1] in targets and (lay['base'] <= ins[1] < lay['end'] or any(s <= ins[1] < e for s, e in hole_ranges)), f'hook {row["address"]} target not a generator label')
    bound = (lay['state'] + lay['state_bytes'] + 15) & ~15
    for site, reg in ((API.hook_bss_end, 2), (API.hook_heap_start, 1)):
        o = site - 0x10000; require(a['b'][o:o + 4] == gp_add(reg, bound - API.gp), f'bound {bound:#x} at {site:#x}')
        for i in range(o, o + 4): sites[i] = 'bound'
    vo = API.version_string - 0x10000
    for i in range(vo, vo + VERSION_ROOM): sites[i] = 'version'
    require(a['b'][vo:vo + VERSION_ROOM] == cfg['version'].encode() + bytes(VERSION_ROOM - len(cfg['version'])), 'version text')
    diff = [i for i in range(seg) if a['b'][i] != p['b'][i]]
    stray = [i for i in diff if i not in sites]
    require(not stray, 'undeclared b changes at ' + ', '.join(hex(i + 0x10000) for i in stray[:8]))
    stock_b = (ROOT / 'work/v110/decoded_b.bin').read_bytes()
    from .features import legacy_ui_c
    # Parent already runs legacy_ui_c (MOD055+): the MOD026/029 assembly helpers are gone from it; with legacy_ui_c this
    # config links those names to the C (LINK_ALIASES) or switches the call sites, so they are not checked in the parent.
    skip = [legacy_ui_c.OLD_SEGMENT] if legacy_ui_c.enabled(cfg) and legacy_ui_c.pinned_mod054() is not None and p['b'][0x16e016 - 0x10000:0x16e018 - 0x10000] != b'\xfa\x26' else []
    from .features import diagnostics_c
    # Parent already runs diagnostics_c (MOD056+): the old block 0x16c6c0.. (mod030_dispatch) is our C/stub segment.
    if diagnostics_c.enabled(cfg) and p['b'][0x16c6e6 - 0x10000:0x16c6ee - 0x10000].hex() != '440060024c028083': skip.append(diagnostics_c.BLOCK)
    bad = api_check(stock_b, p['b'], skip)
    bad += check_c_link(); require(not bad, 'stock-API map: ' + '; '.join(bad))
    n = routing(code, lay['base'], labels)
    kinds = {}
    for i in diff: kinds[sites[i]] = kinds.get(sites[i], 0) + 1
    return dict(status='pass', image_sha256=sha(img), parent_sha256=sha(par), changed_b_bytes_below_segment=len(diff), by_kind=kinds,
                segment=dict(base=hex(lay['base']), end=hex(lay['end']), sha256=sha(code)), cefg=('c/f/g identical to parent; e = stock V1.1.0 + declared assets (own catalog extension)' if cfg.get('region_e') else 'identical to parent'),
                crcs=ck['all_region_crcs_ok'], routing_cases=n, stock_api='consistent with stock, parent and sdk/nds/stock_api.ld')
