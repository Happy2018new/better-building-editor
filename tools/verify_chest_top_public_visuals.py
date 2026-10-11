"""Unaccepted top-view chest probe linked to unchanged public blueprint cells.

The preserved +16 run failed its native positive control. A future +8 run must
be requested explicitly; the original pixel gates are unchanged.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_copper_chest_render as native
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_missing_neighbor_visuals import camera_matches
from verify_native_entity_appearances import execute
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_sign_visuals import SignCheck, SAVE_HUD, RESTORE_HUD
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

PLANS = (
    ('chest', 'south', False, 'test.entities.classic', ((9, 1, 3),)),
    ('chest', 'north', True, 'test.connections.context', ((26, 1, 5), (27, 1, 5))),
    ('copper_chest', 'north', True, 'test.connections.context', ((26, 1, 10), (27, 1, 10))),
)

LOAD_PUBLIC = '''from modern_projection.projection.debug_blueprints import build
from modern_projection.projection.model import Document
from modern_projection.projection.cell import foreground,rebase as rebase_cell
from modern_projection.projection.visible_actor import render_actor
identity,points=%r,%r
public=build(identity)
before=public.to_data()
source=sys._copper_native_document
lo=tuple(min(pos[axis] for pos in points) for axis in range(3))
delta=tuple(1-value for value in lo)
doc=Document((4,3,4),dict((tuple(pos[axis]+delta[axis] for axis in range(3)),
 rebase_cell(public.get(pos),delta)) for pos in points))
assert dict((pos,foreground(value)) for pos,value in source.blocks.items())==dict(
 (pos,foreground(value)) for pos,value in doc.blocks.items()),(source.to_data(),doc.to_data())
assert before==public.to_data()
sys._copper_native_document=doc
sys._chest_top_public_snapshot=doc.to_data()
sys._blueprint_qa_identity=identity
_result=json.dumps({'fixture':identity,'source_cells':points,'translation':delta,
 'document':doc.to_data(),'native_client_document':source.to_data(),
 'public_source_unchanged':before==public.to_data()})
'''

SAVE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_entities_r7_chest_top_player')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
position=factory.CreatePos(player)
flight=factory.CreateFly(player)
foot=position.GetFootPos()
sys._entities_r7_chest_top_player={'player':player,'foot':foot,
 'can_fly':flight.IsPlayerCanFly(),'flying':flight.IsPlayerFlying()}
assert flight.ChangePlayerFlyState(True,True)
assert position.SetFootPos((foot[0],127.,foot[2]))
_result=json.dumps(dict(sys._entities_r7_chest_top_player,after=position.GetFootPos()))
'''

RESTORE_PLAYER = '''import json,sys
import mod.server.extraServerApi as api
saved=getattr(sys,'_entities_r7_chest_top_player',None)
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
 del sys._entities_r7_chest_top_player
else:result={'saved':False}
_result=json.dumps(result)
'''


def capture_at(check, label, expected):
    before = check.run(native.CAMERA)
    assert camera_matches(before, expected), (label, before, expected)
    result = check.capture(label)
    after = check.run(native.CAMERA)
    assert camera_matches(after, expected), (label, after, expected)
    result['camera_before'], result['camera_after'] = before, after
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case-limit', type=int, choices=(1, 2, 3))
    parser.add_argument('--target-height-offset', type=int, choices=(8, 16), default=16)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'completed': False, 'passed': False, 'restored': False,
              'scope': 'Actual player-placed native world chests versus unchanged public blueprint cells; top view only; original chest gates',
              'candidate': '008ca89bf16aab4d12ba2b40bb167844840c18be',
              'candidate_accepted': False, 'cases': [], 'view_offset': [0., 6., .15],
              'native_target_height_offset': args.target_height_offset,
              'limits': {'minimum_native_pixels': 1000, 'shape_iou': .82,
                         'scale_relative_error': .2, 'texture_cosine': .45,
                         'center_distance_pixels': 3, 'boundary_rms_pixels': 4}}
    installed = visual = setup = options = hud = daylight = player = False
    try:
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output, 60, native_resolution=True, background_only=True,
                              native_capture_helper=Path(__file__).resolve().parent / 'capture_native_window.py')
            try:
                report['options'] = check.run(CAPTURE_OPTIONS)
                options = True
                report['hud'] = check.run(SAVE_HUD)
                hud = True
                report['daylight'] = execute(client, SETUP_DAYLIGHT)
                daylight = True
                report['player'] = execute(client, SAVE_PLAYER)
                player = True
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                visual = True
                assert not check.navigation()['open'], 'Preflight requires a closed workspace'
                setup_code = native.SETUP
                original_height = 'int(math.floor(foot[1]))+16'
                assert setup_code.count(original_height) == 1
                setup_code = setup_code.replace(original_height,
                    'int(math.floor(foot[1]))+%d' % args.target_height_offset)
                report['native_setup'] = native.server_run(client, setup_code)
                setup = True
                time.sleep(1.)
                for index, (name, direction, paired, fixture, points) in enumerate(PLANS[:args.case_limit]):
                    row = native.server_run(client, native.PLACE % ('minecraft:' + name, direction, paired))
                    report['cases'].append(row)
                    time.sleep(2.)
                    pose = check.run(native.CAPTURE.replace('(-3.5,-3.,-5.)', '(0.,6.,.15)') % (row['cells'],))
                    row['pose'] = pose
                    row['public_source'] = check.run(LOAD_PUBLIC % (fixture, points))
                    check.wait('native top camera settles', lambda value: camera_matches(value, pose),
                               lambda: check.run(native.CAMERA))
                    time.sleep(.5)
                    row['native'] = capture_at(check, '%d_native' % index, pose)
                    native.server_run(client, native.CLEAR)
                    time.sleep(.5)
                    row['empty'] = capture_at(check, '%d_empty' % index, pose)
                    check.run(native.PROJECT)
                    row['projection'] = check.wait('public proxy projection ready',
                        lambda value: value['active'] and value['ready'] and not value['preparing'],
                        lambda: check.run(PROJECTION_STATUS))
                    assert not row['projection']['error'], row['projection']
                    time.sleep(.5)
                    row['proxy'] = capture_at(check, '%d_proxy' % index, pose)
                    row['document_preserved'] = check.run('_result=s.editor.document.to_data()==sys._chest_top_public_snapshot')
                    assert row['document_preserved']
                    first = native.object_frame(row['native']['path'], row['empty']['path'],
                        args.output.with_name(args.output.stem + '_%d_native_signal.png' % index))
                    second = native.object_frame(row['proxy']['path'], row['empty']['path'],
                        args.output.with_name(args.output.stem + '_%d_proxy_signal.png' % index))
                    comparison = native._prepared_pair(first, second)
                    comparison['world_alignment'] = native.world_alignment(first[2], second[2])
                    comparison['passed'] = (comparison['shape_iou'] >= .82 and
                        comparison['scale_relative_error'] <= .2 and comparison['texture_cosine'] is not None and
                        comparison['texture_cosine'] >= .45 and comparison['world_alignment']['passed'])
                    row.update(comparison=comparison, native_signal=first[2], proxy_signal=second[2])
                    write_json(args.output, report)
                    print(json.dumps({'case': index, 'name': name, 'paired': paired,
                                      'comparison': comparison}), flush=True)
                    check.run('b.stop_projection()\n_result=True')
                report['completed'] = True
                report['passed'] = all(row['comparison']['passed'] for row in report['cases'])
            finally:
                if visual:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')
                if installed:
                    check.run(RESTORE)
                    if check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                        check.wait('restore closed workspace', lambda nav: not nav['open'] and not nav['transition'], check.navigation)
                if setup:
                    report['native_restored'] = native.server_run(client, native.CLEANUP)
                check.run('''for name in ('_copper_native_document','_copper_native_origin','_chest_top_public_snapshot'):
 if hasattr(sys,name):delattr(sys,name)
_result=True''')
                if player:
                    report['player_restored'] = execute(client, RESTORE_PLAYER)
                if hud:
                    report['hud_restored'] = check.run(RESTORE_HUD)
                if options:
                    report['options_restored'] = check.run(RESTORE_OPTIONS)
                if daylight:
                    report['daylight_restored'] = execute(client, RESTORE_DAYLIGHT)
                report['restored'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, report)
    print(json.dumps({'completed': report['completed'], 'passed': report['passed'], 'restored': report['restored']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
