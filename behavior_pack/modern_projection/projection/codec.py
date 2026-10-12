# -*- coding: utf-8 -*-
"""Versioned chunk configs with semantic cells and bounded legacy readers."""
from __future__ import unicode_literals
import base64
import zlib
from .packed import IntegerBuffer
from collections import Counter
from .storage import CELLS, integer_types, position
from .cell import Cell, encode as encode_cell, decode as decode_cell, has_complete_cells
from . import compact_chunk, semantic_wire


def legacy_palette(store):
    """Drop obsolete rich rows that the foreground-only v2 reader cannot decode."""
    if has_complete_cells(store):
        raise ValueError('旧格式无法保存背景层或方块实体')
    palette = [value for value in store.palette if not isinstance(value, Cell)]
    if len(palette) == len(store.palette):
        return store.palette, None
    identities = dict((value, index) for index, value in enumerate(palette))
    return palette, [identities.get(value) for value in store.palette]


def encode_chunk(key, chunk, encoding=0, mapping=None):
    if mapping is not None:
        if isinstance(chunk, integer_types):
            chunk = mapping[chunk]
            if chunk is None:
                raise ValueError('旧格式无法保存背景层或方块实体')
        else:
            chunk = tuple(mapping[value] for value in chunk)
            if None in chunk:
                raise ValueError('旧格式无法保存背景层或方块实体')
    if isinstance(chunk, integer_types):
        payload = int(chunk)
    elif encoding == compact_chunk.VERSION:
        payload = compact_chunk.encode(chunk)
    else:
        values = IntegerBuffer('H', chunk)
        raw = values.tobytes()
        payload = base64.b64encode(zlib.compress(raw, 1)).decode('ascii')
    return list(key) + [payload]


def decode_chunk(document, row, encoding=0, mapping=None):
    if not isinstance(row, (list, tuple)) or len(row) != 4:
        raise ValueError('配置包含无效分块')
    key = tuple(row[:3])
    if any(type(v) is not int or v < 0 or (v << 4) >= document.size[i] for i, v in enumerate(key)):
        raise ValueError('分块超出建筑范围')
    store = document.blocks
    if key in store.chunks:
        raise ValueError('配置包含重复分块')
    payload = row[3]
    palette_length = len(mapping) if mapping is not None else len(store.palette)
    if type(payload) is int:
        if not 0 < payload < palette_length or any((key[i] + 1) * 16 > document.size[i] for i in range(3)):
            raise ValueError('无效的完整分块')
        if mapping is not None:
            payload = mapping[payload]
        store.fill_chunk(key, store.palette[payload])
        return
    if encoding == compact_chunk.VERSION:
        values = compact_chunk.decode(payload)
    else:
        values = _decode_legacy(payload)
    if max(values) >= palette_length:
        raise ValueError('分块包含未知材质')
    if mapping is not None:
        values = IntegerBuffer('H', (mapping[value] for value in values))
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


def _decode_legacy(payload):
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
        values = IntegerBuffer('H')
        values.frombytes(raw)
    except (ValueError, TypeError, UnicodeError, zlib.error):
        raise ValueError('分块压缩数据损坏')
    return values


def to_data(document, version=6):
    store = document.blocks
    if type(version) is not int:
        raise ValueError('不支持的分块配置版本')
    if version in (2, 4):
        palette, mapping = legacy_palette(store) if version == 2 else (store.palette, None)
        return {'version': version, 'name': document.name, 'size': list(document.size), 'biome': document.biome,
            'blockCount': len(store), 'palette': [encode_cell(v) for v in palette],
            'chunks': [encode_chunk(k, store.chunks[k], mapping=mapping) for k in sorted(store.chunks)]}
    if version != 6:
        raise ValueError('不支持的分块配置版本')
    encoder = semantic_wire.Encoder()
    palette = [encoder.cell(value) for value in store.palette]
    return {'version': 6, 'cellVersion': semantic_wire.CELL_VERSION,
            'chunkEncoding': compact_chunk.VERSION, 'registry': semantic_wire.provenance(),
            'name': document.name, 'size': list(document.size), 'biome': document.biome,
            'blockCount': len(store), 'materials': encoder.materials, 'palette': palette,
            'chunks': [encode_chunk(key, store.chunks[key], compact_chunk.VERSION) for key in sorted(store.chunks)]}


def load_steps(data):
    from .model import AIR, Document, block
    version = data.get('version')
    if type(version) is not int or version not in (2, 4, 6):
        raise ValueError('不支持的分块配置版本')
    doc = Document(data.get('size', ()), name=data.get('name', '未命名建筑'), biome=data.get('biome', 'plains'))
    palette = data.get('palette')
    chunks = data.get('chunks')
    if not isinstance(palette, list) or not 1 <= len(palette) <= 65536:
        raise ValueError('配置材质表无效')
    if not isinstance(chunks, list) or len(chunks) > 6144:
        raise ValueError('配置分块数量超限')
    mapping, encoding = None, 0
    if version == 6:
        source = semantic_wire.validate_header(data)
        if type(data.get('chunkEncoding')) is not int or data['chunkEncoding'] != compact_chunk.VERSION:
            raise ValueError('不支持的分块压缩版本')
        encoding = data['chunkEncoding']
        rows = data.get('materials')
        if not isinstance(rows, list) or not 1 <= len(rows) <= semantic_wire.MAX_MATERIALS:
            raise ValueError('语义方块材质表无效')
        materials = [semantic_wire.decode_material(row, source) for row in rows]
        mapping = []
        for row in palette:
            semantic_wire.append_palette(doc.blocks, semantic_wire.decode_cell(row, materials), mapping)
    else:
        decoder = decode_cell if version == 4 else block
        values = [decoder(v) for v in palette]
        if values[0] != AIR or len(set(values)) != len(values):
            raise ValueError('配置材质表有重复或缺少空气')
        doc.blocks.palette, doc.blocks.palette_ids = values, dict((v, i) for i, v in enumerate(values))
    seen = set()
    for row in chunks:
        decode_chunk(doc, row, encoding, mapping)
        key = tuple(row[:3])
        if key in seen:
            raise ValueError('配置包含重复分块')
        seen.add(key)
        yield None
    if data.get('blockCount', len(doc.blocks)) != len(doc.blocks):
        raise ValueError('配置方块计数不一致')
    yield doc
