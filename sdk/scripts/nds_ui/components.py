"""Declarative NDS component discovery (ABI 1; experimental mutable ABI 2).

No modules or build scripts are executed from component directories. Discovery is
explicit, deterministic, validates the entire set before emitting any output, and
keeps selectors and object names disjoint from core components. Resource claims
are declarations for review, not measured execution-time guarantees.
"""
import hashlib
import json
import re
from pathlib import Path


class ComponentError(ValueError):
    pass


def _object(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ComponentError('duplicate manifest key: ' + key)
        out[key] = value
    return out


def _exact(value, keys, where):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ComponentError(where + ': expected keys ' + ', '.join(sorted(keys)))


def _integer(value, lo, hi, where):
    if type(value) is not int or not lo <= value <= hi:
        raise ComponentError(f'{where}: expected integer {lo}..{hi}')


def discover(roots, project_root, *, experimental_persistence=False):
    project_root = Path(project_root).resolve()
    found = []
    ids, selectors, stems, symbols = set(), set(), set(), set()
    for root in sorted({str(Path(p).resolve()) for p in roots}):
        root = Path(root)
        if not root.is_relative_to(project_root):
            raise ComponentError('component root escapes project/package')
        if not root.is_dir():
            raise ComponentError('component root is not a directory: ' + str(root))
        for path in sorted(root.glob('*/component.json')):
            if not path.resolve().is_relative_to(path.parent.resolve()):
                raise ComponentError('manifest escapes component directory')
            folder = path.parent.resolve()
            if not folder.is_relative_to(root) or not folder.is_relative_to(project_root):
                raise ComponentError('component escapes declared root: ' + str(path))
            m = json.loads(path.read_text(), object_pairs_hook=_object)
            if m.get('abi') == 3:
                m = _abi3(m, path, folder, project_root)
                for name, used in ((m['id'], ids), (m['host'] and m['host']['selector'], selectors)):
                    if name and name in used:
                        raise ComponentError('duplicate component id or host selector: ' + str(name))
                ids.add(m['id'])
                if m['host']:
                    selectors.add(m['host']['selector'])
                for symbol in m['callbacks'].values():
                    if symbol in symbols:
                        raise ComponentError('duplicate callback symbol: ' + symbol)
                    symbols.add(symbol)
                for src in m['sources']:
                    if Path(src).stem in stems:
                        raise ComponentError(m['id'] + ': duplicate object stem: ' + Path(src).stem)
                    stems.add(Path(src).stem)
                found.append(m)
                continue
            keys = ('abi', 'id', 'sources', 'callbacks', 'host', 'resources')
            if 'persistence' in m:
                if not experimental_persistence:
                    raise ComponentError('persistence requires the experimental lifecycle integration')
                keys += ('persistence',)
            _exact(m, keys, str(path))
            if type(m['abi']) is not int or m['abi'] not in (1, 2):
                raise ComponentError('unsupported component ABI')
            ident = m['id']
            if not isinstance(ident, str) or not re.fullmatch('[a-z][a-z0-9_]{1,31}', ident):
                raise ComponentError('invalid component id')
            if ident == 'gp50' or ident.startswith('gp50_'):
                raise ComponentError('reserved framework component id')
            if ident in ids:
                raise ComponentError('duplicate component id: ' + ident)
            ids.add(ident)
            callbacks = m['callbacks']
            if isinstance(callbacks, dict) and 'status' in callbacks:
                _exact(callbacks, ('init', 'tick', 'get', 'set', 'status'), ident + ' callbacks')
            else:
                _exact(callbacks, ('init', 'tick', 'get', 'set'), ident + ' callbacks')
            persistence = m.get('persistence')
            if 'persistence' in m:
                if m['abi'] != 2:
                    raise ComponentError(ident + ': persistence requires mutable ABI 2')
                _exact(persistence, ('schema', 'max_bytes', 'defaults', 'load', 'save'), ident + ' persistence')
                _integer(persistence['schema'], 1, 65535, ident + ' payload schema')
                _integer(persistence['max_bytes'], 0, 428, ident + ' payload maximum')
                if any(persistence[role] is None for role in ('defaults','load','save')):
                    raise ComponentError(ident + ': persistence callbacks are required')
            extra = [(role,persistence[role]) for role in ('defaults','load','save')] if persistence else []
            for role, symbol in [*m['callbacks'].items(), *extra]:
                if symbol is None:
                    continue
                if not isinstance(symbol, str) or not re.fullmatch(re.escape(ident) + r'_[a-zA-Z0-9_]+', symbol):
                    raise ComponentError(ident + ': callback must use component id prefix')
                if symbol in symbols:
                    raise ComponentError('duplicate callback symbol: ' + symbol)
                symbols.add(symbol)
            _exact(m['host'], ('selector', 'set_bytes', 'max_reply_bytes'), ident + ' host')
            host = m['host']
            _integer(host['selector'], 0x76, 0x7e, ident + ' selector')
            if host['selector'] in selectors:
                raise ComponentError('duplicate host selector')
            selectors.add(host['selector'])
            _integer(host['set_bytes'], 0, 24, ident + ' set_bytes')
            _integer(host['max_reply_bytes'], 1, 24, ident + ' max_reply_bytes')
            if m['callbacks']['get'] is None or (m['callbacks']['set'] is None and host['set_bytes'] != 0):
                raise ComponentError(ident + ': GET required; SET length requires a SET callback')
            _exact(m['resources'], ('state_bytes', 'stack_bytes', 'tick_us'), ident + ' resources')
            if m['abi'] == 1:
                _integer(m['resources']['state_bytes'], 0, 0, ident + ' state_bytes (ABI 1 is stateless)')
            else:
                _integer(m['resources']['state_bytes'], 1, 4088, ident + ' state_bytes (ABI 2)')
            _integer(m['resources']['stack_bytes'], 0, 512, ident + ' stack_bytes')
            _integer(m['resources']['tick_us'], 0, 1000, ident + ' tick_us')
            if m['callbacks']['tick'] is not None and not m['resources']['tick_us']:
                raise ComponentError(ident + ': tick callback requires nonzero tick_us budget')
            if not isinstance(m['sources'], list) or not m['sources']:
                raise ComponentError(ident + ': nonempty source list required')
            inputs, sources = {}, []
            inputs[str(path.relative_to(project_root))] = hashlib.sha256(path.read_bytes()).hexdigest()
            for src in m['sources']:
                if not isinstance(src, str) or Path(src).is_absolute() or '..' in Path(src).parts:
                    raise ComponentError(ident + ': invalid source path')
                source = (folder / src).resolve()
                if not source.is_relative_to(folder) or not source.is_file() or source.suffix != '.c':
                    raise ComponentError(ident + ': source missing, outside component, or not C')
                if not source.stem.startswith(ident + '_') or source.stem in stems:
                    raise ComponentError(ident + ': duplicate/unprefixed object stem: ' + source.stem)
                stems.add(source.stem)
                relative = str(source.relative_to(project_root))
                sources.append(relative)
                inputs[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
            found.append(dict(m, sources=sources, inputs=inputs))
    stored = [m for m in found if m['abi'] == 3 and m.get('preset_bytes')]
    if sum(2 + len(m['id']) + m['preset_bytes'] for m in stored) > 432:   # GP50_AREA_RECORDS (platform/gp50_features.h)
        raise ComponentError('per-preset bytes of all features (2 + id length + preset_bytes each) exceed 432')
    persistent = [m for m in found if m.get('persistence')]
    if len(persistent) > 32 or 20 + sum(8 + len(m['id']) + m['persistence']['max_bytes'] for m in persistent) > 448:
        raise ComponentError('persistent component maxima exceed the 448-byte preset envelope')
    return sorted(found, key=lambda m: m['id'])


ABI3_CALLBACKS = ('init', 'tick', 'get', 'set', 'event', 'status', 'preset_save', 'preset_load', 'menu_value',
                  'menu_change', 'about', 'strip')
# Limits come from the public header so authors and the build share one definition.
def _header_limits():
    text = (Path(__file__).resolve().parents[2] / 'sdk/nds/components/gp50.h').read_text()
    return {k: int(v, 0) for k, v in re.findall(r'#define (GP50_[A-Z_]+_(?:MAX|FIRST|LAST)|GP50_HOST_SELECTOR_[A-Z]+) (0x[0-9a-f]+|[0-9]+)u', text)}


LIMITS = _header_limits()
ABI3_PRESET_BYTES = LIMITS['GP50_PRESET_BYTES_MAX']
ABI3_MENU_ITEMS = LIMITS['GP50_MENU_ITEMS_MAX']


def _abi3(m, path, folder, project_root):
    """ABI 3 feature component: every key except abi/id/sources/resources is optional (see sdk/nds/components/gp50.h)."""
    allowed = {'abi', 'id', 'sources', 'callbacks', 'host', 'preset_bytes', 'menu', 'resources'}
    if not isinstance(m, dict) or not {'abi', 'id', 'sources', 'callbacks', 'resources'} <= set(m) or set(m) - allowed:
        raise ComponentError(f'{path}: ABI 3 keys are abi, id, sources, callbacks, resources and optional host, '
                             'preset_bytes, menu')
    ident = m['id']
    if not isinstance(ident, str) or not re.fullmatch('[a-z][a-z0-9_]{1,31}', ident) or ident.startswith('gp50'):
        raise ComponentError(f'{path}: id must be 2..32 lowercase letters, digits or _, not starting with gp50')
    cb = m['callbacks']
    if not isinstance(cb, dict) or set(cb) - set(ABI3_CALLBACKS):
        raise ComponentError(f'{ident}: callbacks may be ' + ', '.join(ABI3_CALLBACKS))
    cb = {r: s for r, s in cb.items() if s is not None}
    for role, symbol in cb.items():
        if not isinstance(symbol, str) or not re.fullmatch(re.escape(ident) + r'_[a-zA-Z0-9_]+', symbol):
            raise ComponentError(f'{ident}: callback {role} must be a function named {ident}_...')
    host = m.get('host')
    if host is not None:
        _exact(host, ('selector', 'set_bytes', 'max_reply_bytes'), ident + ' host')
        reserved = {v for k, v in LIMITS.items() if k in ('GP50_HOST_SELECTOR_ASSIGN', 'GP50_HOST_SELECTOR_AB', 'GP50_HOST_SELECTOR_DRUM')}
        if host.get('selector') not in reserved:
            _integer(host['selector'], LIMITS['GP50_HOST_SELECTOR_FIRST'], LIMITS['GP50_HOST_SELECTOR_LAST'], ident + ' host.selector')
        _integer(host['set_bytes'], 0, LIMITS['GP50_HOST_BYTES_MAX'], ident + ' host.set_bytes')
        _integer(host['max_reply_bytes'], 1, LIMITS['GP50_HOST_BYTES_MAX'], ident + ' host.max_reply_bytes')
        if 'get' not in cb or (host['set_bytes'] and 'set' not in cb) or ('set' in cb and not host['set_bytes']):
            raise ComponentError(f'{ident}: host needs a get callback, and a set callback exactly when set_bytes > 0')
    elif 'get' in cb or 'set' in cb:
        raise ComponentError(f'{ident}: get/set callbacks need a host section')
    preset_bytes = m.get('preset_bytes', 0)
    _integer(preset_bytes, 0, ABI3_PRESET_BYTES, ident + ' preset_bytes')
    if bool(preset_bytes) != ('preset_save' in cb) or ('preset_save' in cb) != ('preset_load' in cb):
        raise ComponentError(f'{ident}: preset_bytes > 0 needs both preset_save and preset_load callbacks')
    menu = m.get('menu')
    if menu is not None:
        _exact(menu, ('title', 'items'), ident + ' menu')
        texts = [*menu['items']] if isinstance(menu['items'], list) else None
        if not texts or len(texts) > ABI3_MENU_ITEMS or any(
                not isinstance(s, str) or not re.fullmatch(r'[ -~]{1,%d}' % LIMITS['GP50_MENU_TEXT_MAX'], s) for s in texts) or \
                not isinstance(menu['title'], str) or not re.fullmatch(r'[ -~]{1,%d}' % LIMITS['GP50_MENU_TITLE_MAX'], menu['title']) or \
                any(c in s for s in [menu['title'], *texts] for c in '"\\'):
            raise ComponentError(f'{ident}: menu needs a title of 1..{LIMITS["GP50_MENU_TITLE_MAX"]} and 1..{ABI3_MENU_ITEMS} '
                                 f'items of 1..{LIMITS["GP50_MENU_TEXT_MAX"]} printable characters (no quote or backslash)')
        if 'menu_value' not in cb:
            raise ComponentError(f'{ident}: a menu needs a menu_value callback')
    elif 'menu_value' in cb or 'menu_change' in cb:
        raise ComponentError(f'{ident}: menu callbacks need a menu section')
    _exact(m['resources'], ('state_bytes', 'stack_bytes', 'tick_us'), ident + ' resources')
    _integer(m['resources']['state_bytes'], 0, LIMITS['GP50_STATE_BYTES_MAX'], ident + ' state_bytes')
    _integer(m['resources']['stack_bytes'], 0, LIMITS['GP50_STACK_BYTES_MAX'], ident + ' stack_bytes')
    _integer(m['resources']['tick_us'], 0, 1000, ident + ' tick_us')
    if 'tick' in cb and not m['resources']['tick_us']:
        raise ComponentError(f'{ident}: a tick callback needs a nonzero tick_us estimate')
    if not cb:
        raise ComponentError(f'{ident}: no callbacks')
    if not isinstance(m['sources'], list) or not m['sources']:
        raise ComponentError(ident + ': nonempty source list required')
    inputs, sources, names = {str(path.relative_to(project_root)): hashlib.sha256(path.read_bytes()).hexdigest()}, [], []
    for src in m['sources']:
        if not isinstance(src, str) or Path(src).is_absolute() or '..' in Path(src).parts:
            raise ComponentError(ident + ': invalid source path')
        source = (folder / src).resolve()
        if not source.is_relative_to(folder) or not source.is_file() or source.suffix != '.c':
            raise ComponentError(ident + ': source missing, outside component, or not C: ' + src)
        if not source.stem.startswith(ident + '_') or source.stem.startswith(ident + '_test'):
            raise ComponentError(f'{ident}: source file names must start with {ident}_ (tests are test_*.c)')
        relative = str(source.relative_to(project_root))
        sources.append(relative); names.append(src)
        inputs[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    return dict(m, callbacks=cb, host=host, preset_bytes=preset_bytes, menu=menu, sources=sources,
                source_names=names, inputs=inputs)


def discover_one(path, folder):
    """Validate one ABI 3 manifest outside a project tree (native runs)."""
    path, folder = Path(path).resolve(), Path(folder).resolve()
    m = json.loads(path.read_text(), object_pairs_hook=_object)
    if m.get('abi') != 3:
        return m
    return _abi3(m, path, folder, folder.parent)


def callback_header(components):
    lines = ['/* Generated callback ABI declarations. */', '#include "components/component.h"']
    declarations = {'init': 'void {name}(void);', 'tick': 'void {name}(void);',
                    'get': 'uint32_t {name}(uint8_t *, uint32_t);',
                    'set': 'uint32_t {name}(const uint8_t *, uint32_t);',
                    'status': 'uint32_t {name}(char *, uint32_t);'}
    abi3 = {'init': 'void {name}(const gp50_ctx *);', 'tick': 'void {name}(const gp50_ctx *);',
            'get': 'uint32_t {name}(const gp50_ctx *, uint8_t *, uint32_t);',
            'set': 'uint32_t {name}(const gp50_ctx *, const uint8_t *, uint32_t);',
            'event': 'uint32_t {name}(const gp50_ctx *, const gp50_event *);',
            'status': 'uint32_t {name}(const gp50_ctx *, char *, uint32_t);',
            'preset_save': 'uint32_t {name}(const gp50_ctx *, uint8_t *, uint32_t);',
            'preset_load': 'void {name}(const gp50_ctx *, const uint8_t *, uint32_t);',
            'menu_value': 'uint32_t {name}(const gp50_ctx *, uint32_t, char *, uint32_t);',
            'menu_change': 'uint32_t {name}(const gp50_ctx *, uint32_t, int32_t);',
            'about': 'uint32_t {name}(const gp50_ctx *, char *, uint32_t);',
            'strip': 'uint32_t {name}(const gp50_ctx *, uint32_t, gp50_strip *);'}
    for m in components:
        if m['abi'] == 3:
            if '#include "components/platform/gp50_features.h"' not in lines:
                lines.append('#include "components/platform/gp50_features.h"')
            lines += [abi3[r].format(name=n) for r, n in m['callbacks'].items()]
            continue
        if m['abi'] == 2:
            if '#include "components/experimental/stateful.h"' not in lines:
                lines.append('#include "components/experimental/stateful.h"')
            forms = {'init': 'void {name}(const gp50_state_context *);',
                     'tick': 'void {name}(const gp50_state_context *);',
                     'get': 'uint32_t {name}(const gp50_state_context *, uint8_t *, uint32_t);',
                     'set': 'uint32_t {name}(const gp50_state_context *, const uint8_t *, uint32_t);',
                     'status': 'uint32_t {name}(const gp50_state_context *, char *, uint32_t);'}
        else:
            forms = declarations
        if m.get('persistence'):
            forms = dict(forms, tick='uint32_t {name}(const gp50_state_context *);')
        for role, name in m['callbacks'].items():
            if name:
                lines.append(forms[role].format(name=name))
        if m.get('persistence'):
            lines += [f'void {m["persistence"]["defaults"]}(const gp50_state_context *);',
                      f'uint32_t {m["persistence"]["save"]}(const gp50_state_context *, uint8_t *, uint32_t);',
                      f'uint32_t {m["persistence"]["load"]}(const gp50_state_context *, uint32_t, const uint8_t *, uint32_t);']
    return '\n'.join(lines) + '\n'


def registry_header(components, ram=None, *, preset_session=None):
    if not components:
        raise ComponentError('registry requires at least one component')
    lines = [callback_header(components)]
    persistent = [m for m in components if m.get('persistence')]
    if persistent:
        if type(preset_session) is not int or not 0 < preset_session <= 0xfffffff0 or preset_session % 4:
            raise ComponentError('persistent registration requires a framework-owned preset session')
        lines += ['#include "components/experimental/stateful_preset.h"',
                  '#include "components/experimental/preset_restore.h"',
                  '#include "components/experimental/preset_runtime.h"',
                  f'#define GP50_PRESET_RUNTIME ((gp50_preset_runtime *)(uintptr_t){preset_session:#x}u)',
                  '#define GP50_PRESET_SESSION (&GP50_PRESET_RUNTIME->session)',
                  '#define GP50_PRESET_DIRTY ((volatile uint8_t *)(uintptr_t)0x2001090bu)']
    for m in components:
        if m['abi'] != 2:
            continue
        if ram is None or m['id'] not in ram:
            raise ComponentError('ABI 2 registry requires automatic RAM placement')
        ident, h = m['id'], m['host']
        gate = ram[ident]
        callbacks = ', '.join(m['callbacks'][r] or '0' for r in ('init', 'tick', 'get', 'set'))
        if m.get('persistence'):
            callbacks = ', '.join((m['callbacks'][r] or '0') if r != 'tick' else '0'
                                  for r in ('init', 'tick', 'get', 'set'))
        # Framework symbols use a private prefix distinct from every author symbol.
        name = f'gp50_sdk_state_{ident}'
        runtime = 'gp50_stateful_preset_' if m.get('persistence') else 'gp50_stateful_'
        session = ',GP50_PRESET_SESSION' if m.get('persistence') else ''
        lines += [f'static const gp50_stateful_entry {name} = {{',
                  f' {{ (void *){gate + 8:#x}u, {m["resources"]["state_bytes"]}u }},',
                  f' (volatile uint32_t *){gate:#x}u, {h["set_bytes"]}u, {h["max_reply_bytes"]}u, {callbacks}',
                  '};',
                  f'static void {name}_init(void) {{ gp50_stateful_init(&{name}); }}',
                  f'static uint32_t {name}_get(uint8_t *p, uint32_t n) {{ return {runtime}read(&{name}{session},p,n); }}']
        tick_call = (f'gp50_stateful_preset_tick_tracked(&{name},GP50_PRESET_SESSION,&GP50_PRESET_RUNTIME->revision,{m["callbacks"]["tick"] or "0"})'
                     if m.get('persistence') else f'{runtime}tick(&{name})')
        notify = (' gp50_preset_runtime_notify_dirty(GP50_PRESET_RUNTIME,GP50_PRESET_DIRTY);'
                  if m.get('persistence') else '')
        lines.append(f'static void {name}_tick(void) {{ {tick_call};{notify} }}')
        if m['callbacks']['set']:
            call = (f'gp50_stateful_preset_write_tracked(&{name},GP50_PRESET_SESSION,&GP50_PRESET_RUNTIME->revision,p,n)'
                    if m.get('persistence') else f'{runtime}write(&{name},p,n)')
            body = f'uint32_t result={call};{notify} return result;' if notify else f'return {call};'
            lines.append(f'static uint32_t {name}_set(const uint8_t *p, uint32_t n) {{ {body} }}')
        if m['callbacks'].get('status'):
            lines.append(f'static uint32_t {name}_status(char *p, uint32_t n) {{ return {runtime}status(&{name}{session},{m["callbacks"]["status"]},p,n); }}')
    lines.append(f'#define GP50_PERSISTENT_COMPONENT_COUNT {len(persistent)}u')
    if persistent:
        lines.append('static const gp50_preset_capture_entry gp50_preset_capture_table[] = {')
        for m in persistent:
            p=m['persistence']
            lines.append(f' {{ &gp50_sdk_state_{m["id"]}, "{m["id"]}", {p["save"]}, {p["schema"]}, {p["max_bytes"]}, {len(m["id"])} }},')
        lines += ['};','static const gp50_preset_restore_entry gp50_preset_restore_table[] = {']
        for i,m in enumerate(persistent):
            p=m['persistence']
            lines.append(f' {{ &gp50_preset_capture_table[{i}], {p["defaults"]}, {p["load"]} }},')
        lines.append('};')
    features = [m for m in components if m['abi'] == 3]
    if features:
        if ram is None or '$features' not in ram or any(m['id'] not in ram for m in features):
            raise ComponentError('ABI 3 registry requires automatic RAM placement')
        lines.append('const gp50_feature_entry gp50_feature_table[] = {')
        for m in features:
            h, cb, gate = m['host'] or {'selector': 0, 'set_bytes': 0, 'max_reply_bytes': 0}, m['callbacks'], ram[m['id']]
            roles = ', '.join(cb.get(r) or '0' for r in ABI3_CALLBACKS[:4] + ('event', 'status', 'preset_save',
                                                                             'preset_load', 'menu_value', 'menu_change',
                                                                             'about', 'strip'))
            mn = m.get('menu')
            items = [*(mn['items'] if mn else []), *([None] * ABI3_MENU_ITEMS)][:ABI3_MENU_ITEMS]
            menu = (f'"{mn["title"]}"' if mn else '0') + ', { ' + ', '.join(f'"{s}"' if s else '0' for s in items) + \
                f' }}, {len(mn["items"]) if mn else 0}u'
            lines.append(f' {{ {{ (void *){gate + 8:#x}u, {m["resources"]["state_bytes"]}u }}, "{m["id"]}", (volatile uint32_t *){gate:#x}u, '
                         f'{h["selector"]}u, {h["set_bytes"]}u, {h["max_reply_bytes"]}u, {m["preset_bytes"]}u, {roles}, {menu} }},')
        lines += ['};', f'const uint32_t gp50_feature_count = {len(features)}u;',
                  f'gp50_features_ram *const gp50_features_ram_block = (gp50_features_ram *){ram["$features"]:#x}u;']
        for i, m in enumerate(features):
            name, e = f'gp50_sdk_feature_{m["id"]}', f'&gp50_feature_table[{i}]'
            lines += [f'static void {name}_init(void) {{ gp50_feature_init({e}); }}',
                      f'static void {name}_tick(void) {{ gp50_feature_tick({e}); }}']
            cbs = m['callbacks']   # only the wrappers the feature uses (unused statics fail -Werror)
            if 'get' in cbs:
                lines.append(f'static uint32_t {name}_get(uint8_t *p, uint32_t n) {{ return gp50_feature_get({e},p,n); }}')
            if 'set' in cbs:
                lines.append(f'static uint32_t {name}_set(const uint8_t *p, uint32_t n) {{ return gp50_feature_set({e},p,n); }}')
            if 'status' in cbs:
                lines.append(f'static uint32_t {name}_status(char *p, uint32_t n) {{ return gp50_feature_status({e},p,n); }}')
    lines.append(f'#define GP50_FEATURE_COUNT {len(features)}u')
    lines.append('static const gp50_component_descriptor gp50_component_table[] = {')
    for m in components:
        h = m['host']
        if m['abi'] == 3:
            name, h = f'gp50_sdk_feature_{m["id"]}', h or {'selector': 0, 'set_bytes': 0, 'max_reply_bytes': 0}
            get, sett = (name + '_get' if 'get' in m['callbacks'] else '0'), (name + '_set' if 'set' in m['callbacks'] else '0')
            lines.append(f' {{ {h["selector"]}, {h["set_bytes"]}, {h["max_reply_bytes"]}, {name}_init, {name}_tick, {get}, {sett} }},')
            continue
        if m['abi'] == 2:
            name = f'gp50_sdk_state_{m["id"]}'
            callbacks = ', '.join(name+'_'+r if r != 'set' or m['callbacks'][r] else '0' for r in ('init', 'tick', 'get', 'set'))
        else:
            callbacks = ', '.join(m['callbacks'][r] or '0' for r in ('init', 'tick', 'get', 'set'))
        lines.append(f' {{ {h["selector"]}, {h["set_bytes"]}, {h["max_reply_bytes"]}, {callbacks} }},')
    lines += ['};', f'#define GP50_COMPONENT_COUNT {len(components)}u', '']
    ui = [m for m in components if m['callbacks'].get('status')]
    lines.append(f'#define GP50_COMPONENT_UI_COUNT {len(ui)}u')
    if ui:
        lines.append('static const gp50_component_status_fn gp50_component_ui_table[] = {')
        for m in ui:
            name = (f'gp50_sdk_state_{m["id"]}_status' if m['abi'] == 2 else
                    f'gp50_sdk_feature_{m["id"]}_status' if m['abi'] == 3 else m['callbacks']['status'])
            lines.append(f' {name},')
        lines.append('};')
    return '\n'.join(lines)
