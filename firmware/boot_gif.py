#!/usr/bin/env python3
"""Rebuild the boot animation from your own official GP-50 V1.1.0 file.

The animation is an edit of the stock one, so only the differences ship (boot_gif.packed.json): copy operations into
region b of your stock firmware plus our own bytes. The result must match the recorded SHA-256.

    boot_gif_pack.py unpack --stock STOCK.bin --lzo-library LIBLZO2 --packed boot_gif.packed.json --out boot.gif
"""
import argparse, base64, hashlib, json, sys
from pathlib import Path
MIN_COPY = 12


def regions(stock, lzo):
    here = Path(__file__).resolve().parent
    for p in (here, here.parent / 'sdk/scripts', here.parent / 'scripts'): sys.path.insert(0, str(p))
    import firmware_verify as V
    if lzo: V.LZO = str(lzo)
    rows, report = V.decode(Path(stock).read_bytes())
    return {r[0] if isinstance(r, tuple) else r['id']: (r[-1] if isinstance(r, tuple) else r['data']) for r in rows}


def pack(gif, base):
    """Greedy: longest copy (>= MIN_COPY) from the stock region at each position, else literal."""
    index = {}
    for i in range(len(base) - MIN_COPY + 1): index.setdefault(base[i:i + MIN_COPY], []).append(i)
    ops, lit, at = [], bytearray(), 0
    def flush():
        if lit: ops.append(base64.b64encode(bytes(lit)).decode()); lit.clear()
    while at < len(gif):
        best = (0, 0)
        for i in index.get(gif[at:at + MIN_COPY], [])[:64]:
            n = MIN_COPY
            while at + n < len(gif) and i + n < len(base) and gif[at + n] == base[i + n]: n += 1
            if n > best[0]: best = (n, i)
        if best[0]: flush(); ops.append([best[1], best[0]]); at += best[0]
        else: lit.append(gif[at]); at += 1
    flush()
    return ops


def unpack(ops, base):
    return b''.join(base64.b64decode(o) if isinstance(o, str) else base[o[0]:o[0] + o[1]] for o in ops)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('mode', choices=['pack', 'unpack']); ap.add_argument('--stock', required=True)
    ap.add_argument('--lzo-library'); ap.add_argument('--gif', type=Path); ap.add_argument('--packed', type=Path, required=True); ap.add_argument('--out', type=Path)
    a = ap.parse_args(); base = regions(a.stock, a.lzo_library)['b']
    if a.mode == 'pack':
        gif = a.gif.read_bytes(); ops = pack(gif, base); assert unpack(ops, base) == gif
        a.packed.write_text(json.dumps(dict(schema=1, region='b', sha256=hashlib.sha256(gif).hexdigest(), ops=ops)) + '\n'); return
    p = json.loads(a.packed.read_text()); gif = unpack(p['ops'], base)
    if hashlib.sha256(gif).hexdigest() != p['sha256']: raise SystemExit('boot animation does not match; is this the official V1.1.0 file?')
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_bytes(gif)


if __name__ == '__main__':
    main()
