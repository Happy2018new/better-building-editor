"""Bound client payloads for an explicit A/B/A diagnostic, never production selection."""

HOOK_INSTALL='''import types,base64
from modern_projection.projection import render_context as wire_context
assert not hasattr(sys,'_books_wire_hook')
saved=sys._books_wire_independent
assert all(getattr(wire_context,key) is value for key,value in saved['helpers'].items())
module=types.ModuleType('modern_projection.projection.books_wire_private_candidate')
module.__package__='modern_projection.projection'
eval(compile(base64.b64decode(%r),'<wire-private-candidate>','exec'),module.__dict__)
eval(compile(base64.b64decode(%r),'<wire-private-trace-v2>','exec'),module.__dict__)
sys._books_wire_hook={'module':module,'mode':'base','phase_key':None,'nonhelpers':dict((key,id(value))
 for key,value in wire_context.__dict__.items() if key not in saved['helpers'])}
_result=json.dumps({'installed':True,'candidate_helpers':dict((key,id(getattr(module,key))) for key in saved['helpers'])})
'''

MODE='''assert not s.projection_active and not b.preparing_entity and not b.entity and not b.projection_entities
from modern_projection.projection import render_context as wire_context
saved=sys._books_wire_independent
hook=sys._books_wire_hook
mode=%r
assert mode in ('base','repeat','candidate','restored')
assert dict((key,id(value)) for key,value in wire_context.__dict__.items()
 if key not in saved['helpers'])==hook['nonhelpers']
for key,value in saved['helpers'].items():
 setattr(wire_context,key,getattr(hook['module'],key) if mode=='candidate' else value)
hook['mode']=mode
_result=json.dumps({'mode':mode,'helper_ids':dict((key,id(getattr(wire_context,key))) for key in saved['helpers']),
 'other_module_objects_unchanged':True})
'''

HOOK_RETIRE='''from modern_projection.projection import render_context as wire_context
saved=sys._books_wire_independent
hook=sys._books_wire_hook
for key,value in saved['helpers'].items():setattr(wire_context,key,value)
assert all(getattr(wire_context,key) is value for key,value in saved['helpers'].items())
assert dict((key,id(value)) for key,value in wire_context.__dict__.items()
 if key not in saved['helpers'])==hook['nonhelpers']
del sys._books_wire_hook
_result=json.dumps({'helpers_restored_original_objects':True,'other_context_objects_unchanged':True})
'''

AUDIT_EXTRA_BEGIN='''from modern_projection.projection import render_context as wire_context
saved=sys._books_wire_independent
saved['helpers']=dict((key,getattr(wire_context,key)) for key in
 ('_mark_floor_support','_mark_palette_floor_support','_hidden_neighbor'))
saved['geometry_function']=getattr(type(b).geometry,'im_func',type(b).geometry)
saved['context_writer_function']=getattr(wire_context._ContextWriter.put,'im_func',wire_context._ContextWriter.put)
saved['cache_objects']=dict((key,getattr(b,key)) for key in ('models','context_models','model_layouts'))
saved['cache_values']=dict((key,dict(value)) for key,value in saved['cache_objects'].items())
assert not any('modern_projection_buffer_' in str(key) for key in b.context_models), 'Fresh instance required: native resource names already used'
saved['geometry_instance_override']='geometry' in b.__dict__
_result=json.dumps({'saved':True,'helper_ids':dict((key,id(value)) for key,value in saved['helpers'].items()),
 'geometry_function_id':id(saved['geometry_function']),
 'cache_ids':dict((key,id(value)) for key,value in saved['cache_objects'].items()),
 'cache_sizes':dict((key,len(value)) for key,value in saved['cache_objects'].items())})
'''

CACHE_RESTORE='''saved=sys._books_wire_independent
assert not s.projection_active and not b.entity and not b.projection_entities and not b.preparing_entity
assert s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty
for key,original in saved['cache_objects'].items():
 assert getattr(b,key) is original
 original.clear()
 original.update(saved['cache_values'][key])
_result=json.dumps({'python_cache_maps_restored':True,'native_resources_reclaimed':False,
 'note':'Unique diagnostic native geometry is reclaimed by the subsequent ordinary owned-process stop.'})
'''

AUDIT_EXTRA_CHECK='''result=json.loads(_result)
saved=sys._books_wire_independent
from modern_projection.projection import render_context as wire_context
result['helper_same_objects']=all(getattr(wire_context,key) is value for key,value in saved['helpers'].items())
result['geometry_same_function']=getattr(type(b).geometry,'im_func',type(b).geometry) is saved['geometry_function']
result['geometry_instance_override_same']=('geometry' in b.__dict__)==saved['geometry_instance_override']
result['context_writer_same_function']=getattr(wire_context._ContextWriter.put,'im_func',wire_context._ContextWriter.put) is saved['context_writer_function']
result['cache_same_objects']=all(getattr(b,key) is value for key,value in saved['cache_objects'].items())
result['cache_same_values']=all(getattr(b,key)==value for key,value in saved['cache_values'].items())
result['wire_markers']=[key for key in dir(sys) if key.startswith('_books_wire_') and key!='_books_wire_independent']
result['restored']=result['restored'] and all(result[key] for key in
 ('helper_same_objects','geometry_same_function','geometry_instance_override_same',
 'context_writer_same_function','cache_same_objects','cache_same_values')) and not result['wire_markers']
_result=json.dumps(result)
'''

