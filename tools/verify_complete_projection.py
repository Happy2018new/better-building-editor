"""Retained full-world ghosts; preserve the current draft, world and camera."""
import base64
import json
import time
import verify_ui as ui
from verify_font_share_polish import game
from mcdk import Client


def snapshot(name):
    with Client() as client:
        result = client.call('capture_game_window', {})
    block = next(b for b in result['content'] if b.get('type') == 'image')
    (ui.OUT/(name+'.jpg')).write_bytes(base64.b64decode(block['data']))


def install():
    for name in ('materials', 'world_projection', 'bridge'):
        path = ui.ROOT / ('behavior_pack/HelloScript/projection/'+name+'.py')
        source = base64.b64encode(path.read_bytes()).decode('ascii')
        game('import base64\nfrom HelloScript.projection import '+name+' as module\n'
             'exec(compile(base64.b64decode('+repr(source)+'),'+repr(str(path))+',"exec"),module.__dict__)\n_result=True')
    game('''from HelloScript.projection.bridge import ClientBridge
b=s.bridge
b.__class__=ClientBridge
# Prior profiling tools restored an old bound method on this instance.
# Let the newly installed class handle actual geometry generation.
if 'geometry' in b.__dict__: del b.__dict__['geometry']
if not hasattr(b,'projection_distance'):b.projection_distance=None
if not hasattr(b,'projection_work'):b.projection_work=None
_result=True''')


def main():
    before = game('''import json
b=s.bridge
api._full_projection_saved=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)
_result={'size':s.editor.document.size,'blocks':len(s.editor.document.blocks),
         'old_tiles':len(b.projection_entities),'active':s.projection_active,
         'distance':b.factory.CreateActorRender(b.player).GetEntityRenderDistance()}
''')
    snapshot('full_projection_before')
    install()
    game('''b=s.bridge
cam=b.factory.CreateCamera(b.level)
api._full_projection_camera=(cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw())
b.project()
_result=True''')
    started=time.perf_counter()
    result = {}
    try:
        for unused in range(300):
            result=game('''b=s.bridge
w=b.projection_work
_result={'total':w.total,'done':len(w.completed),'actors':len(b.projection_entities),
         'failed':len(w.failures),'queued':len(w.queue),'message':s.editor.message,
         'distance':b.factory.CreateActorRender(b.player).GetEntityRenderDistance()}
''')
            if result['total']==result['done']:break
            time.sleep(.1)
        elapsed=time.perf_counter()-started
        ui.check('every occupied tile completes, beyond old 32-tile cap',result['done']==result['total'] and result['actors']>32)
        ui.check('full projection covers native entity distance',result['distance']>=256.)
        result['seconds']=elapsed
        snapshot('full_projection_inside_original_view')
        game('''api._full_projection_entities=dict(b.projection_entities)
api._full_projection_models=dict(b.projection_work.models)
cam=b.factory.CreateCamera(b.level)
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
cam.DepartCamera()
_result=True''')
        # Same loaded player area throughout. Camera-only changes cannot affect
        # which tiles the application keeps; no world blocks or player are moved.
        for label, offset, target in [
            ('inside_upper',(0.,64.,0.),(0.,100.,20.)),
            ('inside_lower',(0.,64.,0.),(20.,8.,0.)),
            ('outside', (100.,100.,-100.), (0.,64.,0.))]:
            game('''o=b.projection_work.origin
offset='''+repr(offset)+'''
target='''+repr(target)+'''
pos=(o[0]+32.+offset[0],o[1]+offset[1],o[2]+32.+offset[2])
point=(o[0]+32.+target[0],o[1]+target[1],o[2]+32.+target[2])
rot=api.GetRotFromDir(tuple(point[i]-pos[i] for i in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.SetCameraPos(pos)
cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=True''')
            time.sleep(.6)
            snapshot('full_projection_'+label)
            ui.check(label+' camera retains the same native actors and meshes',game(
                '_result=b.projection_entities==api._full_projection_entities and b.projection_work.models==api._full_projection_models'))
        result['native_ready']=game('''_result=all(b.factory.CreateActorRender(entity).GetActorBlockGeometryScale(b.projection_work.models[key]) is not None
    for key,entity in b.projection_entities.items())''')
        ui.check('each retained ghost has an attached native geometry',result['native_ready'])
    finally:
        game('''cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(api._full_projection_camera[0])
cam.LockModCameraYaw(api._full_projection_camera[1])
assert json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)==api._full_projection_saved
_result=True''')
        if not before['active']:
            game('b.stop_projection()\n_result=True')
        (ui.OUT/'full_projection_checks.json').write_text(json.dumps(
            {'before':before,'after':result,'checks':ui.checks},ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
