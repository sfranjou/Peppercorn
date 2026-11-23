"""One framework feature; ordinary component authors only add directories+JSON.

ABI 1 intentionally has no mutable state or persistence allocation. Lifecycle and
host registration are generated from the validated manifest set. Final-image
execution, stack and placement checks remain required for every component set.
"""
import json
from pathlib import Path
from ..components import discover, registry_header, callback_header
from ..component_ram import propose
NAME='external_components_c'
REQUIRES=('footswitch_ab_c','capture_status_c')
CONFLICTS=()
ORACLES=()
CASE_KINDS=()
C_SOURCES=('sdk/nds/components/components_registry.c',
           'sdk/nds/components/components_host.c',
           'sdk/nds/components/services.c')
C_ENTRIES=('gp50_components_init','gp50_components_tick','gp50_components_has',
           'gp50_components_read','gp50_components_write',
           'gp50_component_host_get','gp50_component_host_set',
           'gp50_components_editor_status','gp50_about_append','gp50_ui_home_tick')
MENU_ENTRIES=('gp50_settings_open','gp50_settings_label')


def c_entries(cfg):
    """The Global settings tile wrappers exist only in builds with a feature menu (GP50_FEATURES_MENU)."""
    return C_ENTRIES+(MENU_ENTRIES if 'GP50_FEATURES_MENU=1' in (cfg or {}).get('c_defines',()) else ())
FEATURE_SOURCES=('sdk/nds/components/platform/gp50_features.c',
                 'sdk/nds/components/platform/gp50_services.c')


class _HardFloatSources:
    """ABI 3 feature sources and the service adapter compile hard-float (parameter values are floats in fs0, as
    the stock knob path); every other component and framework source stays soft-float."""
    def __contains__(self, src):
        if src == FEATURE_SOURCES[1]:
            return True
        from ..build import ROOT
        manifest = (ROOT / src).parent / 'component.json'
        try:
            return json.loads(manifest.read_text()).get('abi') == 3
        except (OSError, ValueError):
            return False


C_HARD_FLOAT=True
C_HARD_FLOAT_SOURCES=_HardFloatSources()
CODE={}
DATA={}
HOOKS={}

def components(cfg):
    from ..build import ROOT
    if 'GP50_COMPONENTS=1' not in (cfg or {}).get('c_defines',()):
        raise ValueError('external components require GP50_COMPONENTS=1')
    roots=(cfg or {}).get('component_roots',())
    if not isinstance(roots,list) or not roots or any(not isinstance(p,str) for p in roots):
        raise ValueError('component_roots must list directories')
    return discover([ROOT/Path(p) for p in roots],ROOT)

def c_sources(cfg):
    from ..build import ROOT
    cs=components(cfg)
    from ..components import LIMITS
    menus=[m['id'] for m in cs if m['abi']==3 and m.get('menu')]
    if len(menus)>LIMITS['GP50_MENU_TILES_MAX']:   # Global settings has one free tile slot
        raise ValueError('only one feature may have a menu (Global settings tile): '+', '.join(menus))
    ram=propose(cfg,cs,ROOT)
    registry_header(cs,ram['addresses'] if ram else None)  # also rejects an empty registry
    runtime=('sdk/nds/components/experimental/stateful.c',) if any(m['abi']==2 for m in cs) else ()
    runtime+=FEATURE_SOURCES if any(m['abi']==3 for m in cs) else ()
    return C_SOURCES+runtime+tuple(src for m in cs for src in m['sources'])

def c_headers(cfg,parent_b=None):
    from ..build import ROOT
    cs=components(cfg)
    ram=propose(cfg,cs,ROOT)
    result={'component_registry.h':registry_header(cs,ram['addresses'] if ram else None), 'component_callbacks.h':callback_header(cs),
            'component_inputs.json':json.dumps(cs,sort_keys=True,indent=2)+'\n',
            # Explicit null overwrites an earlier ABI2 plan when the last mutable
            # component is removed. Stale generated files are not current owners.
            'component_ram.proposed.json':json.dumps(ram,sort_keys=True,indent=2)+'\n'}
    return result

def patches(c):
    """ABI 3 About lines: the About text's last strcat goes through the platform wrapper (only with an `about` feature).
    Feature menu: the Global settings 12th tile (window-9 handler table, item loop bound and 12th label)."""
    from ..stock_api import API
    cs=components(c.cfg)
    out=[]
    if any(m['abi']==3 and 'about' in m['callbacks'] for m in cs):
        out.append((API.hook_about_text_append, f'jal {c.labels["gp50_about_append"]:#x}', 'About page text: stock append, then SDK about lines'))
    if any(m['abi']==3 and m.get('menu') for m in cs):
        out+=[(API.hook_settings_table_register, f'jal {c.labels["gp50_settings_open"]:#x}', 'Global settings open: feature tile handler table'),
              (API.hook_settings_item_loop, 'j 0x1f808', 'Global settings item loop: 4 tiles on page 3 (12th = feature tile)'),
              (API.hook_settings_item_label, f'jal {c.labels["gp50_settings_label"]:#x}', 'Global settings tile labels: 12th = feature menu title')]
    return out
