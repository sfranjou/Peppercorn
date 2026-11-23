"""Name constant stock call targets before compilation, permitting direct jal.

Only preprocessed StockIo calls to indexed original function entries qualify.
Arguments, return casts, dynamic targets and memory addresses remain unchanged.
The linker binds the names to the same original entry addresses (including any
entry redirects). Opt in per candidate; earlier build recipes remain unchanged.
"""
import re


def rewrite(text, allowed):
    targets = set()

    def replacement(match):
        address = int(match['address'], 16)
        if address not in allowed:
            return match[0]
        targets.add(address)
        cast = '(uint32_t)(uintptr_t)' if match['prefix'].startswith('stock_call_') else ''
        return match['prefix'] + cast + f'gp50_absolute_{address:x}'

    # STOCK_CALL / STOCK_CALL0 after preprocessing.
    text = re.sub(r'(?P<prefix>\(stock_fn_t\)\s*\(uintptr_t\)\s*\()'
                  r'(?P<address>0x[0-9a-fA-F]+)\b', replacement, text)
    # Hard-float helpers retain their explicit argument/return conversions.
    text = re.sub(r'(?P<prefix>\bstock_call_(?:f0|rf2|rf|f3|f)\('
                  r'[^,;{}]+,\s*\(*\s*)'
                  r'(?P<address>0x[0-9a-fA-F]+)\b', replacement, text)
    declarations = ''.join(f'extern unsigned long gp50_absolute_{a:x}();\n'
                           for a in sorted(targets))
    return declarations + text, targets


def definitions(targets):
    return ''.join(f'gp50_absolute_{a:x} = {a:#x};\n' for a in sorted(targets))
