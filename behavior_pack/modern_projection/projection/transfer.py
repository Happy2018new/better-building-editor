# -*- coding: utf-8 -*-
"""Ordered, bounded building packets. Receiver publishes only a complete document."""
from __future__ import unicode_literals
from .model import AIR, Document, block
from .codec import encode_chunk, decode_chunk
from .cell import encode as encode_cell, decode as decode_cell, has_complete_cells
from . import compact_chunk, semantic_wire
import json

MAX_CELL_TEXT = 24 * 1024 * 1024
PALETTE_PACKET_SIZE = 12000


def packets(document, version=4):
    store = document.blocks
    if type(version) is not int or version not in (2, 3, 4) or (version == 2 and has_complete_cells(store)):
        raise ValueError('不支持或无法保留完整方块的传输版本')
    encoder = semantic_wire.Encoder() if version == 4 else None
    palette = [encoder.cell(value) if encoder else encode_cell(value) for value in store.palette]
    begin = {'seq': 0, 'kind': 'begin', 'name': document.name, 'size': list(document.size), 'biome': document.biome,
             'version': version, 'paletteCount': len(store.palette), 'chunkCount': len(store.chunks), 'blockCount': len(store)}
    if encoder:
        begin.update({'cellVersion': semantic_wire.CELL_VERSION, 'chunkEncoding': compact_chunk.VERSION,
                      'registry': semantic_wire.provenance(), 'materialCount': len(encoder.materials)})
    yield begin
    seq = 0
    if encoder:
        for record in _material_records(encoder.materials):
            seq += 1
            record['seq'] = seq
            yield record
    for record in _palette_records(palette):
        seq += 1
        record['seq'] = seq
        yield record
    for record in _chunk_records(store, compact_chunk.VERSION if version == 4 else 0):
        seq += 1
        record['seq'] = seq
        yield record
    yield {'seq': seq + 1, 'kind': 'end'}


def _material_records(materials):
    rows, cost = [], 0
    for row in materials:
        size = len(json.dumps(row, ensure_ascii=True, separators=(',', ':')))
        if rows and (len(rows) == 64 or cost + size > PALETTE_PACKET_SIZE):
            yield {'kind': 'materials', 'rows': rows}
            rows, cost = [], 0
        rows.append(row)
        cost += size
    if rows:
        yield {'kind': 'materials', 'rows': rows}


def _palette_records(palette):
    rows, cost = [], 0
    for row in palette:
        encoded = json.dumps(row, ensure_ascii=True, separators=(',', ':'))
        if len(encoded) > MAX_CELL_TEXT:
            raise ValueError('单个方块实体数据超过容量限制')
        if rows and (len(rows) == 64 or cost + len(encoded) > PALETTE_PACKET_SIZE):
            yield {'kind': 'palette', 'rows': rows}
            rows, cost = [], 0
        if len(encoded) > PALETTE_PACKET_SIZE:
            for start in range(0, len(encoded), PALETTE_PACKET_SIZE):
                yield {'kind': 'palette_part', 'text': encoded[start:start + PALETTE_PACKET_SIZE],
                       'last': start + PALETTE_PACKET_SIZE >= len(encoded)}
            continue
        rows.append(row)
        cost += len(encoded)
    if rows:
        yield {'kind': 'palette', 'rows': rows}


def _chunk_records(store, encoding):
    rows, cost, mixed = [], 0, 0
    for key in sorted(store.chunks):
        row = encode_chunk(key, store.chunks[key], encoding)
        size = 40 + (len(row[3]) if not isinstance(row[3], int) else 8)
        is_mixed = not isinstance(row[3], int)
        if rows and (len(rows) >= 64 or cost + size > 16000 or (is_mixed and mixed >= 4)):
            yield {'kind': 'chunks', 'rows': rows}
            rows, cost, mixed = [], 0, 0
        rows.append(row); cost += size
        mixed += int(is_mixed)
    if rows:
        yield {'kind': 'chunks', 'rows': rows}


