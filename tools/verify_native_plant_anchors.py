"""Measure native root offsets independently of complete foliage silhouettes."""
import argparse
import hashlib
import json
import math
import time
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from verify_debug_blueprints import BlueprintCheck, Client, INSTALL_PROBE, RESTORE, write_json
from verify_debug_visuals import SAVE_VISUAL, PROJECTION_STATUS, PROJECTION_SOURCE, camera_restore_code
from verify_missing_neighbor_visuals import camera_matches
from verify_shulker_orientations import server_run
from verify_snow_plant_visibility import (LOAD, NATIVE_SETUP, NATIVE_MUTATE, NATIVE_CLEANUP,
                                          capture_frame, compare_native, cross_assets, count)
from verify_snow_plant_visibility import convex_hull
from camera_projection import project_points
from _session import load_session


POSE = '''base=%r
offset=%r
target=(base[0]+(.5 if offset[0] else 1.),base[1]+.025,
        base[2]+(1. if offset[0] else .5))
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


def centroid(mask):
    pixels = count(mask)
    if pixels == 0:
        return None
    points = [(x, y) for y in range(mask.height) for x in range(mask.width)
              if mask.getpixel((x, y)) == 255]
    return [sum(point[axis] for point in points)/float(pixels) for axis in range(2)]


def replicated(check, base, name):
    def read():
        return check.run('''base=%r
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(base,base,False)
data=palette.SerializeBlockPalette() if palette is not None else {}
_result=json.dumps([value[0] for value in data.get('common',{})])
''' % (base,))
    check.wait('native plant anchor replication', lambda values: name in values, read)


def native_frame(check, base, plant, kind, label):
    check.run('b.stop_projection()\n_result=True')
    readback = server_run(check.client, NATIVE_MUTATE % (plant, kind, 5))
    name = 'minecraft:'+plant if kind == 'plant' else 'minecraft:snow_layer'
    replicated(check, base, name)
    time.sleep(.35)
    shown = check.capture(label+'_native_shown')
    server_run(check.client, NATIVE_MUTATE % (plant, 'blank', 0))
    replicated(check, base, 'minecraft:air')
    time.sleep(.2)
    hidden = check.capture(label+'_native_hidden')
    crop = (0, 0, *shown['size'])
    return capture_frame(shown['path'], crop, hidden['path'], segmented=True), {
        'shown': shown, 'hidden': hidden, 'readback': readback}


def projection_frame(check, base, plant, kind, label):
    source = check.run(LOAD % (plant, 5, kind))
    check.run('''base=%r
