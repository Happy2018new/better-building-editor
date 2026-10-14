import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
cam=b.factory.CreateCamera(b.level)
work=b.projection_work
tracker=b.projection_occupancy
_result=json.dumps({'ready':s.ready,'preview_error':s.preview_error,'pending':s.preview_pending,
 'tile_running':s.tiles.running,'dirty':len(s.tiles.dirty),'model':s.model_name,
 'editor_camera':s.camera_pose,
 'bridge_engine_version':getattr(b,'engine_version',None),
 'geometry_receipts':getattr(sys,'_native_r15_geometry',[]),
 'profile':s.native_render_profile.identity if s.native_render_profile else None,
 'camera':cam.GetPosition(),'rotation':cam.GetCameraRotation(),'screen':b.factory.CreateGame(b.level).GetScreenSize(),
 'top_ui':api.GetTopUI(),'engine':api.GetEngineVersion(),'foot':b.player_position.GetFootPos(),
 'projection':{'active':s.projection_active,'actor':b.entity,'preparing':bool(b.preparing_entity),
  'error':work.error if work else None,'ready':work.ready if work else None,
  'parts':b.context_models.get(b.projection_mesh[1],()) if b.projection_mesh else (),
  'missing':s.projection_missing,'bank':tracker.shader.bank if tracker else None,
  'builds':tracker.builds if tracker else None,'failed':tracker.failed if tracker else None}})
