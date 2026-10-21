from modern_projection.pyreact import navigator
saved=sys._r27_water_anchor_ui
renderer=saved['renderer']
refs=saved['refs'] or []
native=[]
for ref in refs+[saved.get('stone')]:
 if ref is not None and ref.current is not None:
  control=ref.current
  native.append({'position':control.GetPosition(),'global_position':control.GetGlobalPosition(),
   'size':control.GetSize(),'model_id':control.asNeteasePaperDoll().GetModelId()})
state=None if renderer is None else {'front':renderer.front,'ids':renderer.ids,'visible':renderer.visible,
 'pending':renderer.pending is not None,'error':renderer.error,'closed':renderer.closed,
 'native_ids':[doll.GetModelId() for doll in renderer.dolls]}
ready=bool(renderer is not None and saved['ready'] and saved['stable_frames']>=3
 and navigator.top and navigator.top.key=='r27_water_anchor_diagnostic' and not navigator.is_transitioning)
_result=json.dumps({'ready':ready,'stable_frames':saved['stable_frames'],'frames':saved['frames'],
 'config':saved['config'],'native':native,'renderer':state,'logical':factory.CreateGame(level).GetScreenSize(),
 'screen_view_info':factory.CreateGame(level).GetScreenViewInfo()})
