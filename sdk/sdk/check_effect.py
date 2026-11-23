#!/usr/bin/env python3
"""One-command offline check for an SDK effect: build, native tests, interpreter run, cost.

  python3 sdk/check_effect.py sdk/effects/<name> [--blocks 200]

Steps (stops at the first failure):
 1. sdk/build_effect.py -> work/<name>/build (record, descriptor, all conformance gates).
 2. every test_*.c in the effect directory: clang -O2, UBSan, -Wall -Werror; must exit 0.
 3. built Thumb payload on the project's interpreter (sdk/run_effect.py): init with catalog
    defaults, then N 64-frame blocks of a test signal (decaying bursts + silence); output must
    stay finite. Reports instructions per block.
 4. ARM cost estimate = ARM_PER_INSTRUCTION x mean instructions/block, rounded up to 0.001.
    Calibrated 2026-10-19 on 7 effects with interpreter counts and pedal measurements (stock
    Pitch/OCTA, modified OCTA, Long Echo, Slap Echo, Tail Doubler, GR Comp, Afterglow Micro): 1.0e-5
    never under-predicted, over-predicts by up to ~41 % (Afterglow 0.1.1; safe side). Not a timing proof.
 5. admission (latest table version, sdk/telemetry/nds/admission_costs.py): the effect's table
    cost and its source (pedal measurement, or the SDK estimate from sdk_estimates.json, v3+);
    a drift warning when this estimate exceeds the measured cost by more than the calibration
    spread. Not in the table: run `sdk/telemetry/nds/sdk_estimates.py --write` so the next image
    (table v3+) counts the estimate instead of unknown (+0.200, '?').
Writes work/sdk_check/<name>/{build,check.json} (never the tracked work/<name>/build dirs).
No device access, no image is built.
"""
import argparse,json,math,os,struct,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;sys.path[:0]=[str(ROOT),str(ROOT/'sdk')]
ARM_PER_INSTRUCTION=1.0e-5
TAIL_ACCESS_COST=2.05e-4   # ARM load per 16-bit access to 0x29xxxxxx RAM (LOOPER_MEMORY.md, scattered read+write)
CALIBRATION=[  # (effect, mean instructions per 64-frame block, measured ARM delta)
 ('Pitch (stock)',17364,0.167),('OCTA (stock)',17362,0.168),('OCTA B640 (MOD004)',27628,0.277),
 ('Long Echo',9674,0.083),('Slap Echo',9519,0.083),('Tail Doubler',10290,0.085),('GR Comp',6457,0.050),('Afterglow Micro 0.1.1 (installed)',9282,0.066)]
