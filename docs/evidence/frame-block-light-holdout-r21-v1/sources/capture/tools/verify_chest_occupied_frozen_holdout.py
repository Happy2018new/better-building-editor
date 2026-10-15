"""Measure real partial occupancy while preserving logical double-chest context."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageChops

import verify_chest_editor_frozen_holdout as editor
import verify_chest_top_public_visuals as public
import verify_copper_chest_render as native
import verify_hanging_sign_occupied_visuals as occupied
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_hanging_sign_front_holdout import record_file
from verify_missing_neighbor_visuals import camera_matches
from verify_native_entity_appearances import execute
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_sign_visuals import SignCheck, SAVE_HUD, RESTORE_HUD
from visual_environment import SETUP_DAYLIGHT, RESTORE_DAYLIGHT

ROOT = editor.ROOT
LIMITS = {'minimum_native_pixels': 1000, 'shape_iou': .82, 'texture_cosine': .45,
          'scale_relative_error': .2, 'center_distance_pixels': 3, 'boundary_rms_pixels': 4}

DECLARED_CAMERA = '''cells,offset=%r,%r
lo=tuple(min(pos[i] for pos in cells) for i in range(3))
hi=tuple(max(pos[i] for pos in cells) for i in range(3))
target=tuple((lo[i]+hi[i]+1.)/2. for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
_result=json.dumps({'position':position,'rotation':(direction[0],direction[1]+180.,0.),'target':target})
'''

BASELINE = '''import json
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
flight=factory.CreateFly(player)
_result=json.dumps({'foot':factory.CreatePos(player).GetFootPos(),
 'rotation':factory.CreateRot(player).GetRot(),'can_fly':flight.IsPlayerCanFly(),
 'flying':flight.IsPlayerFlying(),'read_only':True})
'''


def declared_pose(check, cells, config):
    pose = check.run(DECLARED_CAMERA % (tuple(tuple(pos) for pos in cells), tuple(config['camera']['world_offset'])))
    position = tuple(pose['position'])
    execute(check.client, public.PLAYER_AT_CAMERA % (position, (pose['rotation'][0], pose['rotation'][1]-180.)))
    check.wait('player replicated beside declared camera',
               lambda value: all(abs(value[i]-position[i]) < .02 for i in range(3)),
               lambda: check.run('_result=b.player_position.GetFootPos()'))
    check.run('cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n'
              'cam.LockModCameraPitch(True)\ncam.LockModCameraYaw(True)\n'
              'assert cam.SetCameraPos(%r)\nassert cam.SetCameraRotation(%r)\n_result=True' %
              (position, tuple(pose['rotation'])))
    check.wait('declared camera settles', lambda value: camera_matches(value, pose), lambda: check.run(native.CAMERA))
    time.sleep(.5)
    return pose


def settled(check, focuses, expected):
    assert len(focuses) == len(expected) and focuses, (focuses, expected)

    def sample():
        return [check.run(occupied.STATE % (tuple(pos),)) for pos in focuses]

    def ready(rows):
        for row, value in zip(rows, expected):
            if row['error'] or row['failed']:
                raise AssertionError(row)
            if not (row['active'] and row['ready'] and row['has_occupancy'] and row['tracked'] and
                    row['state'] == value and row['rendered'] == value and
                    (row['cache_slot'] < 0 if value == 2 else row['cache_slot'] >= 0) and
                    not row['preparing'] and not row['building'] and not row['pending'] and
                    row['changed'] == 0 and row['document_preserved'] and row['history_preserved']):
                return False
        return True

    return check.wait('real double-chest target occupancy settles', ready, sample)


def comparison(first, second):
    result = native._prepared_pair(first, second)
    result['alignment'] = native.world_alignment(first[2], second[2])
    result['passed'] = (result['shape_iou'] >= LIMITS['shape_iou'] and result['texture_cosine'] is not None and
                        result['texture_cosine'] >= LIMITS['texture_cosine'] and
                        result['scale_relative_error'] <= LIMITS['scale_relative_error'] and
                        result['alignment']['passed'])
    return result


def visibility_pair(check, label, focus, pose):
    # The sign helper takes look-direction yaw; chest poses record camera yaw.
    look_pose = dict(pose, rotation=(pose['rotation'][0], pose['rotation'][1]-180., pose['rotation'][2]))
    return occupied.visibility_pair(check, label, focus, look_pose)


def composite_signal(shown, empty, crop, output):
    """Keep disconnected real and virtual pieces in the diagnostic assembly."""
    with Image.open(shown).convert('RGB') as source, Image.open(empty).convert('RGB') as background:
        assert source.size == background.size, 'Frame dimensions changed'
        selected = source.crop(crop)
        mask = editor.maximum(ImageChops.difference(source, background)).crop(crop).point(
            lambda value: 255 if value > 25 else 0)
    bounds, pixels = mask.getbbox(), mask.histogram()[255]
    assert bounds is not None and pixels >= LIMITS['minimum_native_pixels'], \
        'No composite contributes 1000 pixels: %r' % pixels
    signal = Image.new('RGB', selected.size)
    signal.paste(selected, mask=mask)
    signal.save(output)
    mask.save(output.with_name(output.stem+'_mask.png'))
    resize = getattr(Image, 'Resampling', Image)
    record = {'bbox': bounds, 'world_bounds': [value+crop[axis % 2] for axis, value in enumerate(bounds)],
              'pixels': pixels, 'crop': crop, 'signal': str(output.resolve()),
              'component_policy': 'All above-threshold pixels inside the predeclared quartz-backed ROI'}
    return signal.crop(bounds).resize((64, 64), resize.BILINEAR), mask.crop(bounds).resize((64, 64), resize.NEAREST), record


def cleanup(actions, report):
    errors = []
    for name, action in actions:
        try:
            report[name+'_restored'] = action()
        except Exception as error:
            errors.append(name+': '+type(error).__name__+': '+str(error))
    report['cleanup_errors'] = errors
    report['restored'] = not errors


def restoration_matches(baseline, observed):
    return (all(len(baseline[key]) == len(observed[key]) and
                all(abs(left-right) <= .02 for left, right in zip(baseline[key], observed[key]))
                for key in ('foot', 'rotation')) and
            all(baseline[key] == observed[key] for key in ('can_fly', 'flying')))


def occupancy_plan(cells, half):
    if half not in ('main', 'sub') or len(cells) != 2 or cells[0] == cells[1]:
        raise ValueError('Choose main or sub on a two-cell double chest')
    occupied_index = 0 if half == 'main' else 1
    remaining_index = 1 - occupied_index
    focuses = ((1, 1, 1), (2, 1, 1))
    return {'half': half, 'occupied_world': tuple(cells[occupied_index]),
            'remaining_world': tuple(cells[remaining_index]),
            'remaining_focus': focuses[remaining_index], 'focuses': focuses,
            'expected': tuple(2 if index == occupied_index else 1 for index in range(2))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case-limit', type=int, choices=(1, 2), default=2)
    parser.add_argument('--occupied-half', choices=('main', 'sub'), default='sub')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh evidence directory')
    helper = Path(os.environ['MCDEV_NATIVE_CAPTURE_HELPER']).resolve(strict=True)
    executable = Path(os.environ['MCDEV_NATIVE_CAPTURE_EXE']).resolve(strict=True)
    config = editor.VISUAL_CASES['chest_top']
    production = [record_file(path) for folder in ('behavior_pack', 'resource_pack')
                  for path in sorted((ROOT/folder).rglob('*')) if path.is_file()]
    paths = sorted((ROOT/'tools').glob('*.py')) + sorted((ROOT/'tools/native_wgc').glob('*'))
    paths += sorted((ROOT/'.agents/skills/pyreact-debugging/scripts').glob('*.py')) + [helper, executable]
    tools = [record_file(path) for path in paths if path.is_file()]
    frozen = {'schema': 1, 'production': production, 'tools': tools, 'config': config, 'limits': LIMITS,
              'world_signal_roi': [.38, .38, .62, .62],
              'checked_out_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'scope': 'Real stone %s-half occupancy in missing projection; preserve logical main/sub double context; dynamic, initial and recovery' % args.occupied_half,
              'occupied_half': args.occupied_half,
              'oracle': 'Native full double restricted to remaining target bounds from independent stone cube before chest frames; real single/composite diagnostics separately'}
    args.output.mkdir(parents=True)
    write_json(args.output/'frozen_source.json', frozen)
    report = {'schema': 1, 'scope': frozen['scope'], 'limits': LIMITS, 'completed': False,
              'passed': False, 'restored': False, 'cases': [],
              'render_path': 'missing_projection',
              'occupancy_source': 'Real native-world stone; no observer override',
              'logical_pair_policy_preserved': True, 'session_file': os.environ['MCDEV_SESSION_FILE']}
    flags = set()
    try:
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output/'report.json', 60, native_resolution=True,
                              background_only=True, native_capture_helper=helper)
            try:
                assert not check.navigation()['open'], 'Preflight requires closed ordinary workspace'
                report['runtime_config'] = check.run('from modern_projection.projection.debug_blueprints import VISUAL_CASES\n'
                    '_result=json.dumps(VISUAL_CASES["chest_top"])')
                assert json.loads(json.dumps(config)) == report['runtime_config'], 'Loaded chest metadata differs from frozen source'
                report['grounded_baseline'] = execute(client, BASELINE)
                write_json(args.output/'grounded_baseline_before_mutation.json', report['grounded_baseline'])
                report['options'] = check.run(CAPTURE_OPTIONS); flags.add('options')
                report['hud'] = check.run(SAVE_HUD); flags.add('hud')
                report['daylight'] = execute(client, SETUP_DAYLIGHT); flags.add('daylight')
                report['player'] = execute(client, public.SAVE_PLAYER); flags.add('player')
                check.run(INSTALL_PROBE); flags.add('probe')
                check.run(SAVE_VISUAL); flags.add('visual')
                report['grid'] = check.run('_result=s.grid')
                setup = native.SETUP.replace('int(math.floor(foot[1]))+16',
                                            'int(math.floor(foot[1]))+%d' % config['target_height_offset'])
                report['native_setup'] = native.server_run(client, setup); flags.add('world')
                report['native_background'] = native.server_run(client, editor.BACKGROUND %
                    (config['native_background'], editor.material(config['native_background']['material'])))
                target = tuple(report['native_setup']['target'])
                cells = (target, (target[0]+1, target[1], target[2]))
                plan = report['occupancy_plan'] = occupancy_plan(cells, args.occupied_half)
                calibration_code = editor.CUBE.replace("target=tuple(saved['target'])",
                                                      'target=%r' % (plan['remaining_world'],))
                calibration = report['calibration'] = {'placement': native.server_run(client, calibration_code)}
                pose = report['declared_pose'] = declared_pose(check, cells, config)
                time.sleep(1.)
                calibration['shown'] = public.capture_at(check, 'cube_remaining_target', pose)
                native.server_run(client, native.CLEAR); time.sleep(.5)
                calibration['empty'] = public.capture_at(check, 'cube_empty', pose)
                crop = tuple(int(value*calibration['shown']['size'][axis % 2])
                             for axis, value in enumerate(frozen['world_signal_roi']))
                cube = editor.extract(calibration['shown']['path'], calibration['empty']['path'], crop,
                                      args.output/'remaining_target_cube_signal.png')
                half_crop = tuple(cube[2]['world_bounds'])
                calibration['remaining_target_bounds'] = half_crop
                write_json(args.output/'remaining_target_bounds_before_chests.json', calibration)
                for case in config['cases'][1:1+args.case_limit]:
                    label = case['id']
                    row = dict(case); report['cases'].append(row)
                    row['native_double_placement'] = native.server_run(client, native.PLACE %
                        (case['name'], case['direction'], True))
                    time.sleep(2.)
                    row['pose'] = editor.native_pose(check, row['native_double_placement']['cells'], config)
                    assert camera_matches(check.run(native.CAMERA), pose), 'Chest placement changed declared camera'
                    row['public_source'] = check.run(public.LOAD_PUBLIC % (case['fixture'], case['cells']))
                    row['native_double'] = public.capture_at(check, label+'_native_double', pose)
                    native.server_run(client, native.CLEAR); time.sleep(.5)
                    row['native_empty'] = public.capture_at(check, label+'_native_empty', pose)
                    double = editor.extract(row['native_double']['path'], row['native_empty']['path'], crop,
                                            args.output/(label+'_native_double_signal.png'))
                    native_half = editor.extract(row['native_double']['path'], row['native_empty']['path'], half_crop,
                                                 args.output/(label+'_native_logical_half_signal.png'))
                    row['native_double_signal'], row['native_logical_half_signal'] = double[2], native_half[2]
                    check.run(native.PROJECT.replace('s.projection_missing=False', 's.projection_missing=True'))
                    check.run('sys._entity_visual_r8_document=s.editor.document.to_data()\n'
                              'sys._entity_visual_r8_history=(len(s.editor.undo_stack),len(s.editor.redo_stack))\n_result=True')
                    focuses = plan['focuses']
                    row['unoccupied_state'] = settled(check, focuses, (1, 1))
                    unoccupied = visibility_pair(check, label+'_unoccupied', focuses[0], pose)
                    row['unoccupied'] = unoccupied
                    positive = editor.extract(unoccupied['screenshot']['path'], unoccupied['hidden_screenshot']['path'], crop,
                                              args.output/(label+'_projection_double_signal.png'))
                    row['positive_comparison'] = comparison(double, positive)
                    row['reservation'] = execute(client, occupied.RESERVE % (plan['occupied_world'],)); flags.add('occupied')
                    row['stone_write'] = execute(client, occupied.WRITE % 'minecraft:stone')
                    for phase in ('dynamic', 'initial'):
                        if phase == 'initial':
                            check.run('b.stop_projection()\nb.project()\n_result=True')
                        row[phase+'_state'] = settled(check, focuses, plan['expected'])
                        pair = visibility_pair(check, label+'_'+phase, plan['remaining_focus'], pose)
                        row[phase] = pair
                        fragment = editor.extract(pair['screenshot']['path'], pair['hidden_screenshot']['path'], half_crop,
                                                  args.output/(label+'_'+phase+'_half_signal.png'))
                        row[phase+'_logical_half_comparison'] = comparison(native_half, fragment)
                    row['stone_clear'] = execute(client, occupied.WRITE % 'minecraft:air')
                    row['recovery_state'] = settled(check, focuses, (1, 1))
                    recovered = visibility_pair(check, label+'_recovered', focuses[0], pose)
                    row['recovered'] = recovered
                    recovered_signal = editor.extract(recovered['screenshot']['path'], recovered['hidden_screenshot']['path'], crop,
                                                      args.output/(label+'_recovered_signal.png'))
                    row['recovery_comparison'] = comparison(double, recovered_signal)
                    check.run('b.stop_projection()\n_result=True')
                    row['native_single_placement'] = native.server_run(client, native.PLACE %
                        (case['name'], case['direction'], False))
                    time.sleep(2.)
                    row['native_single'] = public.capture_at(check, label+'_native_single', pose)
                    native.server_run(client, native.CLEAR); time.sleep(.5)
                    row['native_single_empty'] = public.capture_at(check, label+'_native_single_empty', pose)
                    # Native single is always at the first cell, including when the
                    # second cell was the earlier logical-half acceptance target.
                    single = editor.extract(row['native_single']['path'], row['native_single_empty']['path'], crop,
                                            args.output/(label+'_native_single_signal.png'))
                    row['native_single_signal'] = single[2]
                    row['single_versus_logical_half_diagnostic'] = comparison(single, native_half)
                    row['native_single_composite_placement'] = native.server_run(client, native.PLACE %
                        (case['name'], case['direction'], False))
                    time.sleep(2.)
                    check.run('b.project()\n_result=True')
                    row['composite_state'] = settled(check, focuses, (2, 1))
                    composite = visibility_pair(check, label+'_real_single_plus_ghost', focuses[1], pose)
                    row['real_single_plus_ghost'] = composite
                    assembly = composite_signal(composite['screenshot']['path'], row['native_empty']['path'], crop,
                                                args.output/(label+'_composite_signal.png'))
                    row['composite_signal'] = assembly[2]
                    row['composite_versus_native_double_diagnostic'] = comparison(double, assembly)
                    check.run('b.stop_projection()\n_result=True')
                    native.server_run(client, native.CLEAR)
                    execute(client, occupied.CLEAR); flags.discard('occupied')
                    row['passed'] = all(row[key]['passed'] for key in
                                        ('positive_comparison', 'dynamic_logical_half_comparison',
                                         'initial_logical_half_comparison', 'recovery_comparison'))
                    write_json(args.output/'report.json', report)
                    print(json.dumps({'case': label, 'passed': row['passed'],
                                      'dynamic': row['dynamic_logical_half_comparison'],
                                      'single_diagnostic': row['single_versus_logical_half_diagnostic'],
                                      'composite_diagnostic': row['composite_versus_native_double_diagnostic']}), flush=True)
                report['completed'] = True
                report['passed'] = all(row['passed'] for row in report['cases'])
            finally:
                actions = [
                    ('occupied_world', lambda: execute(client, occupied.CLEAR) if 'occupied' in flags else True),
                    ('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                    ('workspace', lambda: editor.close_editor(check)),
                    ('camera', lambda: check.run(camera_restore_code(False)) if 'visual' in flags else True),
                    ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\n'
                        's.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                        'del sys._blueprint_visual_saved\ns.grid=%r\n_result=True' % report['grid']) if 'visual' in flags else True),
                    ('editor', lambda: check.run(RESTORE) if 'probe' in flags else True),
                    ('world', lambda: native.server_run(client, native.CLEANUP) if 'world' in flags else True),
                    ('client_flags', lambda: check.run('for name in ("_copper_native_document","_copper_native_origin",'
                        '"_chest_top_public_snapshot","_entity_visual_r8_document","_entity_visual_r8_history"):\n'
                        ' if hasattr(sys,name):delattr(sys,name)\n_result=True')),
                    ('player', lambda: execute(client, public.RESTORE_PLAYER) if 'player' in flags else True),
                    ('hud', lambda: check.run(RESTORE_HUD) if 'hud' in flags else True),
                    ('options', lambda: check.run(RESTORE_OPTIONS) if 'options' in flags else True),
                    ('daylight', lambda: execute(client, RESTORE_DAYLIGHT) if 'daylight' in flags else True)]
                cleanup(actions, report)
                if 'player' in flags:
                    try:
                        time.sleep(.5)
                        observed = execute(client, BASELINE)
                        audit = {'baseline': report['grounded_baseline'], 'observed': observed,
                                 'passed': restoration_matches(report['grounded_baseline'], observed),
                                 'read_only': True, 'position_tolerance': .02}
                        report['restoration_audit'] = audit
                        write_json(args.output/'restoration_audit.json', audit)
                        assert audit['passed'], audit
                    except Exception as error:
                        report['cleanup_errors'].append('restoration_audit: '+type(error).__name__+': '+str(error))
                        report['restored'] = False
    except Exception as error:
        report['error'] = type(error).__name__+': '+str(error)
        raise
    finally:
        unchanged = all(hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                        for row in production+tools)
        write_json(args.output/'frozen_source_after.json', {'production_and_tools_unchanged': unchanged})
        report['passed'] = report['passed'] and report['restored'] and unchanged
        write_json(args.output/'report.json', report)
    print(json.dumps({key: report[key] for key in ('completed', 'passed', 'restored')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
