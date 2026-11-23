"""Experimental mutable-state RAM planning; not enabled by ABI1 composition.

Offsets are linker inputs, never author-chosen addresses or persistence IDs.
The arena must be reserved by BOTH startup-clear and heap-start hooks before use.
Reuse the reviewed reservation algorithm; no second allocator implementation.
"""
from .b_placement import plan as reserve

# MOD097 end of owned capture/A-B RAM; validated by state-reservation probes.
ARENA_START = 0x2001f5b0
MAX_ARENA_BYTES = 4096


def plan_states(components, *, arena_bytes=MAX_ARENA_BYTES, previous=None):
    """Propose placements and heap boundary; does not patch images or commit RAM.

    components: mappings with id, state_bytes and state_align (power of two <=8).
    State is zero at boot; no address/offset stability across releases is promised.
    Unchanged fitting reservations are retained to avoid needless churn. Growth
    can relocate its own reservation. No silent global repack on exhaustion.
    """
    if type(arena_bytes) is not int or not 0 <= arena_bytes <= MAX_ARENA_BYTES or arena_bytes % 8:
        raise ValueError('state arena must be 0..4096 bytes aligned to 8')
    items = []
    seen = set()
    for row in components:
        ident = row['id']
        if not isinstance(ident, str) or not ident or ident in seen:
            raise ValueError('duplicate/invalid component state identity')
        seen.add(ident)
        size, align = row['state_bytes'], row['state_align']
        if type(size) is not int or not 0 <= size <= MAX_ARENA_BYTES:
            raise ValueError('invalid component state size')
        if type(align) is not int or align not in (1, 2, 4, 8):
            raise ValueError('invalid component state alignment')
        if size:
            items.append(dict(id=ident, size=size, align=align))
    pools = [dict(id='component_ram', start=ARENA_START, end=ARENA_START+arena_bytes)] if arena_bytes else []
    layout = reserve(items, pools, previous)
    return dict(layout=layout, arena_start=ARENA_START, arena_bytes=arena_bytes,
                startup_clear_end=ARENA_START+arena_bytes,
                heap_start=ARENA_START+arena_bytes,
                supported_by_abi1=False)
