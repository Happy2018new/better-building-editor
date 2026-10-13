"""Enlarged item animation controls derived from the public source blueprint."""
import time

from capture_native_window import capture
from mcdk import return_value
from item_sprite_capture_contract import camera_matches, scene_layout

FRAMES = 20
INTERVAL = .4
POSITIONS = {'plain': (2, 2, 2), 'enchanted': (5, 2, 2), 'empty': (8, 2, 2)}
EDITOR_POSE = (180., 0., 3.5)
LOAD = '''from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.debug_item_blueprints import IDENTITY,PAIRS
from modern_projection.projection.model import Document
from modern_projection.projection.cell import rebase
source=build(IDENTITY)
pair=PAIRS[0]
positions=%r
doc=Document((11,5,5),name='Public frame animation closeup')
for mode,destination in positions.items():
 old=pair[mode]
 delta=tuple(destination[axis]-old[axis] for axis in range(3))
 for shift in ((0,0,0),(0,0,1)):
  source_pos=tuple(old[axis]+shift[axis] for axis in range(3))
  target_pos=tuple(destination[axis]+shift[axis] for axis in range(3))
  doc.blocks[target_pos]=rebase(source.get(source_pos),delta)
s._loaded(doc)
s.editor.layer=0
s.display_mode('full')
s.grid=False
s.camera_view(*%r)
owner.open_workspace()
_result={'source_fixture':IDENTITY,'source_pair':pair,'positions':positions,'size':doc.size}
'''


