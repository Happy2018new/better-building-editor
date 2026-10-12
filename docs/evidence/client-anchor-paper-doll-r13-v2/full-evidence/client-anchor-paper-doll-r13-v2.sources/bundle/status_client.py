saved=sys._client_anchor_ui_probe
assert saved['nonce']=='91e00c4b19ed4ef68850a59a69f64f3d'
ref=saved.get('ref')
root_ref=saved.get('root_ref')
ready=bool(navigator.top and navigator.top.key==saved['key'] and not navigator.is_transitioning and ref and ref.current and root_ref and root_ref.current and len(saved.get('marker_refs',[]))==4 and all(marker.current for marker in saved['marker_refs']))
model=None
native_layout=None
now=time.time()
if ready:
 host=api.GetTopScreen()
 assert host is not None and host is navigator.top._host
 viewport=host.GetBaseUIControl(host._root_path)
 assert viewport is not None
 def native_rect(control):
  position=control.GetGlobalPosition()
  size=control.GetSize()
  return {'x':position[0],'y':position[1],'width':size[0],'height':size[1],'path':control.GetPath()}
 game=b.factory.CreateGame(b.level)
 native_layout={'paper_doll':native_rect(ref.current),'root':native_rect(root_ref.current),
  'viewport':native_rect(viewport),'screen_size_api_observed':game.GetScreenSize(),
  'screen_view_api_observed':game.GetScreenViewInfo(),
  'markers':[dict(marker,rect=native_rect(saved['marker_refs'][index].current)) for index,marker in enumerate(saved['markers'])],
  'declared_size':saved['declared_size'],'size_inputs':saved['size_inputs']}
 if saved.get('ready_first_seen') is None:saved['ready_first_seen']=now
 if now>=max(saved['ready_first_seen']+.15,saved.get('model_read_after',0.)):
  model=ref.current.asNeteasePaperDoll().GetModelId()
else:saved['ready_first_seen']=None
_result=json.dumps({'ready':ready,'control':saved['control'],'model_id':model,'clock':now,
 'native_layout':native_layout,
 'model_read_deferred':ready and model is None,
 'actor':saved['actor'],'journal':saved['journal'],'body':saved['body'],
 'version':api.GetMinecraftVersion(),'attachments':saved['attachments'],'ui_params':saved['ui_params']})
