"""Generic NDS UI image builder: pinned parent + feature set + version -> container.

Only region b changes: the feature hooks derived by the generator, the paired BSS/heap bound
(when the state grows), the version text, and the NDS segment from the segment base to the
end of b. c/e/f/g are copied from the parent and checked identical. Never installs.
"""
import json, re
from pathlib import Path
from . import build
from .stock_api import API

ROOT = build.ROOT
SEG_OFF = lambda cfg: int(cfg['segment']['base'], 16) - 0x10000
STOCK_SHA = '0e14f2b0293be233db3da8dc3573bf9135dddc575992055570842433dadae836'


def _imports():
    from firmware_verify import decode, require, sha
    from nds_hook_encoding import gp_add
    import htfw_pack, ui_theme
    return decode, require, sha, gp_add, htfw_pack, ui_theme


STOCK_E_SHA = '4f48cf8c1c7e691c8d1df1900491ffd3509eef1b767258ea49fa6f3e231d7d48'


def region_e(cfg, parent_e):
    """Region e for this image: the parent's, or (cfg region_e = stock_v110, item 9 phase C) stock V1.1.0 plus the
    declared assets of sdk/nds/catalog/extension.json (e.g. the MOD034 boot card GIF). Whole-region rule: the parent e
    must equal either that same image e (parent already own-catalog) or the logical region e of the extension
    (logical catalog + assets, i.e. an edited-e parent such as MOD050); any other byte is refused, so nothing in e
    is lost silently (MOD051's first build dropped the boot GIF, 2026-10-22)."""
    _, require, sha, *_ = _imports()
    mode = cfg.get('region_e')
    if not mode: return parent_e
    require(mode == 'stock_v110', 'unknown region_e mode ' + str(mode))
    import importlib.util
    spec = importlib.util.spec_from_file_location('build_catalog_ext', ROOT / 'scripts/build_catalog_ext.py'); X = importlib.util.module_from_spec(spec); spec.loader.exec_module(X)
    text = (ROOT / cfg['catalog_ext']['extension']).read_text(); require(sha(text.encode()) == cfg['catalog_ext']['sha256'], 'extension.json identity')
    ext = json.loads(text); stock = X.stock_e(); X.check(ext, stock)
    new_e = X.image_e(ext, stock)
    require(parent_e == new_e or parent_e == X.logical(ext, stock), 'parent e is neither stock + assets nor the logical region e of the extension')
    return new_e


def bound_for(cfg):
    end = int(cfg['segment']['state'], 16) + cfg['segment']['state_bytes']
    if 'external_components_c' in cfg.get('features', ()):
        from .features.external_components_c import components
        from .component_ram import propose
        ram = propose(cfg, components(cfg), ROOT)
        if ram:
            end = ram['heap_start']
    return (end + 15) & ~15


def check_unique(cfg):
    """MOD number and version letter must not be reused by another image config or by an
    existing built image with a different hash."""
    _, require, *_ = _imports()
    for p in (build.HERE / 'images').glob('*.json'):
        o = json.loads(p.read_text())
        if o['id'] == cfg['id']: continue
        require(o['mod'] != cfg['mod'], f'MOD number {cfg["mod"]} also used by {p.name}')
        require(o['version'] != cfg['version'], f'version {cfg["version"]} also used by {p.name}')
    registry = cfg.get('identity_registry')
    if registry is not None:
        data = json.loads((ROOT / registry).read_text())
        require(isinstance(data, dict) and data.get('schema') == 1,
                'unsupported image identity registry')
        reservations = data.get('reservations')
        require(isinstance(reservations, list), 'image identity reservations must be a list')
        seen = set()
        for entry in reservations:
            require(isinstance(entry, dict) and isinstance(entry.get('output'), str)
                    and isinstance(entry.get('version'), str), 'invalid image identity reservation')
            output = entry['output']
            require(output not in seen, 'duplicate image identity output: ' + output)
            seen.add(output)
            if ROOT / output in (ROOT / cfg['output'], ROOT / cfg.get('reproduces', cfg['output'])):
                continue
            require(entry['version'] != cfg['version'],
                    f'version {cfg["version"]} already used by {Path(output).name}')
    else:
        # Research builds retain their live history guard. Curated packages can
        # explicitly supply the frozen reservations without copying that history.
        for m in ROOT.glob('work/custom_images/*/manifest.json'):
            if m.parent in (ROOT / cfg['output'], ROOT / cfg.get('reproduces', cfg['output'])): continue
            try: v = json.loads(m.read_text()).get('version')
            except ValueError: continue
            require(v != cfg['version'], f'version {cfg["version"]} already used by {m.parent.name}')



