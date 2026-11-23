#!/usr/bin/env python3
"""Rebuild a GP-50 HTFW container from decoded regions (offline container model).

Established for the supplied V1.1.0 (compressed) and V1.0.5 (raw payload) images, by exact reproduction:
  header 0x00 'HTFW'; 0x04 BE CRC-16/MODBUS of file[6:]; 0x06 LE u16 (1 in stock);
  0x08 LE u32 file size; 0x0c.. model/version fields copied from the template;
  0x24 LE u32 decoded payload size; TOC at 0x38: per region
  [BE CRC-16/MODBUS of decoded region][00][id][LE u32 destination][LE u32 offset][LE u32 size];
  0x88 LE u32 decoded payload size; 0x8c lzo1x_1_compress(payload) from stock liblzo2.

This reproduces the stock file byte for byte. The CLI refuses to write outside work/ and refuses to overwrite.
"""
import argparse, ctypes, hashlib, struct, sys
from pathlib import Path

LIBRARY = "/opt/homebrew/Cellar/lzo/2.10/lib/liblzo2.2.dylib"
ROOT = Path(__file__).resolve().parent.parent
TOC, TOC_END = 0x38, 0x88


def crc16_modbus(data: bytes) -> int:
    c = 0xFFFF
    for b in data:
        c ^= b
        for _ in range(8):
            c = (c >> 1) ^ 0xA001 if c & 1 else c >> 1
    return c


def lzo1x_1_compress(data: bytes) -> bytes:
    lib = ctypes.CDLL(LIBRARY)
    out = ctypes.create_string_buffer(len(data) + len(data) // 16 + 64 + 3)
    n = ctypes.c_ulong(0)
    wrk = ctypes.create_string_buffer(8 * (1 << 17))
    if lib.lzo1x_1_compress(data, ctypes.c_ulong(len(data)), out, ctypes.byref(n), wrk) != 0:
        raise RuntimeError("lzo1x_1_compress failed")
    return out.raw[:n.value]


def parse_template(image: bytes):
    """Return (header bytes 0..0x38, [(id, destination)]) from an existing container."""
    if image[:4] != b"HTFW":
        raise ValueError("not an HTFW container")
    recs = [(chr(image[p + 3]), struct.unpack_from("<I", image, p + 4)[0]) for p in range(TOC, TOC_END, 16)]
    return image[:TOC], recs


def is_compressed(image: bytes) -> bool:
    """V1.1.0 stores [LE u32 size][LZO1X stream] after the TOC; V1.0.5 stores the raw payload.

    Distinguished here by the size field: header 0x24 + 0x88 equals the file size only when
    raw. Header bytes 0x20/0x21 are 00 00 in raw V1.0.5 and 03 01 in compressed V1.1.0;
    that they are the device's compression indicator is an inference from two files.
    """
    return struct.unpack_from("<I", image, 0x24)[0] + TOC_END != len(image)


def build(header_template: bytes, regions: list[tuple[str, int, bytes]], compressed: bool = True) -> bytes:
    """regions: ordered (id, destination, decoded bytes). Sizes may differ from stock."""
    if len(header_template) != TOC or len(regions) != 5:
        raise ValueError("this model covers the five-region GP-50 layout only")
    payload = b"".join(d for _, _, d in regions)
    toc, off = b"", 0
    for rid, dest, data in regions:
        toc += struct.pack(">H", crc16_modbus(data)) + b"\0" + rid.encode() + struct.pack("<III", dest, off, len(data))
        off += len(data)
    body = struct.pack("<I", len(payload)) + lzo1x_1_compress(payload) if compressed else payload
    hdr = bytearray(header_template)
    struct.pack_into("<I", hdr, 0x24, len(payload))
    struct.pack_into("<I", hdr, 0x08, TOC_END + len(body))
    image = bytearray(bytes(hdr) + toc + body)
    struct.pack_into(">H", image, 4, crc16_modbus(bytes(image[6:])))
    return bytes(image)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("template", type=Path, help="existing container supplying header fields and destinations")
    ap.add_argument("region_dir", type=Path, help="directory with decoded_{c,g,f,b,e}.bin")
    ap.add_argument("--out", type=Path, help="output file under work/ (omit to only report the hash)")
    a = ap.parse_args()
    tmpl = a.template.read_bytes()
    hdr, recs = parse_template(tmpl)
    image = build(hdr, [(rid, dest, (a.region_dir / f"decoded_{rid}.bin").read_bytes()) for rid, dest in recs],
                  compressed=is_compressed(tmpl))
    print(len(image), hashlib.sha256(image).hexdigest())
    if a.out:
        out = a.out.resolve()
        if (ROOT / "work").resolve() not in out.parents or out.exists():
            sys.exit("refusing: output must be a new file under work/")
        out.write_bytes(image)


if __name__ == "__main__":
    main()
