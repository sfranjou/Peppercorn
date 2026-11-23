"""Admission warning cost table (MOD036): predicted ARM load of the live chain.

Units: thousandths of the ARM load ratio shown on the home ARM page (raw/262244).
Predicted = BASE + sum over enabled ARM-side groups of cost[group][effect id]
          + PING_PONG when the DLY block is off but Ping Pong is selected (it costs the
            same bypassed, model_matrix_full REVIEW) ; unknown ids add UNKNOWN and set '?'.
Values are the per-model delta over the all-off baseline, rounded UP to 0.001:
stock rows from work/host_effect_control/model_matrix_full/summary.json (MOD002, 2026-10-11),
combined (larger value kept) with the measurements on MOD034 in work/admission/cost_*/ (2026-10-19), which also
cover every custom effect and the modified OCTA (+0.277, MOD004 octave fix). ARM deltas
add within ~0.01 for combined chains (LAB_NOTEBOOK 2026-10-11 combined-mask runs; MOD004
OCTA+Gate+A-Chorus+Ring Echo read 1.04-1.05 against 1.048 predicted). No device access here.
"""
import base64,hashlib,json,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
BASE=477            # all-off baseline on MOD034 (resident adapter + telemetry), work/admission/cost_*
WARN=950            # warn at >= 0.95; inferred deadline ratio 1.0625 (LAB_NOTEBOOK normalization)
UNKNOWN=200         # unmeasured ids (diagnostic Probe/ARM Bench/Probe Out, future effects)
PING_PONG_ID=0x0b000004
ARM_GROUPS=(0,1,6,7,8)   # NR, PRE, MOD, DLY, RVB; DST/AMP/CAB/EQ/N-S run on the coprocessor
MEASURED_RUNS=('cost_g1_001','cost_g1_002','cost_g6_001','cost_g6_002','cost_g7_001')
# Table versions (2026-10-20): v1 = the table in MOD036-MOD040 (must stay byte-identical for their
# reproducible rebuilds); v2 adds Ring Echo measured on MOD038 (cost_g7_002). Images choose with
# "admission_table" in their nds_ui config; use() sets the process-wide active version.
# v3 (2026-10-20) = v2 + SDK estimates (sdk_estimates.json) for SDK effects without a measurement.
# A measurement describes the build that was measured; an image that adds a rebuilt (possibly heavier)
# build of a measured effect names it in its nds_ui config "admission_estimate_overrides" so the table
# takes the estimate instead (estimate_drift() lists candidates, e.g. Afterglow Micro 0.1.1 vs 0.2.x).
RUNS={'v1':MEASURED_RUNS,'v2':MEASURED_RUNS+('cost_g7_002',),'v3':MEASURED_RUNS+('cost_g7_002',),'v4':MEASURED_RUNS+('cost_g7_002',),
      'v5':MEASURED_RUNS+('cost_g7_002',),'v6':MEASURED_RUNS+('cost_g7_002',),'v7':MEASURED_RUNS+('cost_g7_002',),'v8':MEASURED_RUNS+('cost_g7_002',)}
