"""Main-processor effect catalog in C (item 9 phase B, analysis/firmware/NDS_EFFECT_CATALOG.md): the stock
catalog accessors/bridges (layer A) and the CAB / N->S slot-table modules (layer B) run the readable sources
compared with the original instructions (firmware/reconstructed/nds/catalog*.c, slot_table.c) through thin
stock-signature wrappers (sdk/nds/catalog/catalog_target.c). Each stock entry becomes `j nds_cat_/nds_slot_XXXXX`.
Behaviour identical; proof: scripts/verify_nds_catalog_image.py reruns the three golden studies on the built b.
Stays stock: init 0x196a8/0x196d8 and the float-result entries 0x198f2/0x19c2e/0x19fe6."""
from ..stock_api import API

NAME = 'catalog_c'
REQUIRES = ()
CONFLICTS = ()
ORACLES = ()
CASE_KINDS = ()
C_SOURCES = ('sdk/nds/catalog/catalog_target.c',)
C_HARD_FLOAT = True   # with cfg c_hard_float: float-result entries in C (stock fs0 convention); other features stay soft-float   # includes the three compared sources (GP50_CATALOG_DIRECT)
LAYER_A = (0x1966a, 0x19746, 0x19782, 0x198a2, 0x1973a, 0x19768, 0x19774, 0x197ac, 0x197bc, 0x198c4, 0x1991e,
           0x197ca, 0x1982e, 0x43996, 0x439b6, 0x439dc)
HOOKED = tuple(int(e['address'], 16) for n, e in API.entries().items() if n.startswith('hook_catalog_'))
FLOAT_HOOKED = tuple(int(e['address'], 16) for n, e in API.entries().items() if n.startswith('hook_catalogf_'))   # 0x198f2/0x19c2e/0x19fe6
C_ENTRIES = tuple(f'nds_cat_{a:05x}' if a in LAYER_A else f'nds_slot_{a:05x}' for a in HOOKED)
LAYER_A_FLOAT = (0x198f2,)


# MOD052 (cfg c_chains, needs c_hard_float): the effect chains above the catalog (NDS_PARAMETER_SET.md) as one module per
# compared source plus the wrappers (sdk/nds/catalog/chains_target.c); proof: scripts/verify_nds_chains_image.py.
CHAIN_HOOKED = tuple(int(e['address'], 16) for n, e in API.entries().items() if n.startswith('hook_chain_'))
CHAIN_SOURCES = ('sdk/nds/catalog/chain_parameter_set.c', 'sdk/nds/catalog/chain_effect_select.c', 'sdk/nds/catalog/chain_effect_link.c',
                 'sdk/nds/catalog/chain_host_param.c', 'sdk/nds/catalog/chain_host_notify.c', 'sdk/nds/catalog/chains_target.c')
REMAINING_CHAIN_HOOKED = (0x43a62, 0x43ac0, 0x43d52, 0x43a32, 0x45396,
                        0x43a80, 0x476e4, 0x427f8, 0x44cb8, 0x46fa2,
                        0x45744, 0x45944, 0x456cc)


NOTIFY_SELECT_HOOKED = (0x40a42, 0x40bbc, 0x40be8, 0x40c10, 0x40c42,
                       0x413f8, 0x4145e, 0x4206a, 0x420a0, 0x420d4, 0x42120,
                       0x427d2, 0x452a8, 0x4578e, 0x45958, 0x47602,
                       0x45382, 0x453ba, 0x46bf4, 0x46bfc, 0x475d0,
                       0x475d8, 0x430b8)

def notify_select_chains(cfg):
    enabled = bool((cfg or {}).get('c_notify_select_chains'))
    if enabled and (not remaining_chains(cfg) or 'refuse_c' not in cfg.get('features', ())):
        raise ValueError('c_notify_select_chains requires c_remaining_chains and refuse_c admission gate')
    return enabled


def remaining_chains(cfg):
    enabled = bool((cfg or {}).get('c_remaining_chains'))
    if enabled and not chains(cfg):
        raise ValueError('c_remaining_chains needs c_chains and c_hard_float')
    return enabled


def chains(cfg):
    if (cfg or {}).get('c_chains') and not (cfg or {}).get('c_hard_float'): raise ValueError('c_chains needs c_hard_float')
    return bool((cfg or {}).get('c_chains'))


def c_sources(cfg):
    base = (OWN_SOURCE,) if _cat_stock(cfg) else C_SOURCES
    sources = CHAIN_SOURCES if chains(cfg) else ()
    if notify_select_chains(cfg):
        sources = tuple(s for s in sources[:-1] if s != 'sdk/nds/catalog/chain_host_notify.c') + ('sdk/nds/catalog/chain_host_select.c', 'sdk/nds/catalog/notify_select_target.c')
    elif remaining_chains(cfg):
        sources = sources[:-1] + ('sdk/nds/catalog/remaining_chains_target.c',)
    return base + sources


