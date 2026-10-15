"""Apply the existing neighbor gates to both public bed halves in all directions.

Requires a managed MCDEV_SESSION_FILE/MCDEV_OWNER binding and a passed
same-instance camera calibration. Uses background native PNG captures only.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_missing_neighbor_visuals as neighbors
from verify_debug_blueprints import Client
from verify_native_entity_appearances import execute
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_sign_visuals import SignCheck, SAVE_HUD, RESTORE_HUD
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT


class BedOccupancyCheck(SignCheck):
    direction = 0

    def fixture(self, identity):
        original = SignCheck.fixture(self, identity)
        derived = self.run('''from modern_projection.projection.model import Document
from modern_projection.projection.cell import transform,foreground,rebase as rebase_cell
from modern_projection.projection.block_groups import group_partner
source=s.editor.document
original=((9,1,19),(9,1,20))
values=[source.get(pos) for pos in original]
foot=(3,1,3)
direction=%r
operation='rotate_y'+str(direction*90)
if direction:
 values=[transform(value,operation) for value in values]
offset,unused=group_partner(foreground(values[0]))
head=tuple(foot[axis]+offset[axis] for axis in range(3))
doc=Document((7,3,7),dict((pos,rebase_cell(value,tuple(pos[axis]-old[axis] for axis in range(3))))
 for pos,old,value in zip((foot,head),original,values)))
s._loaded(doc)
_result=json.dumps({'public_fixture':'test.entities.appearances','source_cells':original,
 'transformation':operation if direction else 'identity','derived_cells':(foot,head)})
''' % self.direction)
        return {'public_fixture': original, 'derived_bed': derived}


def background_check(client, output, timeout):
    return BedOccupancyCheck(client, output, timeout, native_resolution=True, background_only=True)


neighbors.BlueprintCheck = background_check
neighbors.FIXTURE = 'test.entities.appearances'
neighbors.VISUAL_CASES = {}
foot = (3, 1, 3)
for direction, delta in enumerate(((0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0))):
    head = tuple(foot[axis] + delta[axis] for axis in range(3))
    neighbors.VISUAL_CASES['bed_direction%d_keep_foot' % direction] = (foot, head)
    neighbors.VISUAL_CASES['bed_direction%d_keep_head' % direction] = (head, foot)
original_case = neighbors.case


def bed_case(check, label, keep, occupied, args):
    check.direction = int(label[len('bed_direction')])
    return original_case(check, label, keep, occupied, args)


neighbors.case = bed_case
output = Path(sys.argv[1])
evidence = {'scope': 'Both occupancy directions of the same public silver bed; original neighbor gates'}
saved_options = saved_hud = saved_daylight = False
try:
    with Client(timeout=30) as client:
        check = background_check(client, output, 60)
        evidence['options'] = check.run(CAPTURE_OPTIONS)
        saved_options = True
        evidence['hud'] = check.run(SAVE_HUD)
        saved_hud = True
        evidence['daylight'] = execute(client, SETUP_DAYLIGHT)
        saved_daylight = True
        evidence['player'] = execute(client, '''import json,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_entities_r7_bed_occupancy_player')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
position=factory.CreatePos(player)
flight=factory.CreateFly(player)
foot=position.GetFootPos()
sys._entities_r7_bed_occupancy_player={'player':player,'foot':foot,
 'can_fly':flight.IsPlayerCanFly(),'flying':flight.IsPlayerFlying()}
assert flight.ChangePlayerFlyState(True,True)
assert position.SetFootPos((foot[0],127.,foot[2]))
_result=json.dumps(dict(sys._entities_r7_bed_occupancy_player,after=position.GetFootPos()))
''')
    result = neighbors.main()
finally:
    with Client(timeout=30) as client:
        check = background_check(client, output, 60)
        evidence['player_restored'] = execute(client, '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_entities_r7_bed_occupancy_player',None)
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
 del sys._entities_r7_bed_occupancy_player
else:result={'saved':False}
_result=json.dumps(result)
''')
        if saved_hud:
            evidence['hud_restored'] = check.run(RESTORE_HUD)
        if saved_options:
            evidence['options_restored'] = check.run(RESTORE_OPTIONS)
        if saved_daylight:
            evidence['daylight_restored'] = execute(client, RESTORE_DAYLIGHT)
    output.with_name(output.stem + '_environment.json').write_text(
        json.dumps(evidence, indent=2), encoding='utf8')
raise SystemExit(result)
