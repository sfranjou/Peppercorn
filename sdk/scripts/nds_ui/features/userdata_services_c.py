"""Compared word-channel UserData service, mode, order and notification helpers."""
NAME='userdata_services_c'
REQUIRES=('userdata_events_c',)
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_HARD_FLOAT=True
C_SOURCES=('sdk/nds/userdata_services/userdata_services.c',)
C_HARD_FLOAT_SOURCES=C_SOURCES
HOOKED=(288674, 288686, 288834, 288858, 288882, 288914, 289740, 290128, 290440, 290562, 290738, 291040, 291544, 291682, 291706, 291762, 291824, 291874, 291900, 291986, 292400, 292442, 292502, 293510, 293578, 293712, 293888, 294588, 294616, 294652)
C_ENTRIES=tuple(f'nds_uds_{a:05x}' for a in HOOKED)
CODE={}
DATA={}
HOOKS={}
# refuse_c gates block on/off by retargeting the jal at 0x473f6 inside stock 0x473f0. Redirecting
# 0x473f0 to C left that gate unreached (MOD095..MOD116). Keep stock 0x473f0 when refusal is linked;
# its C entry stays a GC root so placement is unchanged.
GATED=(0x473f0,)
def patches(c):
 return [(a,f'j {c.labels[f"nds_uds_{a:05x}"]:#x}',f'compared UserData service {a:05x}')for a in HOOKED
         if not ('refuse_c' in c.enabled and a in GATED)]
