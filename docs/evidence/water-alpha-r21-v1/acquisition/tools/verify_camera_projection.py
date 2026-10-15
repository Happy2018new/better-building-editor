"""Calibrate analytical camera projection against one native client cube."""
import argparse
from collections import deque
import hashlib
import json
import math
import os
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from camera_projection import project_points
from context_test_environment import run as run_environment, SETUP as SETUP_ENVIRONMENT, RESTORE as RESTORE_ENVIRONMENT
from verify_debug_blueprints import Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, camera_restore_code
from verify_missing_neighbor_visuals import camera_matches, hull, maximum, signal
from verify_neighbor_world_visuals import CAPTURE_OPTIONS, RESTORE_OPTIONS
from verify_sign_visuals import SignCheck

LOAD_CUBE = '''from modern_projection.projection.model import Document,block
doc=Document((3,3,3),name='Native camera calibration cube')
doc.blocks[(1,1,1)]=block(('minecraft:stone',0))
sys._blueprint_qa_identity='camera.calibration.stone'
sys._blueprint_qa_nonce+=1
sys._blueprint_qa_expected={'metadata':{'name':doc.name,'size':doc.size,'blocks':1},
 'previous_document_id':id(s.editor.document),'editor_id':None}
s._loaded(doc)
s.emit()
foot=b.player_origin()
s.origin=(foot[0]+5,foot[1]+7+%r,foot[2]+5)
s.opacity=1.
s.projection_missing=False
s.projection_outline=False
b.project()
_result=json.dumps({'player_origin':foot,'projection_origin':s.origin,'cube_size':doc.size,
 'cube_material':('minecraft:stone',0),'cube_cell':(1,1,1)})
'''

POSE = '''offset=%r
target=tuple(s.origin[i]+1.5 for i in range(3))
position=tuple(target[i]+offset[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam=b.factory.CreateCamera(b.level)
cam.DepartCamera()
cam.LockModCameraPitch(True)
cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position)
assert cam.SetCameraRotation(rotation)
_result=json.dumps({'position':position,'rotation':rotation,'target':target})
'''

CAMERA = '''cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()})
'''


def projected_mask(pose, size, vertical_fov):
    target = pose['target']
    corners = [tuple(target[axis] + offset[axis] for axis in range(3))
               for offset in ((x, y, z) for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5))]
    points = project_points(corners, pose['position'], target, size, vertical_fov)
    polygon = hull((row['screenX'], row['screenY']) for row in points)
    result = Image.new('L', size)
    ImageDraw.Draw(result).polygon(polygon, fill=255)
    return result


def fit_fov(actual, pose, fixed_fov=None):
    bounds = actual.getbbox()
    if bounds is None:
        raise AssertionError('The native calibration cube is invisible')
    best = None
    actual_pixels = actual.histogram()[255]
    candidates = (fixed_fov,) if fixed_fov is not None else (step / 10. for step in range(300, 1301))
    for fov in candidates:
        predicted = projected_mask(pose, actual.size, fov)
        expected = predicted.getbbox()
        error = sum((bounds[i] - expected[i]) ** 2 for i in range(4))
        # The full native raster remains the oracle. Outside its bounding box
        # the prediction is zero, so only this exact crop contributes overlap.
        predicted_crop = predicted.crop(expected)
        predicted_pixels = predicted_crop.histogram()[255]
        intersection = ImageChops.multiply(actual.crop(expected), predicted_crop).histogram()[255]
        union = actual_pixels + predicted_pixels - intersection
        score = (-intersection / max(1, union), error)
        if best is None or score < best[0]:
            best = (score, fov, predicted)
    native_edges = actual.filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value else 0)
    predicted_edges = best[2].filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value else 0)
    recall = ImageChops.multiply(native_edges, predicted_edges.filter(ImageFilter.MaxFilter(5))).histogram()[255] / max(1, native_edges.histogram()[255])
    precision = ImageChops.multiply(predicted_edges, native_edges.filter(ImageFilter.MaxFilter(5))).histogram()[255] / max(1, predicted_edges.histogram()[255])
    return {'vertical_fov': best[1], 'bounds': bounds, 'predicted_bounds': best[2].getbbox(),
            'boundary_rms_pixels': math.sqrt(best[0][1] / 4.), 'mask_iou': -best[0][0],
            'outline_recall_2px': recall, 'outline_precision_2px': precision,
            'fit_contract': 'Complete convex hull of eight world cube corners and native silhouette, not width alone'}


