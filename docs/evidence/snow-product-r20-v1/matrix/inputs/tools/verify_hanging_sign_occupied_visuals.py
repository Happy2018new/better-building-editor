"""Actual occupied-cell lifecycle pixels for the unchanged public hanging sign."""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import verify_sign_visuals as signs
from sign_panel_oracle import wooden_rectangle, isolate, baseline_control
from verify_hanging_sign_front_holdout import ControlledSignCheck, record_file
from verify_shulker_orientations import matching_camera


RESERVE = '''import json,sys
import mod.server.extraServerApi as api
assert not hasattr(sys,'_entity_visual_r8_occupied')
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
pos=%r
info=factory.CreateBlockInfo(player)
assert info.GetBlockNew(pos,dimension)['name']=='minecraft:air'
sys._entity_visual_r8_occupied={'player':player,'dimension':dimension,'pos':pos}
_result=json.dumps(sys._entity_visual_r8_occupied)
'''

WRITE = '''import json,sys
import mod.server.extraServerApi as api
saved=sys._entity_visual_r8_occupied
info=api.GetEngineCompFactory().CreateBlockInfo(saved['player'])
name=%r
pos=tuple(saved['pos'])
before=info.GetBlockNew(pos,saved['dimension'])
if before['name']!=name:
 assert info.SetBlockNew(pos,{'name':name,'aux':0},0,saved['dimension'],True,False)
after=info.GetBlockNew(pos,saved['dimension'])
assert after['name']==name
_result=json.dumps({'pos':pos,'before':before,'after':after})
'''

CLEAR = WRITE % 'minecraft:air' + '''del sys._entity_visual_r8_occupied
'''

STATE = '''t=b.projection_occupancy
focus=%r
index=t.index(focus) if t is not None else None
work=b.projection_work
_result=json.dumps({'active':s.projection_active,'ready':work is None or work.ready,
 'error':work.error if work else None,'failed':t.failed if t else None,
 'preparing':bool(b.preparing_entity),'has_occupancy':t is not None,
 'state':t.state[index] if t else None,'rendered':t.rendered[index] if t else None,
 'cache_slot':t.slots[index] if t else None,'tracked':focus in t.targets if t else None,
 'building':t is not None and t.build is not None,
 'pending':t is not None and (t.pending_model is not None or t.attaching),
 'changed':len(t.changed) if t else None,'builds':t.builds if t else None,
 'commits':t.commits if t else None,'mesh':b.projection_mesh,
 'actors':list(b.projection_entities.values())+([b.entity] if b.entity else []),
 'document_preserved':s.editor.document.to_data()==sys._entity_visual_r8_document,
 'history_preserved':(len(s.editor.undo_stack),len(s.editor.redo_stack))==sys._entity_visual_r8_history,
 'origin':s.origin,'serial':b.projection_serial})
'''


def settled(check, focus, expected):
    def ready(value):
        if value['error'] or value['failed']:
            raise AssertionError(value)
        return (value['active'] and value['ready'] and value['has_occupancy'] and
                value['tracked'] and value['state'] == expected and value['rendered'] == expected and
                (value['cache_slot'] < 0 if expected == 2 else value['cache_slot'] >= 0) and
                not value['preparing'] and not value['building'] and not value['pending'] and
                value['changed'] == 0 and value['document_preserved'] and value['history_preserved'])
    return check.wait('actual occupied hanging-sign state', ready,
                      lambda: check.run(STATE % (tuple(focus),)))


