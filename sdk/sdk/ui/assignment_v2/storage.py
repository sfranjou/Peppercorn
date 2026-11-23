"""Proposed preset-tail format; host reference only, not installed firmware.

No device IO. Keep the stock 426-byte record and its header unchanged. Bind the
extension to that exact record so stock replacement/import cannot resurrect a
previous preset's assignments just because it reuses the same physical slot.
"""
from dataclasses import dataclass
import struct
import zlib

CORE_SIZE = 426
SLOT_SIZE = 1024
OFFSET = 512
SIZE = 64
MAGIC = b'GPAM'
VERSION = 1

@dataclass(frozen=True)
class Binding:
    group: int
    parameter: int
    model_id: int  # Public preset ID, not a catalog ordinal.

def _core(core):
    if len(core) != CORE_SIZE or core[:4] != b'\xa5\x5a\x01\x00':
        raise ValueError('Expected a stock version-1 426-byte preset record')

def encode(core: bytes, bindings: tuple) -> bytes:
    _core(core)
    if len(bindings) != 3:
        raise ValueError('Exactly three destination knobs')
    data = bytearray(SIZE)
    struct.pack_into('<4sHHII', data, 0, MAGIC, VERSION, SIZE, zlib.crc32(core), 0)
    for knob, binding in enumerate(bindings):
        if binding is None:
            continue
        if not (0 <= binding.group < 10 and 0 <= binding.parameter < 8
                and 0 <= binding.model_id <= 0xffffffff):
            raise ValueError('Invalid binding')
        struct.pack_into('<BBBBII', data, 16 + 12 * knob, 1, binding.group,
                         binding.parameter, 0, binding.model_id, 0)
    struct.pack_into('<I', data, 60, zlib.crc32(data[:60]))
    return bytes(data)

def decode(core: bytes, data: bytes):
    """Return three bindings or None for an absent/unsupported/stale/bad record.

    Callers must additionally validate the public model IDs and actual parameter
    counts against the loaded preset/catalog before publishing live mappings.
    """
    try:
        _core(core)
    except ValueError:
        return None
    if len(data) != SIZE:
        return None
    magic, version, size, core_crc, flags = struct.unpack_from('<4sHHII', data)
    if (magic != MAGIC or version != VERSION or size != SIZE or flags
            or core_crc != zlib.crc32(core)
            or struct.unpack_from('<I', data, 60)[0] != zlib.crc32(data[:60])
            or any(data[52:60])):
        return None
    bindings = []
    for knob in range(3):
        row = data[16 + 12 * knob:28 + 12 * knob]
        valid, group, parameter, reserved, model_id, extra = struct.unpack('<BBBBII', row)
        if valid == 0 and row == bytes(12):
            bindings.append(None)
        elif valid == 1 and group < 10 and parameter < 8 and reserved == extra == 0:
            bindings.append(Binding(group, parameter, model_id))
        else:
            return None
    return tuple(bindings)

def publishable(bindings, model_ids, parameter_counts):
    """Independently reject changed effect models or missing parameters."""
    if bindings is None:
        return (None, None, None)
    return tuple(binding if binding is not None
                 and model_ids[binding.group] == binding.model_id
                 and binding.parameter < parameter_counts[binding.group]
                 else None for binding in bindings)

def stage_slot(slot: bytes, core: bytes, bindings: tuple) -> bytes:
    """Reference same-slot update for a future ordinary Save transaction."""
    if len(slot) != SLOT_SIZE:
        raise ValueError('Expected exactly one physical slot')
    extension = encode(core, bindings)
    return core + slot[CORE_SIZE:OFFSET] + extension + slot[OFFSET + SIZE:]
