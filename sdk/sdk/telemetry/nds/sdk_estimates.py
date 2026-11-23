#!/usr/bin/env python3
"""Offline ARM cost estimates of SDK effects for the admission table (table version v3+).

An SDK effect in an ARM group (NR/PRE/MOD/DLY/RVB) that has no pedal measurement enters the CPU
table with its sdk/check_effect.py estimate (ARM_PER_INSTRUCTION x mean interpreter instructions per
block, rounded up; calibrated on 8 effects: never under-predicted, up to ~41 % high) instead of the
unknown +0.200 and '?'. Measured costs always win (admission_costs._table). The safe-side
estimate is enough for unmeasured effects.

Diagnostic effects are excluded: an id shared by several sdk/effects directories (Probe, Probe Out,
ARM Bench/ARM Chain variants) has no single cost.

  python3 sdk/telemetry/nds/sdk_estimates.py --write   # re-run the checks, rewrite sdk_estimates.json
  python3 sdk/telemetry/nds/sdk_estimates.py           # report stale/missing entries (exit 1 if any)

sdk_estimates.json is committed so table builds are reproducible; each entry pins the sha256 of
its effect directory's build inputs (BUILD_INPUTS), so a changed effect shows up as stale here and in the nds_ui gate.
"""
import hashlib, json, subprocess, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
EFFECTS = ROOT / 'sdk/effects'
JSON = Path(__file__).resolve().parent / 'sdk_estimates.json'
ARM_GROUPS = (0, 1, 6, 7, 8)


def candidates():
    """[(name, group, public_id)] for single-id ARM-group SDK effects."""
    rows = []
    for d in sorted(p for p in EFFECTS.iterdir() if (p / 'effect.json').exists()):
        e = json.loads((d / 'effect.json').read_text()); rows.append((d.name, e['group'], int(e['public_id'], 16)))
    shared = {i for i, n in Counter(i for _, _, i in rows).items() if n > 1}
    return [r for r in rows if r[1] in ARM_GROUPS and r[2] not in shared]


BUILD_INPUTS = ('.c', '.h', '.s', '.S', '.json')   # what the effect build compiles/reads; docs and models do not count


def source_sha(name):
    """Fingerprint of the effect's build inputs (sources + effect.json), used only to notice a stale estimate on
    the build computer. READMEs, Python models and other notes are not build inputs and are not hashed."""
    h = hashlib.sha256()
    for p in sorted((EFFECTS / name).rglob('*')):
        if p.is_file() and '__pycache__' not in p.parts and p.suffix in BUILD_INPUTS:
            h.update(str(p.relative_to(EFFECTS)).encode() + b'\0' + p.read_bytes())
    return h.hexdigest()


def load():
    return json.loads(JSON.read_text())['effects'] if JSON.exists() else []


def stale():
    have = {e['effect']: e for e in load()}
    out = []
    for name, g, i in candidates():
        e = have.get(name)
        if e is None: out.append((name, 'missing'))
        elif e['sources_sha256'] != source_sha(name): out.append((name, 'sources changed since estimate'))
        elif (e['group'], int(e['public_id'], 16)) != (g, i): out.append((name, 'group/id changed'))
    return out


def write():
    rows = []
    for name, g, i in candidates():
        r = subprocess.run([sys.executable, '-B', str(ROOT / 'sdk/check_effect.py'), str(EFFECTS / name)], capture_output=True, text=True)
        if r.returncode: raise SystemExit(f'{name}: check_effect failed\n{r.stdout[-2000:]}{r.stderr[-2000:]}')
        c = json.loads((ROOT / 'work/sdk_check' / name / 'check.json').read_text())
        rows.append(dict(effect=name, group=g, public_id=f'{i:#010x}', estimate=round(c['arm_cost_estimate']['mean_based'] * 1000),
                         instructions_mean=c['interpreter']['instructions_mean'], factor=c['arm_cost_estimate']['factor'],
                         sources_sha256=source_sha(name)))
    JSON.write_text(json.dumps(dict(schema=1, units='thousandths of the ARM ratio (as admission_costs)', generator='sdk/telemetry/nds/sdk_estimates.py --write',
                                    effects=rows), indent=1) + '\n')
    return rows


if __name__ == '__main__':
    if '--write' in sys.argv: print(json.dumps(write(), indent=1))
    s = stale(); print(json.dumps(dict(stale=s), indent=1)); sys.exit(1 if s else 0)