focus=(1,1,1)
s.origin=tuple(base[i]-focus[i] for i in range(3))
s.opacity=1.
s.projection_missing=False
s.projection_outline=False
b.project()
_result=True
''' % (base,))
    state = check.wait('root projection', lambda row: row['active'] and row['ready'] and
        not row['preparing'] and row['actors'] == 1 and bool(row['mesh']),
        lambda: check.run(PROJECTION_STATUS))
    current_source = check.run(PROJECTION_SOURCE)
    assert current_source['work_current'] and current_source['cache_current'] and current_source['origin_current']
    assert current_source['document_id'] == source['document_id']
    time.sleep(.35)
    shown = check.capture(label+'_projection_shown')
    try:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(True)\n_result=True')
        time.sleep(.2)
        hidden = check.capture(label+'_projection_hidden')
    finally:
        check.run('assert b.factory.CreateActorRender(b.entity).SetNotRenderAtAll(False)\n_result=True')
    after = check.run(PROJECTION_STATUS)
    assert state['mesh'][:3] == after['mesh'][:3]
    crop = (0, 0, *shown['size'])
    check.run('b.stop_projection()\n_result=True')
    return capture_frame(shown['path'], crop, hidden['path'], segmented=True), {
        'shown': shown, 'hidden': hidden, 'state': state, 'source': current_source}


def root_measurement(frame, focal, half_width=.75, center=None):
    width, height = frame['image'].size
    # The camera looks horizontally through Y=.025. A narrow strip stays
    # inside the bottom native texture row and above the support face.
    strip = Image.new('L', (width, height))
    cx, cy = (int(round(value)) for value in (center or (width/2., height/2.)))
    radius = int(math.ceil(focal*half_width/2.5))+4
    ImageDraw.Draw(strip).rectangle((cx-radius, cy-2, cx+radius, cy+2), fill=255)
    mask = ImageChops.multiply(frame['green'], strip)
    bounds, stripe = mask.getbbox(), strip.getbbox()
    clipped = bounds is not None and (bounds[0] <= stripe[0] or bounds[2] >= stripe[2])
    return mask, {'pixels': count(mask), 'centroid': centroid(mask), 'bounds': bounds,
                  'strip': stripe, 'horizontal_clipping': clipped,
                  'texture_rows': [15], 'root_height_blocks': [0., .05]}


def restrict_cell(frame, base, pose, fov):
    points = [tuple(base[i]+delta[i] for i in range(3))
              for delta in ((x,y,z) for x in (0.,1.) for y in (0.,1.) for z in (0.,1.))]
    projected = project_points(points, pose['position'], pose['target'], frame['image'].size, fov)
    mask = Image.new('L', frame['image'].size)
    ImageDraw.Draw(mask).polygon(convex_hull((row['screenX'],row['screenY']) for row in projected), fill=255)
    for key in ('object', 'green'):
        frame[key] = ImageChops.multiply(frame[key], mask)


def solve_offsets(rows):
    by_target = {}
    for row in rows:
        by_target.setdefault(tuple(row['target']), {})[row['view']] = row
    result = []
    for target, views in sorted(by_target.items()):
        if set(views) != {'front', 'right'} or not all(row['roots_valid'] for row in views.values()):
            continue
        front, right = views['front'], views['right']
        front_focal, right_focal = front['focal_pixels'], right['focal_pixels']
        front_width = front.get('screenshot_width', front_focal*2.)
        right_width = right.get('screenshot_width', right_focal*2.)
        front_x = front.get('projection_root', {}).get('centroid', [front_width/2.])[0]
        right_x = right.get('projection_root', {}).get('centroid', [right_width/2.])[0]
        a = -front['root_delta_pixels'][0]/front_focal
        b = right['root_delta_pixels'][0]/right_focal
        u, v = (front_width/2.-front_x)/front_focal+a, (right_x-right_width/2.)/right_focal+b
        x, z = 3.*(a-u*b)/(1.-u*v), 3.*(b-v*a)/(1.-u*v)
        result.append({'target': target, 'offset_blocks': [x, 0., z],
                       'root_vertical_error_pixels': max(abs(row['root_delta_pixels'][1]) for row in views.values()),
                       'method': 'Effective two-view root-centroid offset at distance3; full leaf masks unused',
                       'limitation': 'Native crossed-plane texture centroids need not equal the geometric pivot; not a general native jitter formula'})
    return result


def measure_roots(native, actual, row, output, half_width=.75):
    records = []
    for frame, side in ((native, 'native'), (actual, 'projection')):
        mask, record = root_measurement(frame, row['focal_pixels'], half_width, row['root_center'])
        mask_path = output.with_name(output.stem+'_'+row['view']+'_'+str(row['target'][0])+'_'+
                                    str(row['target'][2])+'_'+side+'_root.png')
        mask.save(mask_path)
        record['mask'] = str(mask_path.resolve())
        record['mask_sha256'] = hashlib.sha256(mask_path.read_bytes()).hexdigest()
        records.append(record)
    valid = all(record['pixels'] >= 12 and not record['horizontal_clipping'] for record in records)
    row['native_root'], row['projection_root'] = records
    row['roots_valid'] = valid
    row['root_delta_pixels'] = ([records[0]['centroid'][i]-records[1]['centroid'][i] for i in range(2)]
                                if valid else None)


def saved_frame(record):
    shown, hidden = record['shown'], record['hidden']
    for capture in (shown, hidden):
        digest = hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest()
        assert digest == capture['sha256'], 'Saved root capture changed: '+capture['path']
    return capture_frame(shown['path'], (0, 0, *shown['size']), hidden['path'], segmented=True)


def summarize(report):
    report['all_snow_anchors_passed'] = bool(report['rows']) and all(row['absolute_snow_comparison']['passed'] for row in report['rows'])
    report['raw_foliage_accepted'] = bool(report['rows']) and all(row['raw_foliage_comparison']['passed'] for row in report['rows'])
    report['coordinate_offsets'] = solve_offsets(report['rows'])
    keys = {(tuple(row['target']), row['view']) for row in report['rows']}
    report['valid'] = (len(report['rows']) == len(keys) == 6 and len(report['coordinate_offsets']) == 3 and
                       all(row['roots_valid'] for row in report['rows']) and report['all_snow_anchors_passed'])
    report['offset_scope'] = 'Diagnostic effective root centroids only; no model, snow, support or raw foliage mask was translated'


def replay_roots(source, output):
    report = json.loads(source.read_text(encoding='utf8'))
    assert report['completed'] and report['restored']
    report['replayed_from'] = str(source.resolve())
    report['root_measurement_revision'] = 'Wide five-pixel bottom stripe; clipped roots rejected'
    for row in report['rows']:
        row['previous_root_measurement'] = {key: row[key] for key in
                                           ('native_root', 'projection_root', 'root_delta_pixels', 'roots_valid')}
        frames = []
        for key in ('native', 'projection'):
            frame = saved_frame(row[key])
            restrict_cell(frame, row['target'], row['pose'], report['calibration']['vertical_fov'])
            frames.append(frame)
        measure_roots(frames[0], frames[1], row, output)
    summarize(report)
    write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--camera-calibration', type=Path)
    parser.add_argument('--replay', type=Path)
    parser.add_argument('--timeout', type=float, default=60.)
    parser.add_argument('--plant', choices=('fern', 'short_grass'), default='fern')
    args = parser.parse_args()
    if args.replay:
        report = replay_roots(args.replay, args.output)
        print(json.dumps({'completed': report['completed'], 'restored': report['restored'],
                          'valid': report['valid'], 'coordinate_offsets': report['coordinate_offsets']}))
        return 0 if report['valid'] else 1
    assert args.camera_calibration is not None, 'A native camera calibration is required for live measurement'
    session = load_session(live=True)
    calibration = json.loads(args.camera_calibration.read_text(encoding='utf8'))
    assert calibration['completed'] and calibration['passed']
    assert Path(calibration['session_file']).resolve() == Path(session['session_file']).resolve()
    model, texture, assets = cross_assets(session, args.plant)
    report = {'schema': 1, 'completed': False, 'restored': False, 'rows': [],
              'session_file': session['session_file'], 'calibration': calibration, 'assets': assets,
              'plant': args.plant,
              'scope': 'Three coordinates, two orthogonal cameras; low root strip only, raw snow anchor and raw full foliage preserved',
              'limits': {'minimum_root_pixels': 12, 'absolute_snow_shape': .75,
                         'full_foliage_shape': .75, 'native_edge_tolerance_pixels': 3}}
    installed = saved = native_created = False
    try:
        with Client(timeout=30) as client:
            check = BlueprintCheck(client, args.output, args.timeout)
            try:
                check.run(INSTALL_PROBE)
                installed = True
                check.run(SAVE_VISUAL)
                saved = True
                if check.navigation()['open']:
                    check.run('navigator.pop()\n_result=True')
                    check.wait('close root probe workspace', lambda row: not row['open'] and not row['transition'], check.navigation)
                foot = check.run('_result=json.dumps(b.player_origin())')
                targets = [tuple(foot[i]+offset[i] for i in range(3))
                           for offset in ((6,8,6), (7,8,6), (6,8,7))]
                for index, base in enumerate(targets):
                    fixture = server_run(client, NATIVE_SETUP % (base,))
                    native_created = True
                    for view, offset in (('front', (0.,0.,3.)), ('right', (3.,0.,0.))):
                        pose = check.run(POSE % (base, offset))
                        camera = check.wait('root camera', lambda value: camera_matches(value, pose), lambda: check.run(CAMERA))
                        assert abs(camera['fov']-calibration['reported_fov']) < .01
                        label = 'cell%d_%s' % (index, view)
                        native, native_record = native_frame(check, base, args.plant, 'plant', label+'_plant')
                        actual, actual_record = projection_frame(check, base, args.plant, 'plant', label+'_plant')
                        for frame in (native, actual):
                            restrict_cell(frame, base, pose, calibration['vertical_fov'])
                        assert camera_matches(check.run(CAMERA), pose)
                        focal = native['image'].height/(2.*math.tan(math.radians(calibration['vertical_fov'])/2.))
                        root_point = (base[0]+.5, base[1]+.025, base[2]+.5)
                        root_screen = project_points((root_point,), pose['position'], pose['target'],
                                                     native['image'].size, calibration['vertical_fov'])[0]
                        root_center = (root_screen['screenX'], root_screen['screenY'])
                        snow_native, snow_native_record = native_frame(check, base, args.plant, 'snow', label+'_snow')
                        snow_actual, snow_actual_record = projection_frame(check, base, args.plant, 'snow', label+'_snow')
                        for frame in (snow_native, snow_actual):
                            restrict_cell(frame, base, pose, calibration['vertical_fov'])
                        snow_match = compare_native(snow_native, snow_actual, foliage=False)
                        native_bounds, actual_bounds = snow_native['object'].getbbox(), snow_actual['object'].getbbox()
                        native_center, actual_center = centroid(snow_native['object']), centroid(snow_actual['object'])
                        snow_match['boundary_error_pixels'] = max(abs(native_bounds[i]-actual_bounds[i]) for i in range(4))
                        snow_match['centroid_delta_pixels'] = [native_center[i]-actual_center[i] for i in range(2)]
                        snow_match['passed'] = (snow_match['passed'] and snow_match['boundary_error_pixels'] <= 3 and
                                               max(abs(value) for value in snow_match['centroid_delta_pixels']) <= 2)
                        full_match = compare_native(native, actual)
                        row = {'target': base, 'view': view, 'pose': pose, 'fixture': fixture,
                               'camera': camera, 'focal_pixels': focal, 'native': native_record,
                               'screenshot_width': native['image'].width, 'root_center': root_center,
                               'projection': actual_record, 'raw_foliage_comparison': full_match,
                               'absolute_snow_comparison': snow_match,
                               'native_snow': snow_native_record, 'projection_snow': snow_actual_record}
                        measure_roots(native, actual, row, args.output)
                        report['rows'].append(row)
                        write_json(args.output, report)
                        print(json.dumps({'target': base, 'view': view, 'native_root': row['native_root'],
                                          'projection_root': row['projection_root'], 'delta': row['root_delta_pixels'],
                                          'snow_anchor_passed': snow_match['passed'], 'raw_shape_passed': full_match['passed']}), flush=True)
                    cleanup = server_run(client, NATIVE_CLEANUP)
                    native_created = False
                    assert all(row['clean'] for row in cleanup)
                report['completed'] = True
                summarize(report)
            finally:
                if native_created:
                    report['native_cleanup'] = server_run(client, NATIVE_CLEANUP)
                if saved:
                    check.run('b.stop_projection()\n_result=True')
                    check.run(camera_restore_code(False))
                    check.run('saved=sys._blueprint_visual_saved\n'
                              's.origin=saved["origin"]\ns.opacity=saved["opacity"]\n'
                              's.projection_missing=saved["missing"]\ns.projection_outline=saved["outline"]\n'
                              'del sys._blueprint_visual_saved\n_result=True')
                if installed:
                    check.run(RESTORE)
                report['restored'] = True
    finally:
        write_json(args.output, report)
    return 0 if report.get('valid') else 1


if __name__ == '__main__':
    raise SystemExit(main())
