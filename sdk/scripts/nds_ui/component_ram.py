"""Automatic experimental ABI2 state+gate reservations, outside the stock heap.

No ABI1 layout change. The existing paired image bounds reserve the arena; its
base must exactly follow the reviewed capture/A-B ownership, never guessed slack.
The completed container builder publishes the ledger after section validation.
"""
from pathlib import Path
from .component_state import ARENA_START, plan_states
from .b_link import load_previous

# Mirrored by the target-compiled assertion in experimental/preset_runtime.h.
# '$' cannot occur in an author component ID, preventing reservation collision.
PRESET_RUNTIME_ID = '$preset_runtime'
PRESET_RUNTIME_BYTES = 3216
PRESET_SERVICES_ID = '$preset_services'
PRESET_SERVICES_BYTES = 768
FEATURES_ID = '$features'      # ABI 3 platform RAM (gp50_features_ram)
FEATURES_BYTES = 932   # sizeof(gp50_features_ram): 13 words + 448 + 432 (platform/gp50_features.h)


def ledger_path(cfg, root):
    path = (Path(root) / cfg['b_placement']['ledger']).resolve().parent / 'component_ram.committed.json'
    if not path.is_relative_to(Path(root).resolve()):
        raise ValueError('component RAM ledger escapes project')
    return path


def propose(cfg, components, root):
    mutable = [m for m in components if m['abi'] in (2, 3)]
    if not mutable:
        return None
    seg = cfg['segment']
    if int(seg['state'], 16) != 0x2001f4a0 or seg['state_bytes'] != 272:
        raise ValueError('mutable components require reviewed paired capture/A-B RAM')
    prior = load_previous(ledger_path(cfg, root), Path(root))
    rows = [dict(id=m['id'], state_bytes=m['resources']['state_bytes']+8, state_align=8) for m in mutable]
    if any(m['abi'] == 3 for m in mutable):
        rows.append(dict(id=FEATURES_ID, state_bytes=FEATURES_BYTES, state_align=8))
    persistent = any(m.get('persistence') for m in mutable)
    if persistent:
        rows.extend((dict(id=PRESET_RUNTIME_ID, state_bytes=PRESET_RUNTIME_BYTES, state_align=8),
                     dict(id=PRESET_SERVICES_ID, state_bytes=PRESET_SERVICES_BYTES, state_align=8)))
    size = cfg.get('component_state_arena_bytes', 4096)
    if type(size) is not int or not 16 <= size <= 4096 or size % 16:
        raise ValueError('integrated component RAM arena must be 16..4096 bytes aligned to 16')
    p = plan_states(rows, arena_bytes=size, previous=prior)
    p['addresses'] = {r['id']: r['address'] for r in p['layout']['allocations']}
    p['gate_bytes'] = 4
    p['state_offset'] = 8
    if persistent:
        p['persistence'] = dict(address=p['addresses'][PRESET_RUNTIME_ID],
                                bytes=PRESET_RUNTIME_BYTES,
                                services_address=p['addresses'][PRESET_SERVICES_ID],
                                services_bytes=PRESET_SERVICES_BYTES)
    assert p['arena_start'] == ARENA_START
    return p
