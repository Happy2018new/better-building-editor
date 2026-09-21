# -*- coding: utf-8 -*-
"""Versioned, bounded clipboard archives; generators never publish partial drafts."""
from __future__ import unicode_literals
import base64
import binascii
import json
import re
import zlib
from .transfer import packets, Receiver

MAX_TEXT = 8 * 1024 * 1024
MAX_RAW = 16 * 1024 * 1024
MAX_RECORD = 32768
PART_SIZE = 12000
TAIL = b'MP-END'
BASE64 = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
IDENTIFIER = re.compile(r'^[a-z0-9_.-]+:[a-z0-9_./-]+$')


def checksum(data):
    return '%08x' % (zlib.crc32(data) & 0xffffffff)


def validate_materials(packet):
    if packet.get('kind') != 'palette':
        return
    rows = packet.get('rows')
    if not isinstance(rows, list):
        raise ValueError('分享码材质表无效')
    for value in rows:
        if (not isinstance(value, list) or len(value) != 2 or
                not isinstance(value[0], type('')) or len(value[0]) > 160 or
                not IDENTIFIER.match(value[0]) or type(value[1]) is not int):
            raise ValueError('分享码包含无效的方块标识')


def encode_steps(document):
    compressor = zlib.compressobj(6)
    output, crc, raw_size, packed_size = [], 0, 0, 0
    total = len(document.blocks.palette) + len(document.blocks.chunks) + 2
    done = 0
    for packet in packets(document):
        validate_materials(packet)
        raw = (json.dumps(packet, ensure_ascii=True, separators=(',', ':'))+'\n').encode('ascii')
        raw_size += len(raw)
        if len(raw) > MAX_RECORD or raw_size > MAX_RAW:
            raise ValueError('建筑分享数据超过容量限制')
        crc = zlib.crc32(raw, crc)
        data = compressor.compress(raw)
        output.append(data)
        packed_size += len(data)
        if packed_size > MAX_TEXT*3//4-64:
            raise ValueError('建筑分享码过长')
        done += len(packet['rows']) if 'rows' in packet else 1
        yield {'progress': (done, total)}
    output.append(compressor.flush())
    text = 'MP2:'+base64.b64encode(b''.join(output)).decode('ascii')+':%08x' % (crc & 0xffffffff)
    if len(text) > MAX_TEXT:
        raise ValueError('建筑分享码过长')
    yield {'text': text}


def decode_steps(text):
    try:
        if isinstance(text, bytes):
            text = text.decode('ascii')
        if not isinstance(text, type('')) or not 1 <= len(text) <= MAX_TEXT:
            raise ValueError('剪贴板没有有效分享码，或内容过长')
        fields = text.strip().split(':')
        if len(fields) != 3 or fields[0] != 'MP2':
            raise ValueError('不是支持的建筑分享码（需要 MP2）')
        encoded, expected = fields[1:]
        if (not encoded or len(encoded)%4 or not BASE64.match(encoded) or
                not re.match(r'^[0-9a-f]{8}$', expected)):
            raise ValueError('分享码格式损坏，请重新复制')
        inflater, receiver = zlib.decompressobj(), Receiver()
        buffer, crc, total_raw, records = b'', 0, 0, 0
        for start in range(0, len(encoded), 16384):
            piece = encoded[start:start+16384]
            packed = base64.b64decode(piece.encode('ascii'))
            if start+len(piece) == len(encoded):
                packed += TAIL
            while packed:
                raw = inflater.decompress(packed, MAX_RECORD)
                packed = inflater.unconsumed_tail
                total_raw += len(raw)
                if total_raw > MAX_RAW:
                    raise ValueError('分享码解压后超过容量限制')
                crc = zlib.crc32(raw, crc)
                buffer += raw
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    records += 1
                    if len(line) > MAX_RECORD or records > 2048:
                        raise ValueError('分享码记录过大或过多')
                    packet = json.loads(line.decode('ascii'))
                    if not isinstance(packet, dict):
                        raise ValueError('分享码记录无效')
                    validate_materials(packet)
                    receiver.feed(packet)
                    yield {'progress': (start+len(piece), len(encoded))}
                if len(buffer) > MAX_RECORD:
                    raise ValueError('分享码记录过大')
                yield {'progress': (start+len(piece), len(encoded))}
        # Python 2 has no inflater.eof. Only a fully terminated zlib stream
        # leaves exactly our sentinel as unused_data, rejecting truncated tails.
        if (inflater.unused_data != TAIL or buffer or receiver.result is None or
                '%08x' % (crc & 0xffffffff) != expected):
            raise ValueError('分享码不完整或校验失败，请重新复制')
        yield {'document': receiver.result}
    except (UnicodeError, binascii.Error, zlib.error, TypeError, KeyError, IndexError, RuntimeError, OverflowError):
        raise ValueError('分享码损坏或格式无效，请重新复制')


def split_text(text):
    if not isinstance(text, type('')) or len(text) > MAX_TEXT:
        raise ValueError('分享码长度无效')
    identity = checksum(text.encode('ascii'))
    total = (len(text)+PART_SIZE-1)//PART_SIZE
    return ['MPS2:%s:%d:%d:%s:%s' % (identity, index+1, total, checksum(piece.encode('ascii')), piece)
            for index, piece in enumerate(text[start:start+PART_SIZE] for start in range(0,len(text),PART_SIZE))]


class Inbox(object):
    def __init__(self):
        self.identity = None
        self.total = 0
        self.parts = {}

    def add(self, text):
        if isinstance(text, bytes):
            text = text.decode('ascii')
        if not isinstance(text, type('')) or len(text) > MAX_TEXT:
            raise ValueError('剪贴板内容过长或不是文字')
        text = text.strip()
        if not text.startswith('MPS2:'):
            return text
        fields = text.split(':', 5)
        if len(fields) != 6:
            raise ValueError('分段分享码格式无效')
        unused, identity, index, total, crc, data = fields
        if not index.isdigit() or not total.isdigit() or len(index)>4 or len(total)>4:
            raise ValueError('分享码分段序号无效')
        index, total = int(index), int(total)
        if (not 1 <= index <= total <= (MAX_TEXT+PART_SIZE-1)//PART_SIZE or len(data)>PART_SIZE or
                not re.match(r'^[0-9a-f]{8}$',identity) or checksum(data.encode('ascii')) != crc):
            raise ValueError('分享码分段损坏或超限')
        if self.identity is not None and (identity != self.identity or total != self.total):
            raise ValueError('这是另一份建筑的分段，请先清空已接收内容')
        if index in self.parts and self.parts[index] != data:
            raise ValueError('同一段的内容不一致，请重新复制')
        self.identity, self.total = identity, total
        self.parts[index] = data
        if sum(len(v) for v in self.parts.values()) > MAX_TEXT:
            raise ValueError('分享码累计长度超过限制')
        if len(self.parts) == total:
            result = ''.join(self.parts[i] for i in range(1,total+1))
            if checksum(result.encode('ascii')) != identity:
                raise ValueError('完整分享码校验失败')
            return result
        return None
