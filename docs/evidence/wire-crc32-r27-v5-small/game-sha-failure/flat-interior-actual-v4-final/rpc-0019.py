import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
import hashlib,base64
saved=sys._books_wire_observer
assert 'phase_export' not in saved,'An unread phase export already exists'
eval(compile(base64.b64decode('aG9vaz1zeXMuX2Jvb2tzX3dpcmVfaG9vawp3b3JrPWIucHJvamVjdGlvbl93b3JrCmFzc2VydCB3b3JrIGlzIG5vdCBOb25lIGFuZCB3b3JrLnJlYWR5IGFuZCB3b3JrLmRvY3VtZW50LmJsb2Nrcz09cy5lZGl0b3IuZG9jdW1lbnQuYmxvY2tzCl9yZXN1bHQ9anNvbi5kdW1wcyh7J3BoYXNlX2tleSc6aG9va1sncGhhc2Vfa2V5J10sJ3dvcmtfaWQnOmlkKHdvcmspLCdzZXJpYWwnOndvcmsuc2VyaWFsLAogJ3JlY29yZHMnOltyZWNvcmQgZm9yIHJlY29yZCBpbiBzeXMuX2Jvb2tzX3dpcmVfb2JzZXJ2ZXJbJ3JlY29yZHMnXSBpZiByZWNvcmRbJ3BoYXNlX2tleSddPT1ob29rWydwaGFzZV9rZXknXV0sCiAnYnVmZmVyX3BhcnRzJzpkaWN0KChuYW1lLGxpc3QoYi5jb250ZXh0X21vZGVscy5nZXQobmFtZSwoKSkpKSBmb3IgbmFtZSBpbiB3b3JrLnNoYWRlci5uYW1lcyksCiAnbG9naWNhbF9kb2N1bWVudCc6c3lzLl9ib29rc193aXJlX29ic2VydmVyX21vZHVsZS5jb25jcmV0ZV9kb2N1bWVudChzLmVkaXRvci5kb2N1bWVudCksCiAnd29ya19kb2N1bWVudCc6c3lzLl9ib29rc193aXJlX29ic2VydmVyX21vZHVsZS5jb25jcmV0ZV9kb2N1bWVudCh3b3JrLmRvY3VtZW50KSwKICdoZWxwZXJfY2FsbF9jb3VudHMnOmRpY3QoaG9va1snbW9kdWxlJ10uX3dpcmVfY2FsbF9jb3VudHMpLAogJ2hlbHBlcl9jYWxscyc6c3lzLl9ib29rc193aXJlX29ic2VydmVyX21vZHVsZS5jb25jcmV0ZV93aXJlKGhvb2tbJ21vZHVsZSddLl93aXJlX2NhbGxzKX0pCg=='),'<original-complete-READ_PHASE>','exec'))
raw=_result
assert isinstance(raw,(str,type(u'')))
raw=raw.encode('ascii')
assert 0<len(raw)<=134217728,'Complete phase JSON exceeds bounded export budget'
phase_key=sys._books_wire_hook['phase_key']
assert json.loads(raw)['phase_key']==phase_key
digest=hashlib.sha256(raw).hexdigest()
chunks=(len(raw)+262143)//262144
meta={'schema':'wire-complete-phase-byte-export-v4','phase_key':phase_key,
 'bytes':len(raw),'sha256':digest,'chunk_bytes':262144,'chunks':chunks}
saved['phase_export']={'raw':raw,'meta':meta,'next':0}
_result=json.dumps(meta)
