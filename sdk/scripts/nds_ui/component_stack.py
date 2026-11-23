"""Conservative callback stack estimates over final linked C instructions.

Accept closed direct/constant-long-call paths with static compiler frame sizes. Unknown
frames, indirect transfers and recursion are unresolved, never assigned zero.
The result excludes framework callers, asynchronous interrupts and stock services.
"""
import re


class StackUnresolved(ValueError):
    pass


def _closed_long_calls(fn):
    """Resolve constants only within a straight-line block of final code.

    Branch targets and every control transfer kill facts. Unknown instructions
    kill all facts too; no ABI register-preservation or memory contents assumed.
    Instruction addresses are mandatory: text alone cannot detect block entries.
    """
    texts = fn['instructions']
    addresses = fn.get('instruction_addresses', ())
    if len(addresses) != len(texts) or len(set(addresses)) != len(addresses):
        return texts
    entries = set()
    for text in texts:
        op, *tail = text.strip().split(None, 1)
        if op.startswith('b') or op in ('j', 'j8', 'jal'):
            match = re.search(r'(?:^|[,\s])(?:0x)?([0-9a-f]+)(?: <[^>]+>)?$', tail[0] if tail else '')
            if match:
                entries.add(int(match[1], 16))
    values, result = {}, []
    reg = r'(\$(?:r[0-9]+|sp|lp|gp|fp))'
    immediate = r'#?(-?(?:0x[0-9a-f]+|[0-9]+))'
    for at, text in zip(addresses, texts):
        if at in entries:
            values.clear()
        op, *tail = text.strip().split(None, 1)
        args = tail[0] if tail else ''
        converted = text
        target_reg = args
        if op == 'jral':
            conventional = re.fullmatch(r'\$lp,\s*' + reg, args)
            if conventional:
                target_reg = conventional[1]
        if op in ('jral', 'jral5', 'jr', 'jr5') and target_reg in values:
            target = values[target_reg]
            # Resolving an internal computed jump would introduce a block entry
            # not present in the direct-branch scan. Keep it unresolved rather
            # than carrying constants across an unmodelled incoming edge.
            internal_jump = (op in ('jr', 'jr5') and
                             fn['address'] <= target < fn['address'] + fn['size'])
            if not internal_jump:
                converted = ('jal' if op.startswith('jral') else 'j') + f' {target:x}'
        result.append(converted)
        one = re.fullmatch(reg + r',\s*' + immediate, args)
        two = re.fullmatch(reg + r',\s*' + reg, args)
        three = re.fullmatch(reg + r',\s*' + reg + r',\s*' + immediate, args)
        if op in ('movi', 'movi55', 'movi45', 'sethi') and one:
            dest, raw = one.groups()
            value = int(raw, 0) if 'x' in raw else int(raw)
            values[dest] = ((value << 12) if op == 'sethi' else value) & 0xffffffff
        elif op in ('mov', 'mov55') and two:
            dest, source = two.groups()
            if source in values:
                values[dest] = values[source]
            else:
                values.pop(dest, None)
        elif op in ('ori', 'addi') and three:
            dest, source, raw = three.groups()
            value = int(raw, 0) if 'x' in raw else int(raw)
            if source in values:
                values[dest] = ((values[source] | value) if op == 'ori' else (values[source] + value)) & 0xffffffff
            else:
                values.pop(dest, None)
        else:
            values.clear()
    return result


def sdk_services():
    """Public ABI 3 service names (sdk/nds/components/gp50.h). Their own C frames are measured; the stock routines
    they call are the platform boundary and are excluded (as every other stock service is), recorded per callback."""
    from pathlib import Path
    text = (Path(__file__).resolve().parents[2] / 'sdk/nds/components/gp50.h').read_text()
    return set(re.findall(r'^\w[\w ]*?\b(gp50_\w+)\(', text, re.M))