def run(check, client, session, report, state_source, camera_source, output, wgc, save, native_reference=False,
        native_player_near=False):
    folder = output/'closeup'
    folder.mkdir()
    closeup = {'schema': 1, 'completed': False, 'captures': [], 'frames_per_route': FRAMES,
               'minimum_duration_seconds': 7., 'minimum_body_side_pixels': 48,
               'declared_editor_pose': EDITOR_POSE, 'cleanup_errors': [], 'routes': ['editor', 'world']}
    report['closeup'] = closeup
    saved = False
    wrote = False
    world_position = None
    def persist():
        save('closeup/report.json', closeup)
        save('report.json', report)
    def state():
        return check.wait('closeup item plan', lambda row: row['plan_ready'] and not row['pending']
            and not row['error'], lambda: check.run(state_source))
    def editor_capture(label):
        before = state()
        start = time.monotonic()
        image = capture(session['session_file'], session['owner'], folder/(label+'.png'), wgc)
        after = state()
        assert scene_layout(before) == scene_layout(after), 'Closeup editor camera/layout drift'
        closeup['captures'].append({'label': label, 'capture': image, 'state': before,
            'state_after': after, 'host_started': start, 'host_finished': time.monotonic()})
        persist()
    world_state = '''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
items=[item for item in owners if item.__class__.__name__=='ItemProjection']
_result={'active':s.projection_active,'preparing':bool(b.preparing_entity),'origin':s.origin,
 'slots':sum(int(row['group'].uniforms[3][1]) for item in items for row in item.renderer.active.values()),
 'pending':bool(b.projection_occupancy and b.projection_occupancy.pending_pair),
 'groups_data':[{'origin':row['group'].origin,'visible':row['visible'],'uniforms':row['group'].uniforms}
  for item in items for row in item.renderer.active.values()]}
'''
    def world_capture(label, slots=2):
        before = check.wait('closeup world '+label, lambda row: row['active'] and not row['preparing']
            and not row['pending'] and row['slots']==slots, lambda: check.run(world_state))
        camera = check.run(camera_source)
        start = time.monotonic()
        image = capture(session['session_file'], session['owner'], folder/(label+'.png'), wgc)
        after = check.run(camera_source)
        assert camera_matches(camera, closeup['world_camera']) and camera_matches(after, closeup['world_camera'])
        closeup['captures'].append({'label': label, 'capture': image, 'state': before,
            'camera_before': camera, 'camera_after': after, 'camera_expected': closeup['world_camera'],
            'host_started': start, 'host_finished': time.monotonic()})
        persist()
    def server(code):
        response = client.call('execute_code', {'is_client': False, 'direct_return': True, 'code':
            "import mod.server.extraServerApi as api\nplayers=api.GetPlayerList()\nassert len(players)==1\n"
            "from modern_projection.server_system import WorldAdapter\nadapter=WorldAdapter(players[0])\n"+code})
        if response.get('isError'):
            raise RuntimeError(response)
        return return_value(response)
    try:
        check.run("assert not hasattr(sys,'_item_closeup_saved')\n"
            "sys._item_closeup_saved={'editor':s.editor,'origin':s.origin,'opacity':s.opacity,"
            "'grid':s.grid,'missing':s.projection_missing,'outline':s.projection_outline}\n_result=True")
        saved = True
        closeup['fixture'] = check.run(LOAD % (POSITIONS, EDITOR_POSE))
        check.wait('exact closeup editor pose', lambda value: value == list(EDITOR_POSE),
                   lambda: check.run('_result=list(s.camera_pose)'))
        time.sleep(.7)
        previous = state()
        check.wait('stable closeup controls', lambda value: scene_layout(value)==scene_layout(previous), state)
        for index in range(FRAMES):
            time.sleep(INTERVAL)
            editor_capture('editor_'+str(index))
        check.run("sys._item_closeup_muted=(s.item_controls,s.item_controls.closed,"
            "[(entry['renderer'],tuple(entry['renderer'].visible)) for entry in s.item_controls.registry.values()])\n"
            "s.item_controls.closed=True\n"
            "for renderer,visible in sys._item_closeup_muted[2]:\n"
            " for slot in (0,1):renderer._show(slot,False)\n_result=True")
        try:
            editor_capture('editor_items_hidden')
        finally:
            check.run("controls,closed,rows=sys._item_closeup_muted\n"
                "for renderer,visible in rows:\n"
                " for slot in (0,1):renderer._show(slot,visible[slot])\n"
                "controls.closed=closed\ndel sys._item_closeup_muted\n_result=True")
        check.run("s.editor.layer=1\ns.display_mode('section')\n_result=True")
        editor_capture('editor_cutaway')
        check.run("s.display_mode('full')\n_result=True")
        editor_capture('editor_restored')
        world_position = check.run("foot=b.player_origin()\ns.origin=(foot[0]+5,foot[1]+18,foot[2]+5)\n"
            "s.opacity=1.\ns.projection_missing=False\ns.projection_outline=False\nb.project()\n"
            "_result=tuple(s.origin[axis]+(5,2,2)[axis] for axis in range(3))")
        check.wait('closeup world publication', lambda row: row['active'] and not row['preparing']
            and row['slots']==2, lambda: check.run(world_state))
        check.run('navigator.pop()\n_result=True')
        check.wait('closeup workspace closed', lambda row: not row['open'] and not row['transition'], check.navigation)
        closeup['world_camera'] = check.run("cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n"
            "target=tuple(s.origin[axis]+%r[axis] for axis in range(3))\n"
            "position=tuple(target[axis]+(0.,1.,-8.)[axis] for axis in range(3))\n"
            "rot=api.GetRotFromDir(tuple(target[axis]-position[axis] for axis in range(3)))\n"
            "rotation=(rot[0],rot[1]+180.,0.)\nassert cam.SetCameraPos(position)\n"
            "assert cam.SetCameraRotation(rotation)\n_result={'position':position,'target':target,'rotation':rotation,"
            "'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()}" %
            ((4.8,2.5,2.9375) if native_reference else (5.5,2.5,2.9375),))
        check.wait('exact closeup world camera', lambda row: camera_matches(row, closeup['world_camera']),
                   lambda: check.run(camera_source))
        time.sleep(.5)
        for index in range(FRAMES):
            time.sleep(INTERVAL)
            world_capture('world_'+str(index))
        check.run("owners=getattr(b.projection_liquid,'companions',(b.projection_liquid,))\n"
            "sys._item_closeup_world_muted=[item for item in owners if item.__class__.__name__=='ItemProjection'][0]\n"
            "assert sys._item_closeup_world_muted.renderer.set_visible(False)\n_result=True")
        try:
            world_capture('world_items_hidden')
        finally:
            check.run("assert sys._item_closeup_world_muted.renderer.set_visible(True)\n"
                      "del sys._item_closeup_world_muted\n_result=True")
        check.run('b.toggle_missing()\n_result=True')
        server("from modern_projection.projection.cell import AIR\nassert adapter.read("+repr(tuple(world_position))+")==AIR\n_result=True")
        wrote = True
        server("adapter.write("+repr(tuple(world_position))+",('minecraft:stone',0))\n_result=True")
        check.run('b.projection_interaction('+repr(tuple(world_position))+')\n_result=True')
        world_capture('world_occupied', 1)
        server("adapter.write("+repr(tuple(world_position))+",('minecraft:air',0))\n_result=True")
        wrote = False
        check.run('b.projection_interaction('+repr(tuple(world_position))+')\n_result=True')
        world_capture('world_restored')
        if native_reference:
            from item_sprite_native_reference import run as run_reference
            run_reference(check,server,session,closeup,world_capture,state_source,camera_source,folder,wgc,persist,
                          native_player_near)
        closeup['completed'] = True
    finally:
        if wrote:
            server("adapter.write("+repr(tuple(world_position))+",('minecraft:air',0))\n_result=True")
        if saved:
            try:
                check.run("b.stop_projection()\ncam=b.factory.CreateCamera(b.level)\ncam.ResetCameraPos()\ncam.UnDepartCamera()\n"
                    "saved=sys._item_closeup_saved\ns.editor=saved['editor']\ns.origin=saved['origin']\ns.opacity=saved['opacity']\n"
                    "s.grid=saved['grid']\ns.projection_missing=saved['missing']\ns.projection_outline=saved['outline']\n"
                    "s.model_revision=None\ns.refresh_preview()\ns.emit()\nowner.open_workspace()\n"
                    "del sys._item_closeup_saved\n_result=True")
            except Exception as error:
                closeup['cleanup_errors'].append(type(error).__name__+': '+str(error))
        persist()
    return closeup
