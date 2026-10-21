import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
hook=sys._books_wire_hook
work=b.projection_work
assert work is not None and work.ready and work.document.blocks==s.editor.document.blocks
_result=json.dumps({'phase_key':hook['phase_key'],'work_id':id(work),'serial':work.serial,
 'records':[record for record in sys._books_wire_observer['records'] if record['phase_key']==hook['phase_key']],
 'buffer_parts':dict((name,list(b.context_models.get(name,()))) for name in work.shader.names),
 'logical_document':sys._books_wire_observer_module.concrete_document(s.editor.document),
 'work_document':sys._books_wire_observer_module.concrete_document(work.document),
 'helper_call_counts':dict(hook['module']._wire_call_counts),
 'helper_calls':sys._books_wire_observer_module.concrete_wire(hook['module']._wire_calls)})
