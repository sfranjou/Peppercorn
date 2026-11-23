"""Oracle for the admission refusal (sdk/nds/ui/refuse.c, feature refuse_c). No IO besides the
admission cost table. State: model_cpu_pct's 37 words + [37] refusal tick, [38] refusal key
((pct*2|unknown)|0x80000000, 0 = none), [39] key shown on the home title (0 = none). Design: analysis/firmware/ADMISSION_REFUSAL.md."""
import struct
from sdk.telemetry.nds import admission_costs as AC
from sdk.telemetry.nds import model_cpu_pct as mc
from sdk.telemetry.nds import model_gr as mg
from sdk.telemetry.nds.model_cpu_pct import W, K, WARN_PCT, mdata, est_pct, meter_value  # noqa: F401
REFUSE = 1000
SHOW = 2000
T, R, H = 37, 38, 39
PRESET_NAME = 'PRESET 13'   # harness stub text for preset_name_text (0x472b8)
M32 = 0xffffffff


def state(**kw):
    s = mc.state(**{k: v for k, v in kw.items() if k not in ('refuse_tick', 'refuse_key')})
    return s + [0] * (37 - len(s)) + [kw.get('refuse_tick', 0), kw.get('refuse_key', 0), kw.get('home_shown', 0)]


def _split(md):
    return struct.unpack_from('<I', md, 0)[0], list(struct.unpack_from('<10I', md, 14))


def _refuse(s, now, before, after, unk):
    if after < REFUSE or after <= before: return False
    s[T] = now & M32; s[R] = (((after + 9) // 10) * 2 | unk) | 0x80000000
    return True


def _rule(s, now, mask0, mask1, ids0, ids1):
    """Capture-pair rules (table v6, sdk/nds/ui/refuse.c refuse_rule): refuse a change that newly creates a violation."""
    if not AC.capture_rules(): return False
    v = AC.capture_violation(mask1, ids1)
    if not v or AC.capture_violation(mask0, ids0): return False
    s[T] = now & M32; s[R] = 0xc0000000 | v << 1
    return True


def enable_gate(s, now, md, group, requested, cur):
    """0x473f6 gate: returns (state, a0). a0 == requested means "refused (looks unchanged)"."""
    s = s.copy(); mask, ids = _split(md)
    if group < 10 and requested and not cur:
        if _rule(s, now, mask, (mask | 1 << group) & M32, ids, ids): return s, requested
        b, _ = AC.predict(mask, ids); a, u = AC.predict(mask | 1 << group, ids)
        if _refuse(s, now, b, a, u): return s, requested
    return s, cur


def select_gate(s, now, md, group, ordinal, count, new_id, apply_ret):
    """0x475de gate: (state, a0, apply called, count queried, id queried)."""
    s = s.copy(); mask, ids = _split(md); qc = qi = False
    if group < 10 and group not in (4, 9):
        qc = True
        if ordinal < count:
            qi = True; ids2 = ids.copy(); ids2[group] = new_id
            if _rule(s, now, mask, mask, ids, ids2): return s, 0, False, qc, qi
            b, _ = AC.predict(mask, ids); a, u = AC.predict(mask, ids2)
            if _refuse(s, now, b, a, u): return s, 0, False, qc, qi
    return s, apply_ret, True, qc, qi


def footswitch_gate(s, now, md, index, assign):
    """0x47456 gate: (state, toggle called)."""
    s = s.copy(); mask, ids = _split(md)
    if index < 2 and assign[index]:
        if assign[index] & ~mask & 0x14 and _rule(s, now, mask, mask ^ assign[index], ids, ids): return s, False
        b, _ = AC.predict(mask, ids); a, u = AC.predict(mask ^ assign[index], ids)
        if _refuse(s, now, b, a, u): return s, False
    return s, True


def editor(s, now, idx, group, ordinal, assign, label=1, md=None):
    """model_cpu_pct.editor plus the pending-refusal message (first, while younger than SHOW)."""
    if assign or (idx < 10 and group == 1 and ordinal == mg.GR_ORDINAL) or not s[R]:
        return mc.editor(s, now, idx, group, ordinal, assign, label, md)
    s = s.copy(); ev = []
    if s[23]:
        if s[34]: ev.append('delete')
        s[34] = 0; s[23] = 0; ev.append('restore')
    if not label: return s, ev
    if (now - s[T]) & M32 >= SHOW:
        s[R] = 0; s2, ev2 = mc.editor(s, now, idx, group, ordinal, assign, label, md); return s2, ev + ev2
    if s[W] and s[K] == s[R]: return s, ev
    key = s[R]; ev.append('warn=' + _full_text(key)); s[W] = 1; s[K] = key
    return s, ev


RULE_TEXT = {1: 'CAB OFF FIRST', 2: 'N->S ON FIRST', 3: 'N->S NOT LTTC'}


def _full_text(key):
    if AC.capture_rules() and key & 0x40000000: return RULE_TEXT.get(key >> 1 & 3, 'N->S NOT LTTC')
    return f'CPU FULL {(key & 0x7fffffff) >> 1}%' + ('?' if key & 1 else '')


def refresh(s, now, mode, md=None):
    """Home-refresh router (nds_refresh2) with the refusal message first. (state, text or None)."""
    s = s.copy(); key = s[R]
    if key and (now - s[T]) & M32 < SHOW:
        if s[H] != key: s[H] = key; return s, _full_text(key)
        return s, None
    if s[H]:
        s[H] = 0
        if mode == 0: return s, PRESET_NAME
    return mc.refresh(s, now=now, mode=mode, md=md)