def visibility_pair(check, label, focus, pose):
    before = check.run(STATE % (tuple(focus),))
    camera = check.run(signs.PROJECTION_STATUS + '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation()})''')
    assert matching_camera(camera, pose), (label, camera, pose)
    time.sleep(.4)
    shown = check.capture(label + '_shown')
    actors = before['actors']
    assert actors, before
    try:
        check.run('for entity in %r:\n assert b.factory.CreateActorRender(entity).SetNotRenderAtAll(True)\n_result=True' % actors)
        time.sleep(.4)
        hidden = check.capture(label + '_hidden')
    finally:
        check.run('for entity in %r:\n assert b.factory.CreateActorRender(entity).SetNotRenderAtAll(False)\n_result=True' % actors)
    after = check.run(STATE % (tuple(focus),))
    camera_after = check.run('cam=b.factory.CreateCamera(b.level)\n'
                            '_result=json.dumps({"position":cam.GetPosition(),"rotation":cam.GetCameraRotation()})')
    assert matching_camera(camera_after, pose), (label, camera_after, pose)
    assert before == after, (before, after)
    return {'screenshot': shown, 'hidden_screenshot': hidden, 'state_before': before, 'state_after': after,
            'camera_before': camera, 'camera_after': camera_after}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output directory')
    helper = Path(os.environ['MCDEV_NATIVE_CAPTURE_HELPER']).resolve(strict=True)
    executable = Path(os.environ['MCDEV_NATIVE_CAPTURE_EXE']).resolve(strict=True)
    production = [record_file(path) for directory in ('behavior_pack', 'resource_pack')
                  for path in sorted((signs.ROOT / directory).rglob('*')) if path.is_file()]
    tools = [record_file(path) for path in (Path(__file__), signs.ROOT / 'tools/verify_sign_visuals.py',
             signs.ROOT / 'tools/sign_panel_oracle.py', signs.ROOT / 'tools/verify_hanging_sign_front_holdout.py',
             signs.ROOT / 'tools/verify_shulker_orientations.py', helper, executable)]
    args.output.mkdir(parents=True)
    frozen = {'schema': 1, 'production': production, 'tools': tools,
              'scope': 'Public hanging sign; actual stone target; dynamic hiding, initial occupied generation and recovery',
              'oracle': 'Blank unoccupied sign board is frozen before any occupied frame',
              'limits': {'minimum_difference': 20, 'occupied_board_changed_pixels': 0,
                         'recovery_glyph_iou': .45, 'layout_center': .1, 'layout_size': .2}}
    signs.write_json(args.output / 'frozen_source.json', frozen)
    report = {'schema': 1, 'completed': False, 'passed': False, 'restored': False,
              'scope': frozen['scope'], 'occupancy_source': 'Actual native world; no occupancy observer override', 'cases': []}
    flags = dict.fromkeys(('installed', 'visual', 'daylight', 'options', 'hud', 'native', 'reserved'), False)
    with signs.Client(timeout=30) as client:
        check = ControlledSignCheck(client, args.output / 'report.json', 60, native_resolution=True)
        try:
            report['workspace_before'] = check.navigation()['open']
            assert not report['workspace_before']
            check.run(signs.INSTALL_PROBE)
            flags['installed'] = True
            check.run(signs.SAVE_VISUAL + 'sys._blueprint_visual_saved["grid"]=s.grid\n_result=True')
            flags['visual'] = True
            report['daylight'] = signs.execute(client, signs.SETUP_DAYLIGHT)
            flags['daylight'] = True
            report['options'] = check.run(signs.CAPTURE_OPTIONS)
            flags['options'] = True
            report['hud'] = check.run(signs.SAVE_HUD)
            flags['hud'] = True
            report['native'] = signs.execute(client, '_native_sign_height_offset=32\n' + signs.SETUP)
            flags['native'] = True
            check.run('sys._native_sign_probe_rows=%r\n_result=True' % report['native']['rows'])
            metadata = check.run('from modern_projection.projection.debug_sign_blueprints import VISUAL_CASE\n_result=json.dumps(VISUAL_CASE)')
            focus = metadata['focus']
            for view in metadata['views']:
                label = 'hanging_' + view['id']
                row = {'view': view['id'], 'samples': {}}
                report['cases'].append(row)
                signs.load(check, 'hanging_front_back', True, view)
                blank = signs.world_sample(check, label + '_blank', focus, view['world_offset'], .85, 32, True)
                width, height = blank['screenshot']['size']
                crop = tuple(round(value * (width if axis % 2 == 0 else height))
                             for axis, value in enumerate(metadata['world_text_roi']))
                panel = wooden_rectangle(blank['screenshot']['path'], crop)
                assert panel, 'Missing positive blank board'
                row.update(crop=crop, frozen_panel=panel)
                row['samples']['blank'] = blank
                signs.load(check, 'hanging_front_back', False, view)
                visible = signs.world_sample(check, label + '_unoccupied', focus, view['world_offset'], .85, 32, True)
                row['samples']['unoccupied'] = visible
                check.run('sys._entity_visual_r8_document=s.editor.document.to_data()\n'
                          'sys._entity_visual_r8_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))\n_result=True')
                row['unoccupied_state'] = settled(check, focus, 1)
                target = check.run('_result=tuple(int(s.origin[i]+%r[i]) for i in range(3))' % (tuple(focus),))
                row['reservation'] = signs.execute(client, RESERVE % (tuple(target),))
                flags['reserved'] = True
                reference, control = signs.colored_text(visible['screenshot']['path'], blank['screenshot']['path'],
                    crop, view['color'], args.output / (label + '_reference_text.png'), True)
                reference = isolate(reference, panel)
                assert reference.histogram()[255] >= 8, control
                row['positive_text_pixels'] = reference.histogram()[255]
                row['native_write'] = signs.execute(client, WRITE % 'minecraft:stone')
                row['dynamic_state'] = settled(check, focus, 2)
                for phase in ('dynamic', 'initial'):
                    if phase == 'initial':
                        check.run('b.stop_projection()\nb.project()\n_result=True')
                        row['initial_state'] = settled(check, focus, 2)
                    pair = visibility_pair(check, label + '_' + phase, focus, visible['pose'])
                    row['samples'][phase] = pair
                    row[phase + '_control'] = baseline_control(pair['screenshot']['path'], pair['hidden_screenshot']['path'],
                        crop, panel, args.output / (label + '_' + phase + '_board_delta.png'))
                row['native_clear'] = signs.execute(client, WRITE % 'minecraft:air')
                row['recovery_state'] = settled(check, focus, 1)
                recovered = visibility_pair(check, label + '_recovered', focus, visible['pose'])
                row['samples']['recovered'] = recovered
                mask, pixels = signs.colored_text(recovered['screenshot']['path'], blank['screenshot']['path'],
                    crop, view['color'], args.output / (label + '_recovered_text.png'), True)
                mask = isolate(mask, panel)
                row['recovery_shape'] = signs.shape_match(reference, mask)
                row['recovery_layout'] = signs.layout_match(reference.getbbox(), panel, mask.getbbox(), panel,
                    metadata['text_layout_tolerance'])
                row['passed'] = all(row[key]['passed'] for key in ('dynamic_control', 'initial_control', 'recovery_shape', 'recovery_layout'))
                signs.execute(client, CLEAR)
                flags['reserved'] = False
                check.run('b.stop_projection()\n_result=True')
                signs.write_json(args.output / 'report.json', report)
            report['completed'] = True
            report['passed'] = all(row['passed'] for row in report['cases'])
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            raise
        finally:
            actions = [
                ('occupied_world', lambda: signs.execute(client, CLEAR) if flags['reserved'] else True),
                ('native', lambda: signs.execute(client, signs.CLEANUP) if flags['native'] else True),
                ('native_client', lambda: check.run('for name in ("_native_sign_probe_rows","_entity_visual_r8_document","_entity_visual_r8_history"):\n if hasattr(sys,name):delattr(sys,name)\n_result=True')),
                ('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                ('camera', lambda: check.run(signs.camera_restore_code(False)) if flags['visual'] else True),
                ('visual_fields', lambda: check.run('saved=sys._blueprint_visual_saved\ns.grid=saved["grid"]\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True') if flags['visual'] else True),
                ('editor', lambda: check.run(signs.RESTORE) if flags['installed'] else True),
                ('workspace', lambda: check.run("if navigator.contains('modern_projection_workspace'):navigator.pop()\n_result=True")),
                ('hud', lambda: check.run(signs.RESTORE_HUD) if flags['hud'] else True),
                ('options', lambda: check.run(signs.RESTORE_OPTIONS) if flags['options'] else True),
                ('daylight', lambda: signs.execute(client, signs.RESTORE_DAYLIGHT) if flags['daylight'] else True)]
            errors = []
            for name, action in actions:
                try:
                    report[name + '_restored'] = action()
                except Exception as error:
                    errors.append(name + ': ' + str(error))
            report['cleanup_errors'] = errors
            report['restored'] = not errors
            unchanged = all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                            for row in production + tools)
            signs.write_json(args.output / 'frozen_source_after.json', {'production_and_tools_unchanged': unchanged})
            report['passed'] = report['passed'] and report['restored'] and unchanged
            signs.write_json(args.output / 'report.json', report)
    print(json.dumps({key: report[key] for key in ('completed', 'passed', 'restored')}))


if __name__ == '__main__':
    main()