def stone_signal(shown, hidden):
    with Image.open(shown).convert('RGB') as image:
        red, green, blue = image.split()
        spread = maximum(Image.merge('RGB', (ImageChops.difference(red, green),
                                              ImageChops.difference(red, blue),
                                              ImageChops.difference(green, blue))))
        neutral = spread.point(lambda value: 255 if value < 13 else 0)
        brightness = red.point(lambda value: 255 if value > 50 else 0)
        mask = ImageChops.multiply(neutral, brightness)
        center = Image.new('L', image.size)
        width, height = image.size
        ImageDraw.Draw(center).rectangle((width * .3, height * .25, width * .7, height * .75), fill=255)
        mask = ImageChops.multiply(mask, center)
    contribution = maximum(signal(shown, hidden)).point(lambda value: 255 if value > 20 else 0)
    mask = largest_component(ImageChops.multiply(mask, contribution))
    outline = fill_enclosed_holes(mask).filter(ImageFilter.MedianFilter(3))
    outline = outline.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    assert ImageChops.multiply(outline, contribution).histogram()[255] >= 1000, 'Native cube contribution is not observable'
    return outline


def fill_enclosed_holes(mask):
    """Fill binary mask holes disconnected from the boundary by four-neighbor paths."""
    # Padding connects all exterior regions; cursor and texture holes remain unfilled by the flood.
    padded = Image.new('L', (mask.width + 2, mask.height + 2))
    padded.paste(mask, (1, 1))
    ImageDraw.floodfill(padded, (0, 0), 128)
    filled = padded.point(lambda value: 0 if value == 128 else 255)
    return filled.crop((1, 1, mask.width + 1, mask.height + 1))


def largest_component(mask):
    pixels = mask.load()
    remaining = set((x, y) for y in range(mask.height) for x in range(mask.width) if pixels[x, y])
    largest = set()
    while remaining:
        first = remaining.pop()
        pending, component = deque((first,)), {first}
        while pending:
            x, y = pending.popleft()
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in remaining:
                    remaining.remove(point)
                    component.add(point)
                    pending.append(point)
        if len(component) > len(largest):
            largest = component
    result = Image.new('L', mask.size)
    output = result.load()
    for x, y in largest:
        output[x, y] = 255
    return result


