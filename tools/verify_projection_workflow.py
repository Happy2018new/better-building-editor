"""Projection workflow: native Esc/touch, grouped settings and authorized world writes.

Run only in the isolated managed test world. Restores the small test area,
player permissions/mode, editor, camera and preference writer in finally.
"""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_projection_outline import server, game
from verify_large_editor import snapshot
from native_input_mode import key, state, open_workspace


def wait_done():
    for unused in range(160):
        value=game('_result={"busy":s.busy,"message":s.editor.message,"progress":s.progress}')
        if not value['busy']:return value
        time.sleep(.1)
    raise AssertionError(value)


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_touch=state()['simulated']
    game('''api._workflow_saved=(s.editor,s.origin,s.apply_air,s.page,s.spectrum_speed,s.bridge.save_preferences,s.camera_pan,s.projection_outline,s.projection_missing)
s.projection_outline=True
s.projection_missing=False
def discard_preferences(data):return True
s.bridge.save_preferences=discard_preferences
_result=True''')
    origin=server('''from HelloScript.HelloServerSystem import WorldAdapter
host=api.GetSystem("ModernProjection","HelloServerSystem")
a=WorldAdapter(p)
foot=tuple(int(v) for v in f.CreatePos(p).GetFootPos())
choices=[(foot[0]+dx,foot[1]+dy,foot[2]) for dy in (20,32,40) for dx in (-16,-32,0)]
for origin in choices:
    cells=[(origin[0]+x,origin[1],origin[2]) for x in range(24)]
    saved=[(pos,a.read(pos)) for pos in cells]
    if all(value==("minecraft:air",0) for pos,value in saved):break
assert all(value==("minecraft:air",0) for pos,value in saved)
api._workflow_saved=(saved,f.CreateGame(api.GetLevelId()).GetPlayerGameType(p),f.CreatePlayer(p).GetPlayerAbilities())
_result=origin''')
    def exists():return game('from HelloScript.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")')
    def reopen():
        if not exists():open_workspace();time.sleep(2.5)
    def actual_click(node):
        button=ui.nodes('Button',node)[0]
        native=ui.call('native_control',button['id'])['result']
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        point=tuple(int(a+(b+d/2)*scale) for a,b,d in zip((left,top),native['global'],native['size']))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        capture.user32.SetCursorPos(*point);time.sleep(.2)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.09)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.65)
        actual=capture.POINT();capture.user32.GetCursorPos(capture.ctypes.byref(actual))
        assert abs(actual.x-point[0])<3 and abs(actual.y-point[1])<3,'Pointer moved during test'
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        return button['id']
    def action(label):return next(n for n in ui.nodes('Action') if n['props'].get('label')==label)
    def feedback(identity):
        return game('''from HelloScript.pyreact.debug import find_fiber_by_id
f=find_fiber_by_id(api.GetTopScreen()._root_fiber,%r)
_result=f.parent_fiber.hooks[3]['value']
'''%identity)
    try:
        reopen()
        key('esc');time.sleep(.6)
        ui.check('native Esc closes workspace through exit animation',not exists())
        reopen()
        game('s.confirm("Test cancellation",lambda:None)\n_result=True');time.sleep(.4)
        key('esc');time.sleep(.5)
        ui.check('Esc dismisses confirmation first and keeps workspace',exists() and game('_result=s.pending_confirm is None'))
        game('s.set("page","projection")\n_result=True');time.sleep(3.)
        snapshot('stage50_projection_display')
        settings=ui.nodes('ProjectionSettings')[0]
        ui.check('display groups contain outline speed and no world-write actions',
                 any(n['props'].get('label')=='炫彩流动速度' for n in ui.nodes('Range',settings)) and
                 not any(n['props'].get('label')=='应用到世界' for n in ui.nodes('Action',settings)))
        speed=next(n for n in ui.nodes('Range',settings) if n['props'].get('label')=='炫彩流动速度')
        ui.call('set_slider',ui.nodes('Slider',speed)[0]['id'],.6);time.sleep(.3)
        ui.check('projection page adjusts shared spectrum speed',abs(game('_result=s.spectrum_speed')-3.7)<.05)
        ui.click('辅助');snapshot('stage50_projection_assist')
        ui.check('assist contains progress and materials', '所需材料' in ui.labels(ui.nodes('ProjectionSettings')[0]))
        ui.click('写入');snapshot('stage50_projection_world')
        ui.check('world undo is removed from settings',not any(n['props'].get('label')=='撤销世界写入' for n in ui.nodes('Action')))

        # Submit old and modern material IDs via the actual client network path.
        game('''from HelloScript.projection.model import Document,Editor
values=[("minecraft:stone",0),("minecraft:planks",2),("minecraft:wool",14),("minecraft:concrete",15),("minecraft:log",5),("minecraft:oak_stairs",2),
        ("minecraft:stonebrick",0),("minecraft:grass",0),("minecraft:leaves",4),("minecraft:leaves",8),("minecraft:log",13),("minecraft:log",9),("minecraft:log2",4),("minecraft:spruce_log",2)]
s.origin='''+repr(tuple(origin))+'''
s.editor=Editor(Document((24,1,1),dict(((i,0,0),value) for i,value in enumerate(values))))
s.apply_air=False
s.refresh_preview()
s.emit()
_result=True''');time.sleep(.8)
        actual_click(action('应用到世界'))
        actual_click(action('确认继续'))
        result=wait_done()
        ui.check('actual apply button sends building and completes authorized write','已写入' in result['message'])
        data=server('a=WorldAdapter(p)\n_result=[a.read((%d+x,%d,%d)) for x in range(14)]'%tuple(origin))
        ui.check('legacy wool/planks become correct modern blocks; log/stair state retained',data[1]==['minecraft:birch_planks',0] and data[2]==['minecraft:red_wool',0] and data[3]==['minecraft:black_concrete',0] and data[4]==['minecraft:spruce_log',1] and data[5]==['minecraft:oak_stairs',2])
        ui.check('renamed default palette and all log axes survive world write',data[6]==['minecraft:stone_bricks',0] and data[7]==['minecraft:grass_block',0] and data[10:]==[['minecraft:spruce_wood',0],['minecraft:spruce_log',2],['minecraft:acacia_log',1],['minecraft:spruce_log',2]])
        flags=server('state=f.CreateBlockState(api.GetLevelId())\n_result=[state.GetBlockStates((%d+x,%d,%d),a.dimension) for x in (8,9)]'%tuple(origin))
        ui.check('legacy leaves preserve persistent and update flags',flags[0]['persistent_bit'] and flags[1]['update_bit'])
        game('s.bridge.check_progress()\n_result=True');result=wait_done()
        ui.check('progress understands legacy material aliases',result['progress']['correct']==14)
        # Actual server permission APIs, not client-provided authorization flags.
        for field,change,restore in (
            ('survival','SetPlayerGameType(0)','SetPlayerGameType(1)'),
            ('operator','SetOperatorCommandAbility(False)','SetOperatorCommandAbility(True)'),
            ('build','SetBuildAbility(False)','SetBuildAbility(True)'),
            ('mine','SetMineAbility(False)','SetMineAbility(True)')):
            server('f.CreatePlayer(p).'+change+'\n_result=True')
            game('s.bridge.apply_world()\n_result=True');result=wait_done()
            ui.check('server rejects missing '+field+' permission before upload allocation','权限' in result['message'] and server('_result=not host.uploads and not host.jobs'))
            server('f.CreatePlayer(p).'+restore+'\n_result=True')
        spare=(origin[0]+23,origin[1],origin[2])
        server('a=WorldAdapter(p)\na.write('+repr(spare)+',("minecraft:gold_block",0))\n_result=True')
        game('s.apply_air=True\ns.bridge.apply_world()\n_result=True');result=wait_done()
        ui.check('air synchronization clears only corresponding draft air','已写入' in result['message'] and server('a=WorldAdapter(p)\n_result=a.read('+repr(spare)+')')==['minecraft:air',0])
        game('s.bridge.project()\n_result=True');time.sleep(.6)
        actors=game('_result=[s.bridge.entity,s.bridge.projection_outline.entity]')
        ui.check('projection and rainbow outline created locally',all(actors))
        ui.check('server entity registry contains neither client actor',server('_result=all(api.GetEngineCompFactory().CreateEngineType(e).GetEngineTypeStr() is None for e in '+repr(actors)+')'))
        game('s.bridge.stop_projection()\ns.set("page","workspace")\n_result=True');time.sleep(.8)

        for touch in (False,True):
            key('esc');time.sleep(.5)
            if state()['simulated']!=touch:key('f11');time.sleep(.3)
            assert state()['simulated']==touch
            reopen()
            identity=actual_click(action('左移'))
            ui.check('touch release clears action hover' if touch else 'PC release retains mouse hover', feedback(identity)==('default' if touch else 'hover'))
            if touch:snapshot('stage50_touch_button_released')
            segment=ui.nodes('Segments',ui.nodes('PageNavigation')[0])[0]
            target=next(n for n in ui.nodes('JellyButton',segment) if n.get('key')=='workspace')
            identity=actual_click(target)
            ui.check('touch segment clears transient hover' if touch else 'PC segment retains hover',feedback(identity)==('default' if touch else 'hover'))
    finally:
        (ui.OUT/'stage50_workflow_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
        game('s.bridge.cancel_world()\ns.bridge.stop_projection()\n_result=True')
        wait_done()
        server('''a=WorldAdapter(p)
saved,mode,abilities=api._workflow_saved
for pos,value in saved:a.write(pos,value)
player=f.CreatePlayer(p)
player.SetPlayerGameType(mode)
player.SetOperatorCommandAbility(abilities['op'])
player.SetBuildAbility(abilities['build'])
player.SetMineAbility(abilities['mine'])
_result=True''')
        game('s.editor,s.origin,s.apply_air,s.page,s.spectrum_speed,s.bridge.save_preferences,s.camera_pan,s.projection_outline,s.projection_missing=api._workflow_saved\ns.set("pending_confirm",None)\ns.refresh_preview()\ns.emit()\n_result=True')
        if exists():key('esc');time.sleep(.5)
        if state()['simulated']!=original_touch:key('f11');time.sleep(.3)
        reopen()


if __name__=='__main__':main()
