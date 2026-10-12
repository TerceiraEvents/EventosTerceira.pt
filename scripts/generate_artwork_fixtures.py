#!/usr/bin/env python3
"""Generate CC0 geometric PNG fixtures labelled TEST ONLY, without event artwork.

Run from the repository root with ``python3 scripts/generate_artwork_fixtures.py``.
The PNG metadata records the generator's AI attribution and CC0-1.0 dedication.
"""
from pathlib import Path
import hashlib
import json
import struct
import zlib

ROOT = Path(__file__).resolve().parent.parent
TARGET = ROOT / 'scripts/tests/fixtures/artwork/source'
GLYPHS = {
    'T': ['11111', '00100', '00100', '00100', '00100', '00100', '00100'],
    'E': ['11111', '10000', '10000', '11110', '10000', '10000', '11111'],
    'S': ['11111', '10000', '10000', '11111', '00001', '00001', '11111'],
    'O': ['01110', '10001', '10001', '10001', '10001', '10001', '01110'],
    'N': ['10001', '11001', '11001', '10101', '10011', '10011', '10001'],
    'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
    'Y': ['10001', '10001', '01010', '00100', '00100', '00100', '00100'],
    ' ': ['00000'] * 7,
}
ATTRIBUTION = 'AI-produced: Codex desktop app (version unknown); gpt-6.1-sol; local session ID 01a12d38-f796-77a1-b056-47c1eb6a90d5'


def _chunk(kind, data):
    """Encode a PNG chunk with its length and CRC."""
    return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))


def _png(width, height):
    """Return a deterministic RGB PNG with visible corner markers and TEST ONLY text."""
    scale = max(4, width // 120)
    margin = scale * 4
    compressor = zlib.compressobj(9)
    encoded = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            color = (248, 248, 248)
            if x < margin: color = (255, 210, 0)
            elif x >= width - margin: color = (0, 80, 255)
            elif y < margin: color = (230, 30, 60)
            elif y >= height - margin: color = (0, 160, 90)
            elif margin * 3 < y < margin * 5: color = (20, 20, 20)
            elif margin * 7 <= y < height - margin * 2:
                color = (200, 225, 240) if (x // (scale * 12) + y // (scale * 12)) % 2 else (225, 205, 240)
            glyph_y = (y - margin * 3) // scale
            glyph_x = (x - margin * 2) // scale
            if 0 <= glyph_y < 7 and 0 <= glyph_x < len('TEST ONLY') * 6:
                letter, column = divmod(glyph_x, 6)
                if column < 5 and GLYPHS['TEST ONLY'[letter]][glyph_y][column] == '1': color = (255, 255, 255)
            row.extend(color)
        encoded.append(compressor.compress(b'\0' + row))
    encoded.append(compressor.flush())
    header = struct.pack('!IIBBBBB', width, height, 8, 2, 0, 0, 0)
    return b'\x89PNG\r\n\x1a\n' + _chunk(b'IHDR', header) + _chunk(b'tEXt', b'Title\0TEST ONLY - not an event poster') + _chunk(b'tEXt', ('License\0CC0-1.0; ' + ATTRIBUTION).encode()) + _chunk(b'IDAT', b''.join(encoded)) + _chunk(b'IEND', b'')


def main():
    """Write the fixture files and a deterministic dimensions/checksum manifest."""
    TARGET.mkdir(parents=True, exist_ok=True)
    records = []
    for name, width, height in [('portrait', 600, 900), ('landscape', 900, 600), ('oversized', 4096, 3072)]:
        data = _png(width, height)
        (TARGET / (name + '.png')).write_bytes(data)
        records.append({'name': name, 'width': width, 'height': height, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (TARGET.parent / 'generated-manifest.json').write_text(json.dumps({'license': 'CC0-1.0', 'purpose': 'Test-only geometry; not an organizer poster or real event', 'agent_attribution': ATTRIBUTION, 'images': records}, indent=2) + '\n')


if __name__ == '__main__':
    main()