def classify_preimage(site, old, stock_b, parent_seg, parent_end, data=False):
    """Why the parent bytes at a hook site are acceptable to overwrite."""
    off = site - 0x10000
    if stock_b[off:off + len(old)] == old: return 'stock'
    w = int.from_bytes(old, 'big')
    if len(old) == 4 and data and parent_seg <= int.from_bytes(old, 'little') < parent_end:   # .word patch (MOD056 diagnostics_c)
        return f'rebind (data word -> {int.from_bytes(old, "little"):#x} in replaced segment)'
    if len(old) == 4 and not data and w >> 25 == 0x24:   # j/jal into the parent's NDS segment = rebinding the previous MOD's hook
        d = w & 0xffffff; d = d - (1 << 24) if d >> 23 else d; t = site + 2 * d
        if parent_seg <= t < parent_end: return f'rebind (parent jumps to {t:#x} in replaced segment)'
    return None


def classify_declared_preimage(cfg, site, old, stock_b):
    """Exact reviewed parent entry overrides; all other bytes keep normal guards."""
    entry = cfg.get('hook_preimages', {}).get(hex(site))
    if not entry: return None
    off = site - 0x10000
    if old.hex() != entry['parent'] or stock_b[off:off + len(old)].hex() != entry['stock']:
        return None
    return 'exact declared parent entry: ' + entry['reason']


def classify_pair(hi_site, parent_b, stock_b, parent_seg, parent_end):
    """sethi/ori address pair (hi at hi_site, lo at +4): stock, or pointing into the replaced segment."""
    off = hi_site - 0x10000; hi, lo = (int.from_bytes(parent_b[off + k:off + k + 4], 'big') for k in (0, 4))
    if parent_b[off:off + 8] == stock_b[off:off + 8]: return 'stock'
    if hi >> 25 == 0x23 and lo >> 25 == 0x2c:
        t = (hi & 0xfffff) << 12 | lo & 0x7fff
        if parent_seg <= t < parent_end: return f'rebind (address pair -> {t:#x} in replaced segment)'
    return None


