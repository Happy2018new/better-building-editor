# -*- coding: utf-8 -*-
"""Ordered, bounded building packets. Receiver publishes only a complete document."""
from __future__ import unicode_literals
from .model import AIR, Document, block
from .codec import encode_chunk, decode_chunk


def packets(document):
    seq = 0
    store = document.blocks
    yield {'seq': seq, 'kind': 'begin', 'name': document.name, 'size': list(document.size), 'biome': document.biome,
           'paletteCount': len(store.palette), 'chunkCount': len(store.chunks), 'blockCount': len(store)}
    for start in range(0, len(store.palette), 64):
        seq += 1
        yield {'seq': seq, 'kind': 'palette', 'rows': [list(v) for v in store.palette[start:start + 64]]}
    rows, cost, mixed = [], 0, 0
    for key in sorted(store.chunks):
        row = encode_chunk(key, store.chunks[key])
        size = 40 + (len(row[3]) if not isinstance(row[3], int) else 8)
        is_mixed = not isinstance(row[3], int)
        if rows and (len(rows) >= 64 or cost + size > 16000 or (is_mixed and mixed >= 4)):
            seq += 1
            yield {'seq': seq, 'kind': 'chunks', 'rows': rows}
            rows, cost, mixed = [], 0, 0
        rows.append(row); cost += size
        mixed += int(is_mixed)
    if rows:
        seq += 1
        yield {'seq': seq, 'kind': 'chunks', 'rows': rows}
    yield {'seq': seq + 1, 'kind': 'end'}


class Receiver(object):
    def __init__(self):
        self.sequence = 0
        self.document = self.result = None
        self.seen = set()
        self.palette_count = self.chunk_count = self.block_count = 0

    def feed(self, packet):
        if not isinstance(packet, dict) or type(packet.get('seq')) is not int or packet['seq'] != self.sequence or self.result is not None:
            raise ValueError('建筑分包顺序错误，请重试')
        kind = packet.get('kind')
        if self.sequence == 0:
            if kind != 'begin':
                raise ValueError('缺少建筑传输头')
            name = packet.get('name')
            if isinstance(name, bytes):
                name = name.decode('utf8')
            if not isinstance(name, type('')) or not 1 <= len(name) <= 64:
                raise ValueError('建筑名称无效')
            self.document = Document(packet.get('size', ()), name=name, biome=packet.get('biome', 'plains'))
            max_chunks = 1
            for length in self.document.size:
                max_chunks *= (length + 15) // 16
            for field, attr, maximum in [('paletteCount', 'palette_count', 65536), ('chunkCount', 'chunk_count', max_chunks),
                                        ('blockCount', 'block_count', self.document.volume)]:
                value = packet.get(field)
                if type(value) is not int or not 0 <= value <= maximum:
                    raise ValueError('建筑传输计数无效')
                setattr(self, attr, value)
            if self.palette_count < 1:
                raise ValueError('建筑材质表为空')
            self.document.blocks.palette = []
            self.document.blocks.palette_ids = {}
        elif kind == 'palette':
            rows = packet.get('rows')
            if not isinstance(rows, list) or not 1 <= len(rows) <= 64 or self.seen:
                raise ValueError('材质分包无效')
            store = self.document.blocks
            for row in rows:
                value = block(row)
                if value in store.palette_ids or (not store.palette and value != AIR) or len(store.palette) >= self.palette_count:
                    raise ValueError('材质表重复或超限')
                store.palette_ids[value] = len(store.palette)
                store.palette.append(value)
        elif kind == 'chunks':
            rows = packet.get('rows')
            if len(self.document.blocks.palette) != self.palette_count or not isinstance(rows, list) or not 1 <= len(rows) <= 64:
                raise ValueError('方块分包无效')
            cost = 0
            for row in rows:
                if not isinstance(row, (list, tuple)) or len(row) != 4:
                    raise ValueError('无效的分块')
                cost += 40 + (len(row[3]) if isinstance(row[3], (str, type(''))) else 8)
                if cost > 16000:
                    raise ValueError('方块分包过大')
                key = tuple(row[:3])
                if key in self.seen or len(self.seen) >= self.chunk_count:
                    raise ValueError('建筑分块重复或超限')
                decode_chunk(self.document, row)
                self.seen.add(key)
        elif kind == 'end':
            if len(self.document.blocks.palette) != self.palette_count or len(self.seen) != self.chunk_count or len(self.document.blocks) != self.block_count:
                raise ValueError('建筑分包不完整')
            self.result = self.document
        else:
            raise ValueError('未知建筑分包')
        self.sequence += 1
        return self.result