WITH_ESTIMATES={'v3','v4','v5','v6','v7','v8'}
# v4 (2026-10-20) adds the coprocessor: predicted = max(ARM, DSP), both in thousandths of their own
# proxy (DSP deadline measured ~1.025, analysis/firmware/COPRO_BUDGET.md). WITH_DSP versions only.
WITH_DSP={'v4','v5','v6','v7','v8'}
DSP_GROUPS=(2,3,4,5,9)        # DST, AMP, CAB, EQ, N->S
DSP_BASE=2                    # all-off DSP proxy 0.0016 (enable_matrix_001, copro_g*_001), rounded up
DSP_UNKNOWN=300               # unmeasured DST/AMP/EQ ids (heaviest stock model 0.282), sets '?'
DSP_CAB=243                   # any cab (0x0a000022 measured 0.2430; same program for all cabs: I)
DSP_NTOS=750                  # fused GPTC IR512 bound: estimated 0.678 from weighted work vs stock 0.5825; rounded + margin; hardware pending
# v5 (2026-11-08) = v4 with the capture (N->S) DSP cost from hardware: our player measured 0.387 (stock VTSI) and 0.399-0.410
# (high-gain GPTC, parallel branch, silent input = the heavier nonlinear path) on MOD145/MOD146, work/mod14[56]_hw;
# Samples repeat within 0.0007 (fixed-length DSP loops; the simulator varies ~2 % with input), so 450 (closer to
# the measurement) keeps ~10 % over 0.410. v4 keeps 750 so MOD141-MOD146 rebuild byte-identically.
DSP_NTOS_BY_VERSION={'v4':750,'v5':450,'v6':450,'v7':450,'v8':500}
# v8 (2026-11-21) = v7 with the N->S capture reservation 500: a two-curve (GPTC v2) capture measured 0.4035 DSP alone on
# MOD153 vs 0.337 for GPTC v1 (work/mod153_hw/upload_test_*), so with a cab IR about 0.465 > 450.
def dsp_ntos():return DSP_NTOS_BY_VERSION.get(_ACTIVE[0],DSP_NTOS)
# v5 (2026-11-08) also gives the DST Capture effect (sdk/effects/dst_capture, 0x0300007c) its DSP cost: its audio is a
# second 4-partition GPTC capture run inside the N->S program (worst offline 58,139 steps alone, +58,000 in a pair;
# 6.2e-6 per step -> 0.36), counted on the DST group so the pair predicts 2 + 400 + 450 + EQ. Older versions: none.
DSP_SDK_BY_VERSION={'v5':{(2,0x0300007c):400},'v6':{(2,0x0300007c):400},'v7':{(2,0x0300007c):400},'v8':{(2,0x0300007c):400}}
# v6 (2026-11-09) = v5 + capture-pair rules in the refusal (sdk/nds/ui/refuse.c, model_refuse.py): a change that newly
# makes the DST Capture active together with the cab on (1), with N->S off (2) or with a factory (VTSI) N->S capture (3)
# is refused like an overload. v5 images (MOD147/148) keep their behaviour.
CAPTURE_RULES={'v6','v7','v8'}
# v7 (2026-11-09) = v6 + the main chip keeps N->S loaded toward the ARM while a DST Capture is active and N->S is off
# (sdk/nds/ui/refuse.c gp50_link_filter; the player sees N->S parameter 8 = CAPTURE_MAIN_OFF and plays the DST
# capture alone). Rule 2 (N->S off) is dropped: that combination is now valid.
CAPTURE_FORCE={'v7','v8'}
CAPTURE_MAIN_OFF=0xc2f6e979     # float bits (-123.456) in N->S parameter 8 toward the ARM: "main capture off"
DST_CAPTURE_ID=0x0300007c
def capture_rules():return _ACTIVE[0] in CAPTURE_RULES
def capture_force():return _ACTIVE[0] in CAPTURE_FORCE
def capture_violation(mask,ids):
    """0 = allowed; 1 cab on, 2 N->S off, 3 factory (VTSI) N->S capture, while the DST Capture is active."""
    if not (mask>>2&1 and ids[2]==DST_CAPTURE_ID):return 0
    if mask>>4&1:return 1
    if not mask>>9&1:return 0 if capture_force() else 2
    if (ids[9]&0xff)<50:return 3
    return 0
DSP_RUNS=('copro_g2_001','copro_g3_001','copro_g5_001')
LATEST='v3'         # SDK tools (check_effect) report against this; images name their version explicitly
ALL_RUNS=tuple(dict.fromkeys(r for v in RUNS.values() for r in v))+DSP_RUNS
ESTIMATES_JSON=Path(__file__).resolve().parent/'sdk_estimates.json'
RESEARCH_INPUTS=('work/host_effect_control/model_matrix_full/summary.json',)+tuple(
    f'work/admission/{run}/result.json' for run in ALL_RUNS)
# Keep one shared list so already-imported feature metadata follows explicit selection.
DATA_INPUTS=list(RESEARCH_INPUTS)+['sdk/telemetry/nds/sdk_estimates.json']
_MEASUREMENTS=None

