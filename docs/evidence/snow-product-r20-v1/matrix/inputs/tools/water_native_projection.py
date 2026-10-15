"""Bind water side samples to the native camera API in the captured session."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw
from scipy.ndimage import map_coordinates

from water_capture_contract import camera_matches

SCHEMA = 1
UNITS = 'physical_pixels'
MAXIMUM_POINT_DRIFT = .02
MINIMUM_STONE_IOU = .95


def require(condition, message):
    if not condition:
        raise ValueError(message)


def grids():
    result = {}
    for name, horizontal, height in (
            ('original', np.linspace(.12, .88, 18), np.linspace(.16, .72, 14)),
            ('texel_centers', np.arange(2, 14) / 15., 1. - np.arange(5, 13) / 15.)):
        u, h = np.meshgrid(horizontal, height)
        for face, positions in (('south', ((3, 3, 4), (4, 3, 4))),
                                ('east', ((4, 3, 3), (4, 3, 4)))):
            for position in positions:
                x, y, z = position
                points = [(x + 1. - a, y + b, z + 1.) if face == 'south'
                          else (x + 1., y + b, z + a) for a, b in zip(u.ravel(), h.ravel())]
                key = '%s_%s_%s' % (name, face, '_'.join(map(str, position)))
                result[key] = {'grid': name, 'face': face, 'cell': position,
                               'dimensions': u.shape, 'points': points}
    return result


def query_code(point_sets):
    return '''cam=b.factory.CreateCamera(b.level)
relative_points=json.loads(%r)
world_points=dict((key,[tuple(point[i]+s.origin[i] for i in range(3)) for point in points])
 for key,points in relative_points.items())
projected=dict((key,[cam.WorldToScreenPoint(*point) for point in points])
 for key,points in world_points.items())
_result=json.dumps({'world_points':world_points,'projection':projected,'origin':s.origin,
 'camera_position':cam.GetPosition(),'camera_rotation':cam.GetCameraRotation(),
 'screen':b.factory.CreateGame(b.level).GetScreenSize(),'fov':cam.GetFov()})
''' % json.dumps(point_sets, sort_keys=True)


def side_query_code():
    return query_code({key: row['points'] for key, row in grids().items()})


def cube_query_code():
    return query_code({'cube': [(x, y, z) for x in (1., 2.)
                               for y in (1., 2.) for z in (1., 2.)]})


def native_camera(reading):
    return {'position': reading['camera_position'], 'rotation': reading['camera_rotation'],
            'screen': reading['screen'], 'fov': reading['fov']}


def coordinates(reading, key, size):
    points = reading['projection'][key]
    require(points and all(point.get('isInScreen') is True for point in points),
            'Native water samples leave the viewport')
    mapped = np.asarray([(point['screenX'], point['screenY']) for point in points], dtype=float)
    require(np.isfinite(mapped).all() and np.all(mapped >= .5) and
            np.all(mapped[:, 0] <= size[0] - .5) and np.all(mapped[:, 1] <= size[1] - .5),
            'Native water samples require finite physical pixel coordinates')
    return mapped


def validate_readings(record, camera, origin, point_sets, size):
    before, after = record['before'], record['after']
    require(set(before['projection']) == set(after['projection']) == set(point_sets),
            'Native point grid differs from its declared plan')
    result = {}
    for reading in (before, after):
        require(camera_matches(native_camera(reading), camera), 'Native point camera differs from its capture')
        require(list(reading['origin']) == list(origin), 'Native point origin differs from its capture')
        for key, points in point_sets.items():
            expected = np.asarray(points) + np.asarray(origin)
            actual = np.asarray(reading['world_points'][key])
            require(actual.shape == expected.shape and np.allclose(actual, expected, atol=1e-9, rtol=0.),
                    'Native point world grid differs from its declared plan')
    for key, points in point_sets.items():
        first, second = (coordinates(reading, key, size) for reading in (before, after))
        require(first.shape == (len(points), 2) and second.shape == first.shape and
                float(abs(first - second).max()) <= MAXIMUM_POINT_DRIFT,
                'Native point coordinates changed during their readback')
        result[key] = first
    return result


def validate_calibration(calibration, binding, source_contract):
    from verify_camera_projection import stone_signal
    from verify_missing_neighbor_visuals import hull
    native = calibration.get('native_projection', {})
    require(native.get('schema') == SCHEMA and native.get('coordinate_units') == UNITS,
            'Same-session native camera calibration is missing')
    require(native.get('session_binding') == binding and
            native.get('source_contract_sha256') == source_contract,
            'Native camera calibration belongs to another session or source')
    require(all(calibration.get(key) is True for key in ('passed', 'completed', 'restored'))
            and not calibration.get('cleanup_errors') and len(calibration['views']) == 3,
            'Native camera calibration did not complete and restore')
    origin = calibration['fixture']['projection_origin']
    points = {'cube': [(x, y, z) for x in (1., 2.) for y in (1., 2.) for z in (1., 2.)]}
    result = {}
    for row in calibration['views']:
        observed = stone_signal(row['shown']['path'], row['hidden']['path'])
        for state in ('shown', 'hidden'):
            capture = row[state]
            require(hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'],
                    'Native calibration PNG changed')
            require(capture['session_file'] == binding['session_file'] and
                    capture['game_pid'] == binding['game_pid'] and
                    capture['game_identity'] == binding['game_identity'],
                    'Native calibration PNG belongs to another session')
            record = native['rows'][row['view'] + '_' + state]
            require(record['capture_sha256'] == capture['sha256'], 'Native calibration point frame differs')
            mapped = validate_readings(record, row['camera'], origin, points, observed.size)['cube']
            if state == 'shown':
                predicted = Image.new('L', observed.size)
                ImageDraw.Draw(predicted).polygon(hull(map(tuple, mapped)), fill=255)
                intersection = ImageChops.multiply(predicted, observed).histogram()[255]
                union = predicted.histogram()[255] + observed.histogram()[255] - intersection
                iou = intersection / max(1, union)
                require(iou >= MINIMUM_STONE_IOU, 'Native camera API hull disagrees with visible stone pixels')
                result[row['view']] = {'native_api_mask_iou': iou}
    return result


def side_coordinates(source, label, images):
    from analyze_product_water import expected_mask
    image = images[label]
    native = source.get('native_side_projection', {})
    require(native.get('schema') == SCHEMA and native.get('coordinate_units') == UNITS,
            'Native side projection contract is missing')
    calibration_ref = source['camera_calibration']
    path = Path(calibration_ref['path'])
    require(hashlib.sha256(path.read_bytes()).hexdigest() == calibration_ref['sha256'],
            'Native side camera calibration changed')
    calibration = json.loads(path.read_bytes())
    validate_calibration(calibration, source['session_binding'], source['source_contract_sha256'])
    record = native['rows'][label]
    capture = source['captures'][label]
    row = source['extra_rows'][label]
    require(row.get('requested_alpha') == 1. and source.get('frozen') is True,
            'Native side sampling requires independently opaque frozen water')
    require(record['session_binding'] == source['session_binding'] and
            record['source_contract_sha256'] == source['source_contract_sha256'],
            'Native side points belong to another session or source')
    require(record['capture_sha256'] == capture['sha256'] and
            list(record['capture_size']) == [image.shape[1], image.shape[0]],
            'Native side points belong to another PNG or physical viewport')
    require(hashlib.sha256(Path(capture['path']).read_bytes()).hexdigest() == capture['sha256'],
            'Native side PNG changed')
    dry_label = label.replace('_wet_side_opaque', '_dry')
    require(record['dry_capture_sha256'] == source['captures'][dry_label]['sha256'],
            'Native side points have a different dry frame')
    require(camera_matches(source['rows'][dry_label]['camera_after'], row['camera_after']),
            'Native side dry and opaque cameras differ')
    wet_label = label[:-len('_side_opaque')]
    wet, dry = images[wet_label], images[dry_label]
    mask = expected_mask(source['rows'][wet_label], source, (image.shape[1], image.shape[0]))
    eligible = mask & (np.max(abs(wet.astype(float) - dry), axis=2) >= 8.)
    require(int(eligible.sum()) >= 24, 'Native side water is absent or stale relative to its dry frame')
    hidden = images[wet_label + '_section']
    restored = images[wet_label + '_section_restored']
    require(int(np.count_nonzero(eligible & (np.max(abs(wet.astype(float) - hidden), axis=2) >= 8.))) >= 24,
            'Native side section did not visibly hide water')
    require(float(np.sqrt(np.mean((wet[eligible].astype(float) - restored[eligible]) ** 2))) <= 2.,
            'Native side water did not restore its pixels')
    default_restored = images[wet_label + '_side_default_restored']
    require(int(np.count_nonzero(eligible & (np.max(abs(image.astype(float) - wet), axis=2) >= 8.))) >= 24
            and float(np.sqrt(np.mean((wet[eligible].astype(float) - default_restored[eligible]) ** 2))) <= 2.,
            'Native side opaque control is stale or its default alpha did not restore')
    return validate_readings(record, row['camera_after'], row['ready']['origin'],
                             {key: grid['points'] for key, grid in grids().items()},
                             (image.shape[1], image.shape[0]))


def sample(image, mapped, dimensions):
    values = np.stack([map_coordinates(image[:, :, channel].astype(float),
        (mapped[:, 1] - .5, mapped[:, 0] - .5), order=1, mode='nearest')
        for channel in range(3)], axis=1)
    return values.reshape(tuple(dimensions) + (3,))
