# -*- coding: utf-8 -*-
"""Paged local archives keep native config IO bounded and the library index small."""
from __future__ import unicode_literals
from .transfer import packets, Receiver
from .model import Document
from . import compact_chunk, semantic_wire

MAX_PAGES = 1024


def validate(data):
    if (not isinstance(data, dict) or type(data.get('version')) is not int or
            data.get('version') not in (3, 5, 7)):
        raise ValueError('无效的建筑存储索引')
    name = data.get('name')
    if isinstance(name, bytes):
        name = name.decode('utf8')
    doc = Document(data.get('size', ()), name=name, biome=data.get('biome', 'plains'))
    if not isinstance(name, type('')) or not 1 <= len(name) <= 64:
        raise ValueError('建筑名称无效')
    # ConfigClient returns UTF-8 bytes in the embedded Python. Normalize before
    # the library truncates a title by characters, including after a restart.
    data['name'] = name
    if type(data.get('parts')) is not int or not 1 <= data['parts'] <= MAX_PAGES:
        raise ValueError('建筑存储页数无效')
    if type(data.get('blockCount')) is not int or not 0 <= data['blockCount'] <= doc.volume:
        raise ValueError('建筑存储计数无效')
    if data['version'] == 7:
        semantic_wire.validate_header(data)
        if type(data.get('chunkEncoding')) is not int or data['chunkEncoding'] != compact_chunk.VERSION:
            raise ValueError('不支持的建筑存储压缩版本')


def save_steps(bridge, document, identity):
    page, count = [], 0
    for packet in packets(document):
        if count >= MAX_PAGES:
            raise ValueError('建筑存储页数超过限制，草稿已保留')
        page.append(packet)
        if len(page) == 8:
            if not bridge.save_archive_page(identity, count, {'version': 1, 'packets': page}):
                raise ValueError('建筑分块保存失败，草稿已保留')
            count += 1
            page = []
        yield None
    if page:
        if not bridge.save_archive_page(identity, count, {'version': 1, 'packets': page}):
            raise ValueError('建筑分块保存失败，草稿已保留')
        count += 1
        yield None
    yield {'version': 7, 'cellVersion': semantic_wire.CELL_VERSION, 'chunkEncoding': compact_chunk.VERSION,
           'registry': semantic_wire.provenance(), 'name': document.name, 'size': list(document.size), 'biome': document.biome,
           'blockCount': len(document.blocks), 'parts': count}


def load_steps(bridge, identity, data):
    validate(data)
    receiver = Receiver()
    for part in range(data['parts']):
        page = bridge.load_archive_page(identity, part)
        if not isinstance(page, dict) or not isinstance(page.get('packets'), list) or not 1 <= len(page['packets']) <= 8:
            raise ValueError('建筑存储页缺失或损坏，当前草稿已保留')
        if data['version'] == 7 and (type(page.get('version')) is not int or page['version'] != 1):
            raise ValueError('不支持的建筑存储页版本')
        for packet in page['packets']:
            receiver.feed(packet)
            yield None
    expected = {3: 2, 5: 3, 7: 4}[data['version']]
    if receiver.version != expected:
        raise ValueError('建筑存储版本与分块协议不一致')
    if expected == 4 and receiver.source != data['registry']:
        raise ValueError('建筑存储来源方块表与分包不一致')
    doc = receiver.result
    if doc is None or list(doc.size) != data['size'] or len(doc.blocks) != data['blockCount']:
        raise ValueError('建筑存储不完整，当前草稿已保留')
    doc.name = data['name']
    if doc.biome != data.get('biome', 'plains'):
        raise ValueError('建筑染色数据不一致，当前草稿已保留')
    yield doc