def use_measurements(path=None):
    """Select a verified curated snapshot explicitly; None retains live research inputs."""
    global _MEASUREMENTS
    values=None
    if path is not None:
        path=Path(path).resolve()
        if not path.is_relative_to(ROOT):raise ValueError('measurements must reside inside the package')
        bundle=json.loads(path.read_text())
        if bundle.get('schema')!=1 or bundle.get('kind')!='gp50_admission_measurements':
            raise ValueError('unsupported admission measurement bundle')
        inputs=bundle.get('inputs',{})
        if set(inputs)!=set(RESEARCH_INPUTS):raise ValueError('admission measurement input set')
        values={}
        for name,record in inputs.items():
            raw=base64.b64decode(record['content_base64'],validate=True)
            if len(raw)!=record['bytes'] or hashlib.sha256(raw).hexdigest()!=record['sha256']:
                raise ValueError('admission measurement identity: '+name)
            values[name]=json.loads(raw)
    # Commit only after all entries validate; a failed selection changes no state.
    _MEASUREMENTS=values
    DATA_INPUTS[:]=([str(path.relative_to(ROOT))] if values is not None else list(RESEARCH_INPUTS))+['sdk/telemetry/nds/sdk_estimates.json']
    _CACHE.clear()

def _measurement(name):
    return json.loads((ROOT/name).read_text()) if _MEASUREMENTS is None else _MEASUREMENTS[name]

CALIBRATION_MAX=1.41   # check_effect: estimate / measured never above this on the 8 calibration effects
_ACTIVE=['v1'];_CACHE={};_OVERRIDES=set()
def use(version,overrides=()):
    if version not in RUNS:raise ValueError('unknown admission table version '+str(version))
    if overrides and version not in WITH_ESTIMATES:raise ValueError('estimate overrides need a table version with estimates')
    _ACTIVE[0]=version;_OVERRIDES.clear();_OVERRIDES.update(overrides);_CACHE.pop(version,None)
def active():return _ACTIVE[0]+(('+'+'+'.join(sorted(_OVERRIDES))) if _OVERRIDES else '')
def _ceil(x):return max(0,math.ceil(round(x*1000,6)))
def table():
    """{group: [(id, cost)]} in a fixed order, plus provenance rows (active version, cached)."""
    v=_ACTIVE[0]
    if v not in _CACHE:_CACHE[v]=_table(RUNS[v],v in WITH_ESTIMATES)
    return _CACHE[v]
def _table(runs,estimates=False):
    rows=_measurement('work/host_effect_control/model_matrix_full/summary.json')['rows']
    cost={};src={}
    for r in rows:
        g=r['group']
        if g in ARM_GROUPS:k=(g,int(r['model'],16));cost[k]=_ceil(r['arm_delta']);src[k]='model_matrix_full'
    for run in runs:
        res=_measurement(f'work/admission/{run}/result.json')
        assert res['status']=='complete' and res['restored'],run
        for m in res['measurements']:
            if not m.get('model'):continue
            k=({'PRE':1,'MOD':6,'DLY':7}[m['label'].split('_')[0]],int(m['model'],16))
            v=_ceil(m['arm_mean_minus_start_baseline'])
            if k not in src:cost[k]=v;src[k]=run
            else:cost[k]=max(cost[k],v);src[k]+='+'+run   # conservative: larger of matrix and MOD034 runs
    # Long Echo was measured +0.083 on MOD031 (LAB_NOTEBOOK 2026-10-19, granted lease, other conditions); keep the larger.
    k=(7,0x0b0000f4);cost[k]=max(cost[k],83);src[k]+='+MOD031 audio check (0.083)'
    if estimates:   # unmeasured SDK effects: safe-side offline estimate (measured always wins)
        from sdk.telemetry.nds import sdk_estimates
        bad=sdk_estimates.stale()
        if bad:raise ValueError(f'sdk_estimates.json is stale {bad}: run sdk/telemetry/nds/sdk_estimates.py --write')
        for e in json.loads(ESTIMATES_JSON.read_text())['effects']:
            k=(e['group'],int(e['public_id'],16))
            if k not in cost:cost[k]=e['estimate'];src[k]='sdk estimate '+e['effect']+' (check_effect)'
            elif e['effect'] in _OVERRIDES:   # this image carries a rebuilt build of a measured effect
                src[k]=f"sdk estimate {e['effect']} (image override; measured {cost[k]} was an older build)";cost[k]=e['estimate']
    out={g:sorted([(i,c) for (gg,i),c in cost.items() if gg==g]) for g in ARM_GROUPS}
    return out,{f'{g}:{i:#010x}':dict(cost=cost[(g,i)],source=src[(g,i)]) for (g,i) in sorted(cost)}