def measure_callbacks(components, functions, services=frozenset()):
    starts = {}
    excluded = {}
    for name, fn in functions.items():
        starts.setdefault(fn['address'], []).append(name)
    memo = {}

    def visit(name, active, platform=False):
        if name in active:
            raise StackUnresolved('recursive callback path: ' + ' -> '.join((*active, name)))
        if (name, platform) in memo:
            return memo[name, platform]
        fn = functions.get(name)
        if fn is None or type(fn.get('frame')) is not int or fn['frame'] < 0:
            raise StackUnresolved('missing/unbounded static frame: ' + name)
        callees = []
        for text in _closed_long_calls(fn):
            op, *rest = text.strip().split(None, 1)
            args = rest[0] if rest else ''
            if op in ('ret', 'ret5') or op in ('jr', 'jr5') and args == '$lp':
                continue
            if op.startswith(('jral', 'jr', 'ifcall')):
                raise StackUnresolved('indirect callback transfer: ' + name + ': ' + text)
            branch = op.startswith('b') and op not in ('bset', 'bclr', 'btgl', 'btst', 'bmski33', 'bitci', 'bitc', 'bse', 'bsp')   # bit ops, not branches
            if op not in ('jal', 'j', 'j8') and not branch:
                continue
            target_args = args.rsplit(',', 1)[-1].strip() if branch else args
            match = re.fullmatch(r'(?:0x)?([0-9a-f]+)(?: <([^>]+)>)?', target_args)
            if not match:
                raise StackUnresolved('unknown direct callback transfer: ' + name + ': ' + text)
            target = int(match[1], 16)
            if op != 'jal' and fn['address'] <= target < fn['address'] + fn['size']:
                continue
            candidates = starts.get(target, [])
            label = match[2]
            callee = label if label in candidates else candidates[0] if len(candidates) == 1 else None
            if callee is None and platform and not candidates:
                excluded.setdefault(name, set()).add(f'{target:#x}')
                continue                                           # stock service called by an SDK service
            if callee is None:
                raise StackUnresolved('unresolved callback target: ' + name + ': ' + text)
            callees.append(visit(callee, (*active, name), platform or callee in services))
        # Count full frames even for tail transfers; safe overestimate.
        memo[name, platform] = fn['frame'] + max(callees, default=0)
        return memo[name, platform]

    rows = []
    for component in components:
        budget = component['resources']['stack_bytes']
        callbacks = list(component['callbacks'].items())
        if component.get('persistence'):
            callbacks += [('preset_'+role, component['persistence'][role]) for role in ('defaults','load','save')]
        for role, name in callbacks:
            if name is None:
                continue
            try:
                size = visit(name, ())
                row = dict(component=component['id'], role=role, symbol=name,
                           declared_bytes=budget, callback_path_bytes=size,
                           status='pass' if size <= budget else 'over_budget')
                rows.append(row)
            except StackUnresolved as error:
                rows.append(dict(component=component['id'], role=role, symbol=name,
                                 declared_bytes=budget, status='unresolved', reason=str(error)))
    if excluded:   # one summary row: SDK service -> stock routines left to the platform boundary
        rows.append(dict(component='$platform', role='excluded_stock_services', status='pass',
                         services={k: sorted(v) for k, v in sorted(excluded.items())}))
    return rows


def check_build(build, nm_tool):
    """Read a linked build and return a conservative callback-budget report."""
    import bisect
    import hashlib
    import json
    from pathlib import Path
    import subprocess
    build = Path(build).resolve()
    c = build/'c/linked'
    elfs = sorted(c.glob('*.elf'))
    if len(elfs) != 1:
        raise ValueError('expected exactly one linked ELF in ' + str(c))
    elf = elfs[0]
    inputs = [elf, c/'component_inputs.json', build/'c_spec.tsv']
    frames = {}
    for path in sorted(c.glob('*.su')):
        inputs.append(path)
        for line in path.read_text().splitlines():
            source, count, kind = line.split('\t')
            frames.setdefault(source.split(':')[-1], set()).add((int(count), kind))
    raw = subprocess.check_output([str(nm_tool), '-S', str(elf)], text=True)
    functions = {}
    duplicate = set()
    for line in raw.splitlines():
        bits = line.split()
        if len(bits) != 4 or bits[2] not in ('t', 'T'):
            continue
        at, size, _, name = bits
        if name in functions:
            duplicate.add(name)
        claims = frames.get(name) or frames.get(re.sub(r'\.\d+$', '', name), set())   # GCC clones: nm 'f.constprop.0', .su 'f.constprop'
        frame = next(iter(claims))[0] if len(claims) == 1 and next(iter(claims))[1] == 'static' else None
        functions[name] = dict(address=int(at, 16), size=int(size, 16), frame=frame, instructions=[])
    instructions = []
    for line in (build/'c_spec.tsv').read_text().splitlines():
        at, size, text = line.split('\t', 2)
        instructions.append((int(at, 16), text))
    instructions.sort()
    addresses = [at for at, _ in instructions]
    for name, fn in functions.items():
        lo = bisect.bisect_left(addresses, fn['address'])
        hi = bisect.bisect_left(addresses, fn['address']+fn['size'])
        fn['instructions'] = [text for _, text in instructions[lo:hi]]
        fn['instruction_addresses'] = addresses[lo:hi]
        if name in duplicate or not fn['instructions']:
            fn['frame'] = None
    rows = measure_callbacks(json.loads((c/'component_inputs.json').read_text()), functions, sdk_services())
    report = dict(status='pass' if rows and all(r['status']=='pass' for r in rows) else 'fail', callbacks=rows,
                  inputs={str(q.relative_to(build)):hashlib.sha256(q.read_bytes()).hexdigest() for q in inputs},
                  limits=['Compiler static frames plus direct/straight-line constant long calls; tail frames conservatively summed',
                          'Excludes framework callers, asynchronous interrupts and unmodeled stock services',
                          'No execution time, interrupt latency, mutable-state or hardware acceptance proof'])
    return report
