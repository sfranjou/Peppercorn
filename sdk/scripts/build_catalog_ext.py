#!/usr/bin/env python3
"""Own effect catalog (item 9 phase C, analysis/firmware/NDS_EFFECT_CATALOG.md section 7).

Source of truth: sdk/nds/catalog/extension.json — our catalog entries on top of stock region e (which stays
byte-identical to stock V1.1.0):
  append    a descriptor after the group's stock ordinals (and after earlier appended ones), in list order;
  override  a replacement for a stock ordinal (same public ID: our edits of stock effects).
Commands (use --stock-e FILE for an explicit supported decoded stock e):
  build_catalog_ext.py                      extension.json -> sdk/nds/catalog/catalog_ext_data.h (checked)
  build_catalog_ext.py --check              both files current and consistent
  build_catalog_ext.py --from-e E           derive extension.json from an installed catalog E (diff vs stock e;
                                            records derived_from_sha256 = sha of E for the image builder's rule)
  build_catalog_ext.py --add-effect DIR     append an SDK-built effect (DIR/descriptor.bin, DIR/manifest.json)
  build_catalog_ext.py --logical OUT.bin    write the logical catalog as a region-e image (stock e with the
                                            extension merged into its catalog container) for host tools
Region-e assets (extension.json "e_assets"): content that our images keep in region e outside the catalog,
e.g. the MOD034 boot card GIF at e+0x19600 (b points the boot animation there). An image's region e is then stock +
assets; the logical region e (for host tools and the transition rule) is the logical catalog + assets. --from-e refuses
any difference between the source e and (logical catalog + declared assets): nothing may be lost silently.
  --asset NAME:OFFSET:FILE   (with --from-e) declare an asset; its bytes must be at OFFSET in the source e.
Checks: every descriptor parses, length multiple of 4, <= 8 parameters, unique storage indices; public IDs unique per
group; overrides keep the stock ID and address a stock ordinal. Descriptor blobs are relocatable (name offsets are
relative to the descriptor's own string pool).
"""
import argparse, hashlib, json, struct, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; sys.path.insert(0, str(ROOT))
from protocol.overlay_image import parse_container, build_container, parse_descriptor
STOCK = ROOT / 'work/v110/decoded_e.bin'; STOCK_SHA = '4f48cf8c1c7e691c8d1df1900491ffd3509eef1b767258ea49fa6f3e231d7d48'
EXT = ROOT / 'sdk/nds/catalog/extension.json'; OUT = ROOT / 'sdk/nds/catalog/catalog_ext_data.h'
CAT = 0x10000; GROUPS = 10
sha = lambda b: hashlib.sha256(b).hexdigest()


def stock_e(path=None):
    e = (STOCK if path is None else Path(path)).read_bytes()
    if sha(e) != STOCK_SHA: raise SystemExit('stock e identity')
    return e


def groups(e):
    c = parse_container(e[CAT:0x20000]); return [list(c.groups[g]) for g in range(GROUPS)]


def entry(kind, group, blob, origin, ordinal=None):
    d = parse_descriptor(blob); x = dict(kind=kind, group=group)
    if ordinal is not None: x['ordinal'] = ordinal
    x.update(public_id=f'{d.public_id:#010x}', name=d.name, origin=origin, descriptor=blob.hex()); return x


def check(ext, stock):
    S = groups(stock); ids = {g: [struct.unpack_from('<I', b)[0] for b in S[g]] for g in range(GROUPS)}; seen = set()
    for x in ext['entries']:
        g = x['group']; blob = bytes.fromhex(x['descriptor']); d = parse_descriptor(blob)
        if not 0 <= g < GROUPS or g in (4, 9): raise ValueError(f'{x["name"]}: group {g} has no catalog list (4/9 are slot tables)')
        if len(blob) % 4 or blob[8] > 8 or len({p.storage_index for p in d.parameters}) != len(d.parameters): raise ValueError(f'{x["name"]}: descriptor limits')
        if f'{d.public_id:#010x}' != x['public_id']: raise ValueError(f'{x["name"]}: public_id field')
        if x['kind'] == 'override':
            o = x['ordinal']
            if not 0 <= o < len(S[g]) or ids[g][o] != d.public_id: raise ValueError(f'{x["name"]}: override must keep stock ordinal {o} ID')
            if (g, o) in seen: raise ValueError('duplicate override'); seen.add((g, o))
        elif x['kind'] == 'append':
            if d.public_id in ids[g]: raise ValueError(f'{x["name"]}: public ID {d.public_id:#010x} already in group {g}')
            ids[g].append(d.public_id)
        else: raise ValueError('kind')