class Receiver(object):
    def __init__(self):
        self.sequence = 0
        self.document = self.result = None
        self.seen = set()
        self.palette_count = self.chunk_count = self.block_count = 0
        self.version = 2
        self.encoding = 0
        self.source = None
        self.materials = []
        self.material_count = 0
        self.palette_received = 0
        self.mapping = None
        self.partial_palette = []
        self.partial_size = 0

    def feed(self, packet):
        if not isinstance(packet, dict) or type(packet.get('seq')) is not int or packet['seq'] != self.sequence or self.result is not None:
            raise ValueError('建筑分包顺序错误，请重试')
        kind = packet.get('kind')
        if self.sequence == 0:
            if kind != 'begin':
                raise ValueError('缺少建筑传输头')
            self._begin(packet)
        elif kind == 'palette_part':
            self._palette_part(packet)
        elif self.partial_palette:
            raise ValueError('方块实体分包不完整')
        elif kind == 'materials':
            self._materials(packet)
        elif kind == 'palette':
            rows = packet.get('rows')
            if not isinstance(rows, list) or not 1 <= len(rows) <= 64 or self.seen:
                raise ValueError('材质分包无效')
            for row in rows:
                self._append_palette(row)
        elif kind == 'chunks':
            self._chunks(packet)
        elif kind == 'end':
            if (self.palette_received != self.palette_count or len(self.seen) != self.chunk_count or
                    len(self.document.blocks) != self.block_count or
                    (self.version == 4 and len(self.materials) != self.material_count)):
                raise ValueError('建筑分包不完整')
            self.result = self.document
        else:
            raise ValueError('未知建筑分包')
        self.sequence += 1
        return self.result

    def _begin(self, packet):
        self.version = packet.get('version', 2)
        if type(self.version) is not int or self.version not in (2, 3, 4):
            raise ValueError('不支持的建筑传输版本')
        if self.version == 4:
            self.source = semantic_wire.validate_header(packet)
            self.encoding = packet.get('chunkEncoding')
            self.material_count = packet.get('materialCount')
            if (type(self.encoding) is not int or self.encoding != compact_chunk.VERSION or
                    type(self.material_count) is not int or not 1 <= self.material_count <= semantic_wire.MAX_MATERIALS):
                raise ValueError('语义材质数量或分块压缩版本无效')
            self.mapping = []
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

    def _materials(self, packet):
        rows = packet.get('rows')
        if (self.version != 4 or self.palette_received or self.seen or
                not isinstance(rows, list) or not 1 <= len(rows) <= 64 or
                len(self.materials) + len(rows) > self.material_count):
            raise ValueError('语义材质分包无效')
        for row in rows:
            self.materials.append(semantic_wire.decode_material(row, self.source))

    def _palette_part(self, packet):
        piece = packet.get('text')
        if (self.version not in (3, 4) or self.seen or not isinstance(piece, type('')) or
                self.palette_received >= self.palette_count or
                (self.version == 4 and len(self.materials) != self.material_count) or
                not 1 <= len(piece) <= PALETTE_PACKET_SIZE or type(packet.get('last')) is not bool):
            raise ValueError('方块实体分包无效')
        self.partial_size += len(piece)
        if self.partial_size > MAX_CELL_TEXT:
            raise ValueError('单个方块实体数据超过容量限制')
        self.partial_palette.append(piece)
        if packet['last']:
            value = json.loads(''.join(self.partial_palette))
            self._append_palette(value)
            self.partial_palette, self.partial_size = [], 0

    def _chunks(self, packet):
        rows = packet.get('rows')
        if self.palette_received != self.palette_count or not isinstance(rows, list) or not 1 <= len(rows) <= 64:
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
            decode_chunk(self.document, row, self.encoding, self.mapping)
            self.seen.add(key)

    def _append_palette(self, row):
        store = self.document.blocks
        if self.version == 4:
            if len(self.materials) != self.material_count or self.palette_received >= self.palette_count:
                raise ValueError('语义材质表不完整或超限')
            value = semantic_wire.decode_cell(row, self.materials)
            semantic_wire.append_palette(store, value, self.mapping)
            self.palette_received += 1
            return
        value = decode_cell(row) if self.version == 3 else block(row)
        if value in store.palette_ids or (not store.palette and value != AIR) or len(store.palette) >= self.palette_count:
            raise ValueError('材质表重复或超限')
        store.palette_ids[value] = len(store.palette)
        store.palette.append(value)
        self.palette_received += 1
