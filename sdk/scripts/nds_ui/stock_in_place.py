"""Stock in place (patching release): cfg "stock_in_place" lists reconstructed module stems whose stock functions run
unmodified from the user's file instead of compiled translations. Generic rule for features whose adapter sources each
wrap one module and whose C entries are named <prefix>_<stock address>: a source is reverted when its single module is
listed; its entries are the hooked addresses whose entry name appears in that source. Features with their own
hooked() (application_bulk_c) are left to their own implementation. Only features named in cfg
"stock_in_place_features" take part, so a stem shared with another feature never changes that feature silently."""
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def _text(src):
    return (ROOT / src).read_text()


def modules(src):
    return re.findall(r'#include\s+"[^"]*reconstructed/nds/([^"/]+)\.c"', _text(src))


def applies(m):
    return not hasattr(m, 'hooked') and hasattr(m, 'HOOKED') and getattr(m, 'C_SOURCES', None)


def sources_of(m, cfg):
    return tuple(m.c_sources(cfg) if hasattr(m, 'c_sources') else m.C_SOURCES)


def reverted(m, cfg):
    """(sources, entry addresses, entry names) this config takes out of feature module m."""
    by_feature = (cfg or {}).get('stock_in_place_by_feature', {})   # per-feature stems override the global list
    keep = set(by_feature.get(m.NAME, (cfg or {}).get('stock_in_place', ())))
    if not keep or not applies(m) or m.NAME not in (cfg or {}).get('stock_in_place_features', ()):
        return (), frozenset(), frozenset()
    sources = tuple(s for s in sources_of(m, cfg) if modules(s) and set(modules(s)) <= keep)   # every wrapped module listed
    entries = m.c_entries(cfg) if hasattr(m, 'c_entries') else m.C_ENTRIES
    names = {n: a for a in m.HOOKED for n in entries if n.endswith(f'_{a:05x}')}
    if hasattr(m, 'ENTRY_MODULES'):   # explicit pairing (entries defined through aliases)
        stems = {x for s in sources for x in modules(s)}
        gone = {n for n, a in names.items() if m.ENTRY_MODULES.get(a) in stems and a not in getattr(m, 'STOCK_IN_PLACE_KEEP', ())}
    else:
        gone = {n for s in sources for n in names if re.search(r'\b' + re.escape(n) + r'\b', _text(s))}
    return sources, frozenset(names[n] for n in gone), frozenset(gone)


def stems(m, cfg):
    return {x for s in reverted(m, cfg)[0] for x in modules(s)}


# MOD005 theme: colour immediates of `movi rt, imm20` (opcode byte 0x44/0x45) changed in the parent from these stock
# RGB565 values to the theme's. Bytes of such an instruction may differ from stock inside a reverted body.
THEME = {0xfe23: 0x56fb, 0xcc11: 0x8a71, 0xcc10: 0x8a71}


def theme_sites(stock, parent, lo, hi):
    """Addresses in [lo, hi] covered by a theme colour swap between stock and parent (2-aligned 4-byte movi)."""
    out = set()
    for a in range(lo & ~1, hi + 1, 2):
        o = a - 0x10000
        s, p = int.from_bytes(stock[o:o + 4], 'big'), int.from_bytes(parent[o:o + 4], 'big')
        if s != p and s >> 20 == p >> 20 and s >> 25 == 0x22 and THEME.get(s & 0xffff) == p & 0xffff:
            out.update(range(a, a + 4))
    return out


def body_of(entry):
    from .holes import stock_facts
    return next((r for r in stock_facts()[2].get(entry, []) if r[0] <= entry <= r[1]), None)


def inside(address, entries):
    """True when address lies in the stock body of one of these (reverted) entries."""
    for e in entries:
        b = body_of(e)
        if b and b[0] <= address <= b[1]:
            return True
    return False


def bulk_stems(cfg):
    """Modules application_bulk_c runs as stock for this config (empty when the feature is off)."""
    if 'application_bulk_c' not in ((cfg or {}).get('features') or ()):
        return set()
    from .features import application_bulk_c as AB
    return {m for s in AB._reverted(cfg) for m in AB._module(s)}


def hook_windows():
    """Bytes of every hook site declared in the stock-API map (a parent hook there must be re-patched by this build)."""
    from .stock_api import API
    out = set()
    for e in API.entries().values():
        if e['kind'] != 'hook_site': continue
        for a in ([int(v, 16) for v in e['address']] if isinstance(e['address'], list) else [int(e['address'], 16)]):
            out.update(range(a, a + 4))
    return out


def palette_sites(features_modules, cfg):
    """4-byte windows of every SUPERSEDED palette site declared by the given feature modules."""
    out = set()
    for m in features_modules:
        sup = m.superseded(cfg) if False else getattr(m, 'SUPERSEDED', {})
        for a, v in sup.items():
            if 'palette' in v: out.update(range(a, a + 4))
    return out


def parent_edits(features_modules):
    """Bytes of intended parent edits inside stock bodies that features declare (PARENT_EDITS {address: (bytes, why)})."""
    out = set()
    for m in features_modules:
        for a, (n, _) in getattr(m, 'PARENT_EDITS', {}).items():
            out.update(range(a, a + n))
    return out