def resolve(ext, stock):
    """Logical catalog: per group the list of descriptor blobs by ordinal."""
    S = groups(stock); L = [list(S[g]) for g in range(GROUPS)]
    for x in ext['entries']:
        if x['kind'] == 'override': L[x['group']][x['ordinal']] = bytes.fromhex(x['descriptor'])
    for x in ext['entries']:
        if x['kind'] == 'append': L[x['group']].append(bytes.fromhex(x['descriptor']))
    return L


def logical_e(ext, stock):
    c = parse_container(stock[CAT:0x20000]); L = resolve(ext, stock)
    fill = c.trailing
    if set(fill) != {0xff}: raise ValueError('stock catalog area is not followed by 0xff fill')
    for g in range(GROUPS): c.groups[g] = L[g]
    c.trailing = b''; body = build_container(c); e = bytearray(stock)
    if CAT + len(body) > 0x20000: raise ValueError('logical catalog exceeds the container area')
    e[CAT:0x20000] = body + b'\xff' * (0x10000 - len(body)); return bytes(e)


def asset_bytes(a):
    b = (ROOT / a['source']).read_bytes()
    if sha(b) != a['sha256'] or len(b) != a['length']: raise ValueError(f'asset {a["name"]}: file changed')
    return b


def with_assets(e, ext):
    e = bytearray(e)
    for a in ext.get('e_assets', []):
        o = int(a['offset'], 16); b = asset_bytes(a)
        if o < 0x10000 or o + len(b) > len(e): raise ValueError('asset outside region e data area')
        e[o:o + len(b)] = b
    return bytes(e)


def image_e(ext, stock):
    """Region e of an own-catalog image: stock with the declared assets; the catalog itself stays stock."""
    e = with_assets(stock, ext); cat_end = CAT + struct.unpack_from('<I', stock, CAT + 4)[0]
    for a in ext.get('e_assets', []):
        o = int(a['offset'], 16)
        if o < cat_end + 0x1000 and o + a['length'] > CAT: raise ValueError('asset too close to the catalog container')
        if set(stock[o:o + a['length']]) != {0xff}: raise ValueError(f'asset {a["name"]} would overwrite stock data')
    return e


def logical(ext, stock):
    """Logical region e: logical catalog + assets (what an edited-e image like MOD050 holds)."""
    return with_assets(logical_e(ext, stock), ext)


def from_e(path, stock, assets=()):
    src = path.read_bytes(); S, M = groups(stock), groups(src)
    if src[:CAT] != stock[:CAT] or src[0x20000:] != stock[0x20000:]: raise SystemExit('source e differs from stock outside the catalog container')
    origin = f'derived from {path.resolve().relative_to(ROOT) if path.resolve().is_relative_to(ROOT) else path}'
    entries = [entry('override', g, M[g][o], origin, o) for g in range(GROUPS) for o in range(len(S[g])) if M[g][o] != S[g][o]]
    entries += [entry('append', g, b, origin) for g in range(GROUPS) for b in M[g][len(S[g]):]]
    e_assets = []
    for spec in assets:
        name, off, f = spec.split(':', 2); b = (ROOT / f).read_bytes(); o = int(off, 16)
        if src[o:o + len(b)] != b: raise SystemExit(f'asset {name} not found at {off} in the source e')
        e_assets.append(dict(name=name, offset=f'{o:#x}', length=len(b), source=f, sha256=sha(b)))
    ext = dict(schema=1, derived_from_sha256=sha(src), entries=entries, e_assets=e_assets)
    check(ext, stock)
    if [b for g in resolve(ext, stock) for b in g] != [b for g in M for b in g]: raise SystemExit('derived extension does not reproduce the source catalog')
    rebuilt = logical(ext, stock)
    if rebuilt != src:
        d = [i for i in range(len(src)) if rebuilt[i] != src[i]]
        raise SystemExit(f'source e has {len(d)} bytes not explained by catalog + declared assets ({d[0]:#x}..{d[-1]:#x}); declare them with --asset')
    image_e(ext, stock)
    return ext


