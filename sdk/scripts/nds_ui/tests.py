"""Tiered tests for nds_ui images.

tier a  `nds_ui test <img>`: oracle-vs-emulation cases only for modules whose cache entry is
        missing or stale. Cache key per module = sha256(normalized module bytes, the module's
        oracle files, case generator, harness, stock-API map). Cases are regenerated only
        when the case key changes and are kept gzipped in work/nds_ui/cache/ (not committed).
tier b  `nds_ui gate <img>` (cli.cmd_gate): always, before any image.
tier c  `nds_ui full <img>`: every case + routing + GUI with Ghidra re-assembling the spec and
        requiring identical bytes. Writes full.json.
"""
import gzip, hashlib, json, os, subprocess, time
from pathlib import Path
from . import build, cases as case_gen
from .stock_api import API, JSON as API_JSON

ROOT = build.ROOT; HERE = build.HERE
CACHE = ROOT / 'work/nds_ui/cache'
RESULTS = ROOT / 'work/nds_ui/test_cache.json'      # small, committed: proof records per module key
HARNESS = ROOT / 'scripts/ghidra/NDSUiStudy.java'
CASE_SOURCES = ['scripts/nds_ui/cases.py', 'sdk/telemetry/nds/model.py', 'sdk/telemetry/nds/model_lease.py', 'sdk/telemetry/nds/model_gr.py',
                'sdk/telemetry/nds/model_gr_meter.py', 'sdk/telemetry/nds/model_admission.py', 'sdk/telemetry/nds/model_cpu_pct.py',
                'sdk/telemetry/nds/admission_costs.py',
                'scripts/nds_ui/cases_refuse.py', 'sdk/telemetry/nds/model_refuse.py']


def _sha_files(paths):
    h = hashlib.sha256()
    for p in paths: h.update(p.encode() + b'\0' + (ROOT / p).read_bytes())
    return h.hexdigest()


def case_key():
    from .features import admission
    from sdk.telemetry.nds import admission_costs as AC
    return (_sha_files(CASE_SOURCES + list(admission.DATA_INPUTS)) + AC.active())[:20] if AC.active() == 'v1' else _sha_files(CASE_SOURCES + list(admission.DATA_INPUTS))[:16] + AC.active()


def load_cases():
    """(all cases dict, key, seconds). Regenerates only when the oracle/generator inputs change."""
    key = case_key(); p = CACHE / f'cases-{key}.json.gz'; t = time.time()
    if not p.exists():
        CACHE.mkdir(parents=True, exist_ok=True); data = case_gen.generate()
        from . import cases_refuse; data['cases'] += cases_refuse.generate()   # refuse=1 rows: images with refuse_c only
        tmp = p.with_suffix('.tmp'); tmp.write_bytes(gzip.compress((json.dumps(data, indent=1) + '\n').encode(), 6)); tmp.rename(p)
        for old in CACHE.glob('cases-*.json.gz'):
            if old != p: old.unlink()
        return data, key, round(time.time() - t, 1), True
    return json.loads(gzip.decompress(p.read_bytes())), key, round(time.time() - t, 1), False


def module_keys(cfg):
    gen = ROOT / 'work/nds_ui' / cfg['id']; mods = json.loads((gen / 'modules.json').read_text())
    # The emulator's language semantics are part of every proof (2026-10-19: bmski33 fix).
    lang = ghidra_assets() / 'nds_backend/languages_extended'
    common = _sha_files([str(HARNESS.relative_to(ROOT)), str(API_JSON.relative_to(ROOT))]) + case_key() + hashlib.sha256((lang / 'nds32.sinc').read_bytes() + (lang / 'nds32le.slaspec').read_bytes()).hexdigest()
    out = {}
    for f, m in mods.items():
        mod = build.feature(f)
        oracle = _sha_files(list(mod.ORACLES) + list(getattr(mod, 'DATA_INPUTS', ())))
        out[f] = hashlib.sha256((m['normalized_sha256'] + oracle + common + json.dumps(cfg['segment'], sort_keys=True)).encode()).hexdigest()[:24]
    return out


def _results():
    return json.loads(RESULTS.read_text()) if RESULTS.exists() else {}


def stale_modules(cfg):
    r = _results(); return [f for f, k in module_keys(cfg).items() if r.get(f, {}).get(k, {}).get('status') != 'pass']


