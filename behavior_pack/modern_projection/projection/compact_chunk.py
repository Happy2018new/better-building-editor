# -*- coding: utf-8 -*-
"""Bounded chunk payload v1: select the smallest compressed native index layout."""
from __future__ import unicode_literals
import base64
import binascii
import struct
import zlib
from .packed import IntegerBuffer

VERSION = 1
CELLS = 4096
MAX_RAW = CELLS * 4 + 2
MAX_TEXT = 24000
TAIL = b'CHUNK-END'


def _paletted(values):
    palette = sorted(set(values))
    width = max(1, (len(palette) - 1).bit_length())
    ids = dict((value, index) for index, value in enumerate(palette))
    packed, accumulator, bits = bytearray(), 0, 0
    for value in values:
        accumulator |= ids[value] << bits
        bits += width
        while bits >= 8:
            packed.append(accumulator & 255)
            accumulator >>= 8
            bits -= 8
    if bits:
        packed.append(accumulator)
    return struct.pack('<HB', len(palette), width) + IntegerBuffer('H', palette).tobytes() + bytes(packed)


def candidates(chunk):
    values = tuple(chunk)
    if len(values) != CELLS:
        raise ValueError('分块方块数量错误')
    runs = []
    last, count = values[0], 0
    sparse = []
    for index, value in enumerate(values):
        if value != last:
            runs.extend((count, last))
            last, count = value, 0
        count += 1
        if value:
            sparse.extend((index, value))
    runs.extend((count, last))
    return {'u': IntegerBuffer('H', values).tobytes(), 'p': _paletted(values),
            'r': IntegerBuffer('H', runs).tobytes(),
            's': struct.pack('<H', len(sparse) // 2) + IntegerBuffer('H', sparse).tobytes()}


def encode(chunk):
    compressed = [(zlib.compress(raw, 6), mode) for mode, raw in candidates(chunk).items()]
    packed, mode = min(compressed, key=lambda item: (len(item[0]), item[1]))
    return '1' + mode + ':' + base64.b64encode(packed).decode('ascii')


def _inflate(payload):
    if (not isinstance(payload, (str, type(''))) or not 4 <= len(payload) <= MAX_TEXT or
            payload[:2] not in ('1u', '1p', '1r', '1s') or payload[2] != ':'):
        raise ValueError('不支持的分块压缩格式')
    try:
        encoded = payload[3:].encode('ascii')
        packed = base64.b64decode(encoded)
        if base64.b64encode(packed) != encoded:
            raise ValueError('分块Base64编码无效')
        inflater = zlib.decompressobj()
        raw = inflater.decompress(packed + TAIL, MAX_RAW + 1)
        if len(raw) > MAX_RAW or inflater.unconsumed_tail or inflater.unused_data != TAIL:
            raise ValueError('分块解压长度或压缩校验无效')
    except (binascii.Error, UnicodeError, zlib.error):
        raise ValueError('分块压缩数据损坏')
    return payload[1], raw


def decode(payload):
    mode, raw = _inflate(payload)
    if mode == 'u':
        if len(raw) != CELLS * 2:
            raise ValueError('分块数据长度错误')
        values = IntegerBuffer('H')
        values.frombytes(raw)
        return values
    if mode == 'p':
        return _decode_palette(raw)
    if mode == 's':
        if len(raw) < 2:
            raise ValueError('稀疏分块记录无效')
        count = struct.unpack_from('<H', raw)[0]
        if count > CELLS or len(raw) != 2 + count * 4:
            raise ValueError('稀疏分块长度错误')
        values, seen = [0] * CELLS, set()
        for offset in range(2, len(raw), 4):
            index, value = struct.unpack_from('<HH', raw, offset)
            if index >= CELLS or index in seen or not value:
                raise ValueError('稀疏分块坐标或材质无效')
            seen.add(index)
            values[index] = value
        return IntegerBuffer('H', values)
    if not raw or len(raw) % 4:
        raise ValueError('游程分块记录无效')
    values = []
    for offset in range(0, len(raw), 4):
        count, value = struct.unpack_from('<HH', raw, offset)
        if not count or len(values) + count > CELLS:
            raise ValueError('游程分块长度错误')
        values.extend([value] * count)
    if len(values) != CELLS:
        raise ValueError('游程分块长度错误')
    return IntegerBuffer('H', values)


def _decode_palette(raw):
    if len(raw) < 3:
        raise ValueError('局部材质表分块无效')
    count, width = struct.unpack_from('<HB', raw)
    if not 1 <= count <= CELLS or width != max(1, (count - 1).bit_length()):
        raise ValueError('局部材质表数量或位宽错误')
    offset = 3 + count * 2
    if len(raw) != offset + CELLS * width // 8:
        raise ValueError('局部材质表分块长度错误')
    palette = struct.unpack_from('<%dH' % count, raw, 3)
    if len(set(palette)) != count:
        raise ValueError('局部材质表包含重复记录')
    values, accumulator, bits = [], 0, 0
    mask = (1 << width) - 1
    for byte in bytearray(raw[offset:]):
        accumulator |= byte << bits
        bits += 8
        while bits >= width and len(values) < CELLS:
            identity = accumulator & mask
            if identity >= count:
                raise ValueError('局部分块包含未知材质')
            values.append(palette[identity])
            accumulator >>= width
            bits -= width
    if len(values) != CELLS or accumulator:
        raise ValueError('局部分块位流损坏')
    return IntegerBuffer('H', values)
