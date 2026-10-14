import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
if navigator.top is not None:navigator.pop()
s.origin=(0,-57,0)
s.opacity=1.
s.projection_outline=False
s.projection_missing=False
b.project()
_result=True