def header(ext):
    ov = [x for x in ext['entries'] if x['kind'] == 'override']; ap = [[x for x in ext['entries'] if x['kind'] == 'append' and x['group'] == g] for g in range(GROUPS)]
    blobs = [bytes.fromhex(x['descriptor']) for x in ov] + [bytes.fromhex(x['descriptor']) for a in ap for x in a]
    text = json.dumps(ext, indent=1) + '\n'
    L = [f'/* GENERATED by scripts/build_catalog_ext.py from sdk/nds/catalog/extension.json (sha256 {sha(text.encode())}).',
         ' * Own effect catalog extension: descriptors of our effects (appended after the stock ordinals) and our',
         ' * edits of stock entries (overrides, same public ID). Region e stays stock. Do not edit. */',
         '#ifndef GP50_CATALOG_EXT_DATA_H', '#define GP50_CATALOG_EXT_DATA_H', '#include <stdint.h>']
    for i, b in enumerate(blobs):
        d = parse_descriptor(b)
        L.append(f'/* {struct.unpack_from("<I", b)[0]:#010x} {d.name} ({len(b)} B) */')
        L.append(f'static const uint8_t ext_desc_{i}[{len(b)}] __attribute__((aligned(4))) = {{' + ','.join(f'0x{x:02x}' for x in b) + '};')
    L.append('static const struct { uint8_t group, ordinal; const uint8_t *descriptor; } ext_override[] = {')
    L += [f' {{{x["group"]}, {x["ordinal"]}, ext_desc_{i}}},' for i, x in enumerate(ov)] + ['};', f'#define EXT_OVERRIDES {len(ov)}u']
    k = len(ov)
    for g in range(GROUPS):
        if ap[g]: L.append(f'static const uint8_t *const ext_append_{g}[] = {{' + ', '.join(f'ext_desc_{k + j}' for j in range(len(ap[g]))) + '};'); k += len(ap[g])
    L.append('static const uint8_t ext_count[10] = {' + ', '.join(str(len(a)) for a in ap) + '};')
    L.append('static const uint8_t *const *const ext_append[10] = {' + ', '.join(f'ext_append_{g}' if ap[g] else '0' for g in range(GROUPS)) + '};')
    return '\n'.join(L + ['#endif', '']), text


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--from-e', type=Path); ap.add_argument('--add-effect', type=Path); ap.add_argument('--logical', type=Path)
    ap.add_argument('--asset', action='append', default=[])
    ap.add_argument('--ext', type=Path, default=EXT, help='extension.json path (tests use scratch copies)')
    ap.add_argument('--stock-e', type=Path, help='explicit supported decoded stock e (default: research workspace)')
    ap.add_argument('--header', type=Path, default=OUT)
    ap.add_argument('--check', action='store_true'); a = ap.parse_args(); stock = stock_e(a.stock_e)
    if a.from_e: ext = from_e(a.from_e, stock, a.asset)
    else: ext = json.loads(a.ext.read_text())
    if a.add_effect:
        m = json.loads((a.add_effect / 'manifest.json').read_text()); blob = (a.add_effect / 'descriptor.bin').read_bytes()
        if sha(blob) != m['sha256']['descriptor.bin']: raise SystemExit('descriptor differs from its SDK manifest')
        ext['entries'].append(entry('append', m['effect']['group'], blob, f'SDK {a.add_effect.resolve().relative_to(ROOT) if a.add_effect.resolve().is_relative_to(ROOT) else a.add_effect}'))
    check(ext, stock); h, text = header(ext)
    if a.logical: a.logical.write_bytes(logical(ext, stock)); print('logical region e ->', a.logical); return
    if a.check:
        if a.ext.read_text() != text or a.header.read_text() != h: raise SystemExit('extension.json / catalog_ext_data.h not current')
        print('current'); return
    a.ext.write_text(text); a.header.write_text(h)
    n = sum(x['kind'] == 'append' for x in ext['entries'])
    print(f'{len(ext["entries"]) - n} overrides, {n} appended -> {a.ext}, {a.header}')


if __name__ == '__main__':
    main()
