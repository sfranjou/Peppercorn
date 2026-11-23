#!/usr/bin/env python3
"""Prepare explicit ARM SDK build inputs from supported, user-supplied stock.

Read-only with respect to firmware and devices. Reuses the bounded HTFW verifier;
never downloads, updates a device, or copies a complete firmware into the output.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import firmware_verify as verifier

STOCK_SHA256 = '0e14f2b0293be233db3da8dc3573bf9135dddc575992055570842433dadae836'
E_SHA256 = '4f48cf8c1c7e691c8d1df1900491ffd3509eef1b767258ea49fa6f3e231d7d48'
G_SHA256 = '1239fb16a533a3f8b7258e3f6b1bc7f2e244b4a4edd3f5bb377e091d51656e13'


def prepare(stock, output, library, with_catalog=False):
    if output.exists():
        raise ValueError('output already exists; choose a fresh directory')
    data = stock.read_bytes()
    if verifier.sha(data) != STOCK_SHA256:
        raise ValueError('unsupported stock SHA-256; requires the documented unmodified GP-50 V1.1.0 image')
    if not library.is_file():
        raise ValueError('LZO shared library does not exist; provide --lzo-library')
    previous_library = verifier.LZO
    try:
        verifier.LZO = str(library.resolve())
        regions, report = verifier.decode(data)
    finally:
        verifier.LZO = previous_library
    g = next(raw for name, _, raw in regions if name == 'g')
    if verifier.sha(g) != G_SHA256:
        raise ValueError('decoded g identity mismatch')
    manifest = dict(schema=1, supported_firmware='GP-50 V1.1.0',
                    input_sha256=report['sha256'], decoded_g_sha256=verifier.sha(g),
                    decoded_g_bytes=len(g), all_region_crcs_ok=report['all_region_crcs_ok'],
                    lzo_library=str(library.resolve()),
                    lzo_library_sha256=verifier.sha(library.read_bytes()),
                    outputs=['decoded_g.bin', 'stock_inputs.json'])
    catalog = None
    if with_catalog:
        catalog = next(raw for name, _, raw in regions if name == 'e')
        if verifier.sha(catalog) != E_SHA256:
            raise ValueError('decoded e identity mismatch')
        manifest.update(decoded_e_sha256=E_SHA256, decoded_e_bytes=len(catalog))
        manifest['outputs'].insert(1, 'decoded_e.bin')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'decoded_g.bin').open('xb') as handle:
        handle.write(g)
    if catalog is not None:
        with (output / 'decoded_e.bin').open('xb') as handle:
            handle.write(catalog)
    with (output / 'stock_inputs.json').open('x') as handle:
        handle.write(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stock', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--lzo-library', type=Path, default=Path(verifier.LZO),
                        help='existing liblzo2 shared library; default: %(default)s')
    parser.add_argument('--with-catalog', action='store_true',
                        help='also prepare decoded stock e for catalog integration')
    args = parser.parse_args()
    try:
        manifest = prepare(args.stock, args.out, args.lzo_library, args.with_catalog)
    except (ValueError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
