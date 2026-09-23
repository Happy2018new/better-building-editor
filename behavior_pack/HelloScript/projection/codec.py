# -*- coding: utf-8 -*-
"""Version 2 chunk format; bounded records also serve network streaming."""
from __future__ import unicode_literals
import base64
import sys
import zlib
from array import array
from collections import Counter
from .storage import CELLS, integer_types, position


def encode_chunk(key, chunk):
    if isinstance(chunk, integer_types):
        payload = int(chunk)
    else:
        values = array('H', chunk)
        if sys.byteorder != 'little':
            values.byteswap()
        raw = values.tobytes() if hasattr(values, 'tobytes') else values.tostring()
        payload = base64.b64encode(zlib.compress(raw, 1)).decode('ascii')
    return list(key) + [payload]


def decode_chunk(document, row):
    if not isinstance(row, (list, tuple)) or len(row) != 4:
        raise ValueError('配置包含无效分块')
    key = tuple(row[:3])
    if any(type(v) is not int or v < 0 or (v << 4) >= document.size[i] for i, v in enumerate(key)):
        raise ValueError('分块超出建筑范围')
    store = document.blocks
    if key in store.chunks:
        raise ValueError('配置包含重复分块')
    payload = row[3]
    if type(payload) is int:
        if not 0 < payload < len(store.palette) or any((key[i] + 1) * 16 > document.size[i] for i in range(3)):
            raise ValueError('无效的完整分块')
        store.fill_chunk(key, store.palette[payload])
        return
    if not isinstance(payload, (str, type(''))) or len(payload) > 12000:
        raise ValueError('无效的分块编码')
    try:
        packed = base64.b64decode(payload.encode('ascii'))
        inflater = zlib.decompressobj()
        raw = inflater.decompress(packed, CELLS * 2 + 1)
        if len(raw) != CELLS * 2 or inflater.unconsumed_tail or inflater.unused_data:
            raise ValueError('分块数据长度错误')
        # Python 2 has no Decompress.eof; validating the bounded payload again
        # detects truncated streams/checksums without accepting zip bombs.
        if zlib.decompress(packed) != raw:
            raise ValueError('分块压缩校验失败')
        values = array('H')
        if hasattr(values, 'frombytes'):
            values.frombytes(raw)
        else:
            values.fromstring(raw)
        if sys.byteorder != 'little':
            values.byteswap()
    except (ValueError, TypeError, UnicodeError, zlib.error):
        raise ValueError('分块压缩数据损坏')
    if max(values) >= len(store.palette):
        raise ValueError('分块包含未知材质')
    if any((key[i] + 1) * 16 > document.size[i] for i in range(3)):
        if any(v and not document.contains(position(key, i)) for i, v in enumerate(values)):
            raise ValueError('方块超出建筑范围')
    counts = Counter(values)
    store.chunks[key] = values
    store.owned.add(key)
    store.count += CELLS - counts.get(0, 0)
    for identity, count in counts.items():
        if identity:
            store.counts[store.palette[identity]] += count
    for y in range(16):
        store.layers[(key[1] << 4) + y] += sum(bool(v) for v in values[y * 256:(y + 1) * 256])
    store.compact(key)


def to_data(document):
    store = document.blocks
    return {'version': 2, 'name': document.name, 'size': list(document.size), 'biome': document.biome,
            'blockCount': len(store), 'palette': [list(v) for v in store.palette],
            'chunks': [encode_chunk(k, store.chunks[k]) for k in sorted(store.chunks)]}


def load_steps(data):
    from .model import AIR, Document, block
    doc = Document(data.get('size', ()), name=data.get('name', '未命名建筑'), biome=data.get('biome', 'plains'))
    palette = data.get('palette')
    chunks = data.get('chunks')
    if not isinstance(palette, list) or not 1 <= len(palette) <= 65536:
        raise ValueError('配置材质表无效')
    if not isinstance(chunks, list) or len(chunks) > 6144:
        raise ValueError('配置分块数量超限')
    values = [block(v) for v in palette]
    if values[0] != AIR or len(set(values)) != len(values):
        raise ValueError('配置材质表有重复或缺少空气')
    doc.blocks.palette, doc.blocks.palette_ids = values, dict((v, i) for i, v in enumerate(values))
    seen = set()
    for row in chunks:
        decode_chunk(doc, row)
        key = tuple(row[:3])
        if key in seen:
            raise ValueError('配置包含重复分块')
        seen.add(key)
        yield None
    if data.get('blockCount', len(doc.blocks)) != len(doc.blocks):
        raise ValueError('配置方块计数不一致')
    yield doc
