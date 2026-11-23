"""Stock scalar reply serializers in C. No new wire behavior or selector.

Compared source: protocol_scalar_packets.c; all36 entry wrappers, same a0/a1,
low-byte return, fully initialized envelopes into the existing queue0x15a1e.
"""
NAME='protocol_scalars_c'
REQUIRES=('host_layer_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/protocol_scalars/protocol_scalars.c',)
ENTRIES={265318: 'protocol_scalar_40c66', 265372: 'protocol_scalar_40c9c', 265426: 'protocol_scalar_40cd2', 265480: 'protocol_scalar_40d08', 265534: 'protocol_scalar_40d3e', 265588: 'protocol_scalar_40d74', 265638: 'protocol_scalar_40da6', 265688: 'protocol_scalar_40dd8', 265738: 'protocol_scalar_40e0a', 265788: 'protocol_scalar_40e3c', 265838: 'protocol_scalar_40e6e', 265888: 'protocol_scalar_40ea0', 265938: 'protocol_scalar_40ed2', 265988: 'protocol_scalar_40f04', 266038: 'protocol_scalar_40f36', 266088: 'protocol_scalar_40f68', 266138: 'protocol_scalar_40f9a', 266188: 'protocol_scalar_40fcc', 266238: 'protocol_scalar_40ffe', 266288: 'protocol_scalar_41030', 266338: 'protocol_scalar_41062', 266388: 'protocol_scalar_41094', 266438: 'protocol_scalar_410c6', 266488: 'protocol_scalar_410f8', 266538: 'protocol_scalar_4112a', 266588: 'protocol_scalar_4115c', 266638: 'protocol_scalar_4118e', 266688: 'protocol_scalar_411c0', 266738: 'protocol_scalar_411f2', 266788: 'protocol_scalar_41224', 266838: 'protocol_scalar_41256', 266888: 'protocol_scalar_41288', 266938: 'protocol_scalar_412ba', 266988: 'protocol_scalar_412ec', 267056: 'protocol_scalar_41330', 267106: 'protocol_scalar_41362'}
HOOKED=tuple(sorted(ENTRIES))
C_ENTRIES=tuple(f'nds_scalar_{a:05x}'for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
def patches(c):
    return [(a,f'j {c.labels[f"nds_scalar_{a:05x}"]:#x}',f'stock scalar packet{a:05x} in compared C')for a in HOOKED]