def analyze_calibration(evidence, signal_cache=None):
    rows = evidence['views']
    if signal_cache is not None:
        assert len(signal_cache) == len(rows), 'Calibration signal cache length changed'
    actual = []
    for index, row in enumerate(rows):
        for capture in (row['shown'], row['hidden']):
            assert hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'], capture
        if signal_cache is None:
            actual.append(stone_signal(row['shown']['path'], row['hidden']['path']))
        else:
            key, mask = signal_cache[index]
            assert key == (row['view'], row['shown']['sha256'], row['hidden']['sha256']), 'Calibration signal cache pair/order changed'
            assert mask.mode == 'L' and mask.size == tuple(row['shown']['size']), 'Calibration signal cache viewport changed'
            actual.append(mask)
    fitted = [fit_fov(image, row['pose'])['vertical_fov'] for image, row in zip(actual, rows)]
    candidates = [step / 10. for step in range(int(min(fitted) * 10), int(max(fitted) * 10) + 1)]
    def score(fov):
        return sum(fit_fov(image, row['pose'], fov)['mask_iou'] for image, row in zip(actual, rows))
    common = max(candidates, key=score)
    for image, row in zip(actual, rows):
        row['fit'] = fit_fov(image, row['pose'], common)
        fit = row['fit']
        row['passed'] = (fit['boundary_rms_pixels'] <= 2 and fit['mask_iou'] >= .95 and
                         fit['outline_recall_2px'] >= .985 and fit['outline_precision_2px'] >= .985)
        image.save(row['signal'])
        native_outline = image.filter(ImageFilter.FIND_EDGES)
        fitted_outline = projected_mask(row['pose'], image.size, common).filter(ImageFilter.FIND_EDGES)
        Image.merge('RGB', (native_outline, fitted_outline, Image.new('L', image.size))).save(row['outline_comparison'])
    evidence['passed'] = len(rows) == 3 and all(row['passed'] for row in rows)
    evidence['vertical_fov'] = common
    evidence['individual_fitted_vertical_fov'] = fitted
    evidence['limits'] = {'boundary_rms_pixels': 2, 'mask_iou': .95, 'outline_recall_2px': .985,
                          'outline_precision_2px': .985,
                          'source': 'Native JPEG edge extraction; complete hull must agree within two pixels in all three views'}
    return evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--timeout', type=float, default=90.)
    parser.add_argument('--native-resolution', action='store_true')
    parser.add_argument('--skyward-tilted', action='store_true',
                        help='Calibration-only tilted camera below the cube to use a sky background')
    parser.add_argument('--fixture-lift-y', type=int, default=0,
                        help='Fixed world-space lift of the entire cube and camera fixture, chosen before capture')
    parser.add_argument('--native-api', action='store_true',
                        help='Bind native WorldToScreenPoint cube corners to each exact PNG and session')
    parser.add_argument('--native-capture-exe', type=Path,
                        help='Owner-bound WGC executable required by --native-api')
    parser.add_argument('--replay', type=Path, help='Reanalyze preserved native captures without calling a game')
    args = parser.parse_args()
    if args.replay is not None:
        evidence = json.loads(args.replay.read_text(encoding='utf8'))
        analyze_calibration(evidence)
        write_json(args.output, evidence)
        print(json.dumps({'passed': evidence['passed'], 'vertical_fov': evidence['vertical_fov'],
                          'replayed': str(args.replay)}))
        return 0 if evidence['passed'] else 1
    if not -64 <= args.fixture_lift_y <= 64:
        parser.error('Fixture lift must be between -64 and 64 blocks')
    if args.native_api and (not args.native_resolution or args.native_capture_exe is None):
        parser.error('Native camera API evidence requires --native-resolution and --native-capture-exe')
    evidence = {'schema': 1, 'passed': False, 'completed': False, 'views': [],
                'scope': 'Exact full native client cube; world blocks and player position untouched',
                'session_file': os.environ.get('MCDEV_SESSION_FILE'),
                'native_resolution': args.native_resolution,
                'skyward_tilted': args.skyward_tilted,
                'fixture_lift_y': args.fixture_lift_y}
    if args.native_api:
        from _session import load_session
        from probe_product_water import snapshot_sources, snapshot_digest
        from water_native_projection import SCHEMA, UNITS, cube_query_code
        session = load_session(os.environ['MCDEV_SESSION_FILE'], os.environ['MCDEV_OWNER'], live=True)
        evidence['native_projection'] = {'schema': SCHEMA, 'coordinate_units': UNITS, 'rows': {},
            'session_binding': {key: session[key] for key in
                ('id', 'owner', 'game_pid', 'game_identity', 'session_file')},
            'source_contract_sha256': snapshot_digest(snapshot_sources(Path(__file__).resolve().parents[1]))}

    def capture_frame(check, label):
        if not args.native_api:
            return check.capture(label)
        from capture_native_window import capture as native_capture
        reading = {'before': check.run(cube_query_code())}
        capture = native_capture(session['session_file'], session['owner'],
            args.output.with_name(args.output.stem + '_' + label + '.png'), args.native_capture_exe)
        capture['size'] = [capture['width'], capture['height']]
        reading.update(after=check.run(cube_query_code()), capture_sha256=capture['sha256'])
        evidence['native_projection']['rows'][label] = reading
        write_json(args.output, evidence)
        return capture
    installed = saved = environment_saved = options_saved = False
    signal_cache = []
    try:
        with Client(timeout=30) as client:
            check = SignCheck(client, args.output, args.timeout, args.native_resolution)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                saved = True
                evidence['environment'] = run_environment(client, SETUP_ENVIRONMENT)
                environment_saved = True
                evidence['capture_options'] = check.run(CAPTURE_OPTIONS)
                options_saved = True
                evidence['weather_settle_seconds'] = 10.
                time.sleep(evidence['weather_settle_seconds'])
                evidence['fixture'] = check.run(LOAD_CUBE % args.fixture_lift_y)
                state = check.wait('calibration cube projection',
                                   lambda value: value['active'] and value['ready'] and not value['preparing'] and
                                   value['actors'] == 1 and bool(value['mesh']),
                                   lambda: check.run(PROJECTION_STATUS))
                if check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close calibration workspace', lambda nav: not nav['open'] and not nav['transition'],
                               check.navigation)
                tilted_y = -3. if args.skyward_tilted else 3.
                for label, offset in (('front', (0., 0., 6.)), ('right', (6., 0., 0.)),
                                      ('tilted', (0., tilted_y, 6.))):
                    pose = check.run(POSE % (offset,))
                    camera = check.wait('cube camera ' + label, lambda value: camera_matches(value, pose),
                                        lambda: check.run(CAMERA))
                    time.sleep(.4)
                    shown = capture_frame(check, label + '_shown')
                    try:
                        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
                        time.sleep(.25)
                        hidden = capture_frame(check, label + '_hidden')
                    finally:
                        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
                    after = check.run(CAMERA)
                    final = check.run(PROJECTION_STATUS)
                    assert camera_matches(after, pose), (after, pose)
                    assert state['mesh'][:3] == final['mesh'][:3], (state, final)
                    actual = stone_signal(shown['path'], hidden['path'])
                    size = actual.size
                    bounds = actual.getbbox()
                    assert bounds and bounds[0] > size[0] / 4. and bounds[2] < size[0] * 3. / 4., bounds
                    assert bounds[1] > size[1] / 4. and bounds[3] < size[1] * 3. / 4., bounds
                    native_fov = camera['fov']
                    horizontal = math.degrees(2. * math.atan(math.tan(math.radians(native_fov) / 2.) * size[1] / size[0]))
                    candidates = {}
                    for convention, fov in (('vertical', native_fov), ('horizontal', horizontal)):
                        predicted = projected_mask(pose, size, fov)
                        expected = predicted.getbbox()
                        candidates[convention] = {'vertical_fov': fov, 'bounds': expected,
                                                  'max_boundary_error_pixels': max(abs(bounds[i] - expected[i]) for i in range(4))}
                    chosen = min(candidates, key=lambda key: candidates[key]['max_boundary_error_pixels'])
                    path = args.output.with_name(args.output.stem + '_' + label + '_signal.png')
                    actual.save(path)
                    outline_path = path.with_name(path.stem + '_outline_comparison.png')
                    row = {'view': label, 'pose': pose, 'camera': camera,
                           'candidates': candidates, 'convention': chosen,
                           'passed': False,
                           'signal': str(path.resolve()), 'shown': shown, 'hidden': hidden}
                    row['outline_comparison'] = str(outline_path.resolve())
                    evidence['views'].append(row)
                    signal_cache.append(((label, shown['sha256'], hidden['sha256']), actual))
                    write_json(args.output, evidence)
                evidence['completed'] = True
                direct = all(row['candidates'][row['convention']]['max_boundary_error_pixels'] <= 4
                             for row in evidence['views']) and len({row['convention'] for row in evidence['views']}) == 1
                evidence['fov_convention'] = evidence['views'][0]['convention'] if direct else 'calibrated_vertical'
                evidence['reported_fov'] = evidence['views'][0]['camera']['fov']
                evidence['screen_aspect'] = evidence['views'][0]['camera']['screen'][0] / evidence['views'][0]['camera']['screen'][1]
                evidence['reported_fov_is_effective'] = direct
                evidence['runtime_minecraft_version'] = check.run('_result=json.dumps(api.GetMinecraftVersion())')
                analyze_calibration(evidence, signal_cache)
            finally:
                cleanup_errors = []
                for label, action in (
                        ('environment', lambda: run_environment(client, RESTORE_ENVIRONMENT) if environment_saved else True),
                        ('capture_options', lambda: check.run(RESTORE_OPTIONS) if options_saved else True),
                        ('projection', lambda: check.run('b.stop_projection()\n_result=True') if saved else True),
                        ('camera', lambda: check.run(camera_restore_code(False)) if saved else True),
                        ('visual', lambda: check.run('saved=sys._blueprint_visual_saved\n'
                             's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                             's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                             'del sys._blueprint_visual_saved\n_result=True') if saved else True),
                        ('editor', lambda: check.run(RESTORE) if installed else True)):
                    try:
                        evidence[label + '_restored'] = action()
                    except Exception as error:
                        cleanup_errors.append(label + ': ' + str(error))
                evidence['cleanup_errors'] = cleanup_errors
                evidence['restored'] = installed and not cleanup_errors
                evidence['passed'] = evidence['passed'] and evidence['restored']
    except Exception as error:
        evidence['error'] = '%s: %s' % (type(error).__name__, error)
        raise
    finally:
        write_json(args.output, evidence)
    if args.native_api:
        from water_native_projection import validate_calibration
        evidence['native_projection']['validation'] = validate_calibration(evidence,
            evidence['native_projection']['session_binding'], evidence['native_projection']['source_contract_sha256'])
        write_json(args.output, evidence)
    print(json.dumps(evidence), flush=True)
    return 0 if evidence['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
