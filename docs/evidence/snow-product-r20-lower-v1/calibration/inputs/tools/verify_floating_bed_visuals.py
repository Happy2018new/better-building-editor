"""Run the bed oracle above the canopy and restore player state.

Requires a managed MCDEV_SESSION_FILE/MCDEV_OWNER binding and a passed
same-instance camera calibration. Uses background native PNG captures only.
"""
import base64
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_entity_appearance_visuals as appearance
from verify_debug_blueprints import Client
from verify_native_entity_appearances import execute
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS

BaseCheck = appearance.AppearanceCheck
base_center_editor = appearance.center_editor


def settled_center_editor(check, focus, view):
    result = base_center_editor(check, focus, view)
    check.run('s.camera_pan=(0.,0.)\ns.emit("camera_pan")\n_result=True')
    time.sleep(2.5)
    result['exact_settle'] = check.run('_result=json.dumps({"pose":s.camera_pose,"pan":s.camera_pan})')
    assert tuple(result['exact_settle']['pose']) == tuple(view['editor']), result
    assert tuple(result['exact_settle']['pan']) == (0., 0.), result
    return result


appearance.center_editor = settled_center_editor


class FloatingBedCheck(BaseCheck):
    def capture(self, label, tree=None):
        if label.endswith('_editor'):
            time.sleep(1.)
            editor_state = self.run('''from modern_projection.pyreact.debug import _type_name
host=navigator.top._host
def walk(fiber):
 yield fiber
 for child in fiber.child_fibers:
  for descendant in walk(child):yield descendant
tiles=[fiber for fiber in walk(host._root_fiber) if _type_name(fiber)=='PreviewTile']
rows=[]
for tile in tiles:
 key=tile.props['identity']
 dolls,surfaces,preview=tile.props['registry'][key]
 if preview.front is None:continue
 control=dolls[preview.front].current
 pose=preview.poses[preview.front]
 rows.append({'key':key,'model_pose':pose,'control_position':control.GetPosition(),
  'control_size':control.GetSize(),'render_params':{'scale':pose[0],
  'init_rot_x':pose[1],'init_rot_y':0.,'init_rot_z':pose[2]}})
_result=json.dumps({'pose':s.camera_pose,'pivot':s.camera_pivot,'pan':s.camera_pan,
 'scene_origin':s.scene_origin,'scene_size':s.scene_size,'dolls':rows})
''')
        if label.endswith('_real_native'):
            self.floating_native = execute(self.client, '''import json,sys
import mod.server.extraServerApi as api
saved=sys._p0_entity_appearances
row=saved['rows'][0]
factory=api.GetEngineCompFactory()
info=factory.CreateBlockInfo(saved['player'])
target=tuple(row['pos'])
supports=[(target[0]+dx,target[1]-1,target[2]+dz)
 for dx,dz in ((0,0),(1,0),(-1,0),(0,1),(0,-1))]
for pos in supports:
 assert pos in [tuple(value) for value in saved['reserved']],pos
 assert info.GetBlockNew(pos,saved['dimension'])['name']=='minecraft:stone',pos
 assert info.SetBlockNew(pos,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
cells=[tuple(value) for value in row['cells']]
blocks=[info.GetBlockNew(pos,saved['dimension']) for pos in cells]
assert all(value['name']=='minecraft:bed' for value in blocks),blocks
_result=json.dumps({'source_cells':cells,'blocks':blocks,'supports_removed':supports,
 'placement':'native PlayerUseItemToPos; supports removed with updateNeighbors=False'})
''')
            time.sleep(.5)
        shot = BaseCheck.capture(self, label, tree)
        if label.endswith('_editor'):
            shot['settled_native_editor_state'] = editor_state
        if label.endswith('_real_native'):
            shot['floating_native_positive_control'] = self.floating_native
        return shot


appearance.AppearanceCheck = FloatingBedCheck


SAVE_AND_LIFT = '''import json,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_entities_r7_bed_player')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
position=factory.CreatePos(player)
flight=factory.CreateFly(player)
foot=position.GetFootPos()
sys._entities_r7_bed_player={'player':player,'foot':foot,
 'can_fly':flight.IsPlayerCanFly(),'flying':flight.IsPlayerFlying()}
assert flight.ChangePlayerFlyState(True,True)
assert position.SetFootPos((foot[0],127.,foot[2]))
_result=json.dumps(dict(sys._entities_r7_bed_player,after=position.GetFootPos(),
 after_can_fly=flight.IsPlayerCanFly(),after_flying=flight.IsPlayerFlying()))
'''

RESTORE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_entities_r7_bed_player',None)
if saved is not None:
 factory=api.GetEngineCompFactory()
 position=factory.CreatePos(saved['player'])
 flight=factory.CreateFly(saved['player'])
 assert position.SetFootPos(tuple(saved['foot']))
 assert flight.ChangePlayerFlyState(saved['can_fly'],saved['flying'])
 result={'foot':position.GetFootPos(),'can_fly':flight.IsPlayerCanFly(),
  'flying':flight.IsPlayerFlying(),'expected':saved}
 assert tuple(result['foot'])==tuple(saved['foot']),result
 assert result['can_fly']==saved['can_fly'] and result['flying']==saved['flying'],result
 del sys._entities_r7_bed_player
else:result={'saved':False}
_result=json.dumps(result)
'''

output = Path(sys.argv[1])
evidence = {'scope': 'Fixed player lift to y127 chosen before native fixture capture'}
options_saved = False
try:
    with Client(timeout=30) as client:
        check = appearance.AppearanceCheck(client, output, 60, native_resolution=True, background_only=True)
        for name in ('geometry_palette', 'render_context'):
            source = Path(__file__).resolve().parents[1] / ('behavior_pack/modern_projection/projection/' + name + '.py')
            encoded = base64.b64encode(source.read_bytes()).decode('ascii')
            evidence[name + '_refresh'] = check.run(
                'import base64\nimport modern_projection.projection.%s as module\n'
                'eval(compile(base64.b64decode(%r),%r,"exec"),module.__dict__)\n_result=True' %
                (name, encoded, str(source)))
        evidence['capture_options'] = check.run(CAPTURE_OPTIONS)
        options_saved = True
        evidence['setup'] = execute(client, SAVE_AND_LIFT)
    result = appearance.main()
finally:
    with Client(timeout=30) as client:
        evidence['restore'] = execute(client, RESTORE_PLAYER)
        if options_saved:
            check = appearance.AppearanceCheck(client, output, 60, native_resolution=True, background_only=True)
            evidence['capture_options_restored'] = check.run(RESTORE_OPTIONS)
    output.with_name(output.stem + '_player_lift.json').write_text(
        json.dumps(evidence, indent=2), encoding='utf8')
raise SystemExit(result)
