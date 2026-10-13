"""Accept centered snapshot plants through built-in editor and world projections.

The declared style is fixed-centered. Its geometry oracle comes from the pinned
plant texture alpha and mesh, independently projected into the actual camera.
Native random plant placements remain diagnostics in the older native suite.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, camera_restore_code
from verify_snow_plant_visibility import (LOAD, cross_assets, count, convex_hull, capture_frame,
                                         projection_capture, editor_cross_above_snow,
                                         editor_snow_geometry, compare_controls, world_cell_roi)
from verify_sign_visuals import SignCheck
from verify_shulker_orientations import viewport_crop
from camera_projection import project_points
from _session import load_session
from generate_centered_plant_profiles import PROFILE, validate_profile
from projection.geometry_palette import PLANT_MAX_Y
from projection.debug_snow_blueprints import NAMES, VISUAL_CASE
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from context_test_environment import run as run_environment, SETUP as SETUP_ENVIRONMENT, RESTORE as RESTORE_ENVIRONMENT
from native_draw_response import INSTALL as INSTALL_FRAMES, REMOVE as REMOVE_FRAMES, ui_preflight
from snow_contrast_backdrop import SETUP as SETUP_BACKDROP, RESTORE as RESTORE_BACKDROP

WORLD_OFFSET = (-2., 1.2, -2.5)


def selected_heights(name):
    """Thin, immediately before/at alpha burial, and completely covered."""
    top = PLANT_MAX_Y.get(('minecraft:'+name, 0), .8)
    burial = int(math.ceil(top*8.-1e-9))-1
    return tuple(sorted({0, max(0, burial-1), max(0, burial), 7}))


def height_matrix(plants, requested=None):
    heights = tuple(sorted(set(requested))) if requested else None
    if heights is not None and any(type(height) is not int or not 0 <= height <= 7 for height in heights):
        raise ValueError('Snow product heights must be integers from 0 to 7')
    return {name: heights if heights is not None else selected_heights(name) for name in plants}


def shape_metrics(expected, observed, minimum=80):
    expected_count, observed_count = count(expected), count(observed)
    recall = count(ImageChops.multiply(expected, observed.filter(ImageFilter.MaxFilter(7))))/max(1, expected_count)
    precision = count(ImageChops.multiply(observed, expected.filter(ImageFilter.MaxFilter(7))))/max(1, observed_count)
    empty = expected_count == 0
    passed = (observed_count < minimum//2 if empty else expected_count >= minimum and
              observed_count >= minimum and recall >= .75 and precision >= .75 and
              .5 <= observed_count/expected_count <= 2.)
    return {'passed': passed, 'expected_pixels': expected_count, 'observed_pixels': observed_count,
            'recall': recall, 'precision': precision, 'edge_tolerance_pixels': 3,
            'minimum_observable_pixels': minimum, 'expected_empty': empty}


def world_alpha(model, texture, pose, screenshot_size, crop, base, calibration, height=-1):
    result = Image.new('L', (crop[2]-crop[0], crop[3]-crop[1]))
    draw = ImageDraw.Draw(result)
    snow_top = (height+1)/8.
    if height >= 0 and pose['position'][1] <= base[1]+snow_top:
        raise ValueError('Y-clipped plant oracle requires a camera above the snow surface')
    for bone in model['netease:block_geometry']['bones']:
        angle = math.radians(bone['rotation'][1])
        px, unused, pz = bone['pivot']
        for cube in bone['cubes']:
            ox, oy, oz = cube['origin']
            sx, sy, sz = cube['size']
            if sz != 0:
                raise ValueError('Centered snapshot oracle needs crossed planes')

            def point(u, y):
                dx, dz = ox+sx*u-px, oz-pz
                x, z = px+dx*math.cos(angle)+dz*math.sin(angle), pz-dx*math.sin(angle)+dz*math.cos(angle)
                projected = project_points([(base[0]-x/16., base[1]+y, base[2]+z/16.)],
                                           pose['position'], pose['target'], screenshot_size,
                                           calibration['vertical_fov'], pose['rotation'][2])[0]
                return projected['screenX']-crop[0], projected['screenY']-crop[1]

            for row in range(texture.height):
                low = max(snow_top, (oy+sy*(1.-(row+1)/float(texture.height)))/16.)
                high = (oy+sy*(1.-row/float(texture.height)))/16.
                if high <= low:
                    continue
                for column in range(texture.width):
                    if texture.getpixel((column, row))[3] <= 127:
                        continue
                    left, right = column/float(texture.width), (column+1)/float(texture.width)
                    for a, b in ((left, right), (1.-right, 1.-left)):
                        draw.polygon((point(a, low), point(b, low), point(b, high), point(a, high)), fill=255)
    return result


def save_mask(mask, output, label):
    path = output.with_name(output.stem+'_'+label+'_mask.png')
    mask.save(path)
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'pixels': count(mask), 'bounds': mask.getbbox()}


def run(args):
    session = load_session(live=True)
    profile = json.loads(PROFILE.read_bytes())
    validate_profile(profile, Path(session['game_executable']).parent/'data/resource_packs/vanilla')
    calibration = json.loads(args.camera_calibration.read_bytes())
    if not calibration.get('passed') or Path(calibration['session_file']).resolve() != Path(session['session_file']).resolve():
        raise ValueError('Same-session passing cube calibration is required')
    plants = tuple(dict.fromkeys(args.plant or NAMES))
    heights = height_matrix(plants, args.height)
    report = {'schema': 1, 'completed': False, 'passed': False, 'rows': [],
              'style': profile['style'], 'profile_sha256': hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
              'plants': plants, 'heights': heights,
              'calibration': calibration, 'blueprint_case': VISUAL_CASE,
              'session_file': session['session_file'], 'agent_activation_allowed': False,
              'capture_policy': 'Owner-bound guarded capture; user may foreground the game',
              'native_random_jitter_is_diagnostic': True,
              'scope': 'Centered snapshot dry and alpha burial boundaries; built-in editor and separate full/missing projections'}
    installed = saved = options_saved = environment_saved = frames_installed = backdrop_started = False
    snow_frames, snow_records = {}, {}
    started = time.monotonic()
    with Client(timeout=30) as client:
        check = SignCheck(client, args.output, args.timeout, native_resolution=True, background_only=True)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            original_open = check.run('_result=sys._blueprint_qa_saved["workspace"]')
            check.run(SAVE_VISUAL)
            saved = True
            report['capture_options'] = check.run(CAPTURE_OPTIONS)
            options_saved = True
            report['environment'] = run_environment(client, SETUP_ENVIRONMENT)
            environment_saved = True
            focus = tuple(VISUAL_CASE['focus'])
            # Y clipping alone does not model snow's occlusion from below.
            offset = WORLD_OFFSET
            target = tuple(check.run('_result=json.dumps(tuple(b.player_origin()[i]+(6,32,6)[i] for i in range(3)))'))
            report['target'], report['world_offset'] = target, offset
            check.run(INSTALL_FRAMES)
            frames_installed = True
            backdrop_started = True
            report['backdrop'] = run_environment(client, SETUP_BACKDROP % (target,))
            check.require_native_response = True
            ui_verified = False
            for plant in plants:
                assets = cross_assets(session, plant)
                if assets is None:
                    raise ValueError('Known snow plant has no centered render source: '+plant)
                model, texture, asset_record = assets
                report.setdefault('assets', {})[plant] = asset_record
                frames = {'editor': {}, 'full': {}, 'missing': {}}
                blank = None
                cases = [('blank', 0), ('plant', 0)]+[(kind, height) for height in heights[plant]
                                                     for kind in ('snow', 'covered')]
                for kind, height in cases:
                    label = plant+'_'+kind+'_h'+str(height)
                    if kind == 'snow' and height in snow_frames:
                        for mode, frame in snow_frames[height].items():
                            frames[mode][('snow', height)] = frame
                        report['rows'].append({'plant': plant, 'kind': kind, 'height': height,
                                               'shared_snow_control': snow_records[height]})
                        continue
                    check.run('b.stop_projection()\nowner.open_workspace()\n_result=True')
                    check.wait('open centered snapshot editor', lambda nav: nav['open'] and not nav['transition'], check.navigation)
                    source = check.run(LOAD % (plant, height, kind))
                    check.editor_preview(label, source['metadata'], source['editor_id'], source['document_id'])
                    camera_state = check.run('_result=json.dumps({"pose":s.camera_pose,"pan":s.camera_pan,"pivot":s.camera_pivot,"size":s.scene_size})')
                    time.sleep(.15)
                    editor = check.capture(label+'_editor')
                    crop = viewport_crop(check, editor)
                    row = {'plant': plant, 'kind': kind, 'height': height, 'source': source,
                           'editor': editor, 'editor_crop': crop, 'camera_state': camera_state,
                           'checks': {}}
                    if kind == 'blank':
                        blank = editor
                        if not ui_verified:
                            report['native_draw_preflight'] = ui_preflight(check)
                            ui_verified = True
                        report['rows'].append(row)
                        write_json(args.output, report)
                        continue
                    geometry = None
                    if kind == 'snow':
                        geometry, row['snow_geometry'] = editor_snow_geometry(crop, camera_state, focus, height)
                    frame = capture_frame(editor['path'], crop, blank['path'], geometry=geometry)
                    if kind == 'plant':
                        frame['above_snow'] = {h: editor_cross_above_snow(crop, camera_state, focus, h, model, texture)
                                               for h in heights[plant]}
                        expected = editor_cross_above_snow(crop, camera_state, focus, -1, model, texture)
                        row['checks']['editor_shape'] = shape_metrics(expected, frame['object'])
                        row['editor_expected_alpha'] = save_mask(expected, args.output, label+'_editor_expected')
                    if kind == 'covered':
                        row['checks']['editor_snow'] = compare_controls(frames['editor'][('plant', 0)], frames['editor'][('snow', height)], frame, height)
                    frames['editor'][(kind, height)] = frame
                    row['editor_mask'] = save_mask(frame['object'], args.output, label+'_editor')
                    row['world'] = {}
                    world_frames = {}
                    for mode in ('full', 'missing'):
                        world = projection_capture(check, label+'_'+mode, focus, offset,
                                                   missing=mode == 'missing', world_target=target,
                                                   settle_seconds=2.)
                        width, pixels_high = world['screenshot']['size']
                        world_crop = (width//4, pixels_high//4, width*3//4, pixels_high*3//4)
                        roi, roi_record = world_cell_roi(check, world_crop, (width, pixels_high), target, world['pose'], calibration)
                        unclipped = capture_frame(world['screenshot']['path'], world_crop, world['hidden_screenshot']['path'])
                        outside = ImageChops.subtract(unclipped['object'], roi.filter(ImageFilter.MaxFilter(7)))
                        outside_pixels = count(outside)
                        actual = dict(unclipped, object=ImageChops.multiply(unclipped['object'], roi),
                                      green=ImageChops.multiply(unclipped['green'], roi))
                        row['checks'][mode+'_inside_cell'] = {
                            'passed': outside_pixels <= max(24, count(actual['object'])*.02),
                            'outside_pixels': outside_pixels, 'tolerance_pixels': 3,
                            'method': 'Immediate shown-hidden difference outside calibrated unit-cell hull before ROI clipping'}
                        if kind == 'plant':
                            expected = world_alpha(model, texture, world['pose'], (width, pixels_high), world_crop, target, calibration)
                            actual['above_snow'] = {h: world_alpha(model, texture, world['pose'], (width, pixels_high), world_crop, target, calibration, h)
                                                   for h in heights[plant]}
                            row['checks'][mode+'_shape'] = shape_metrics(expected, actual['object'])
                            world['expected_alpha'] = save_mask(expected, args.output, label+'_'+mode+'_expected')
                        if kind == 'snow':
                            actual['geometry'] = actual['object']
                        if kind == 'covered':
                            row['checks'][mode+'_snow'] = compare_controls(frames[mode][('plant', 0)], frames[mode][('snow', height)], actual, height)
                        frames[mode][(kind, height)] = actual
                        world_frames[mode] = actual
                        world['roi'], world['mask'] = roi_record, save_mask(actual['object'], args.output, label+'_'+mode)
                        row['world'][mode] = world
                        check.run('b.stop_projection()\n_result=True')
                    row['checks']['full_missing_equivalence'] = shape_metrics(world_frames['full']['object'], world_frames['missing']['object'])
                    row['passed'] = all(value['passed'] for value in row['checks'].values())
                    report['rows'].append(row)
                    if kind == 'snow':
                        snow_frames[height] = {mode: frames[mode][('snow', height)] for mode in frames}
                        snow_records[height] = {'plant': plant, 'height': height,
                                                'editor_sha256': editor['sha256'],
                                                'full_sha256': row['world']['full']['screenshot']['sha256'],
                                                'missing_sha256': row['world']['missing']['screenshot']['sha256']}
                    write_json(args.output, report)
                    print(json.dumps({'case': label, 'passed': row['passed'],
                                      'checks': {key: value['passed'] for key, value in row['checks'].items()}}), flush=True)
                    check.run(camera_restore_code(False))
            # Use the same built-in flower/snow cell, hide its logical Y layer,
            # and prove the editor has no leftover overlay before restoring it.
            check.run('owner.open_workspace()\n_result=True')
            check.wait('open cutaway editor', lambda nav: nav['open'] and not nav['transition'], check.navigation)
            empty_source = check.run(LOAD % ('poppy', 0, 'blank'))
            check.editor_preview('cutaway empty control', empty_source['metadata'], empty_source['editor_id'], empty_source['document_id'])
            empty_editor = check.capture('cutaway_empty_control')
            source = check.run(LOAD % ('poppy', 0, 'covered'))
            check.editor_preview('cutaway source', source['metadata'], source['editor_id'], source['document_id'])
            check.run('s.editor.layer=0\ns.display_mode("section")\n_result=True')
            check.wait('cutaway removes foreground and snow overlay',
                       lambda value: not value['pending'] and not value['running'] and not value['model'] and value['visible_cells']==0,
                       lambda: check.run('_result=json.dumps({"pending":s.preview_pending,"running":s.tiles.running,"model":s.model_name,"visible_cells":sum(part.get("count",0) for key,part in s.tiles.parts.items() if key in s.tiles.region_owners)})'))
            hidden_editor = check.capture('cutaway_hidden')
            cut_crop = viewport_crop(check, hidden_editor)
            cut_frame = capture_frame(hidden_editor['path'], cut_crop, empty_editor['path'])
            cut_check = shape_metrics(Image.new('L', cut_frame['object'].size), cut_frame['object'])
            report['cutaway'] = {'source': source, 'screenshot': hidden_editor,
                                 'empty_control': empty_editor, 'checks': cut_check,
                                 'mask': save_mask(cut_frame['object'], args.output, 'cutaway'),
                                 'passed': cut_check['passed']}
            report['completed'] = True
        finally:
            prior = __import__('sys').exc_info()
            if prior[0] is not None:
                report['error'] = prior[0].__name__+': '+str(prior[1])
            errors = []
            actions = []
            if frames_installed:
                actions.append(('render_observer', lambda: check.run(REMOVE_FRAMES)))
            if backdrop_started:
                actions.append(('contrast_backdrop', lambda: run_environment(client, RESTORE_BACKDROP)))
            if environment_saved:
                actions.append(('environment', lambda: run_environment(client, RESTORE_ENVIRONMENT)))
            if options_saved:
                actions.append(('capture_options', lambda: check.run(RESTORE_OPTIONS)))
            if saved:
                actions.extend((('projection', lambda: check.run('b.stop_projection()\n_result=True')),
                                ('camera', lambda: check.run(camera_restore_code(False))),
                                ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\ns.origin=saved["origin"]\ns.opacity=saved["opacity"]\ns.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\ndel sys._blueprint_visual_saved\n_result=True'))))
            if installed:
                actions.append(('workspace', lambda: check.run(RESTORE)))
            for name, action in actions:
                try:
                    action()
                except Exception as error:
                    errors.append(name+': '+str(error))
            if installed and saved and not errors:
                try:
                    if original_open:
                        check.run('owner.open_workspace()\n_result=True')
                    elif check.navigation()['open']:
                        check.run('navigator.pop()\n_result=True')
                    check.wait('restore navigation', lambda nav: nav['open']==original_open and not nav['transition'], check.navigation)
                except Exception as error:
                    errors.append('navigation: '+str(error))
            report['cleanup_errors'], report['restored'] = errors, not errors
            report['elapsed_seconds'] = time.monotonic()-started
            report['passed'] = report['completed'] and report['restored'] and all(row.get('passed', True) for row in report['rows']) and report.get('cutaway', {}).get('passed', False)
            write_json(args.output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', type=Path, required=True)
    parser.add_argument('--plant', choices=NAMES, action='append')
    parser.add_argument('--height', choices=range(8), type=int, action='append',
                        help='Explicit snow height matrix; defaults to each plant burial boundaries')
    parser.add_argument('--timeout', type=float, default=45)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps({key: report[key] for key in ('completed', 'passed', 'restored', 'elapsed_seconds')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
