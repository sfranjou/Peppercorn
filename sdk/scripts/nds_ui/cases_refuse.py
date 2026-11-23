"""Oracle cases for the admission refusal (feature refuse_c; oracle sdk/telemetry/nds/model_refuse.py).
Kept apart from cases.generate() so the MOD037 case set (pinned hash) is unchanged; tests.load_cases
appends these. Every row carries refuse=1 (refuse=2: home-title rows, images with "refusal_home" only) so
tests.select() gives them only to images with refuse_c.
Chains are searched around the refusal threshold so both outcomes occur for each gate."""
import random, struct
from sdk.telemetry.nds import admission_costs as AC
from sdk.telemetry.nds import model_refuse as mr

M32 = 0xffffffff


def generate():
    rng = random.Random(0x0f011); tbl = AC.table()[0]; cases = []
    known = {g: [i for i, _ in tbl[g]] for g in AC.ARM_GROUPS}
    def ids_for(ch):
        return [ch.get(g, rng.choice([0, 0x03000000, 0x07000001, 0x0a000001])) for g in range(10)]
    def pick(g):
        r = rng.random()
        return AC.PING_PONG_ID if g == 7 and r < .1 else rng.randrange(2 ** 32) if r < .15 else rng.choice(known[g])
    # chains: every single-step change of interest crosses 1000 for some of them
    mds = [mr.mdata(), mr.mdata(0x3ff, ids_for({0: 0x1b, 1: 0x01000021, 6: 0x04000000, 7: 0x0b000009, 8: 0x0c000000})),
           mr.mdata(0, ids_for({7: AC.PING_PONG_ID})), mr.mdata(0xffffffff, ids_for({}))]
    near = {}
    for _ in range(60000):
        m = rng.randrange(1024); md = mr.mdata(m, ids_for({g: pick(g) for g in AC.ARM_GROUPS}))
        e, _ = AC.predict(m, list(struct.unpack_from('<10I', md, 14)))
        b = e // 25
        if 28 <= b <= 44 and near.get(b, 0) < 6: near[b] = near.get(b, 0) + 1; mds.append(md)
    nows = (0, 10, 0xfffffff0, 0x80000000)
    def base_state():
        w = rng.random() < .3
        return mr.state(valid=1, flags=15, arm=123, frames=64, ui_valid=1, warn=int(w), warn_key=rng.randrange(400) if w else 0,
                        refuse_tick=rng.choice([0, 5, 0xffffff00]), refuse_key=rng.choice([0, 0, 0x800000c9]))
    for md in mds:
        mask = struct.unpack_from('<I', md, 0)[0]
        for group in (0, 1, 2, 4, 6, 7, 8, 9, 10, 31, 0x80000000):
            for requested, cur in ((1, 0), (1, 1), (0, 0), (0, 1), (2, 0)):
                if group >= 10 and (requested, cur) not in ((1, 0),): continue
                s = base_state(); now = rng.choice(nows); after, ret = mr.enable_gate(s, now, md, group, requested, cur)
                cases.append(dict(kind='enable_gate', refuse=1, state=s, legacy=[0] * 16, now=now, mdata=md.hex(), group=group, requested=requested, cur=cur, ret=ret, after=after))
        for group in (0, 1, 3, 4, 6, 7, 8, 9, 12):
            for _ in range(3):
                count = rng.choice([1, 12, 32]); ordinal = rng.choice([0, count - 1, count, rng.randrange(256)])
                new_id = pick(group) if group in AC.ARM_GROUPS else rng.randrange(2 ** 32)
                apply_ret = rng.choice([0, 1]); s = base_state(); now = rng.choice(nows)
                after, ret, applied, qc, qi = mr.select_gate(s, now, md, group, ordinal, count, new_id, apply_ret)
                cases.append(dict(kind='select_gate', refuse=1, state=s, legacy=[0] * 16, now=now, mdata=md.hex(), group=group, ordinal=ordinal, count=count,
                                  new_id=new_id, apply_ret=apply_ret, ret=ret, applied=int(applied), queried_count=int(qc), queried_id=int(qi), after=after))
        for index in (0, 1, 2, 0x80000000):
            assign = [rng.choice([0, 1 << rng.choice(AC.ARM_GROUPS), rng.randrange(1024), mask & rng.randrange(1024), 0xffffffff]) for _ in range(2)]
            s = base_state(); now = rng.choice(nows); after, toggled = mr.footswitch_gate(s, now, md, index, assign)
            cases.append(dict(kind='footswitch_gate', refuse=1, state=s, legacy=[0] * 16, now=now, mdata=md.hex(), index=index, assign=assign, toggled=int(toggled), after=after))
    # capture-pair rules (table v6 only): DST Capture with/without cab, N->S on/off, factory/user N->S slot, every gate
    if AC.capture_rules():
        D = AC.DST_CAPTURE_ID
        for dst_id in (D, 0x03000000):
            for ns_id in (0x0f00004d, 0x0f000000, 0x0f000031, 0x0f000032, 0x0f00004c):
                for mask in (0x000, 0x004, 0x010, 0x014, 0x200, 0x204, 0x210, 0x214, 0x24d, 0x3ff):
                    md = mr.mdata(mask, [0, 0x01000021, dst_id, 0x05000000, 0x0a000022, 0x07000001, 0x04000000, 0x0b000009, 0x0c000000, ns_id])
                    for group in (2, 4, 9, 0):
                        s = base_state(); now = rng.choice(nows); after, ret = mr.enable_gate(s, now, md, group, 1, mask >> group & 1)
                        cases.append(dict(kind='enable_gate', refuse=1, state=s, legacy=[0] * 16, now=now, mdata=md.hex(), group=group, requested=1, cur=mask >> group & 1, ret=ret, after=after))
                    for new_id in (D, 0x03000000):
                        s = base_state(); now = rng.choice(nows)
                        after, ret, applied, qc, qi = mr.select_gate(s, now, md, 2, 5, 14, new_id, 1)
                        cases.append(dict(kind='select_gate', refuse=1, state=s, legacy=[0] * 16, now=now, mdata=md.hex(), group=2, ordinal=5, count=14,
                                          new_id=new_id, apply_ret=1, ret=ret, applied=int(applied), queried_count=int(qc), queried_id=int(qi), after=after))
                    for assign in ([0x004, 0x010], [0x014, 0x200], [0x204, 0]):
                        for index in (0, 1):
                            s = base_state(); now = rng.choice(nows); after, toggled = mr.footswitch_gate(s, now, md, index, assign)
                            cases.append(dict(kind='footswitch_gate', refuse=1, state=s, legacy=[0] * 16, now=now, mdata=md.hex(), index=index, assign=assign, toggled=int(toggled), after=after))
        for key in (0xc0000002, 0xc0000004, 0xc0000006):       # rule texts on the edit page and the home title
            md = mds[0]
            for tick, now in ((10, 10), (10, 2010)):
                s = mr.state(valid=1, flags=15, arm=123, frames=64, ui_valid=1, refuse_tick=tick, refuse_key=key)
                after, events = mr.editor(s, now, 0, 6, 3, 0, 1, md=md)
                cases.append(dict(kind='editor', refuse=1, state=s, legacy=[0] * 16, now=now, idx=0, group=6, ordinal=3, assign=0,
                                  label=1, after=after, events=events, mdata=md.hex()))
                for mode in (0, 1):
                    s = mr.state(valid=1, flags=15, arm=123, arm_last=173000, arm_peak=200000, frames=64, ui_valid=1, refuse_tick=tick, refuse_key=key)
                    after, text = mr.refresh(s, now, mode, md=md)
                    cases.append(dict(kind='refresh', refuse=2, state=s, legacy=[0] * 16, now=now, mode=mode, mdata=md.hex(), after=after, text=text))
    # edit-page message: pending / expired (boundary 1999/2000, wrap) / already shown, around the warning threshold
    for md in mds[:40]:
        p, u = mr.est_pct(md)
        for key in (0, 0x800000c9, 0x800000ca, 0x80000001):
            for tick, now in ((10, 10), (10, 2009), (10, 2010), (0xffffff00, 0x6cf), (0xffffff00, 0x6d0), (5, 4)):
                for warn, wkey, shownm in ((0, 0, 0), (1, key, 0), (1, p * 2 | u, 0), (0, 0, 1)):
                    for idx, group, ordinal, assign, label in ((0, 6, 3, 0, 1), (0, 1, 15, 0, 1), (0, 6, 3, 1, 1), (0, 6, 3, 0, 0)):
                        s = mr.state(valid=1, flags=15, arm=123, frames=64, ui_valid=1, warn=warn, warn_key=wkey, refuse_tick=tick, refuse_key=key)
                        s[23] = shownm; s[34] = 0x30000000 if shownm else 0
                        after, events = mr.editor(s, now, idx, group, ordinal, assign, label, md=md)
                        cases.append(dict(kind='editor', refuse=1, state=s, legacy=[0] * 16, now=now, idx=idx, group=group, ordinal=ordinal, assign=assign,
                                          label=label, after=after, events=events, mdata=md.hex()))
    # home title: pending / just expired (1999/2000, wrap) / already shown, every DRUM mode
    for md in mds[:12]:
        for key in (0, 0x800000c9, 0x80000001):
            for tick, now in ((10, 10), (10, 2009), (10, 2010), (0xffffff00, 0x6cf), (0xffffff00, 0x6d0), (5, 4)):
                for shown in (0, key, 0x800000ca):
                    for mode in (0, 1, 2, 3):
                        s = mr.state(valid=1, flags=15, arm=123, arm_last=173000, arm_peak=200000, frames=64, ui_valid=1,
                                     refuse_tick=tick, refuse_key=key, home_shown=shown)
                        after, text = mr.refresh(s, now, mode, md=md)
                        cases.append(dict(kind='refresh', refuse=2, state=s, legacy=[0] * 16, now=now, mode=mode, mdata=md.hex(), after=after, text=text))
    return cases
