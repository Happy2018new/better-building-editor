# -*- coding: utf-8 -*-
"""Paged local archives keep native config IO bounded and the library index small."""
from __future__ import unicode_literals
from .transfer import packets, Receiver
from .model import Document


def validate(data):
    if not isinstance(data, dict) or data.get('version') != 3:
        raise ValueError('无效的建筑存储索引')
    name = data.get('name')
    if isinstance(name, bytes):
        name = name.decode('utf8')
    doc = Document(data.get('size', ()), name=name)
    if not isinstance(name, type('')) or not 1 <= len(name) <= 64:
        raise ValueError('建筑名称无效')
    # ConfigClient returns UTF-8 bytes in the embedded Python. Normalize before
    # the library truncates a title by characters, including after a restart.
    data['name'] = name
    if type(data.get('parts')) is not int or not 1 <= data['parts'] <= 1024:
        raise ValueError('建筑存储页数无效')
    if type(data.get('blockCount')) is not int or not 0 <= data['blockCount'] <= doc.volume:
        raise ValueError('建筑存储计数无效')


def save_steps(bridge, document, identity):
    page, count = [], 0
    for packet in packets(document):
        page.append(packet)
        if len(page) == 8:
            if not bridge.save_archive_page(identity, count, {'packets': page}):
                raise ValueError('建筑分块保存失败，草稿已保留')
            count += 1
            page = []
        yield None
    if page:
        if not bridge.save_archive_page(identity, count, {'packets': page}):
            raise ValueError('建筑分块保存失败，草稿已保留')
        count += 1
        yield None
    yield {'version': 3, 'name': document.name, 'size': list(document.size),
           'blockCount': len(document.blocks), 'parts': count}


def load_steps(bridge, identity, data):
    validate(data)
    receiver = Receiver()
    for part in range(data['parts']):
        page = bridge.load_archive_page(identity, part)
        if not isinstance(page, dict) or not isinstance(page.get('packets'), list) or not 1 <= len(page['packets']) <= 8:
            raise ValueError('建筑存储页缺失或损坏，当前草稿已保留')
        for packet in page['packets']:
            receiver.feed(packet)
            yield None
    doc = receiver.result
    if doc is None or list(doc.size) != data['size'] or len(doc.blocks) != data['blockCount']:
        raise ValueError('建筑存储不完整，当前草稿已保留')
    doc.name = data['name']
    yield doc
