"""Sample public snow cases in independent editor, full and missing projections."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_shulker_orientations import server_run, viewport_crop
from verify_snow_plant_visibility import (LOAD, NATIVE_SETUP, NATIVE_CLEANUP, native_capture,
                                         projection_capture, world_cell_roi, capture_frame,
                                         compare_native, compare_controls, cross_assets,
                                         editor_snow_geometry, editor_cross_above_snow, count)
from reanalyze_snow_visibility import stored_geometry, stored_upper
from _session import load_session
from verify_sign_visuals import SignCheck
from camera_projection import project_points
from verify_snow_plant_visibility import convex_hull

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from projection.debug_snow_blueprints import NAMES, VISUAL_CASE


def image_record(capture):
    path = Path(capture['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != capture['sha256']:
        raise ValueError('Saved snow catalogue capture changed: ' + str(path))
    if capture.get('compact_screenshot'):
        image_record(capture['compact_screenshot'])
    return path


def native_assets(session, plant):
    data = Path(session['game_executable']).parent/'data/resource_packs/vanilla'
    blocks_path, terrain_path = data/'blocks.json', data/'textures/terrain_texture.json'
    blocks, terrain = (json.loads(path.read_text(encoding='utf8')) for path in (blocks_path, terrain_path))
    definition = blocks[plant]
    names = definition['textures']
    names = names.values() if isinstance(names, dict) else (names,)
    paths = []
    for name in names:
        values = terrain['texture_data'][name]['textures']
        for value in values if isinstance(values, list) else (values,):
            value = value['path'] if isinstance(value, dict) else value
            path = next((data/(value+extension) for extension in ('.tga', '.png')
                         if (data/(value+extension)).is_file()), None)
            if path is None:
                raise ValueError('Installed native plant texture is missing: ' + value)
            raw = path.read_bytes()
            with Image.open(path) as image:
                size, alpha_bounds = image.size, image.convert('RGBA').getchannel('A').getbbox()
            paths.append({'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(),
                          'size': size, 'alpha_bounds': alpha_bounds})
    return {'definition': definition, 'textures': paths,
            'mapping_sources': {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (blocks_path, terrain_path)}}


def frame_for(capture, hidden, crop, roi=None):
    return capture_frame(image_record(capture), crop, image_record(hidden), roi=roi)


def save_mask(frame, output, label):
    path = output.with_name(output.stem+'_'+label+'_mask.png')
    frame['object'].save(path)
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'pixels': count(frame['object']), 'bounds': frame['object'].getbbox()}


def compare_world(native, actual, foliage):
    return compare_native(native, actual, foliage=foliage)


def exposed_plant(frame, snow):
    result = dict(frame)
    # The independent snow control removes its own edge tolerance, never a fitted plant hull.
    result['object'] = ImageChops.subtract(frame['object'], snow['object'].filter(ImageFilter.MaxFilter(7)))
    return result


def covered_control(report, row):
    control = next(value for value in report['rows']
                   if value['plant'] == row['plant'] and value['kind'] == 'snow' and value['height'] == row['height'])
    if control['crop'] != row['crop'] or control['world_roi'] != row['world_roi']:
        raise ValueError('Covered plant snow control pose or calibrated ROI changed')
    return control


def compare_exposed(comparison, native, actual, snow):
    plant = compare_native(exposed_plant(native, snow), exposed_plant(actual, snow), foliage=False)['masks']['object']
    comparison['masks']['exposed_plant'] = plant
    comparison['passed'] = comparison['passed'] and plant['passed']
    comparison['exposed_plant_method'] = 'Independent native snow-only mask expanded by the unchanged 3-pixel edge tolerance; plant pixels must separately pass'
    return comparison


def snow_control_matches(source, original):
    return all(source[key] == original[key] for key in
               ('front', 'back', 'focus', 'fixture', 'fixture_schema', 'metadata',
                'registry_fingerprint', 'registry_version', 'runtime_minecraft_version', 'render_layout_version'))


def native_boundary(frame, roi, record, crop, screenshot_size):
    base, pose = record['world_base'], record['camera']
    points = [tuple(base[i]+delta[i] for i in range(3))
              for delta in ((x, y, z) for x in (0., 1.) for y in (0., .1) for z in (0., 1.))]
    projected = project_points(points, pose['position'], pose['target'], screenshot_size,
                               record['calibration']['vertical_fov'], pose['rotation'][2])
    foot = Image.new('L', roi.size)
    ImageDraw.Draw(foot).polygon(convex_hull((point['screenX']-crop[0], point['screenY']-crop[1])
                                           for point in projected), fill=255)
    boundary = ImageChops.subtract(roi, roi.filter(ImageFilter.MinFilter(5)))
    boundary = ImageChops.subtract(boundary, foot.filter(ImageFilter.MaxFilter(7)))
    observed = count(ImageChops.multiply(frame['object'], boundary))
    return {'passed': observed == 0, 'clipped_boundary_pixels': observed,
            'method': 'Fixed calibrated unit-cell hull boundary, excluding bottom .1-block root/support band; boundary contact is unaccepted, never used to widen the ROI'}


def summarize(report):
    expected = {(plant, kind, height) for plant in report['plants']
                for kind, height in [('plant', 0)]+[(kind, height) for height in report['heights']
                                                 for kind in ('snow', 'covered')]}
    measured = [row for row in report['rows'] if row['kind'] != 'blank']
    actual = {(row['plant'], row['kind'], row['height']) for row in measured}
    report['completed'] = expected == actual and len(measured) == len(expected)
    comparisons = [row['comparisons'] for row in report['rows'] if row['kind'] != 'blank']
    report['scopes'] = {mode: {'passed': bool(comparisons) and all(row[mode]['passed'] for row in comparisons),
                              'failures': [{'plant': row['plant'], 'kind': row['kind'], 'height': row['height'],
                                            'comparison': row['comparisons'][mode]}
                                           for row in report['rows'] if row['kind'] != 'blank'
                                           and not row['comparisons'][mode]['passed']]}
                       for mode in report['modes']}
    editor = [row['editor_controls'] for row in report['rows'] if row['kind'] == 'covered']
    report['scopes']['editor'] = {'passed': bool(editor) and all(row['passed'] for row in editor),
                                 'failures': [{'plant': row['plant'], 'height': row['height'],
                                               'controls': row['editor_controls']}
                                              for row in report['rows'] if row['kind'] == 'covered'
                                              and not row['editor_controls']['passed']],
                                 'scope': 'Standalone and snow controls within editor; no native editor pixel equivalence claim'}
    report['passed'] = report['completed'] and report.get('restored', False) and report.get('source_assets_stable', False) and all(
        row['passed'] for row in report['scopes'].values())
    report['all_current_plants_and_heights_sampled'] = set(report['plants']) == set(NAMES) and set(report['heights']) == set(range(8)) and report['completed']
    report['independent_nonblank_capture_rows'] = sum(row['kind'] != 'blank' and not row.get('shared_snow_control')
                                                    for row in report['rows'])
    report['covered_cases_captured'] = sum(row['kind'] == 'covered' for row in report['rows'])


def replay(source, output):
    report = json.loads(source.read_text(encoding='utf8'))
    if not report.get('completed') or not report.get('restored'):
        raise ValueError('Replay requires complete restored snow captures')
    report['replayed_from'] = {'path': str(source.resolve()), 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    editor_frames, blanks = {}, {}
    for row in report['rows']:
        if row['kind'] == 'blank':
            blanks[row['plant']] = row['editor']
            continue
        crop = row['editor_crop']
        editor = frame_for(row['editor'], blanks[row['plant']], crop)
        editor['geometry'] = stored_geometry(row.get('editor_geometry'), editor['image'].size) if row.get('editor_geometry') else editor['object']
        editor['above_snow'] = stored_upper(row.get('upper_geometry'), editor['image'].size)
        editor_frames[(row['plant'], row['kind'], row['height'])] = editor
        native = frame_for(row['native']['screenshot'], row['native']['hidden_screenshot'], row['crop'])
        polygon = row['world_roi']['polygon']
        from PIL import ImageDraw
        roi = Image.new('L', native['image'].size)
        ImageDraw.Draw(roi).polygon(polygon, fill=255)
        native['object'] = ImageChops.multiply(native['object'], roi)
        native['green'] = ImageChops.multiply(native['green'], roi)
        snow = None
        if row['kind'] == 'covered':
            control = covered_control(report, row)
            snow = frame_for(control['native']['screenshot'], control['native']['hidden_screenshot'], row['crop'], roi)
            row['visible_plant_control'] = {'plant': control['plant'], 'height': control['height'],
                                            'native_sha256': control['native']['screenshot']['sha256']}
        for mode, capture in row['world'].items():
            actual = frame_for(capture['screenshot'], capture['hidden_screenshot'], row['crop'], roi)
            row['comparisons'][mode] = compare_world(native, actual, row['plant'] in ('short_grass', 'fern') and row['kind'] != 'snow')
            if snow is not None:
                compare_exposed(row['comparisons'][mode], native, actual, snow)
        for mask in row['masks'].values():
            if hashlib.sha256(Path(mask['path']).read_bytes()).hexdigest() != mask['sha256']:
                raise ValueError('Saved snow catalogue mask changed: '+mask['path'])
        if row['kind'] == 'covered':
            row['editor_controls'] = compare_controls(editor_frames[(row['plant'], 'plant', 0)],
                                                      editor_frames[(row['plant'], 'snow', row['height'])], editor, row['height'])
        if row['kind'] == 'plant':
            row['native_roi_boundary'] = native_boundary(native, roi, row['world_roi'], row['crop'], row['native']['screenshot']['size'])
            for comparison in row['comparisons'].values():
                comparison['native_roi_not_clipped'] = row['native_roi_boundary']['passed']
                comparison['passed'] = comparison['passed'] and row['native_roi_boundary']['passed']
    summarize(report)
    write_json(output, report)
    return report


def run(args):
    session = load_session(live=True)
    calibration = json.loads(args.camera_calibration.read_text(encoding='utf8'))
    assert calibration['completed'] and calibration['passed']
    assert Path(calibration['session_file']).resolve() == Path(session['session_file']).resolve()
    plants = tuple(dict.fromkeys(args.plant or NAMES))
    heights = sorted(set(args.height or range(8)))
    modes = tuple(dict.fromkeys(args.mode or ('full', 'missing')))
    report = {'schema': 1, 'completed': False, 'restored': False, 'passed': False, 'rows': [],
              'plants': plants, 'heights': heights, 'modes': modes, 'session_file': session['session_file'],
              'native_resolution': args.native_resolution, 'fixture_lift_y': args.fixture_lift_y,
              'reuse_snow_controls': args.reuse_snow_controls,
              'calibration': calibration, 'blueprint_case': VISUAL_CASE, 'native_assets': {},
              'limits': {'native_recall': .75, 'native_precision': .75, 'native_edge_tolerance_pixels': 3},
              'scope': 'Fixed public snow cells moved to one isolated native-world focus; full and missing-only comparisons are independent',
              'mask_method': 'Immediate shown/cleared pixel difference inside calibrated cell ROI; all colors retained'}
    installed = saved = native_created = False
    frames, snow_controls = {}, {}
    with Client(timeout=30) as client:
        check = SignCheck(client, args.output, args.timeout, args.native_resolution)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            check.run(SAVE_VISUAL)
            saved = True
            report['original_workspace_open'] = check.run('_result=sys._blueprint_qa_saved["workspace"]')
            report['original_visual'] = check.run('_result=json.dumps(sys._blueprint_visual_saved)')
            check.refresh()
            focus = tuple(VISUAL_CASE['focus'])
            native_target = tuple(check.run('_result=json.dumps(tuple(b.player_origin()[i]+(6,8+%r,6)[i] for i in range(3)))' % args.fixture_lift_y))
            report['native_target'] = native_target
            native_created = True
            report['native_fixture'] = server_run(client, NATIVE_SETUP % (native_target,))
            for plant in plants:
                report['native_assets'][plant] = native_assets(session, plant)
                assets = cross_assets(session, plant)
                if assets is not None:
                    report.setdefault('proxy_assets', {})[plant] = assets[2]
                cases = [('blank', 0), ('plant', 0)]+[(kind, height) for height in heights for kind in ('snow', 'covered')]
                blank = crop = None
                for kind, height in cases:
                    label = plant+'_'+kind+'_h'+str(height)
                    support = 'podzol' if plant in ('brown_mushroom', 'red_mushroom') else 'dirt'
                    control_key = (support, height)
                    if kind == 'snow' and args.reuse_snow_controls and control_key in snow_controls:
                        original, snow_frame = snow_controls[control_key]
                        source = check.run(LOAD % (plant, height, kind))
                        assert snow_control_matches(source, original['source'])
                        row = deepcopy(original)
                        row['shared_snow_control'] = {'plant': original['plant'], 'height': height,
                                                      'support': support, 'reused_for_source': source,
                                                      'contract': 'Identical complete isolated snow/air input, pose, native support and frozen daylight; original capture source identity retained'}
                        row['plant'] = plant
                        frames[(plant, kind, height)] = snow_frame
                        report['rows'].append(row)
                        write_json(args.output, report)
                        continue
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('open snow catalogue', lambda row: row['open'] and not row['transition'], check.navigation)
                    source = check.run(LOAD % (plant, height, kind))
                    state = check.editor_preview('snow catalogue editor', source['metadata'], source['editor_id'], source['document_id'])
                    if kind != 'blank':
                        assert state['model_name'] and state['parts'] and state['renderer_active']
                    camera = check.wait('snow catalogue editor pose', lambda pose: all(abs(pose[i]-VISUAL_CASE['camera']['editor'][i]) < .01 for i in range(3)),
                                        lambda: check.run('_result=json.dumps(s.camera_pose)'))
                    time.sleep(.25)
                    editor = check.capture(label+'_editor')
                    current_crop = viewport_crop(check, editor)
                    assert crop is None or current_crop == crop
                    crop = current_crop
                    row = {'plant': plant, 'kind': kind, 'height': height, 'source': source, 'editor': editor,
                           'editor_crop': crop, 'editor_camera': camera}
                    if kind == 'blank':
                        blank = editor
                        report['rows'].append(row)
                        write_json(args.output, report)
                        continue
                    editor_frame = frame_for(editor, blank, crop)
                    editor_state = check.run('_result=json.dumps({"pose":s.camera_pose,"pan":s.camera_pan,"pivot":s.camera_pivot,"size":s.scene_size})')
                    if kind == 'snow':
                        geometry, geometry_record = editor_snow_geometry(crop, editor_state, focus, height)
                        editor_frame['geometry'] = geometry
                        row['editor_geometry'] = geometry_record
                    if kind == 'plant' and assets is not None:
                        editor_frame['above_snow'] = {h: editor_cross_above_snow(crop, editor_state, focus, h, assets[0], assets[1]) for h in heights}
                        row['upper_geometry'] = {}
                        for h, mask in editor_frame['above_snow'].items():
                            path = args.output.with_name(args.output.stem+'_'+plant+'_h'+str(h)+'_upper_geometry.png')
                            mask.save(path)
                            row['upper_geometry'][h] = {'mask': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bounds': mask.getbbox()}
                    frames[(plant, kind, height)] = editor_frame
                    row['masks'] = {'editor': save_mask(editor_frame, args.output, label+'_editor')}
                    world = {}
                    for mode in modes:
                        world[mode] = projection_capture(check, label+'_'+mode, focus, tuple(VISUAL_CASE['camera']['world_offset']), missing=mode == 'missing', fixture_lift_y=args.fixture_lift_y)
                        check.run('b.stop_projection()\n_result=True')
                    capture = world[modes[0]]
                    width, pixels_high = capture['screenshot']['size']
                    world_crop = (width//4, pixels_high//4, width*3//4, pixels_high*3//4)
                    roi, roi_record = world_cell_roi(check, world_crop, (width, pixels_high), native_target, capture['pose'], calibration)
                    native = native_capture(check, plant, kind, height, native_target, tuple(VISUAL_CASE['camera']['world_offset']))
                    assert all(value['pose'] == native['pose'] for value in world.values())
                    native_frame = frame_for(native['screenshot'], native['hidden_screenshot'], world_crop, roi)
                    row['masks']['native'] = save_mask(native_frame, args.output, label+'_native')
                    row['world'], row['native'], row['crop'], row['world_roi'] = world, native, world_crop, roi_record
                    row['comparisons'] = {}
                    snow = None
                    if kind == 'covered':
                        control = covered_control(report, row)
                        snow = frame_for(control['native']['screenshot'], control['native']['hidden_screenshot'], world_crop, roi)
                        row['visible_plant_control'] = {'plant': control['plant'], 'height': height,
                                                        'native_sha256': control['native']['screenshot']['sha256']}
                        row['masks']['native_exposed_plant'] = save_mask(exposed_plant(native_frame, snow), args.output, label+'_native_exposed_plant')
                    for mode, value in world.items():
                        actual = frame_for(value['screenshot'], value['hidden_screenshot'], world_crop, roi)
                        row['masks'][mode] = save_mask(actual, args.output, label+'_'+mode)
                        row['comparisons'][mode] = compare_world(native_frame, actual, plant in ('short_grass', 'fern') and kind != 'snow')
                        if snow is not None:
                            compare_exposed(row['comparisons'][mode], native_frame, actual, snow)
                            row['masks'][mode+'_exposed_plant'] = save_mask(exposed_plant(actual, snow), args.output, label+'_'+mode+'_exposed_plant')
                    if kind == 'plant':
                        row['native_roi_boundary'] = native_boundary(native_frame, roi, roi_record, world_crop, (width, pixels_high))
                        for comparison in row['comparisons'].values():
                            comparison['native_roi_not_clipped'] = row['native_roi_boundary']['passed']
                            comparison['passed'] = comparison['passed'] and row['native_roi_boundary']['passed']
                    if kind == 'covered':
                        row['editor_controls'] = compare_controls(frames[(plant, 'plant', 0)], frames[(plant, 'snow', height)], editor_frame, height)
                    report['rows'].append(row)
                    if kind == 'snow':
                        snow_controls[control_key] = (row, editor_frame)
                    write_json(args.output, report)
                    print(json.dumps({'case': label, 'comparisons': {mode: value['passed'] for mode, value in row['comparisons'].items()},
                                      'editor_controls': row.get('editor_controls', {}).get('passed')}), flush=True)
                    check.run(camera_restore_code(False))
            report['source_assets_stable'] = all(native_assets(session, plant) == report['native_assets'][plant]
                                                  for plant in plants)
            for plant, recorded in report.get('proxy_assets', {}).items():
                report['source_assets_stable'] = report['source_assets_stable'] and cross_assets(session, plant)[2] == recorded
            summarize(report)
        finally:
            prior = sys.exc_info()[0]
            errors = []
            actions = []
            if native_created:
                def cleanup_native():
                    created = server_run(client, 'import sys\n_result=hasattr(sys,"_snow_visibility_native")')
                    return server_run(client, NATIVE_CLEANUP) if created else [{'resource': 'fixture_not_created', 'clean': True}]
                actions.append(('native_fixture', cleanup_native))
            if saved:
                actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                ('camera', lambda: check.run(camera_restore_code(False))),
                                ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True'))))
            if installed:
                actions.append(('workspace', lambda: check.run(RESTORE)))
            for name, action in actions:
                try:
                    value = action()
                    if name == 'native_fixture':
                        report['native_cleanup'] = value
                        assert value and all(row['clean'] for row in value)
                except Exception as error:
                    errors.append(name+': '+str(error))
            if saved and installed and not errors:
                try:
                    original_open = report['original_workspace_open']
                    navigation = check.navigation()
                    if original_open and not navigation['open']:
                        check.run('owner.open_workspace()\n_result=True')
                    elif not original_open and navigation['open']:
                        check.run('navigator.pop()\n_result=True')
                    report['restored_navigation'] = check.wait('restore catalogue navigation',
                        lambda value: value['open'] == original_open and not value['transition'], check.navigation)
                    current = check.run('''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'origin':s.origin,'opacity':s.opacity,'missing':s.projection_missing,
 'outline':s.projection_outline,'camera_rot':cam.GetCameraRotation(),
 'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw()})''')
                    report['restored_visual'] = current
                    original = report['original_visual']
                    assert all(current[key] == original[key] for key in ('origin', 'opacity', 'missing', 'outline', 'pitch_lock', 'yaw_lock'))
                    assert all(abs(current['camera_rot'][i]-original['camera_rot'][i]) < .01 for i in range(3))
                except Exception as error:
                    errors.append('restoration_readback: '+str(error))
            report['cleanup_errors'] = errors
            report['restored'] = not errors
            summarize(report)
            write_json(args.output, report)
            if errors and prior is None:
                raise RuntimeError('Snow catalogue cleanup failed: '+repr(errors))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', type=Path)
    parser.add_argument('--plant', action='append', choices=NAMES)
    parser.add_argument('--height', type=int, action='append', choices=range(8))
    parser.add_argument('--mode', action='append', choices=('full', 'missing'))
    parser.add_argument('--timeout', type=float, default=60.)
    parser.add_argument('--native-resolution', action='store_true')
    parser.add_argument('--fixture-lift-y', type=int, default=0,
                        help='Fixed world-space lift of the complete plant, reference and camera fixture, chosen before capture')
    parser.add_argument('--reuse-snow-controls', action='store_true',
                        help='Reuse independently captured identical snow-only controls within the batch; every covered plant is freshly captured')
    parser.add_argument('--replay', type=Path)
    args = parser.parse_args()
    if not args.replay and args.camera_calibration is None:
        parser.error('Native camera calibration from this session is required')
    report = replay(args.replay, args.output) if args.replay else run(args)
    print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                      'passed': report['passed'], 'failures': {name: len(row['failures']) for name, row in report['scopes'].items()}}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
