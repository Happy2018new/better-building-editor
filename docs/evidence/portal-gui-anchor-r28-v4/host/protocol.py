"""Anchor-only gates. Engine TIME and pixel equality are deliberately outside scope."""
from math import isfinite
from camera_gate import camera_settled,assert_frame_identity

SAMPLES=((2,(1280,720)),(3,(1600,900)),(4,(1994,1105)))
FAMILIES=('end_gateway','end_portal')

def near(a,b):
 if isinstance(a,(tuple,list)):
  return isinstance(b,(tuple,list)) and len(a)==len(b) and all(near(x,y) for x,y in zip(a,b))
 return type(a) in (int,float) and type(b) in (int,float) and isfinite(a) and isfinite(b) and abs(a-b)<.001

def ready(row):
 assert not any(row[key] for key in ('preview_error','portal_error','controls_error','plan_error'))
 assert row['default_profile_same_object'] and not row['projection_active'] and row['world_actors']==0
 return row['workspace'] and row['page']=='workspace' and row['preview_ready'] and row['plan_ready'] and not row['controls_pending'] and camera_settled(row)

def require_state(row,expected,family,gui,stage):
 assert ready(row)
 assert row['document']==expected,'Complete typed document changed'
 assert row['theme_native_gui_scale']==gui
 screen=row['native_screen'];assert round(float(screen['physical'][0])/screen['logical'][0])==gui
 assert row['instance_offset']==(stage=='b')
 assert row['groups'] and all(g['model']=='modern_projection_portal_'+family for g in row['groups'])
 groups={g['key']:g for g in row['groups']}
 native={r['key']:r for r in row['native_portal_doll_readback']}
 ancestry={r['key']:r for r in row['owned_surface_native_ancestry']}
 geometry={r['key']:r for r in row['portal_geometry']}
 assert set(geometry)==set(groups)
 for key,geo in geometry.items():
  assert not geo['clipped'] and geo['ready_request']
  assert near(geo['geometry'],geo['predicted_geometry']),'Actual cached rectangle differs from current Scene formula'
  expected_position=geo['corrected_position'] if stage=='b' else geo['legacy_position']
  assert near(geo['geometry'][0],expected_position)
  actual=native[key];active=[r for r in actual['slots'] if r['visible']]
  assert len(active)==1 and active[0]['slot']==actual['front']
  slot=active[0];assert slot['ids_equal'] and slot['native_model_id']!=-1
  assert all(u['equal'] for u in slot['uniforms'])
  surface=next(r for r in ancestry[key]['slots'] if r['slot']==slot['slot'])
  assert surface['direct_surface_visible'] and surface['doll_direct_visible']
  assert all(a['exists'] and a['native_visible'] for a in surface['ancestors_from_actual_surface'])
  doll=next(r for r in geo['slots'] if r['slot']==slot['slot'])
  assert doll['native_visible'] and doll['surface_visible'] and doll['renderer_visible']
  assert doll['native_model_id']==slot['native_model_id']
  assert near(doll['position'],geo['geometry'][0]) and near(doll['size'],geo['geometry'][1])
 return True

def binding(row):
 return [(r['key'],r['front'],[(s['slot'],s['native_model_id'],s['cached_model_id'],s['uniforms'])
  for s in r['slots'] if s['visible']]) for r in row['native_portal_doll_readback'] if any(s['visible'] for s in r['slots'])]

def capture_stable(before,after):
 assert_frame_identity(before,after)
 for key in ('document','groups','native_screen','mounted_viewport','portal_geometry','theme_native_gui_scale',
             'camera_pan','camera_pivot','profile_models','portal_profile_identity','instance_offset'):
  assert before[key]==after[key],key
 assert binding(before)==binding(after),'Actual native binding/uniforms changed during capture'

def triplet(a,b,returned,gui):
 assert_frame_identity(a,b);assert_frame_identity(a,returned)
 for other in (b,returned):
  for key in ('document','groups','native_screen','mounted_viewport','camera_pan','camera_pivot','profile_models','portal_profile_identity'):
   assert a[key]==other[key],key
  assert binding(a)==binding(other)
 ag={r['key']:r for r in a['portal_geometry']};bg={r['key']:r for r in b['portal_geometry']};rg={r['key']:r for r in returned['portal_geometry']}
 assert set(ag)==set(bg)==set(rg)
 deltas=[]
 for key,original in ag.items():
  changed,restored=bg[key],rg[key]
  assert near(original['geometry'],restored['geometry']),'A return rectangle differs'
  assert original['slots']==restored['slots'],'A return actual native rectangle/IDs differ'
  assert near(original['geometry'][1],changed['geometry'][1])
  for x,y in zip(original['slots'],changed['slots']):
   assert x['size']==y['size'] and x['native_model_id']==y['native_model_id']
  delta=min(original['size'])*(1./gui-1./4.)
  assert near(changed['geometry'][0],(original['geometry'][0][0],original['geometry'][0][1]+delta))
  deltas.append({'key':key,'predicted_logical_dy':delta,'actual_logical_dy':changed['geometry'][0][1]-original['geometry'][0][1],
                 'gui4_zero_control':gui==4})
 assert gui!=4 or all(row['predicted_logical_dy']==0. for row in deltas)
 return deltas
