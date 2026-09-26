"""Native PC/F11 biome choices and world projection screenshots, no world writes."""
import json
import time
import sys
import verify_ui as ui
from verify_font_share_polish import game
from verify_complete_projection import snapshot
from native_input_mode import set_touch, state
from verify_projection_outline import server, aim
from mcdk import Client
from PIL import Image, ImageChops, ImageStat


def action(label, root=None):
    return next(n for n in ui.nodes('Action', root) if n['props'].get('label')==label)


def native_click(node):
    control = ui.call('native_control',ui.nodes('Button',node)[0]['id'])['result']
    size = ui.nodes('SafeArea')[0]['children'][0]['layout']
    pos = [(control['global'][i]+control['size'][i]*.5)/size[key] for i,key in enumerate(('width','height'))]
    assert all(0. < v < 1. for v in pos), pos
    print('CLICK',node['props'].get('label'),pos,flush=True)
    with Client() as client:
        result = client.call('mc_input', {'op':'/click','args':{'at':pos}})
    assert not result.get('isError') and result.get('structuredContent',{}).get('ok'), result
    time.sleep(.5)


def main():
    touch = state()['simulated']
    server('api._biome_player_saved=(f.CreatePos(p).GetFootPos(),f.CreateFly(p).IsPlayerFlying())\n_result=True')
    saved = game('''b=s.bridge
cam=b.factory.CreateCamera(b.level)
api._biome_control_saved=(s.editor.document.biome,s.origin,s.opacity,s.page,s.inspector,s.projection_outline,s.projection_missing)
api._biome_camera_saved=(cam.IsModCameraLockPitch(),cam.IsModCameraLockYaw())
_result=True''')
    try:
        for touch_mode in (() if '--world-only' in sys.argv else (True,) if '--touch-only' in sys.argv else (False,True)):
            set_touch(touch_mode)
            game('s.set("page","workspace")\ns.set("inspector","layers")\n_result=True')
            time.sleep(1)
            settings=ui.nodes('BiomeTintSettings')[0]
            if len(ui.nodes('Action',settings))==1:
                native_click(ui.nodes('Action',settings)[0])
            layers=ui.nodes('Layers')[0]
            ui.call('scroll',ui.nodes('VisibleScroll',layers)[0]['id'],0)
            time.sleep(.3)
            settings=ui.nodes('BiomeTintSettings')[0]
            snapshot('biome65_before_'+('touch' if touch_mode else 'pc'))
            native_click(action('森林',settings))
            snapshot('biome65_clicked_'+('touch' if touch_mode else 'pc'))
            ui.check(('F11' if touch_mode else 'PC')+' native biome button sets forest',
                     game('_result=s.editor.document.biome')=='forest')
            snapshot('biome65_controls_'+('touch' if touch_mode else 'pc'))
            # Use a second real button so a preselected forest cannot pass alone.
            native_click(action('草原',ui.nodes('BiomeTintSettings')[0]))
            ui.check(('F11' if touch_mode else 'PC')+' native selection switches back',
                     game('_result=s.editor.document.biome')=='plains')
            native_click(action('使用当前位置的群系',ui.nodes('BiomeTintSettings')[0]))
            ui.check(('F11' if touch_mode else 'PC')+' current biome button samples actual world',game('''from modern_projection.projection.biomes import from_native
expected=from_native(b.factory.CreateBiome(b.level).GetBiomeName(b.player_origin()))
_result=expected is not None and s.editor.document.biome==expected'''))
        set_touch(False)
        game('''s.origin=tuple(v+(18 if i==1 else 0) for i,v in enumerate(b.player_origin()))
s.opacity=.85
s.projection_outline=True
s.projection_missing=False
b.project()
_result=True''')
        for unused in range(100):
            ready=game('_result=s.projection_active and b.entity is not None and b.preparing_entity is None')
            if ready:break
            time.sleep(.2)
        assert ready,'projection did not attach'
        game('''from modern_projection.pyreact import navigator
navigator.pop()
cam=b.factory.CreateCamera(b.level)
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
_result=True''')
        time.sleep(.5)
        aim((-24.,18.,-30.))
        game('b.factory.CreateActorRender(b.projection_outline.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(1.)
        images={}
        for biome in ('desert','jungle','desert'):
            game('s.set_biome('+repr(biome)+')\n_result=True')
            time.sleep(.7)
            name='biome65_world_'+biome
            snapshot(name)
            images[biome]=Image.open(ui.OUT/(name+'.jpg')).convert('RGB')
        game('b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.25)
        snapshot('biome65_world_hidden')
        hidden=Image.open(ui.OUT/'biome65_world_hidden.jpg').convert('RGB')
        mask=list(ImageChops.difference(images['desert'],hidden).getdata())
        pixels=sum(max(p)>25 for p in mask)
        ui.check('world screenshot actually contains the projection',pixels>2000)
        # Require visible model pixels to turn from yellow to green. Global
        # screenshot differences alone can be caused by world chunks loading.
        tinted=sum(max(m)>25 and d[0]>j[0]+10 and j[1]>j[0]*1.4
                   for m,d,j in zip(mask,images['desert'].getdata(),images['jungle'].getdata()))
        ui.check('world projection visible foliage and grass change tint',tinted>400)
        (ui.OUT/'biome65_control_checks.json').write_text(json.dumps(ui.checks,indent=2),encoding='utf8')
    finally:
        game('''from modern_projection.pyreact import navigator
from modern_projection.projection.ui import Workspace
b.stop_projection()
cam=b.factory.CreateCamera(b.level)
cam.ResetCameraPos()
cam.UnDepartCamera()
cam.LockModCameraPitch(api._biome_camera_saved[0])
cam.LockModCameraYaw(api._biome_camera_saved[1])
biome,s.origin,s.opacity,s.page,s.inspector,s.projection_outline,s.projection_missing=api._biome_control_saved
s.set_biome(biome)
if not navigator.contains('modern_projection_workspace'):
    navigator.push(Workspace(session=s),key='modern_projection_workspace')
s.emit()
_result=True''')
        server('f.CreatePos(p).SetFootPos(api._biome_player_saved[0])\nf.CreateFly(p).ChangePlayerFlyState(api._biome_player_saved[1])\n_result=True')
        set_touch(touch)


if __name__ == '__main__':
    main()
