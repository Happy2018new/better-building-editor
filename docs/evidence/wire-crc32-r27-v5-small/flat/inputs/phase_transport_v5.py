"""Bounded byte transport for the original complete READ_PHASE JSON.

The native observer and restoration sequence are unchanged. An export is stored
inside the observer state; ordinary observer retirement removes it on any error.
"""
import base64
import hashlib
import json
import zlib


CHUNK_BYTES = 256 * 1024
MAX_PHASE_BYTES = 128 * 1024 * 1024

PREFLIGHT = '''import zlib
checksum=zlib.crc32('123456789') & 0xffffffff
assert checksum==3421780262,'Game zlib.crc32 known-answer preflight failed'
_result=json.dumps({'schema':'wire-game-crc32-known-answer-v1','input':'123456789',
 'crc32':'%08x'%checksum,'engine':api.GetEngineVersion(),'game_SHA256_required':False})
'''


START = '''import zlib,base64
saved=sys._books_wire_observer
assert 'phase_export' not in saved,'An unread phase export already exists'
eval(compile(base64.b64decode(%r),'<original-complete-READ_PHASE>','exec'))
raw=_result
assert isinstance(raw,(str,type(u'')))
raw=raw.encode('ascii')
assert 0<len(raw)<=134217728,'Complete phase JSON exceeds bounded export budget'
phase_key=sys._books_wire_hook['phase_key']
assert json.loads(raw)['phase_key']==phase_key
digest='%%08x' %% (zlib.crc32(raw) & 0xffffffff)
chunks=(len(raw)+262143)//262144
meta={'schema':'wire-complete-phase-byte-export-v5-crc32','phase_key':phase_key,
 'bytes':len(raw),'crc32':digest,'chunk_bytes':262144,'chunks':chunks}
saved['phase_export']={'raw':raw,'meta':meta,'next':0}
_result=json.dumps(meta)
'''

CHUNK = '''import zlib,base64
export=sys._books_wire_observer['phase_export']
expected,index=%r,%r
assert export['meta']==expected and export['next']==index
assert 0<=index<expected['chunks']
offset=index*262144
raw=export['raw'][offset:offset+262144]
assert len(raw)==min(262144,expected['bytes']-offset)
result={'schema':'wire-complete-phase-chunk-v5-crc32','phase_key':expected['phase_key'],
 'index':index,'offset':offset,'bytes':len(raw),'crc32':'%%08x' %% (zlib.crc32(raw) & 0xffffffff),
 'phase_bytes':expected['bytes'],'phase_crc32':expected['crc32'],
 'base64':base64.b64encode(raw).decode('ascii')}
_result=json.dumps(result)
assert len(_result.encode('ascii'))<=350500
export['next']+=1
'''

RELEASE = '''saved=sys._books_wire_observer
export=saved['phase_export']
expected=%r
assert export['meta']==expected and export['next']==expected['chunks']
assert len(export['raw'])==expected['bytes'] and '%%08x' %% (zlib.crc32(export['raw']) & 0xffffffff)==expected['crc32']
del saved['phase_export']
_result=json.dumps({'released':True,'phase_key':expected['phase_key'],
 'bytes':expected['bytes'],'crc32':expected['crc32']})
'''


def metadata(value):
    assert value['schema'] == 'wire-complete-phase-byte-export-v5-crc32'
    assert isinstance(value['phase_key'], str) and 0 < len(value['phase_key']) <= 192
    assert type(value['bytes']) is int and 0 < value['bytes'] <= MAX_PHASE_BYTES
    assert value['chunk_bytes'] == CHUNK_BYTES
    assert value['chunks'] == (value['bytes'] + CHUNK_BYTES - 1) // CHUNK_BYTES
    assert isinstance(value['crc32'], str) and len(value['crc32']) == 8
    int(value['crc32'], 16)
    return value


class Collector:
    def __init__(self, meta):
        self.meta = metadata(meta)
        self.chunks = []
        self.receipts = []

    def add(self, value):
        expected = self.meta
        index = len(self.chunks)
        assert index < expected['chunks']
        assert value['schema'] == 'wire-complete-phase-chunk-v5-crc32'
        assert value['phase_key'] == expected['phase_key']
        assert value['index'] == index and value['offset'] == index * CHUNK_BYTES
        assert value['phase_bytes'] == expected['bytes'] and value['phase_crc32'] == expected['crc32']
        raw = base64.b64decode(value['base64'], validate=True)
        assert len(raw) == value['bytes'] == min(CHUNK_BYTES, expected['bytes'] - index * CHUNK_BYTES)
        assert '%08x' % (zlib.crc32(raw) & 0xffffffff) == value['crc32']
        self.chunks.append(raw)
        receipt={key: value[key] for key in value if key != 'base64'}
        receipt['host_chunk_sha256']=hashlib.sha256(raw).hexdigest()
        self.receipts.append(receipt)

    def finish(self):
        assert len(self.chunks) == self.meta['chunks']
        raw = b''.join(self.chunks)
        assert len(raw) == self.meta['bytes']
        assert '%08x' % (zlib.crc32(raw) & 0xffffffff) == self.meta['crc32']
        value = json.loads(raw)
        assert value['phase_key'] == self.meta['phase_key']
        return raw, value


def collect(check, original_read_phase, folder, phase_number, expected_phase_key, host_wires):
    encoded = base64.b64encode(original_read_phase.encode('utf8')).decode('ascii')
    meta = metadata(check.run(START % encoded))
    assert meta['phase_key'] == expected_phase_key
    collector = Collector(meta)
    for index in range(meta['chunks']):
        collector.add(check.run(CHUNK % (meta, index)))
    raw, snapshot = collector.finish()
    # Preserve the exact original game-side JSON before adding host-only hashes.
    output = folder / ('phase-%02d-complete-original.json' % phase_number)
    with output.open('xb') as stream:
        stream.write(raw)
    receipt = {'complete_original_JSON_bytes_preserved': True, 'metadata': meta,
               'chunks': collector.receipts, 'original_json_path': output.name,
               'native_records': len(snapshot['records']), 'runtime_fields_removed': False,
               'host_original_json_sha256':hashlib.sha256(raw).hexdigest(),
               'SHA256_origin':'host-derived after full byte reconstruction; game provides CRC32 only'}
    released = check.run(RELEASE % (meta,))
    assert released == {'released': True, 'phase_key': meta['phase_key'],
                        'bytes': meta['bytes'], 'crc32': meta['crc32']}
    receipt['release'] = released
    with (folder / ('phase-%02d-transport.json' % phase_number)).open('xb') as stream:
        stream.write((json.dumps(receipt, indent=2) + '\n').encode('ascii'))
    host_wires(snapshot)
    return snapshot
