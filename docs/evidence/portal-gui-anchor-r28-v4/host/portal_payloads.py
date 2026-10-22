"""Explicit instance-only GUI anchor probe over unchanged legacy default resources."""
CLIENT='''import copy,json,sys
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
from modern_projection.projection.widgets import Theme
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None
s=owner.session;b=owner.bridge
'''

SNAPSHOT='''assert not hasattr(sys,'_portal_anchor_r28')
assert not s.busy and s.edit_job is None and s.io_job is None
assert not s.projection_active and not b.preparing_entity and not b.entity and not b.projection_entities
assert s.pending_confirm is None and s.pending_rename is None and not s.sharing.opened
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
from modern_projection.projection.portal_profile import production_profile,PREFIX,STYLE
profile=s.portal_profile;expected=production_profile('3.10.0.420447')
assert expected is not None and profile is not None and profile.identity==expected.identity
assert profile.models==expected.models and profile.world_models==expected.world_models
assert profile.identity[2]==STYLE
assert all(name.startswith(PREFIX) and not name.startswith(PREFIX+'native_') for name in profile.models.values())
assert 'ui_offset' not in profile.__dict__ and not hasattr(profile,'ui_offset_for_gui')
fields=('tool','page','name','view','focus_view','section','solo_layer','focused','box_anchor',
 'canvas_x','canvas_z','paste_origin','paste_pinned','camera_pose','camera_yaw','camera_pitch',
 'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_focus_request',
 'camera_reset_animated','progress','direct_mode','origin','opacity','projection_missing','projection_outline','grid')
saved={'session':s,'editor':s.editor,'document':s.editor.document,
 'data':copy.deepcopy(s.editor.document.to_data()),'factory':b.factory,
 'fields':dict((key,copy.deepcopy(getattr(s,key))) for key in fields),
 'profiles':dict((key,getattr(s,key)) for key in ('liquid_profile','book_profile','portal_profile','item_profile','native_render_profile','cauldron_profile','spawner_profile')),
 'workspace':navigator.contains('modern_projection_workspace'),
 'library':s.library,'library_data':copy.deepcopy(s.library),'library_serial':s.library_serial,
 'stored_library':copy.deepcopy(b.load_library()),'undo':copy.deepcopy(s.editor.undo_stack),
 'redo':copy.deepcopy(s.editor.redo_stack),'selection':set(s.editor.selection),'revision':s.editor.revision}
sys._portal_anchor_r28=saved
_result=json.dumps({'editor_id':id(s.editor),'document_id':id(s.editor.document),
 'document':saved['data'],'workspace':saved['workspace'],'profile_identity':profile.identity,
 'profile_models':profile.models,'legacy_default_selection':True,'native_candidate_selected':False})
'''

def load(family):
 assert family in ('end_portal','end_gateway')
 return '''assert not hasattr(sys,'_portal_gui_control_r28')
from modern_projection.projection.debug_portal_blueprints import source_document
doc=source_document(%r)
s._loaded(doc)
s.grid=False;s.camera_focus_request=None
s.camera_view(35.,35.,2.);s.emit()
owner.open_workspace()
_result=json.dumps({'document':doc.to_data(),'family':%r,'editor_id':id(s.editor),'document_id':id(doc)})
'''%(family,family)

SAVE_CONTROL='''assert not hasattr(sys,'_portal_gui_control_r28')
saved=sys._portal_anchor_r28
profile=s.portal_profile
assert profile is saved['profiles']['portal_profile'] and 'ui_offset' not in profile.__dict__
assert s.portal_preview is not None and s.portal_controls is not None
sys._portal_gui_control_r28={'profile':profile,'original_resolved':profile.ui_offset,
 'editor':s.editor,'document':s.editor.document,'data':copy.deepcopy(s.editor.document.to_data()),
 'groups':dict(s.portal_preview.groups),'models':dict(profile.models),
 'camera':(s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot)}
_result=json.dumps({'inherited_offset':True,'profile_identity':profile.identity,'group_count':len(s.portal_preview.groups)})
'''