def signal(t):
    p=t%2205                      # 50 ms period: 10 ms decaying burst, 40 ms silence
    if p>=441:return 0.0
    return (0.5 if (t//23)&1 else -0.5)*(1-p/441)
def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('effect',type=Path);ap.add_argument('--blocks',type=int,default=200);a=ap.parse_args()
    src=a.effect.resolve();spec=json.loads((src/'effect.json').read_text());name=src.name
    out=ROOT/'work/sdk_check'/name;build=out/'build';out.mkdir(parents=True,exist_ok=True);report=dict(effect=name,public_id=spec['public_id'],group=spec['group'])
    # 1. build
    r=subprocess.run([sys.executable,'-B',str(ROOT/'sdk/build_effect.py'),str(src),'--out',str(build)],capture_output=True,text=True)
    if r.returncode:print(r.stdout+r.stderr);sys.exit('build failed')
    man=json.loads((build/'manifest.json').read_text());report['build']={k:man.get(k) for k in ('payload_bytes','bss_bytes','slot_bytes','tail') if k in man}
    # 2. native tests
    report['native_tests']=[]
    for t in sorted(src.glob('test_*.c')):
        exe=Path(tempfile.mkdtemp())/t.stem
        base=['clang','-std=c11','-O2','-ffp-contract=off','-Wall','-Wextra','-Werror','-fsanitize=undefined','-fno-sanitize-recover=all','-I',str(ROOT/'sdk/resources'),'-I',str(ROOT/'sdk/include'),'-I',str(src)]
        q=subprocess.run(base+[str(ROOT/'sdk/resources/gp50_resources.c'),str(ROOT/'sdk/resources/gp50_resident.c'),str(t),'-o',str(exe),'-lm'],capture_output=True,text=True)
        if q.returncode:q=subprocess.run(base+[str(t),'-o',str(exe),'-lm'],capture_output=True,text=True)
        if q.returncode:print(q.stderr);sys.exit('native test does not compile: '+t.name)
        p=subprocess.run([str(exe)],capture_output=True,text=True,timeout=600)
        report['native_tests'].append(dict(test=t.name,exit=p.returncode))
        if p.returncode:print(p.stdout+p.stderr);sys.exit('native test failed: '+t.name)
    # 3. interpreter
    import run_effect
    params=[float(p['default']) for p in spec['parameters']]+[0.0]*(8-len(spec['parameters']))
    extra=()
    if spec.get('looper_ring'):   # empty stock looper with the V1.1.0 signature + its RAM, so the ring path is costed
        extra=((0x29000000,bytearray(882048)),)
    if spec.get('tail_region'):   # RAM above the looper's range (LOOPER_MEMORY.md): 166,528 bytes
        extra=extra+((0x290d7580,bytearray(166528)),)
    if spec.get('copro'):         # coprocessor data cells D[0..0xfff] (the ARM side only writes its group's cells)
        extra=extra+((0x28000000,bytearray(0x4000)),)
    runner=run_effect.OverlayRunner.from_build(build,extra)
    if spec.get('looper_ring'):
        o=0x20003a4c-run_effect.RAM;runner.cpu.ram[o:o+2]=b'\0\0';struct.pack_into('<II',runner.cpu.ram,o+0x28,0x29000000,441024)
    runner.init(params)
    peak=0.0
    for b in range(a.blocks):
        got=runner.process([(signal(b*64+i),)*2 for i in range(64)],params)
        for l,rr in got:
            if not (math.isfinite(l) and math.isfinite(rr)):sys.exit(f'non-finite output in block {b}')
            peak=max(peak,abs(l),abs(rr))
    steps=runner.process_steps;mean=sum(steps)/len(steps)
    if spec.get('copro',{}).get('stock_program')=='eq':   # end-to-end: these cells through the stock EQ program
        from sdk import eq_chain
        report['eq_chain']=[]
        for setting in spec.get('chain_settings',[params]):   # each setting: fresh load, init, three blocks
            mem=bytearray(0x4000);r2=run_effect.OverlayRunner.from_build(build,((0x28000000,mem),));st=[float(v) for v in setting]+[0.0]*(8-len(setting));r2.init(st)
            for b in range(3):r2.process([(signal(b*64+i),)*2 for i in range(64)],st)
            report['eq_chain'].append(dict(setting=setting,**eq_chain.check(bytes(mem),spec,st,(build/'secondary.bin').read_bytes())))
    if spec.get('looper_ring'):report['looper_ring_written_cells']=sum(1 for i in range(0,882048,2) if extra[0][1][i] or extra[0][1][i+1])
    report['interpreter']=dict(blocks=a.blocks,instructions_mean=round(mean,1),instructions_max=max(steps),output_peak=round(peak,4))
    # 4. cost
    # Tail-region RAM is slow (measured 2.05e-4 ARM per 16-bit access, LOOPER_MEMORY.md): the effect declares its
    # accesses per block ("tail_accesses_per_block") and they are added on top of the instruction-count estimate.
    surcharge=TAIL_ACCESS_COST*int(spec.get('tail_accesses_per_block',0)) if spec.get('tail_region') else 0.0
    est=math.ceil((ARM_PER_INSTRUCTION*mean+surcharge)*1000)/1000;worst=math.ceil((ARM_PER_INSTRUCTION*max(steps)+surcharge)*1000)/1000
    report['arm_cost_estimate']=dict(mean_based=est,worst_block_based=worst,factor=ARM_PER_INSTRUCTION,calibration=CALIBRATION,
        note='Instruction count only; external tail-RAM accesses, flash wait states and interrupts are folded into the factor. Measure on the pedal before relying on it.')
    # 5. admission table
    from sdk.telemetry.nds import admission_costs as AC
    AC.use(AC.LATEST)
    try:tbl,prov=AC.table()
    except ValueError as error:  # a new/changed effect is not in sdk_estimates.json yet: this check is what produces it
        if 'sdk_estimates.json is stale' not in str(error):raise
        report['admission']=dict(table_version=AC.LATEST,in_table=False,estimate_pending=str(error),
            note='Run sdk/telemetry/nds/sdk_estimates.py --write to add this estimate to the admission table.')
        (out/'check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2));return
    pid=int(spec['public_id'],16);g=spec['group']
    known=dict(tbl.get(g,[])).get(pid);source=prov.get(f'{g}:{pid:#010x}',{}).get('source')
    heavy=AC.BASE+sum(max(c for _,c in tbl[x]) for x in AC.ARM_GROUPS if x!=g)
    measured=dict(AC._table(AC.RUNS[AC.LATEST])[0].get(g,[])).get(pid);drift=None
    if measured and est*1000>AC.CALIBRATION_MAX*measured:
        drift=f'estimate {est:.3f} > {AC.CALIBRATION_MAX} x measured {measured/1000:.3f}: heavier than the measured build; an image adding this build must list it in "admission_estimate_overrides" (table {AC.LATEST})'
    report['admission']=dict(table_version=AC.LATEST,in_table=known is not None,table_cost=None if known is None else known/1000,table_source=source,drift_warning=drift,
        worst_stock_chain_with_this=round((heavy+(known if known is not None else est*1000))/1000,3),warn_at=AC.WARN/1000,
        note='Worst chain = all-off base + the heaviest model of every other ARM group + this effect.')
    (out/'check.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
