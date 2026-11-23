"""Final application adapters, focused studies first; image review remains required.

4215c retains its two-byte push and falls into shared 4215e C redirect.
Legacy diagnostics use tiny live-frame bridges; the receiver itself calls C.
The stock reset terminal 4a070..4a092 must stay byte-identical.
"""
NAME='remaining_application_c'
REQUIRES=('application_bulk_c','host_layer_c','diagnostics_c')
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=tuple('sdk/nds/remaining/'+s+'.c' for s in ('safe_packets','link_parsers','identity_apply','float_format','receive','control','reset'))
C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=('sdk/nds/remaining/float_format.c','sdk/nds/remaining/safe_packets.c','sdk/nds/remaining/link_parsers.c')
TARGETS={a:f'nds_remaining_{a:05x}' for a in (0x14bf6,0x14fd6,0x18f0a,0x41f34,0x46336,0x46366,0x464b2,0x46678,0x467fe,0x471de,0x46a0a)}
TARGETS.update({0x16ea4:'draft_power_assert',0x4215e:'draft_protocol_assert',0x49d92:'draft_audio_task',0x49ff6:'reset_shim_draft'})
KEPT_CODE_RANGES=((0x4a070,0x4a094,'reset terminal CSR/PC0/return tail'),)
HOOKED=tuple(TARGETS)
C_ENTRIES=tuple(TARGETS.values())+('nds_remaining_diag_receive',)
CODE={}
DATA={}
HOOKS={}
def patches(c):
    return [(a,f'j {c.labels[n]:#x}',f'remaining application adapter {a:05x}') for a,n in TARGETS.items()]