def ghidra_assets():
    """Ghidra project/backend live (gitignored) in the main checkout's work/firmware_source."""
    w = ROOT / 'work/firmware_source'
    if (w / 'fixed_extended_export_checkpoint.json').exists() and (w / 'projects').exists(): return w
    common = subprocess.run(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    main = Path(common if os.path.isabs(common) else ROOT / common).resolve().parent
    return main / 'work/firmware_source'


def study_json(cfg, run_dir, cases_path, routing, gui, assemble):
    from .features import gr_meter
    api = {k: (e['address'] if isinstance(e['address'], str) else None) for k, e in API.entries().items()}
    api = {k: v for k, v in api.items() if v}
    r = gr_meter.BAR['radius']; api['expect_bar_radius_calls'] = [f'{r}:0', f'{r}:{API.LV_PART_INDICATOR}']
    seg = cfg['segment']; gen = ROOT / 'work/nds_ui' / cfg['id']
    from .features import legacy_ui_c
    if legacy_ui_c.enabled(cfg):   # MOD055+: the MOD026 leaves the harness models are our relinked C / close stub (proved by verify_nds_generic_image.py --remap)
        lab = json.loads((gen / 'labels.json').read_text())
        for name, sym in {**legacy_ui_c.LINK_ALIASES, 'mod026_window4_close': 'legacy_w4_close'}.items(): api[name] = hex(lab[sym])
    from .features import diagnostics_c
    if diagnostics_c.enabled(cfg):   # MOD056+: the legacy 0x6002 dispatch is our stub (routing stops there; its own routing in review.routing)
        api['mod030_dispatch'] = hex(json.loads((gen / 'labels.json').read_text())['diag_dispatch_asm'])
    st = dict(base=seg['base'], state=seg['state'], state_bytes=seg['state_bytes'], legacy_cache=seg['legacy_cache'], gen=str(gen),
              parent_b=str(gen / 'parent_b.bin'), cases=str(cases_path) if cases_path else None, routing=routing, gui=gui, assemble=assemble, api=api)
    (run_dir / 'study.json').write_text(json.dumps(st, indent=1) + '\n')


def run_ghidra(run_dir, script='NDSUiStudy.java'):
    w = ghidra_assets(); env = os.environ.copy()
    env['JAVA_HOME'] = '/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home'; env['JAVA_TOOL_OPTIONS'] = '-Duser.home=' + str(w / 'home')
    project = json.loads((w / 'fixed_extended_export_checkpoint.json').read_text())['rows'][0]['project']
    jars = list(Path('/opt/homebrew/opt/ghidra/libexec/Ghidra').rglob('*.jar'))
    target = w / 'home/Library/ghidra/ghidra_12.1.4_PUBLIC/osgi/compiled-bundles/991c18c9'
    q = subprocess.run(['/opt/homebrew/opt/openjdk@21/bin/javac', '-proc:none', '-Xlint:none', '-cp', ':'.join(map(str, jars)), '-d', str(target), str(ROOT / 'scripts/ghidra' / script)], capture_output=True, text=True)
    (run_dir / 'javac.log').write_text(q.stdout + q.stderr)
    if q.returncode: raise RuntimeError('Java compilation failed; see ' + str(run_dir / 'javac.log'))
    holder = 'NDSUiHolder_' + str(time.time_ns())
    cmd = ['/opt/homebrew/opt/ghidra/libexec/support/analyzeHeadless', str(w / 'projects'), holder, '-import', str(w / 'nds_inputs/nds_main.bin'),
           '-processor', 'NDS32:LE:32:default', '-noanalysis', '-deleteProject', '-scriptPath', str(ROOT / 'scripts/ghidra'), '-preScript', 'FirmwareSourceLocalNDS.java',
           str(w / 'nds_backend/languages_extended/nds32.ldefs'), '-postScript', 'NDSOriginalProof.java', str(w / 'projects'), project, str(w.parent.parent), script, str(run_dir)]
    v = run_dir / 'verification.json'
    if v.exists(): v.unlink()
    with (run_dir / 'console.log').open('w') as log: subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    if not v.exists(): raise RuntimeError('Ghidra produced no verification.json; see ' + str(run_dir / 'console.log'))
    rep = json.loads(v.read_text())
    if rep.get('status') != 'pass': raise RuntimeError('emulation FAILED: ' + str(rep.get('error')))
    return rep


def _prepare(cfg):
    from .cli import parent_b
    _, regs = parent_b(cfg); g = build.generate(cfg, regs['b']); gen = ROOT / 'work/nds_ui' / cfg['id']
    build.write_outputs(gen, cfg, g, cfg['parent']['label']); (gen / 'parent_b.bin').write_bytes(regs['b'])
    return g


def select(data, modules, quick=0, home=False):
    tags = {build.tag_name(f) for f in modules}
    rows = [c for c in data['cases'] if case_gen.tag(c) & tags and (not c.get('refuse') or 'refuse' in tags) and (c.get('refuse') != 2 or home)]
    if quick and len(rows) > quick:
        step = len(rows) / quick; rows = [rows[int(i * step)] for i in range(quick)]
    return dict(cases=rows, formats=data['formats'] if 'home_meter' in tags else [])


def tier_a(cfg, force=False, quick=0):
    t0 = time.time(); _prepare(cfg); keys = module_keys(cfg); res = _results()
    todo = set(keys) if force else {f for f, k in keys.items() if res.get(f, {}).get(k, {}).get('status') != 'pass'}
    report = dict(tier='a', modules={f: ('run' if f in todo else 'cached') for f in keys}, quick=quick)
    if not todo:
        report.update(status='pass (all modules cached)', seconds=round(time.time() - t0, 1)); return report
    data, ckey, csec, regenerated = load_cases()
    sub = select(data, todo, quick, bool(cfg.get('refusal_home'))); run_dir = ROOT / 'work/nds_ui' / cfg['id'] / 'tier_a'; run_dir.mkdir(parents=True, exist_ok=True)
    cp = CACHE / 'tier_a_cases.json.gz'; cp.write_bytes(gzip.compress(json.dumps(sub).encode(), 1))
    tel = any(build.tag_name(f) == 'telemetry' for f in todo)
    study_json(cfg, run_dir, cp, routing=tel, gui=tel, assemble=False)
    t1 = time.time(); rep = run_ghidra(run_dir); t2 = time.time()
    if not quick:
        for f in todo:
            res.setdefault(f, {})[keys[f]] = dict(status='pass', image=cfg['id'], cases=sum(1 for c in sub['cases'] if build.tag_name(f) in case_gen.tag(c)),
                                                 run=time.strftime('%Y-%m-%d %H:%M'), tier='a')
        RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
    report.update(status='pass' + (' (quick sample: cache not updated)' if quick else ''), execution_cases=rep['execution_cases'], routing_cases=rep['routing_cases'],
                  by_kind=rep['by_kind'], case_key=ckey, cases_regenerated=regenerated,
                  seconds=dict(case_load_or_generate=csec, ghidra=round(t2 - t1, 1), total=round(time.time() - t0, 1)))
    (run_dir / 'tier_a.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def tier_c(cfg, verify_only=False):
    t0 = time.time()
    if verify_only:
        # Review the existing image/artifacts before executing them. Recompiling
        # here would race the independent linked-image checks and discard their
        # frozen inputs.
        from .review import review
        review(cfg)
        from .cli import parent_b
        _, regs = parent_b(cfg)
        (ROOT / 'work/nds_ui' / cfg['id'] / 'parent_b.bin').write_bytes(regs['b'])
    else:
        _prepare(cfg)
    keys = module_keys(cfg)
    data, ckey, csec, regenerated = load_cases()
    run_dir = ROOT / 'work/nds_ui' / cfg['id'] / 'full'; run_dir.mkdir(parents=True, exist_ok=True)
    cp = CACHE / f'cases-{ckey}.json.gz'
    if 'refuse' not in {build.tag_name(f) for f in keys} or not cfg.get('refusal_home'):   # the full set minus rows this image lacks
        cp = CACHE / f'full-{cfg["id"]}.json.gz'; cp.write_bytes(gzip.compress(json.dumps(select(data, keys, home=bool(cfg.get('refusal_home')))).encode(), 1))
    study_json(cfg, run_dir, cp, routing=True, gui=True, assemble=True)
    t1 = time.time(); rep = run_ghidra(run_dir); t2 = time.time()
    gen = ROOT / 'work/nds_ui' / cfg['id']
    full = dict(tier='c', status='pass', image=cfg['id'], code_sha256=json.loads((gen / 'layout.json').read_text())['code_sha256'],
                execution_cases=rep['execution_cases'], routing_cases=rep['routing_cases'], gui_cases=rep['gui_cases'],
                ghidra_assembly_checked=rep['ghidra_assembly_checked'], by_kind=rep['by_kind'], case_key=ckey,
                cases_sha256=hashlib.sha256(gzip.decompress(cp.read_bytes())).hexdigest(), module_keys=keys,
                harness_sha256=hashlib.sha256(HARNESS.read_bytes()).hexdigest(),
                seconds=dict(case_load_or_generate=csec, cases_regenerated=regenerated, ghidra=round(t2 - t1, 1), total=round(time.time() - t0, 1)),
                scope=rep['scope'])
    (gen / 'full.json').write_text(json.dumps(full, indent=2) + '\n')
    res = _results()
    for f, k in keys.items():
        res.setdefault(f, {})[k] = dict(status='pass', image=cfg['id'], cases=sum(1 for c in data['cases'] if build.tag_name(f) in case_gen.tag(c)), run=time.strftime('%Y-%m-%d %H:%M'), tier='c')
    RESULTS.write_text(json.dumps(res, indent=1, sort_keys=True) + '\n')
    return full