def with_dsp():return _ACTIVE[0] in WITH_DSP
def dsp_table():
    """{group: [(id, cost)]} for DST/AMP/EQ (DSP proxy thousandths): stock model matrix dsp_delta,
    then the MOD041 runs of our own programs (larger kept). CAB and N->S use DSP_CAB / DSP_NTOS."""
    key='dsp:'+_ACTIVE[0]          # per version (v5 adds SDK DSP costs)
    if key in _CACHE:return _CACHE[key]
    cost={}
    for r in _measurement('work/host_effect_control/model_matrix_full/summary.json')['rows']:
        if r['group'] in (2,3,5):cost[(r['group'],int(r['model'],16))]=_ceil(r['dsp_delta'])
    for run in DSP_RUNS:
        res=_measurement(f'work/admission/{run}/result.json')
        assert res['status']=='complete' and res['restored'],run
        for m in res['measurements']:
            if not m.get('model'):continue
            k=({'DST':2,'AMP':3,'EQ':5}[m['label'].split('_')[0]],int(m['model'],16));v=_ceil(m['dsp_mean_minus_start_baseline'])
            cost[k]=max(cost.get(k,0),v)
    cost.update(DSP_SDK_BY_VERSION.get(_ACTIVE[0],{}))
    _CACHE[key]={g:sorted([(i,c) for (gg,i),c in cost.items() if gg==g]) for g in (2,3,5)}
    return _CACHE[key]
def predict_dsp(mask,ids,tbl=None):
    """(DSP thousandths, unknown): N->S on replaces AMP and CAB; any cab / any N->S slot one cost."""
    tbl=tbl or dsp_table();est=DSP_BASE;unk=0;ntos=mask>>9&1
    for g in (2,3,5):
        if not mask>>g&1 or (ntos and g==3):continue
        d=dict(tbl[g])
        if ids[g] in d:est+=d[ids[g]]
        else:est+=DSP_UNKNOWN;unk=1
    if mask>>4&1 and not ntos:est+=DSP_CAB
    if ntos:est+=dsp_ntos()
    return est,unk
def predict(mask,ids,tbl=None):
    """(thousandths, unknown) for an enable mask and 10 effect ids; with a WITH_DSP table version the
    larger of the ARM and DSP predictions (the one safe-side CPU number)."""
    a,u=predict_arm(mask,ids,tbl)
    if not with_dsp():return a,u
    d,v=predict_dsp(mask,ids);return max(a,d),u|v
def predict_arm(mask,ids,tbl=None):
    tbl=tbl or table()[0];est=BASE;unk=0
    for g in ARM_GROUPS:
        d=dict(tbl[g])
        if mask>>g&1:
            if ids[g] in d:est+=d[ids[g]]
            else:est+=UNKNOWN;unk=1
        elif g==7 and ids[g]==PING_PONG_ID:est+=d[PING_PONG_ID]
    return est,unk
def estimate_drift():
    """SDK effects whose current estimate exceeds the measured table cost by more than the calibration
    spread: the effect has probably become heavier since it was measured (re-measure or drop the row)."""
    measured=dict(((g,i),c) for g,rows in _table(RUNS[LATEST])[0].items() for i,c in rows)
    out=[]
    for e in json.loads(ESTIMATES_JSON.read_text())['effects']:
        m=measured.get((e['group'],int(e['public_id'],16)))
        if m and e['estimate']>CALIBRATION_MAX*m:out.append(dict(effect=e['effect'],measured=m,estimate=e['estimate'],ratio=round(e['estimate']/m,2)))
    return out
def fmt(est):
    h=(est+5)//10;return f'{h//100}.{h%100:02d}'
if __name__=='__main__':
    t,p=table();print(json.dumps(p,indent=1));print({g:len(v) for g,v in t.items()})
