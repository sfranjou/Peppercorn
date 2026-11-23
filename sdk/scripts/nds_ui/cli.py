import argparse, fcntl, json, time
from contextlib import contextmanager
from pathlib import Path
from . import build
ROOT = build.ROOT
def load_cfg(p):
    p = Path(p)
    if not p.exists(): p = build.HERE / 'images' / (str(p) + '.json')
    return json.loads(p.read_text())
def parent_b(cfg):
    from firmware_verify import decode, require, sha
    img = (ROOT / cfg['parent']['image']).read_bytes()
    require(sha(img) == cfg['parent']['sha256'], 'parent identity ' + cfg['parent']['image'])
    regions, _ = decode(img); return img, {r: v for r, _, v in regions}
def gen_dir(cfg): return ROOT / 'work/nds_ui' / cfg['id']
def cmd_gen(cfg):
    t = time.time(); _, regs = parent_b(cfg); g = build.generate(cfg, regs['b'])
    lay = build.write_outputs(gen_dir(cfg), cfg, g, cfg['parent']['label'])
    print(json.dumps(dict(out=str(gen_dir(cfg).relative_to(ROOT)), end=hex(lay['end']), bytes=lay['end'] - lay['base'],
                          instructions=lay['instructions'], patches=len(g['patches']), code_sha256=lay['code_sha256'],
                          seconds=round(time.time() - t, 2)), indent=1))
    return g
@contextmanager
def image_lock(cfg):
    """CLI generation/review commands share mutable per-image compiler outputs."""
    folder = ROOT / 'work/nds_ui/.locks'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / (cfg['id'] + '.lock')).open('a') as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Waiting for image workspace lock: ' + cfg['id'], flush=True)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

def main(argv):
    ap = argparse.ArgumentParser(prog='nds_ui')
    ap.add_argument('command', choices=['gen', 'image', 'gate', 'test', 'full', 'cases'])
    ap.add_argument('config'); ap.add_argument('--quick', type=int, default=0)
    ap.add_argument('--force', action='store_true'); ap.add_argument('--verify-only', action='store_true')
    a = ap.parse_args(argv); cfg = load_cfg(a.config)
    with image_lock(cfg):
        return dispatch(a, cfg)

def dispatch(a, cfg):
    from sdk.telemetry.nds import admission_costs as AC
    AC.use(cfg.get('admission_table', 'v1'), cfg.get('admission_estimate_overrides', ()))   # cost table version (+ estimate overrides) baked into this image
    if a.command == 'gen': cmd_gen(cfg); return 0
    if a.command == 'image': cmd_image(cfg, a.verify_only); return 0
    if a.command == 'gate': return cmd_gate(cfg)
    from . import tests
    if a.command == 'test': print(json.dumps(tests.tier_a(cfg, force=a.force, quick=a.quick), indent=1)); return 0
    if a.command == 'full': print(json.dumps(tests.tier_c(cfg, verify_only=a.verify_only), indent=1)); return 0
    if a.command == 'cases':
        d, key, sec, regen = tests.load_cases(); print(json.dumps(dict(key=key, cases=len(d['cases']), formats=len(d['formats']), seconds=sec, regenerated=regen))); return 0
    raise SystemExit('not implemented yet: ' + a.command)
def cmd_image(cfg, verify_only=False):
    from . import image
    t = time.time(); img, man, g = image.build_image(cfg, verify_only=verify_only)
    # Keep review metadata bound to the exact successful image generation.
    build.write_outputs(gen_dir(cfg), cfg, g, cfg["parent"]["label"])
    print(json.dumps(dict(image=man['image'], image_sha256=man['image_sha256'], version=man['version'],
                          hooks=len(man['declared']['hooks']), bound=len(man['declared']['bound']), version_bytes=len(man['declared']['version']),
                          segment=man['declared']['segment'], seconds=round(time.time() - t, 2)), indent=1))
    return man
def cmd_gate(cfg):
    """Tier b: generate, build (or verify the existing image), independent review, routing,
    stock-API pins, and report which modules lack a passing tier-a result for their bytes."""
    from . import review, tests
    t0 = time.time(); cmd_gen(cfg); t1 = time.time()
    img = ROOT / cfg['output'] / cfg['name']
    man = cmd_image(cfg, verify_only=img.exists()); t2 = time.time()
    rep = review.review(cfg); t3 = time.time()
    stale = tests.stale_modules(cfg)
    rep.update(tier='b', modules_needing_tier_a=stale, seconds=dict(generate=round(t1 - t0, 2), image=round(t2 - t1, 2), review_and_routing=round(t3 - t2, 2), total=round(t3 - t0, 2)))
    out = gen_dir(cfg) / 'gate.json'; out.write_text(json.dumps(rep, indent=2) + '\n'); print(json.dumps(rep, indent=1))
    return 0
