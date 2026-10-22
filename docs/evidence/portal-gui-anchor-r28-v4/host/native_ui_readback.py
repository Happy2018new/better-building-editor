"""Read cached UI renderer values against the owning native controls and model IDs."""
READBACK = '''row=json.loads(_result)
entries=[]
for key,entry in (s.portal_controls.registry.items() if s.portal_controls else ()):
 renderer=entry.get('renderer')
 if renderer is None:continue
 slots=[]
 for index,doll in enumerate(renderer.dolls):
  actual=doll.GetModelId()
  cached=renderer.ids[index]
  uniforms=[]
  for group in range(1,5):
   expected=renderer.uniforms[index].get(group)
   returned=renderer.model_component.GetExtraUniformValue(actual,group) if actual!=-1 else None
   uniforms.append({'group':group,'cached':expected,'native':returned,
    'equal':tuple(returned)==tuple(expected) if returned is not None and expected is not None else returned==expected})
  slots.append({'slot':index,'visible':renderer.visible[index],
   'cached_model_id':cached,'native_model_id':actual,'ids_equal':actual==cached,
   'uniforms':uniforms})
 entries.append({'key':repr(key),'front':renderer.front,'closed':renderer.closed,
  'pending':repr(renderer.pending),'slots':slots})
row['native_portal_doll_readback']=entries
_result=json.dumps(row)
'''
