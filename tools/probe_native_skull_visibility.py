"""Diagnose native skull visibility with a near player and matched stone control."""
import argparse
import json
from pathlib import Path
import time

from PIL import Image
from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_entity_appearance_visuals import cleanup_native_fixture
from verify_native_entity_appearances import execute, replicated_palettes
from verify_shulker_orientations import wait_camera_pose
from verify_snow_plant_visibility import changed, count
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = Path(__file__).resolve().parents[1]


def pose(check, target, offset):
    result = check.run('''target=%r
offset=%r
center=tuple(v+.5 for v in target)
position=tuple(center[axis]+offset[axis] for axis in range(3))
rotation=api.GetRotFromDir(tuple(center[axis]-position[axis] for axis in range(3)))
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation((rotation[0],rotation[1]+180.,0.))
_result=json.dumps({'position':position,'rotation':rotation,'target':center})
''' % (target, offset))
    result['settled'] = wait_camera_pose(check, result)
    time.sleep(.3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    evidence = {'schema': 1, 'completed': False, 'rows': [],
                'scope': 'Native visibility diagnostic only; no enum or NBT overrides'}
    installed = saved_visual = daylight_saved = native_created = player_moved = False
    with Client(timeout=30) as client:
        check = BlueprintCheck(client, args.output, 60)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL)
            saved_visual = True
            evidence['daylight'] = execute(client, SETUP_DAYLIGHT)
            daylight_saved = True
            native_created = True
            setup = execute(client, "import sys\nsys._p0_entity_appearance_selected=('skull_floor_yaw_0',)\n" +
                            (ROOT / 'tools/p0_entity_appearance_setup.py').read_text(encoding='utf8'))
            execute(client, 'import sys\nsys._p0_entity_appearance_rows=%r\n_result=True' % setup['rows'], True)
            evidence['native'] = replicated_palettes(client,
                (ROOT / 'tools/p0_entity_appearance_read.py').read_text(encoding='utf8'))
            row = evidence['native']['rows'][0]
            player_moved = True
            evidence['near_player'] = execute(client, '''import json,sys
import mod.server.extraServerApi as api
saved=sys._p0_entity_appearances
player=saved['player']
factory=api.GetEngineCompFactory()
comp=factory.CreatePos(player)
saved['diagnostic_player_foot']=comp.GetFootPos()
target=%r
platform=(target[0]-2,target[1]-1,target[2]-3)
info=factory.CreateBlockInfo(player)
assert info.GetBlockNew(platform,saved['dimension'])['name']=='minecraft:air'
saved['reserved'].append(platform)
assert info.SetBlockNew(platform,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
assert comp.SetFootPos((platform[0]+.5,platform[1]+1.,platform[2]+.5))
_result=json.dumps({'before':saved['diagnostic_player_foot'],'after':comp.GetFootPos(),'platform':platform})
''' % (tuple(row['pos']),))
            check.run('b.stop_projection()\n_result=True')
            if check.navigation()['open']:
                check.run('navigator.pop()\n_result=True')
                check.wait('workspace closed', lambda state: not state['open'] and not state['transition'], check.navigation)
            for label, offset in (('below', (-2., -.8, -3.)), ('above', (-2., .8, -3.))):
                result = {'camera': label, 'pose': pose(check, tuple(row['pos']), offset)}
                result['native_shown'] = check.capture('native_' + label)
                execute(client, '''import sys
import mod.server.extraServerApi as api
saved=sys._p0_entity_appearances
api.GetEngineCompFactory().CreateBlockInfo(saved['player']).SetBlockNew(%r,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
_result=True
''' % (tuple(row['pos']),))
                time.sleep(.3)
                result['hidden'] = check.capture('hidden_' + label)
                execute(client, '''import sys
import mod.server.extraServerApi as api
saved=sys._p0_entity_appearances
assert api.GetEngineCompFactory().CreateBlockInfo(saved['player']).SetBlockNew(%r,{'name':'minecraft:stone','aux':0},0,saved['dimension'],True,False)
_result=True
''' % (tuple(row['pos']),))
                time.sleep(.3)
                result['stone_shown'] = check.capture('stone_' + label)
                hidden = Image.open(result['hidden']['path']).convert('RGB')
                crop = (hidden.width // 3, hidden.height // 3, hidden.width * 2 // 3, hidden.height * 2 // 3)
                for material in ('native', 'stone'):
                    shown = Image.open(result[material + '_shown']['path']).convert('RGB')
                    mask = changed(shown.crop(crop), hidden.crop(crop), 25)
                    result[material + '_pixels'] = count(mask)
                    mask.save(args.output.with_name(args.output.stem + '_' + material + '_' + label + '_mask.png'))
                evidence['rows'].append(result)
                write_json(args.output, evidence)
                execute(client, '''import sys
import mod.server.extraServerApi as api
saved=sys._p0_entity_appearances
factory=api.GetEngineCompFactory()
info,items=factory.CreateBlockInfo(saved['player']),factory.CreateItem(saved['player'])
info.SetBlockNew(%r,{'name':'minecraft:air','aux':0},0,saved['dimension'],True,False)
assert items.SpawnItemToPlayerInv({'itemName':'minecraft:skeleton_skull','auxValue':0,'count':1},saved['player'],saved['slot'])
assert info.PlayerUseItemToPos(%r,api.GetMinecraftEnum().ItemPosType.INVENTORY,saved['slot'],1)
items.SetInvItemNum(saved['slot'],0)
_result=True
''' % (tuple(row['pos']), tuple(row['support'])))
            evidence['positive_control'] = all(row['stone_pixels'] >= 100 for row in evidence['rows'])
            evidence['native_nonblank'] = all(row['native_pixels'] >= 100 for row in evidence['rows'])
            assert evidence['positive_control'], 'The matched stone visibility control is blank'
            evidence['completed'] = True
        finally:
            errors = []
            actions = []
            if player_moved:
                actions.append(('player', lambda: execute(client, '''import sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_p0_entity_appearances',{})
if 'diagnostic_player_foot' in saved:
 assert api.GetEngineCompFactory().CreatePos(saved['player']).SetFootPos(tuple(saved['diagnostic_player_foot']))
_result=True
''')))
            if native_created:
                actions.append(('native', lambda: cleanup_native_fixture(client)))
            if daylight_saved:
                actions.append(('daylight', lambda: execute(client, RESTORE_DAYLIGHT)))
            if saved_visual:
                actions.append(('camera', lambda: check.run(camera_restore_code(False))))
                actions.append(('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True')))
            if installed:
                def restore_workspace():
                    opened = check.run('_result=sys._blueprint_qa_saved["workspace"]')
                    check.run(RESTORE)
                    if opened:
                        check.run('owner.open_workspace()\n_result=True')
                        check.wait('workspace reopened', lambda state: state['open'] and not state['transition'], check.navigation)
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('workspace closed', lambda state: not state['open'] and not state['transition'], check.navigation)
                actions.append(('workspace', restore_workspace))
            for label, action in actions:
                try:
                    action()
                except Exception as error:
                    errors.append(label + ': ' + str(error))
            execute(client, 'import sys\nfor name in ("_p0_entity_appearance_rows","_p0_entity_appearance_palettes","_p0_entity_appearance_entities"):\n if hasattr(sys,name):delattr(sys,name)\n_result=True', True)
            evidence['restored'] = not errors
            evidence['cleanup_errors'] = errors
            write_json(args.output, evidence)
    print(json.dumps({'completed': evidence['completed'], 'restored': evidence['restored'],
                      'positive_control': evidence.get('positive_control'),
                      'native_nonblank': evidence.get('native_nonblank')}))


if __name__ == '__main__':
    main()