LOAD='''from modern_projection.projection.model import Document,Editor
from modern_projection.projection.cell import make_cell
item,opacity,phase_key=%r,%r,%r
b.stop_projection()
doc=Document(tuple(item['size']),name=item['id'])
for position,front,back in item['cells']:doc.blocks[tuple(position)]=make_cell(tuple(front),tuple(back))
s.editor=Editor(doc)
s.section=s.solo_layer=False
s.focused=None
s.name=doc.name
sys._blueprint_qa_identity=item['id']
sys._blueprint_qa_nonce+=1
sys._concrete_color_r23['document']=doc.blocks.copy()
s.origin=tuple(sys._concrete_color_r23['origin'][i]+item['origin_shift'][i] for i in range(3))
s.opacity=opacity
s.projection_missing=False
s.projection_outline=False
hook=sys._books_wire_hook
hook['phase_key']=phase_key
hook['module']._wire_phase_key=phase_key
hook['module']._wire_call_counts={}
hook['module']._wire_calls=[]
b.project()
work=b.projection_work
assert work is not None and work.document is not doc
assert work.document.blocks==doc.blocks
sys._books_wire_observer['retained_phase_objects'].append((s.editor,doc,work,work.document))
_result=json.dumps({'fixture':item['id'],'editor_id':id(s.editor),'document_id':id(doc),
 'nonce':sys._blueprint_qa_nonce,'logical_document':sys._books_wire_observer_module.concrete_document(doc),
 'origin':s.origin,'opacity':s.opacity,'mode':hook['mode'],'phase_key':phase_key,
 'work_id':id(work),'work_document_id':id(work.document),'serial':work.serial,
 'size':doc.size,'profile_id':id(s.liquid_profile)})
'''

PROFILE='''from modern_projection.projection import liquid_render_ownership
profile=s.liquid_profile
_result=json.dumps({'profile_is_none':profile is None,'profile_id':id(profile),
 'type_module':type(profile).__module__,'type_name':type(profile).__name__,
 'owned_names':liquid_render_ownership.identity(profile),
 'renderer_factory':getattr(getattr(profile,'renderer_factory',None),'__name__',None),
 'bridge_engine':b.engine_version,'api_engine':api.GetEngineVersion(),
 'same_as_initial':profile is sys._books_wire_independent['profiles']['liquid_profile'],
 'all_profile_ids':dict((key,id(getattr(s,key))) for key in sys._books_wire_independent['profiles']),
 'all_profiles_same_objects':all(getattr(s,key) is value for key,value in sys._books_wire_independent['profiles'].items())})
'''

READ_PHASE='''hook=sys._books_wire_hook
work=b.projection_work
assert work is not None and work.ready and work.document.blocks==s.editor.document.blocks
_result=json.dumps({'phase_key':hook['phase_key'],'work_id':id(work),'serial':work.serial,
 'records':[record for record in sys._books_wire_observer['records'] if record['phase_key']==hook['phase_key']],
 'buffer_parts':dict((name,list(b.context_models.get(name,()))) for name in work.shader.names),
 'logical_document':sys._books_wire_observer_module.concrete_document(s.editor.document),
 'work_document':sys._books_wire_observer_module.concrete_document(work.document),
 'helper_call_counts':dict(hook['module']._wire_call_counts),
 'helper_calls':sys._books_wire_observer_module.concrete_wire(hook['module']._wire_calls)})
'''

OBSERVER_INSTALL='''import types,base64
assert not hasattr(sys,'_books_wire_observer_module')
module=types.ModuleType('books_wire_readonly_observer')
module.__dict__.update(s=s,b=b)
eval(compile(base64.b64decode(%r),'<wire-readonly-observer>','exec'),module.__dict__)
sys._books_wire_observer_module=module
module.concrete_install()
saved=sys._books_wire_observer
_result=json.dumps({'installed':True,'original_factory_id':id(saved['factory']),
 'installed_factory_id':id(saved['installed_factory']),'record_count':len(saved['records'])})
'''

OBSERVER_RETIRE='''module=sys._books_wire_observer_module
try:
 receipt=module.concrete_retire()
finally:
 del sys._books_wire_observer_module
receipt['module_removed']=not hasattr(sys,'_books_wire_observer_module')
_result=json.dumps(receipt)
assert len(_result.encode('ascii'))<=8192,'Final observer retirement payload exceeds eight KiB'
'''
