"""Replay falling corners with native projection and unchanged depth/geometry gates."""
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_product_water as analysis
from camera_projection import project_points
from water_native_projection import validate_calibration, validate_readings

BASE = ROOT / '.runtime/water-r20-state-v7'
SOURCE_PATH = BASE / 'falling-native-skyward.json'
NATIVE_PATH = BASE / 'falling-native-skyward-points.json'
FIT_PATH = BASE / 'native-calibration-fit.json'
OUTPUT = BASE / 'falling-native-depth-v1'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not OUTPUT.exists()
    source = json.loads(SOURCE_PATH.read_bytes())
    native = json.loads(NATIVE_PATH.read_bytes())
    fitted = json.loads(FIT_PATH.read_bytes())
    calibration_path = Path(source['camera_calibration']['path'])
    assert sha(calibration_path) == source['camera_calibration']['sha256']
    calibration = json.loads(calibration_path.read_bytes())
    validation = validate_calibration(calibration, source['session_binding'],
                                      source['source_contract_sha256'])
    assert all(source.get(key) is True for key in ('completed', 'restored', 'source_unchanged'))
    assert all(native.get(key) is True for key in ('completed', 'restored', 'source_unchanged'))
    assert not source['cleanup_errors']
    assert native['source_report_sha256'] == sha(SOURCE_PATH)
    assert native['session_binding'] == source['session_binding']
    assert native['source_contract_sha256'] == source['source_contract_sha256']
    assert fitted['source_sha256'] == sha(calibration_path)
    assert fitted['source_contract_sha256'] == source['source_contract_sha256']
    failures = analysis.capture_failures(source['captures'], source['session_binding'])
    assert not failures, failures
    row = source['rows']['full_falling_wet']
    size = source['captures']['full_falling_wet']['width'], source['captures']['full_falling_wet']['height']
    assert list(size) == fitted['physical_size']
    expected_points = {}
    for index, (shape, polygon) in enumerate(analysis.water_polygons(row['ready']['shapes'])):
        expected_points['water_' + str(index)] = [list(point) for point in polygon]
    for index, box in enumerate(analysis.fixture_solid_boxes(row)):
        x0, y0, z0, x1, y1, z1 = box
        corners = ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
                   (x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1))
        for face, indices in enumerate(analysis.FACE_INDICES):
            expected_points['solid_%d_%d' % (index, face)] = [list(corners[item]) for item in indices]
    assert native['point_sets'] == expected_points
    mapped_rows = {}
    projection_residuals = {}
    for label, capture in source['captures'].items():
        assert sha(capture['path']) == capture['sha256']
        record = native['rows'][Path(capture['path']).stem]
        assert record['capture_path'] == capture['path']
        assert record['capture_sha256'] == capture['sha256']
        assert record['capture_size'] == list(size)
        assert record['state_before']['ready']['origin'] == row['ready']['origin']
        mapped = validate_readings(record, capture['camera_before'], row['ready']['origin'],
                                   expected_points, size)
        mapped_rows[label] = mapped
        errors = []
        for key, points in expected_points.items():
            world = np.asarray(points) + np.asarray(row['ready']['origin'])
            values = project_points(world, row['camera']['position'], row['camera']['target'], size, 90.)
            basis = np.asarray([(point['screenX'] - size[0] / 2.,
                                 point['screenY'] - size[1] / 2.) for point in values])
            fitted_xy = basis * fitted['shared']['scale_relative_fov90']
            fitted_xy += np.asarray(fitted['shared']['center_physical_pixels'])
            errors.append(float(abs(fitted_xy - mapped[key]).max()))
        projection_residuals[label] = max(errors)
    eye = np.asarray(row['camera']['position']) - np.asarray(row['ready']['origin'])
    direction = np.asarray(row['camera']['target']) - np.asarray(row['camera']['position'])
    direction /= np.linalg.norm(direction)
    water = np.full((size[1], size[0]), np.inf)
    solid = np.full_like(water, np.inf)
    for key, points in expected_points.items():
        depths = [float(np.dot(np.asarray(point) - eye, direction)) for point in points]
        analysis.raster_depth(water if key.startswith('water_') else solid,
            mapped_rows['full_falling_wet'][key], depths, True)
    native_union = np.isfinite(water)
    native_depth = native_union & (water <= solid + 1e-5)
    original = analysis.expected_mask(row, source, size)
    analytic_depth = analysis.unoccluded_neighbor_mask(row, source, size)
    selected = np.asarray(Image.fromarray((original * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17))) > 0
    selected[size[1] // 2 - 6:size[1] // 2 + 6, size[0] // 2 - 6:size[0] // 2 + 6] = False
    wet = analysis.rgb(source['captures']['full_falling_wet']['path'])
    dry = analysis.rgb(source['captures']['full_falling_dry']['path'])
    actual = analysis.difference_mask(wet, dry, selected, analysis.LIMITS['rgb_delta'])
    masks = {'original': original & selected, 'analytic_support_depth': analytic_depth & selected,
             'native_union': native_union & selected, 'native_support_depth': native_depth & selected}
    negative = actual.copy()
    negative[300:450, 890:1100] = False
    report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
        'source_report_sha256': sha(SOURCE_PATH), 'native_report_sha256': sha(NATIVE_PATH),
        'fit_report_sha256': sha(FIT_PATH), 'host_sha256': sha(__file__),
        'analyzer_sha256': sha(analysis.__file__), 'session_binding': source['session_binding'],
        'source_contract_sha256': source['source_contract_sha256'],
        'stone_calibration_validation': validation, 'limits': analysis.LIMITS,
        'native_vs_stone_fit_maximum_pixels': projection_residuals,
        'geometry': {key: analysis.product_geometry(actual, mask) for key, mask in masks.items()},
        'negative_controls': {'blank': analysis.product_geometry(np.zeros_like(actual), masks['native_support_depth']),
            'removed_fixed_rectangle': analysis.product_geometry(negative, masks['native_support_depth'])},
        'solid_boxes': list(analysis.fixture_solid_boxes(row)),
        'native_support_occluded_pixels': int(np.count_nonzero(native_union & ~native_depth)),
        'fixed_removed_rectangle': [890, 300, 1100, 450]}
    assert all(not result['passed'] for result in report['negative_controls'].values())
    OUTPUT.mkdir()
    for name, mask in list(masks.items()) + [('actual', actual)]:
        Image.fromarray((mask * 255).astype(np.uint8)).save(OUTPUT / (name + '.png'))
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
