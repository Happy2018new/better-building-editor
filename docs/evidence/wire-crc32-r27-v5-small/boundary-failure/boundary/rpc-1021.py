import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
import zlib,base64
export=sys._books_wire_observer['phase_export']
expected,index={'phase_key': 'wire-r27.flat-boundary:opaque:grazing:restored', 'bytes': 28929741, 'chunks': 111, 'crc32': 'ff582f8b', 'chunk_bytes': 262144, 'schema': 'wire-complete-phase-byte-export-v5-crc32'},81
assert export['meta']==expected and export['next']==index
assert 0<=index<expected['chunks']
offset=index*262144
raw=export['raw'][offset:offset+262144]
assert len(raw)==min(262144,expected['bytes']-offset)
result={'schema':'wire-complete-phase-chunk-v5-crc32','phase_key':expected['phase_key'],
 'index':index,'offset':offset,'bytes':len(raw),'crc32':'%08x' % (zlib.crc32(raw) & 0xffffffff),
 'phase_bytes':expected['bytes'],'phase_crc32':expected['crc32'],
 'base64':base64.b64encode(raw).decode('ascii')}
_result=json.dumps(result)
assert len(_result.encode('ascii'))<=350500
export['next']+=1
