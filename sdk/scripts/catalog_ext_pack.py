#!/usr/bin/env python3
"""Ship the catalog extension without copies of stock catalog records.

The catalog extension (sdk/nds/catalog/extension.json and the generated catalog_ext_data.h) holds effect descriptors:
our edits of stock effects (overrides such as C-Wah + Auto Engage) and our own effects. Overrides are mostly stock
descriptor bytes. The package therefore carries `extension.packed.json`: every descriptor as ops
    [offset, "copy", "e", source_offset, length]   bytes taken from region e of the user's own stock V1.1.0
    [offset, "hex"]                                 our bytes
with every run of >= MIN_COPY bytes that also occurs in stock region e taken from the user's file. The build
rebuilds both files from the user's stock and refuses unless they match the recorded SHA-256 exactly.

    catalog_ext_pack.py --check EXT HEADER STOCK_E    pack, unpack, compare (offline round trip)
"""
import argparse, hashlib, json
from pathlib import Path

MIN_COPY = 8          # copy any shared run of >= 8 bytes (the release scan rule is 16; 8 leaves margin)
sha = lambda b: hashlib.sha256(b).hexdigest()


def _ops(blob, stock, index):
    ops, i, lit = [], 0, bytearray()
    def flush(at):
        if lit: ops.append([at - len(lit), lit.hex()]); lit.clear()
    while i < len(blob):
        best, src = 0, 0
        for j in index.get(blob[i:i + MIN_COPY], ()) if i + MIN_COPY <= len(blob) else ():
            n = MIN_COPY
            while i + n < len(blob) and j + n < len(stock) and blob[i + n] == stock[j + n]: n += 1
            if n > best: best, src = n, j
        if best:
            flush(i); ops.append([i, 'copy', 'e', src, best]); i += best
        else:
            lit.append(blob[i]); i += 1
    flush(i)
    return ops


def pack(ext_text, header_text, stock_e):
    ext = json.loads(ext_text)
    if ext_text != json.dumps(ext, indent=1) + '\n': raise ValueError('extension.json is not in canonical form')
    index = {}
    for j in range(len(stock_e) - MIN_COPY + 1):
        index.setdefault(stock_e[j:j + MIN_COPY], []).append(j)
    entries = []
    for x in ext['entries']:
        blob = bytes.fromhex(x['descriptor'])
        y = {k: v for k, v in x.items() if k != 'descriptor'}
        y['descriptor_length'] = len(blob); y['descriptor_ops'] = _ops(blob, stock_e, index)
        entries.append(y)
    packed = dict(schema=1, kind='catalog_extension_packed', stock_e_sha256=sha(stock_e),
                  extension_sha256=sha(ext_text.encode()), header_sha256=sha(header_text.encode()),
                  extension={k: v for k, v in ext.items() if k != 'entries'}, entries=entries,
                  key_order=dict(extension=list(ext), entry=[list(x) for x in ext['entries']]))
    if unpack(packed, stock_e) != (ext_text, header_text):
        raise ValueError('packed catalog extension does not round-trip')
    return packed


def unpack(packed, stock_e, header=None):
    """-> (extension.json text, catalog_ext_data.h text), both checked against the recorded SHA-256."""
    if packed.get('schema') != 1 or packed.get('kind') != 'catalog_extension_packed': raise ValueError('packed schema')
    if sha(stock_e) != packed['stock_e_sha256']: raise ValueError('stock region e identity')
    entries = []
    for y in packed['entries']:
        blob = bytearray(y['descriptor_length'])
        for op in y['descriptor_ops']:
            if len(op) == 2:
                part, at = bytes.fromhex(op[1]), op[0]
            else:
                at, kind, region, src, n = op
                if kind != 'copy' or region != 'e' or src < 0 or n <= 0 or src + n > len(stock_e): raise ValueError('copy op')
                part = stock_e[src:src + n]
            if at < 0 or at + len(part) > len(blob): raise ValueError('op bounds')
            blob[at:at + len(part)] = part
        x = {k: v for k, v in y.items() if k not in ('descriptor_length', 'descriptor_ops')}
        x['descriptor'] = bytes(blob).hex()
        entries.append(x)
    ext = dict(packed['extension']); ext['entries'] = entries
    text = json.dumps(_reorder(ext, packed), indent=1) + '\n'
    if sha(text.encode()) != packed['extension_sha256']: raise ValueError('rebuilt extension.json identity')
    if header is None:
        import build_catalog_ext
        header = build_catalog_ext.header(json.loads(text))[0]
    if sha(header.encode()) != packed['header_sha256']: raise ValueError('rebuilt catalog_ext_data.h identity')
    return text, header


def _reorder(ext, packed):
    """Restore the original key order of the extension and of each entry (json.dumps keeps insertion order)."""
    keys = packed.get('key_order')
    if not keys: return ext
    out = {k: ext[k] for k in keys['extension'] if k in ext}
    out['entries'] = [{k: e[k] for k in keys['entry'][i] if k in e} for i, e in enumerate(ext['entries'])]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--check', nargs=3, metavar=('EXT', 'HEADER', 'STOCK_E'), required=True)
    a = ap.parse_args()
    import sys; sys.path.insert(0, str(Path(__file__).resolve().parent))
    ext, header, stock = (Path(p) for p in a.check)
    packed = pack(ext.read_text(), header.read_text(), stock.read_bytes())
    lit = sum(len(op[1]) // 2 for y in packed['entries'] for op in y['descriptor_ops'] if len(op) == 2)
    cop = sum(op[4] for y in packed['entries'] for op in y['descriptor_ops'] if len(op) == 5)
    print(json.dumps(dict(status='pass', entries=len(packed['entries']), literal_bytes=lit, copied_bytes=cop)))


if __name__ == '__main__':
    main()
