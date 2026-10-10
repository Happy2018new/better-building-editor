"""Compare actual editor payloads and a controlled Bedrock padded-index layout.

The disk-style candidate uses identical local global-ID references for a fair
layout comparison. It is not a full bedrock-world-operator NBT disk archive.
This script also runs in embedded Python 2.7 when its projection imports exist.
"""
from __future__ import print_function
import base64
import json
import os
import random
import struct
import sys
import time
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'behavior_pack', 'modern_projection'))
from projection import compact_chunk
from projection.cell import AIR, make_cell
from projection.codec import to_data, encode_chunk
from projection.model import Document
from projection.packed import IntegerBuffer
from projection.sharing_codec import encode_steps
from projection.transfer import packets


def disk_style(values):
    palette = sorted(set(values))
    if len(palette) == 1:
        return struct.pack('<HBH', 1, 0, palette[0])
    width = next(width for width in (1, 2, 3, 4, 5, 6, 8, 16) if len(palette) <= 1 << width)
    ids = dict((value, index) for index, value in enumerate(palette))
    per_word = 32 // width
    words = [0] * ((4096 + per_word - 1) // per_word)
    for index, value in enumerate(values):
        words[index // per_word] |= ids[value] << ((index % per_word) * width)
    return (struct.pack('<HB', len(palette), width) + IntegerBuffer('H', palette).tobytes() +
            struct.pack('<%dI' % len(words), *words))


def legacy_share_bytes(document):
    version = 3 if any(hasattr(value, '_actor') for value in document.blocks.palette) else 2
    raw = b''.join((json.dumps(packet, ensure_ascii=True, separators=(',', ':')) + '\n').encode('ascii')
                   for packet in packets(document, version))
    return len('MP%d:' % version) + len(base64.b64encode(zlib.compress(raw, 6))) + 9


def cases():
    randomizer = random.Random(601)
    uniform = Document((16, 16, 16))
    uniform.blocks.fill_chunk((0, 0, 0), ('minecraft:stone', 0))
    result = [('uniform', uniform)]
    for name in ('sparse', 'regular', 'random16', 'unique_actor'):
        doc = Document((16, 16, 16), name=name)
        for index in range(4096):
            if name == 'sparse' and index not in range(0, 4096, 67):
                continue
            pos = (index & 15, index >> 8, (index >> 4) & 15)
            if name == 'unique_actor':
                value = make_cell(('minecraft:chest', 0), AIR, {'id': 'Chest', 'x': pos[0],
                                  'y': pos[1], 'z': pos[2], 'CustomName': 'box%d' % index})
            else:
                material = randomizer.randrange(16) if name == 'random16' else index % 4
                names = ('stone', 'dirt', 'glass', 'gold_block', 'iron_block', 'diamond_block',
                         'emerald_block', 'redstone_block', 'lapis_block', 'coal_block',
                         'quartz_bricks', 'obsidian', 'cobblestone', 'sand', 'gravel', 'netherrack')
                value = ('minecraft:' + names[material], 0)
            doc.blocks[pos] = value
        result.append((name, doc))
    return result


def benchmark(repeat=20):
    result = {'python': sys.version, 'repeat': repeat, 'cases': []}
    for name, doc in cases():
        chunk = doc.blocks.chunks[(0, 0, 0)]
        values = [chunk] * 4096 if isinstance(chunk, int) else list(chunk)
        layouts = compact_chunk.candidates(values)
        layouts['disk_padded'] = disk_style(values)
        legacy = to_data(doc, 4 if name == 'unique_actor' else 2)
        modern = to_data(doc)
        start = time.time()
        for unused in range(repeat):
            payload = encode_chunk((0, 0, 0), chunk, 1)[3]
        encode_ms = (time.time() - start) * 1000 / repeat
        start = time.time()
        if not isinstance(payload, int):
            for unused in range(repeat):
                compact_chunk.decode(payload)
        decode_ms = (time.time() - start) * 1000 / repeat
        result['cases'].append({'case': name,
            'raw_bytes': dict((mode, len(raw)) for mode, raw in layouts.items()),
            'zlib6_bytes': dict((mode, len(zlib.compress(raw, 6))) for mode, raw in layouts.items()),
            'legacy_config_json': len(json.dumps(legacy, ensure_ascii=True, separators=(',', ':'))),
            'semantic_config_json': len(json.dumps(modern, ensure_ascii=True, separators=(',', ':'))),
            'legacy_share_chars': legacy_share_bytes(doc),
            'semantic_share_chars': len(list(encode_steps(doc))[-1]['text']),
            'encode_ms': round(encode_ms, 3), 'decode_ms': round(decode_ms, 3),
            'chosen': 'integer' if isinstance(payload, int) else payload[:2]})
    return result


if __name__ == '__main__':
    print(json.dumps(benchmark(), indent=2, sort_keys=True))
