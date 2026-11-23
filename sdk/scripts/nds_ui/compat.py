"""Pinned stock ownership facts used by the builder, without decompiler exports.

These are derived compatibility facts, not a provenance/license clearance. The
whole stock B hash binds every address/range to the exact decoded input. There is
no fallback to inferred function bounds when the facts or stock do not match.
"""
import hashlib
import json
import zlib
from pathlib import Path

MAP_PATH = 'sdk/nds/compat/v110_code_ownership.json.zlib'
MAP_SHA256 = 'b61fe7d7e1f2680ede1d83c44d50a9484a6c37e43a4b1fa12048abe2c718f602'


def load_stock_facts(root, *, map_path=None, stock_path=None):
    root = Path(root)
    raw = (Path(map_path) if map_path else root/MAP_PATH).read_bytes()
    if hashlib.sha256(raw).hexdigest() != MAP_SHA256:
        raise ValueError('stock compatibility map hash mismatch')
    facts = json.loads(zlib.decompress(raw))
    if facts['schema'] != 1:
        raise ValueError('unsupported stock compatibility schema')
    stock = (Path(stock_path) if stock_path else root/'work/v110/decoded_b.bin').read_bytes()
    if hashlib.sha256(stock).hexdigest() != facts['stock_b_sha256']:
        raise ValueError('stock compatibility B hash mismatch')
    spans = [tuple(row) for row in facts['instruction_spans']]
    refs = [tuple(row) for row in facts['references']]
    bodies = {entry: [tuple(row) for row in ranges] for entry, ranges in facts['bodies']}
    code = sorted(row for ranges in bodies.values() for row in ranges)
    return spans, refs, bodies, code