def entry_name(a):
    if a in CHAIN_HOOKED or a in REMAINING_CHAIN_HOOKED or a in NOTIFY_SELECT_HOOKED: return f'nds_chain_{a:05x}'
    return f'nds_cat_{a:05x}' if a in LAYER_A or a in LAYER_A_FLOAT else f'nds_slot_{a:05x}'


def hooked(cfg):
    gone = _reverted_entries(cfg)
    return tuple(a for a in HOOKED + (FLOAT_HOOKED if (cfg or {}).get('c_hard_float') else ()) if a not in gone) + _rest_hooked(cfg)


def _rest_hooked(cfg):
    return (CHAIN_HOOKED if chains(cfg) else ()) + (REMAINING_CHAIN_HOOKED if remaining_chains(cfg) else ()) + (NOTIFY_SELECT_HOOKED if notify_select_chains(cfg) else ())


def c_entries(cfg):
    return tuple(entry_name(a) for a in hooked(cfg))
def c_headers(cfg=None, parent_b=None):
    """catalog_config.h: CATALOG_EXT 1 only with an own-catalog config (cfg['catalog_ext'], phase C), whose region e
    must be stock; the extension data header must have been generated from the declared source e."""
    ext = (cfg or {}).get('catalog_ext')
    if ext:
        import hashlib, re
        from ..build import ROOT
        if (cfg or {}).get('region_e') != 'stock_v110': raise ValueError('catalog_ext needs region_e stock_v110')
        text = (ROOT / ext['extension']).read_text()
        if hashlib.sha256(text.encode()).hexdigest() != ext['sha256']: raise ValueError('extension.json differs from the image config')
        header = (ROOT / ext.get('header', 'sdk/nds/catalog/catalog_ext_data.h')).read_text()
        m = re.search(r'sha256 ([0-9a-f]{64})', header)
        if not m or m.group(1) != ext['sha256']: raise ValueError('catalog_ext_data.h was not generated from this extension.json (run scripts/build_catalog_ext.py)')
    flt = int(bool((cfg or {}).get('c_hard_float')))
    author = '#define CATALOG_EXT_AUTHOR 1\n' if ext and 'header' in ext else ''
    out = {'catalog_config.h': f'#ifndef CATALOG_CONFIG_H\n#define CATALOG_CONFIG_H\n#define CATALOG_EXT {int(bool(ext))}\n#define CATALOG_FLOAT {flt}\n{author}#endif\n'}
    if author: out['catalog_ext_author.h'] = header
    return out


# stock_in_place (patching release): with cfg stock_in_place_by_feature['catalog_c'] naming catalog_accessors, the
# catalog, accessors and slot tables run as stock and only the three helpers below are ours (own_catalog_entries.c).
OWN_HELPERS = (0x1966a, 0x19746, 0x19782, 0x198a2, 0x197ca, 0x1982e)   # helpers + own-catalog names
OWN_SOURCE = 'sdk/nds/catalog/own_catalog_entries.c'


def _cat_stock(cfg):
    return 'catalog_accessors' in ((cfg or {}).get('stock_in_place_by_feature') or {}).get(NAME, ())


def _chain_off_entries(cfg):
    """Chain entries this config leaves to stock (chain options off). The parent (MOD055) redirects some of them into
    its old segment; those redirects are restored to stock, never left live."""
    if not _cat_stock(cfg): return set()
    return set(CHAIN_HOOKED + REMAINING_CHAIN_HOOKED + NOTIFY_SELECT_HOOKED) - set(_rest_hooked(cfg))


def _reverted_entries(cfg):
    if not _cat_stock(cfg): return set()
    return (set(HOOKED + (FLOAT_HOOKED if (cfg or {}).get('c_hard_float') else ())) - set(OWN_HELPERS)) | _chain_off_entries(cfg)


def superseded(cfg):
    out = dict(globals().get('SUPERSEDED', {}))
    out.update({e: 'stock_in_place: a parent redirect at this reverted catalog entry is restored to stock' for e in _reverted_entries(cfg)})
    return out


def cat_tails(c):
    if not _cat_stock(c.cfg): return
    # The helpers start by loading the catalog directory pointer gp-relative (gp-51396 = 0x20004d94); the tails load the
    # same word from its absolute address into the same register and rejoin the stock body after the 4-byte hook.
    c.s.label('cat_stock_1966a'); c.s.address('a2', 0x20004d94); c.s.emit('lwi a2,[a2 + 0]\nj 0x1966e')
    c.s.label('cat_stock_19746'); c.s.address('a1', 0x20004d94); c.s.emit('lwi a1,[a1 + 0]\nj 0x1974a')


CODE = {'cat_tails': cat_tails}
DATA = {}
HOOKS = {}


def patches(c):
    return [(a, f'j {c.labels[entry_name(a)]:#x}', f'stock entry {a:#x} -> C {entry_name(a)}') for a in hooked(c.cfg)]