ASSERT_CONTROL='''control=sys._portal_gui_control_r28
assert s.portal_profile is control['profile'] and s.portal_profile.models==control['models']
assert s.editor is control['editor'] and s.editor.document is control['document']
assert s.editor.document.to_data()==control['data']
assert set(s.portal_preview.groups)==set(control['groups'])
assert all(s.portal_preview.groups[key] is value for key,value in control['groups'].items())
assert (s.camera_yaw,s.camera_pitch,s.zoom,s.camera_pan,s.camera_pivot)==control['camera']
'''

APPLY=ASSERT_CONTROL+'''def private_portal_gui_offset(size):
 gui=Theme.native_gui_scale
 assert isinstance(gui,(int,long,float)) and not isinstance(gui,bool) and gui>=1. and gui==round(gui)
 return (0.,min(size)/float(gui))
control['profile'].ui_offset=private_portal_gui_offset
_result=json.dumps({'instance_only':True,'gui':Theme.native_gui_scale,'production_modified':False})
'''

RESTORE_CONTROL='''control=getattr(sys,'_portal_gui_control_r28',None)
if control is not None:
 profile=control['profile']
 if 'ui_offset' in profile.__dict__:del profile.ui_offset
 assert profile.ui_offset is control['original_resolved']
_result=json.dumps({'restored':True,'exact_inherited_method':True})
'''

REMOVE_CONTROL=RESTORE_CONTROL+'''if control is not None:
'''+''.join(' '+line+'\n' for line in ASSERT_CONTROL.splitlines())+''' del sys._portal_gui_control_r28
_result=json.dumps({'restored':True,'marker_removed':True})
'''

STATE='''saved=sys._portal_anchor_r28
assert s is saved['session'] and s.portal_profile is saved['profiles']['portal_profile']
assert b.factory is saved['factory']
assert s.library is saved['library'] and s.library==saved['library_data'] and s.library_serial==saved['library_serial']
assert b.load_library()==saved['stored_library']
preview=s.portal_preview;controls=s.portal_controls;profile=s.portal_profile
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
row={'editor_id':id(s.editor),'document_id':id(s.editor.document),'document':s.editor.document.to_data(),
 'workspace':navigator.contains('modern_projection_workspace'),'page':s.page,
 'preview_ready':s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty,
 'preview_error':s.preview_error,'portal_error':s.portal_error,
 'portal_profile_identity':profile.identity,'profile_models':profile.models,
 'instance_offset':'ui_offset' in profile.__dict__,'default_profile_same_object':True,
 'theme_native_gui_scale':Theme.native_gui_scale,'theme_scale':Theme.scale,
 'native_screen':{'logical':game.GetScreenSize(),'physical':game.GetScreenViewInfo()},
 'plan_ready':preview is not None and preview.published==preview.signature(),
 'controls_pending':controls.pending if controls is not None else True,
 'controls_error':str(controls.error or '') if controls is not None else '',
 'plan_error':str(preview.error or '') if preview is not None else '',
 'groups':[{'key':repr(key),'object_id':id(group),'model':group.model_name,'origin':group.origin,'uniforms':group.uniforms} for key,group in sorted(preview.groups.items())] if preview is not None else [],
 'camera_pose':s.camera_pose,'camera_pan':s.camera_pan,'camera_pivot':s.camera_pivot,
 'projection_active':s.projection_active,'world_actors':len(b.projection_entities)+int(bool(b.entity))}
_result=json.dumps(row)
'''

