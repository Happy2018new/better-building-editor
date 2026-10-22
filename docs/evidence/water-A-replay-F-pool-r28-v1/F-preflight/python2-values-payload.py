import json,sys
sys.path.insert(0,sys.argv[1])
from modern_projection.projection import liquid_product_deployment as product
from modern_projection.projection.debug_product_water_blueprints import CASES
from modern_projection.projection.liquid_render_plan import iter_groups,render_steps
from modern_projection.projection.liquid_transport import validate_uniforms
request=json.loads(sys.stdin.read())
class FakeEditor(object):
 document=None
class FakeSession(object):
 grid=True
 liquid_profile=product.production_profile(product.TARGET_ENGINE_VERSION)
 editor=FakeEditor()
 def _loaded(self,doc):self.editor.document=doc
 def camera_view(self,*pose):self.camera_pose=pose
 def emit(self):pass
s=FakeSession()
original=s.liquid_profile
exec request['profile']
assert s.liquid_profile is not original
assert s.liquid_profile.ui_offset_for_gui((300.,400.),2)==(0.,150.)
assert set(request['cases'])==set(row['id'] for row in CASES)
sys._blueprint_qa_nonce=0
rows=[]
for case in request['cases']:
 controls=('wet','dry','liquid_only','water_only','rearless','empty') if case.startswith('wet_') else ('wet','dry')
 for control in controls:
  pose=(0.,0.,3.) if case.startswith('wet_') else (35.,25.,4.6)
  exec request['load'] % ((case,control,pose),)
  doc=s.editor.document
  groups=list(iter_groups(doc,s.liquid_profile.provider_factory(doc)))
  packed=list(render_steps(groups,s.liquid_profile.models,1.,s.liquid_profile.max_groups))
  for row in packed:validate_uniforms(row.uniforms)
  assert len(groups)<=256
  rows.append({'case':case,'control':control,'cells':len(doc.blocks),'groups':len(groups),'packed':len(packed)})
assert len(rows)==54
s.liquid_profile,s.grid=sys._product_water_saved_profile
del sys._product_water_saved_profile
assert s.liquid_profile is original and s.grid is True
print(json.dumps({'passed':True,'rows':rows,'profile_restored':True,'SDK_called':False,'UI_and_session_fake':True}))