def build_image(cfg, write=True, verify_only=False, *, component_bundle=False):
    # The paired component builder consumes this in-memory result and then
    # replaces C/G. It cannot write or verify a standalone NDS-only container.
    if component_bundle and (write or verify_only or not cfg.get('component_only')):
        raise ValueError('component bundle requires in-memory component-only draft')
    if cfg.get("component_only") and not component_bundle:
        raise ValueError("component-only draft: paired firmware image review is incomplete")
    decode, require, sha, gp_add, htfw_pack, ui_theme = _imports()
    check_unique(cfg)
    parent = (ROOT / cfg['parent']['image']).read_bytes(); require(sha(parent) == cfg['parent']['sha256'], 'parent identity')
    regions, _ = decode(parent); old = {r: v for r, _, v in regions}
    stock_b = (ROOT / 'work/v110/decoded_b.bin').read_bytes()
    g = build.generate(cfg, old['b']); seg = SEG_OFF(cfg)
    require(len(old['b']) > seg, 'parent b has no NDS segment at the configured base')
    parent_end = len(old['b']) + 0x10000
    b = bytearray(old['b']); edits = []; touched = set()

    def patch(at, raw, why, kind):
        off = at - 0x10000; before = bytes(b[off:off + len(raw)])
        require(off + len(raw) <= seg, f'patch {at:#x} inside the replaced segment')
        require(not touched & set(range(off, off + len(raw))), f'overlapping patch {at:#x}')
        b[off:off + len(raw)] = raw; touched.update(range(off, off + len(raw)))
        edits.append(dict(address=hex(at), before=before.hex(), after=raw.hex(), reason=why, kind=kind))

    for p in g['patches']:
        at = int(p['address'], 16); oldb = bytes.fromhex(p['old'])
        base = int(cfg['segment']['base'], 16)
        if p['assembly'].startswith(('sethi', 'ori')):
            why = classify_pair(at if p['assembly'].startswith('sethi') else at - 4, old['b'], stock_b, base, parent_end)
        else:
            why = classify_preimage(at, oldb, stock_b, base, parent_end, data=p['assembly'].startswith('.word'))
        if why is None: why = classify_declared_preimage(cfg, at, oldb, stock_b)
        require(why is not None, f'hook {at:#x}: parent bytes {p["old"]} are neither stock nor a previous NDS hook')
        hooks = {v for k, e in API.entries().items() if e['kind'] in ('hook_site', 'parent_resident') for v in ([int(x, 16) for x in e['address']] if isinstance(e['address'], list) else [int(e['address'], 16)])}
        require(at in hooks, f'hook {at:#x} not declared in the stock-API map')
        patch(at, bytes.fromhex(p['new']), f'{p["feature"]}: {p["assembly"]} ({p["reason"]}; preimage {why})', 'hook')
    bound = bound_for(cfg)
    for site, reg in ((API.hook_bss_end, 2), (API.hook_heap_start, 1)):
        want = gp_add(reg, bound - API.gp); off = site - 0x10000
        if bytes(b[off:off + 4]) != want: patch(site, want, f'BSS/heap bound -> {bound:#x} (state {cfg["segment"]["state_bytes"]} B)', 'bound')
    # Code room step 2 (cfg code_holes): compiled C placed into dead stock bodies below the segment. The parent bytes there
    # must be stock, except the parent's hooks inside replaced bodies that a feature declares superseded.
    superseded = {a for f in g['enabled'] for a in build.superseded_of(f, cfg)}
    for h in g['holes']:
        lo = h['address']; raw = h['bytes']; o = lo - 0x10000
        diff = [i + 0x10000 for i in range(o, o + len(raw)) if old['b'][i] != stock_b[i]]
        require(all(any(s <= a < s + 4 for s in superseded) for a in diff), f'hole {lo:#x}: parent bytes differ from stock outside superseded hooks {[hex(a) for a in diff[:4]]}')
        require(lo + len(raw) <= h['end'], f'hole {lo:#x} overflow')
        patch(lo, raw, f'code hole behind redirected entry {h["entry"]:#x}: ' + ', '.join(s['section'][6:] or s['section'] for s in h['sections']), 'hole')
    for a in g.get('restores', []):
        o = a - 0x10000; require(old['b'][o:o + 4] != stock_b[o:o + 4] and a in superseded, f'restore {a:#x}: not a superseded parent hook')
        patch(a, stock_b[o:o + 4], 'stock bytes back at a superseded parent hook inside a replaced body (dead code)', 'restore')
    # cfg stock_theme: the parent's MOD005 colour loads back to the user's stock bytes (ui_theme's 59 sites, found in stock).
    if cfg.get('stock_theme'):
        for role, rows in ui_theme.find_sites(stock_b).items():
            for at, raw in rows:
                o = at - 0x10000
                if bytes(b[o:o + 4]) == raw: continue
                require(old['b'][o:o + 4] == bytes(b[o:o + 4]) and old['b'][o:o + 2] == b'\x44\x10' and not set(range(o, o + 4)) & touched,
                        f'theme site {at:#x} is not the untouched parent colour load')
                patch(at, raw, f'stock {role} colour back', 'restore')
    # Theme locations can now contain checked code-hole payloads. Validate the
    # parent's theme and derive only its version-text delta; never retheme code.
    v, _ = ui_theme.apply(old['b'], version_text=cfg['version'])
    version_range = range(ui_theme.VERSION_ADDRESS - 0x10000,
                          ui_theme.VERSION_ADDRESS - 0x10000 + ui_theme.VERSION_ROOM)
    changes = [i for i, (x, y) in enumerate(zip(old['b'], v)) if x != y]
    require(all(i in version_range for i in changes), 'version update changed non-version parent bytes')
    for i in changes:
        patch(i + 0x10000, v[i:i + 1], 'Version ' + cfg['version'], 'version')
    b = bytes(b[:seg]) + g['code']
    require({i for i, (x, y) in enumerate(zip(old['b'][:seg], b[:seg])) if x != y} <= touched, 'unexpected b edits')
    new_e = region_e(cfg, old['e'])
    from .catalog_storage import apply as apply_catalog_storage
    from .expanded_e import extend
    new_e = extend(cfg, new_e)
    new_e = apply_catalog_storage(new_e, g.get('external', []), cfg)
    final = [(r, dd, b if r == 'b' else new_e if r == 'e' else vv) for r, dd, vv in regions]
    head, records = htfw_pack.parse_template(parent); require(records == [(r, dd) for r, dd, _ in final], 'template')
    out = ROOT / cfg['output']; img_path = out / cfg['name']
    image = img_path.read_bytes() if verify_only else htfw_pack.build(head, final, compressed=True)
    actual, checks = decode(image); require(actual == final, 'independent decode/CRCs')
    mutable = {4, 5, *range(8, 12), *range(0x24, 0x28)}
    require(all(image[i] == parent[i] for i in range(0x38) if i not in mutable), 'header')
    for r in 'cfg': require({x: vv for x, _, vv in actual}[r] == old[r], r + ' identical to parent')
    require({x: vv for x, _, vv in actual}['e'] == new_e, 'e as declared (parent, or stock V1.1.0 with region_e)')
    for nm in ('GP-50 Firmware V1.1.0/Valeton GP-50 V1.1.0.bin', 'work/recovery_archive/Valeton GP-50 V1.1.0.stock.bin'):
        require(sha((ROOT / nm).read_bytes()) == STOCK_SHA, 'stock preserved')
    if cfg.get('expected_image_sha256'): require(sha(image) == cfg['expected_image_sha256'], f'image {sha(image)} != expected {cfg["expected_image_sha256"]}')
    lay = g['ctx']
    man = dict(status='BUILT AND VERIFIED OFFLINE; NOT INSTALLED', builder='scripts/nds_ui (generic image builder)', config=f'scripts/nds_ui/images/{cfg["id"]}.json',
               image=str(img_path.relative_to(ROOT)), image_sha256=sha(image), image_bytes=len(image), mod=cfg['mod'], version=cfg['version'],
               parent=cfg['parent'], features=g['enabled'], scope=cfg['summary'],
               declared=dict(hooks=[e for e in edits if e['kind'] == 'hook'], bound=[e for e in edits if e['kind'] == 'bound'],
                             **({'holes': [dict(address=e['address'], bytes=len(e['after']) // 2, sha256=sha(bytes.fromhex(e['after'])), reason=e['reason']) for e in edits if e['kind'] == 'hole'],
                                 'restored': [e for e in edits if e['kind'] == 'restore']} if any(e['kind'] in ('hole', 'restore') for e in edits) else {}),   # restores need declaring even when no hole is used
                             external_data=[dict(region=x['region'], address=hex(x['address']), offset=hex(x['offset']), bytes=len(x['bytes']), sha256=x['sha256'], reason=x['reason']) for x in g.get('external', [])],
                             version=[e for e in edits if e['kind'] == 'version'],
                             segment=dict(base=cfg['segment']['base'], end=hex(g['end']), bytes=len(g['code']), sha256=sha(g['code']))),
               modules=g['modules'], unchanged=['c', 'f', 'g'] + ([] if cfg.get('region_e') or g.get('external') else ['e']), region_e=cfg.get('region_e', 'parent'), regions=[dict(id=r, bytes=len(vv), sha256=sha(vv)) for r, _, vv in actual],
               container_checks=checks, authorization='')
    if write and not verify_only:
        (out / 'regions').mkdir(parents=True, exist_ok=True)
        for p, data in [(img_path, image)] + [(out / 'regions' / f'decoded_{r}.bin', vv) for r, _, vv in actual]:
            if p.exists(): require(p.read_bytes() == data, 'Refuse different artifact ' + str(p))
            else: p.write_bytes(data)
        (out / 'nds_ui_manifest.json').write_text(json.dumps(man, indent=2) + '\n')
    return image, man, g