GEOMETRY='''row=json.loads(_result)
from modern_projection.projection.liquid_viewport import group_view
assert camera_values['portal_profile'] is s.portal_profile
assert camera_values['portal_controls'] is s.portal_controls
viewport=(camera_values['width']*Theme.scale,camera_values['height']*Theme.scale)
unit=camera_values['unit']()
entries=[]
for key,entry in sorted(s.portal_controls.registry.items(),key=lambda pair:repr(pair[0])):
 group=s.portal_preview.groups.get(key)
 if group is None:continue
 view=group_view(group.origin,actual_camera,s.scene_origin,s.scene_size,viewport,unit)
 offset=s.portal_profile.ui_offset(view.size)
 predicted=(tuple(view.position[axis]+offset[axis] for axis in range(2)),view.size)
 legacy=(view.position[0],view.position[1]+min(view.size)/4.)
 corrected=(view.position[0],view.position[1]+min(view.size)/float(Theme.native_gui_scale))
 renderer=entry.get('renderer');slots=[]
 for index,ref in enumerate(entry['dolls']):
  control=ref.current;surface=entry['surfaces'][index].current
  slots.append({'slot':index,'position':control.GetPosition(),'global_position':control.GetGlobalPosition(),
   'size':control.GetSize(),'native_visible':control.GetVisible(),'surface_visible':surface.GetVisible(),
   'renderer_visible':renderer.visible[index],'native_model_id':control.asNeteasePaperDoll().GetModelId()})
 entries.append({'key':repr(key),'geometry':entry.get('geometry'),'predicted_geometry':predicted,
  'legacy_position':legacy,'corrected_position':corrected,'size':view.size,'offset':offset,
  'clipped':view.clipped,'distance':view.distance,'clip_offset':entry.get('clip_offset'),
  'ready_request':entry.get('ready_request') is not None,'front':renderer.front,'slots':slots})
row['portal_geometry']=entries
row['mounted_viewport']={'size':viewport,'unit':unit,'scene_origin':s.scene_origin,'scene_size':s.scene_size}
_result=json.dumps(row)
'''

RESTORE_SESSION=RESTORE_CONTROL+'''saved=getattr(sys,'_portal_anchor_r28',None)
if saved is not None:
 b.stop_projection();s.tiles.cancel();b.factory=saved['factory'];s.editor=saved['editor']
 for key,value in saved['fields'].items():setattr(s,key,value)
 s.pending_confirm=None
 if saved['workspace'] and navigator.top is None:owner.open_workspace()
 if not saved['workspace'] and navigator.top is not None:navigator.pop()
 s.model_revision=None;s.camera_reset_revision+=1;s.refresh_preview();s.emit()
_result=True
'''

AUDIT='''saved=sys._portal_anchor_r28
assert s is saved['session'] and s.editor is saved['editor'] and s.editor.document is saved['document']
assert s.editor.document.to_data()==saved['data']
assert s.editor.undo_stack==saved['undo'] and s.editor.redo_stack==saved['redo']
assert set(s.editor.selection)==saved['selection'] and s.editor.revision==saved['revision']
assert b.factory is saved['factory'] and all(getattr(s,key) is value for key,value in saved['profiles'].items())
assert not [key for key,value in saved['fields'].items() if getattr(s,key)!=value]
assert s.library is saved['library'] and s.library==saved['library_data'] and s.library_serial==saved['library_serial']
assert b.load_library()==saved['stored_library']
assert not s.projection_active and not b.preparing_entity and not b.entity and not b.projection_entities
assert navigator.contains('modern_projection_workspace')==saved['workspace'] and not navigator.is_transitioning
profile=saved['profiles']['portal_profile']
assert 'ui_offset' not in profile.__dict__
_result=json.dumps({'restored':True,'original_document':s.editor.document.to_data(),
 'editor_id':id(s.editor),'document_id':id(s.editor.document),'profiles_same':True,
 'library_equal':True,'undo_redo_selection_equal':True,'fields_equal':True,
 'preview_ready':not saved['workspace'] or (s.ready and not s.preview_pending and not s.tiles.running and not s.tiles.dirty)})
'''
REMOVE="if hasattr(sys,'_portal_gui_control_r28'):del sys._portal_gui_control_r28\ndel sys._portal_anchor_r28\n_result=True\n"
