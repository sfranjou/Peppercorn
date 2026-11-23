#!/usr/bin/env python3
"""Validate an author boot animation and derive its descriptor. Offline. Limits are what hardware has shown to work."""
import struct
import gif_blocks

WIDTH, HEIGHT = 144, 28
TOTAL_CS = 392                 # stock animation length; boot timing beyond it is unmeasured
E_OFFSET = 0x19600             # erased E range used by the tested boot card
E_ADDRESS = 0x190000+E_OFFSET
MAX_BYTES = 0x20000-E_OFFSET
DESCRIPTOR_OFFSET = 0x1271d0-0x10000
STOCK_DESCRIPTOR = bytes.fromhex('0340820329660000dc711200')


def validate(data):
    """Return facts about a usable GIF, or raise ValueError with the limit it breaks."""
    if len(data) > MAX_BYTES:
        raise ValueError(f'boot GIF is {len(data)} bytes; the limit is {MAX_BYTES}')
    if data[:6] != b'GIF89a':
        raise ValueError('boot GIF must be GIF89a')
    try:
        gif = gif_blocks.parse(data)
    except (AssertionError, IndexError, ValueError, struct.error) as error:
        raise ValueError(f'boot GIF cannot be parsed: {error}') from error
    if (gif['w'], gif['h']) != (WIDTH, HEIGHT):
        raise ValueError(f'boot GIF must be {WIDTH}x{HEIGHT}, not {gif["w"]}x{gif["h"]}')
    frames = gif['frames']
    if not frames:
        raise ValueError('boot GIF has no frames')
    for frame in frames:
        if frame['x']+frame['w'] > WIDTH or frame['y']+frame['h'] > HEIGHT:
            raise ValueError('boot GIF frame extends outside the canvas')
    total = sum(frame.get('delay') or 0 for frame in frames)
    if total > TOTAL_CS:
        raise ValueError(f'boot GIF runs {total*10} ms; the limit is {TOTAL_CS*10} ms')
    return dict(bytes=len(data), frames=len(frames), total_ms=total*10)


def descriptor(length):
    return STOCK_DESCRIPTOR[:4]+struct.pack('<II', length, E_ADDRESS)
