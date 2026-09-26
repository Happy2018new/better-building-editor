"""Live world-outline validation: temporary ghosts and camera only; no block writes."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_large_editor import snapshot
from native_input_mode import key, state, open_workspace
from mcdk import Client, return_value


def server(code):
    with Client() as client:
        return return_value(client.call('execute_code', {'code':
            'import mod.server.extraServerApi as api\nf=api.GetEngineCompFactory()\np=api.GetPlayerList()[0]\n'+code,
            'is_client':False,'direct_return':True}))


def wait_active():
    for unused in range(35):
        result = game('b=s.bridge\no=b.projection_outline\n_result={"active":s.projection_active,"preparing":b.preparing_entity,"outline":o.entity,"bounds":o.bounds,"ghost":b.entity,"chunks":len(b.projection_entities)}')
        if result['active'] and not result['preparing'] and result['outline']:
            return result
        time.sleep(.15)
    raise AssertionError(result)


def aim(offset, target=None):
    pos=game('''b=s.bridge
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
o,size=b.projection_outline.bounds
target='''+repr(target)+'''
center=tuple(o[i]+(target[i] if target else size[i]*.5) for i in range(3))
offset='''+repr(offset)+'''
pos=tuple(center[i]+offset[i] for i in range(3))
rot=api.GetRotFromDir(tuple(center[i]-pos[i] for i in range(3)))
api._outline_test_view=(pos,(rot[0],rot[1]+180.,0.))
cam.SetCameraPos(pos)
cam.SetCameraRotation((rot[0],rot[1]+180.,0.))
_result=pos
''')
    # Native actor rendering also uses the player's loaded area, not just a
    # detached camera. Move only the managed-world test player, restored below.
    server('f.CreateFly(p).ChangePlayerFlyState(True)\nf.CreatePos(p).SetFootPos('+repr(tuple(pos))+')\n_result=True')
    time.sleep(.4)
    game('cam=s.bridge.factory.CreateCamera(s.bridge.level)\ncam.SetCameraPos(api._outline_test_view[0])\ncam.SetCameraRotation(api._outline_test_view[1])\n_result=True')
    time.sleep(.4)


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_touch=state()['simulated']
    if not game('from modern_projection.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):
        open_workspace();time.sleep(2.)
    server('api._outline_saved_player=(f.CreatePos(p).GetFootPos(),f.CreateFly(p).IsPlayerFlying())\n_result=True')
    game('''b=s.bridge
api._outline_test_saved=(s.editor,s.origin,s.projection_outline,s.spectrum_speed,s.reduced_motion,b.save_preferences,s.page)
api._outline_test_geometry=b.geometry
api._outline_test_builds=0
api._outline_test_preferences={}
def wrap_geometry(original, counter):
    def geometry(*args,**kwargs):
        counter._outline_test_builds+=1
        return original(*args,**kwargs)
    return geometry
def wrap_save(target):
    def save(value):
        target._outline_test_preferences=value
        return True
    return save
geometry=wrap_geometry(b.geometry,api)
save=wrap_save(api)
b.geometry=geometry
b.save_preferences=save
cam=b.factory.CreateCamera(b.level)
api._outline_test_camera=(cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw())
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
r=b.factory.CreateActorRender(b.player)
api._outline_test_distance=r.GetEntityRenderDistance()
r.SetEntityRenderDistance(256.)
s.projection_outline=True
s.reduced_motion=False
s.spectrum_speed=3.
s.origin=tuple(v+(18 if i==1 else 0) for i,v in enumerate(b.player_origin()))
s.set("page","projection")
_result=True
''')
    try:
        time.sleep(.8)
        snapshot('stage48_projection_settings')
        game('s.bridge.project()\n_result=True')
        first=wait_active()
        ui.check('default world projection has one outline with exact draft size',first['bounds'][1]==[24,16,24])
        game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True')
        aim((26.,16.,-30.))
        snapshot('stage48_world_outline_a')
        time.sleep(.4)
        snapshot('stage48_world_outline_b')
        before=game('_result=api._outline_test_builds')
        game('s.set("projection_outline",False)\n_result=True')
        ui.check('hide preserves ghost and performs no geometry build',game('_result=(s.bridge.entity=='+repr(first['ghost'])+' and s.bridge.projection_outline.entity is None and api._outline_test_builds=='+str(before)+')'))
        snapshot('stage48_world_outline_off')
        game('s.set("projection_outline",True)\n_result=True')
        wait_active()
        ui.check('toggle saves preference',game('_result=api._outline_test_preferences.get("projection_outline") is True'))
        game('s.set("reduced_motion",True)\n_result=True')
        ui.check('reduced motion freezes only shader phase',game('_result=s.bridge.factory.CreateActorRender(s.bridge.projection_outline.entity).GetEntityExtraUniforms(1)[3]==0.'))
        game('s.set("reduced_motion",False)\ns.range_value("spectrum_speed",6.,False)\n_result=True')
        time.sleep(.4)
        ui.check('speed changes shader without rebuilding projection',game('_result=s.bridge.factory.CreateActorRender(s.bridge.projection_outline.entity).GetEntityExtraUniforms(1)[3]==1. and api._outline_test_builds=='+str(before)))
        game('''from modern_projection.projection.model import Document,Editor
s.editor=Editor(Document((4,6,8),dict(((x,y,z),("minecraft:quartz_block",0)) for x in range(4) for y in range(6) for z in range(8))))
s.bridge.project()
_result=True
''')
        wait_active(); aim((10.,8.,-13.))
        snapshot('stage48_outline_asymmetric')
        game('''s.bridge.stop_projection()
s.editor=Editor(Document((64,128,64),{(0,0,0):("minecraft:quartz_block",0),(16,0,0):("minecraft:gold_block",0),(63,127,63):("minecraft:quartz_block",0)}))
s.bridge.project()
_result=True
''')
        maximum=wait_active()
        ui.check('maximum streamed projection has full 64x128x64 bounds',maximum['bounds'][1]==[64,128,64] and maximum['ghost'] is None)
        aim((110.,65.,-125.));time.sleep(.8)
        snapshot('stage48_outline_maximum')
        # Inspect a seam between independent native chunk models up close.
        game('''b=s.bridge
b.stop_projection()
s.editor=Editor(Document((64,128,64),dict(((x,y,z),("minecraft:gold_block" if x>=16 else "minecraft:quartz_block",0)) for x in range(14,18) for y in range(3) for z in range(3))))
b.project()
_result=True
''')
        wait_active()
        aim((7.,5.,-10.),(16.,1.5,1.5))
        for unused in range(30):
            if game('_result=len(s.bridge.projection_entities)>=2'):break
            time.sleep(.2)
        ui.check('adjacent world projection chunks both load',game('_result=len(s.bridge.projection_entities)>=2'))
        snapshot('stage48_outline_chunk_seam')
        game('s.bridge.stop_projection()\n_result=True');time.sleep(.4)
        ui.check('stop clears complete and streamed ghost actors plus outline',game('_result=not s.projection_active and s.bridge.entity is None and not s.bridge.projection_entities and s.bridge.projection_outline.entity is None and s.bridge.projection_outline.bounds is None'))
        # Use the actual button in both PC and F11 native touch mode.
        for touch in (False,True):
            if state()['simulated']!=touch:
                key('f11');time.sleep(.3)
                assert state()['simulated']==touch
            open_workspace();time.sleep(2.5)
            node=next(n for n in ui.nodes('Action') if n['props'].get('label')=='炫彩范围框')
            button=ui.nodes('Button',node)[0]
            ctrl=ui.call('native_control',button['id'])['result']
            left,top,width,height=capture._window_rect(window['hwnd'])
            scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
            x,y=[int(a+(b+c/2)*scale) for a,b,c in zip((left,top),ctrl['global'],ctrl['size'])]
            assert left<=x<left+width and top<=y<top+height
            assert capture.user32.GetForegroundWindow()==window['hwnd']
            previous=game('_result=s.projection_outline')
            capture.user32.SetCursorPos(x,y);time.sleep(.3)
            capture.user32.mouse_event(2,0,0,0,0)
            try:time.sleep(.08)
            finally:capture.user32.mouse_event(4,0,0,0,0)
            time.sleep(.4)
            ui.check('actual outline toggle touch='+str(touch),game('_result=s.projection_outline')!=previous)
            game('from modern_projection.pyreact import navigator\nnavigator.pop()\n_result=True');time.sleep(.3)
    finally:
        (ui.OUT/'stage48_outline_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
        game('''b=s.bridge
b.stop_projection()
s.editor,s.origin,s.projection_outline,s.spectrum_speed,s.reduced_motion,b.save_preferences,s.page=api._outline_test_saved
b.geometry=api._outline_test_geometry
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(api._outline_test_camera[0])
cam.LockModCameraYaw(api._outline_test_camera[1])
b.factory.CreateActorRender(b.player).SetEntityRenderDistance(api._outline_test_distance)
s.refresh_preview()
s.emit()
_result=True
''')
        game('from modern_projection.pyreact import navigator\nif navigator.contains("modern_projection_workspace"): navigator.pop()\n_result=True')
        server('f.CreatePos(p).SetFootPos(api._outline_saved_player[0])\nf.CreateFly(p).ChangePlayerFlyState(api._outline_saved_player[1])\n_result=True')
        if state()['simulated']!=original_touch:
            key('f11');time.sleep(.3)
            assert state()['simulated']==original_touch
        open_workspace();time.sleep(1.)


if __name__=='__main__':
    main()
