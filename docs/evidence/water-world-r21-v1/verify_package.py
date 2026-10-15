"""Verify world water evidence, including its original failures and native diagnostic."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def captures(value):
    if isinstance(value, dict):
        if value.get('path', '').endswith('.png') and 'sha256' in value:
            yield value
        else:
            for row in value.values():
                yield from captures(row)
    elif isinstance(value, list):
        for row in value:
            yield from captures(row)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    manifest, references = read('manifest.json'), read('references.json')
    assert manifest['production_qualified'] is False and manifest['performance_without_intervention'] is False
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == expected['bytes']
        assert sha(path) == expected['sha256'], name
    actual_files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*')
                    if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual_files == set(manifest['files'])
    for key in ('prior_manifest', 'launch_inputs'):
        assert sha(ROOT / references[key]['path']) == references[key]['sha256']
    launch = read(references['launch_inputs']['path'])
    sources = launch['source_sha256']
    contract = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
    assert len(sources) == 3093 and contract == launch['source_contract_sha256']
    reports = {name: read(row['path']) for name, row in manifest['reports'].items()}
    world, falling, calibration = (reports[key] for key in ('world-full-public19', 'falling-native', 'calibration'))
    count = 0
    for name, report in reports.items():
        assert report['completed'] is True and report['restored'] is True and not report['cleanup_errors']
        frames = list(captures(report['views'] if name == 'calibration' else report['captures']))
        assert len(frames) == manifest['reports'][name]['capture_count']
        for frame in frames:
            path = ROOT / 'captures' / name / Path(frame['path']).name
            receipt = json.loads(path.with_suffix('.capture.json').read_bytes())
            assert sha(path) == frame['sha256'] == receipt['sha256']
            assert receipt['schema'] == 3 and receipt['reliable'] and receipt['background_safe']
            assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
            assert receipt['guarded_no_activation'] is True
            assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']
            assert receipt['game_pid'] == world['session_binding']['game_pid']
            assert receipt['game_identity'] == world['session_binding']['game_identity']
            assert receipt['session_file'] == world['session_binding']['session_file']
            count += 1
    assert count == 102 and len(world['cases']) == 19 and len(world['captures']) == 92
    assert len(falling['captures']) == 4 and world['routes'] == falling['routes'] == ['full']
    for report in (world, falling):
        assert report['source_unchanged'] is True
        assert report['launch_source_sha256'] == report['source_file_sha256_before'] == report['source_file_sha256_after'] == sources
        assert report['source_contract_sha256'] == contract
        assert not report['production_default_requested'] and not report['flow_bursts']
    intervention = read('world-full-public19-intervention.json')
    assert intervention['performance_without_intervention'] is False and intervention['game_paused'] is False
    assert intervention['window_actions'] == []
    assert abs(intervention['host_paused_seconds'] - (intervention['resumed_at'] - intervention['paused_at'])) < 1e-9
    assert abs(intervention['host_paused_seconds'] - 49.02993726730347) < 1e-9
    archived_product = read('world-full-public19-product-analysis.json')
    assert archived_product['evidence_valid'] is True and not archived_product['geometry']['full_falling_wet']['passed']
    assert archived_product['geometry']['full_falling_wet']['maximum_boundary_pixels'] == 88
    assert read('falling-depth/report.json')['support_depth']['maximum_boundary_pixels'] == 7
    native = read('falling-native-points.json')
    assert all(native.get(key) is True for key in ('completed', 'restored', 'source_unchanged'))
    assert native['source_report_sha256'] == sha(ROOT / 'falling-native.json')
    assert native['source_contract_sha256'] == contract and native['session_binding'] == falling['session_binding']
    assert native['host_sha256'] == sha(ROOT / 'hosts/falling-native.py')
    fit = read('native-calibration-fit.json')
    assert fit['source_sha256'] == sha(ROOT / 'calibration.json')
    assert fit['host_sha256'] == sha(ROOT / 'hosts/native-calibration-fit.py')
    assert fit['fit_input'] == '24 native stone cube corners; no water pixels or polygons'
    assert fit['production_qualified'] is False
    native_analysis = read('falling-native-depth/report.json')
    assert native_analysis['native_report_sha256'] == sha(ROOT / 'falling-native-points.json')
    assert native_analysis['fit_report_sha256'] == sha(ROOT / 'native-calibration-fit.json')
    assert native_analysis['host_sha256'] == sha(ROOT / 'hosts/falling-native-replay.py')
    assert native_analysis['production_qualified'] is False
    assert native_analysis['source_report_sha256'] == sha(ROOT / 'falling-native.json')
    assert native_analysis['geometry']['native_support_depth']['passed'] is True
    assert native_analysis['geometry']['native_support_depth']['maximum_boundary_pixels'] == 2
    assert native_analysis['geometry']['native_union']['passed'] is False
    assert max(native_analysis['native_vs_stone_fit_maximum_pixels'].values()) < .000149
    archives = []
    try:
        for entry in references['source_archives_in_precedence_order']:
            path = (ROOT / entry['path']).resolve(strict=True)
            assert sha(path) == entry['sha256']
            archives.append(zipfile.ZipFile(path))
        contents = {}
        for archive in archives:
            for name in archive.namelist():
                if name in sources:
                    contents[name] = archive
        assert set(contents) == set(sources)
        for name, expected in sources.items():
            assert hashlib.sha256(contents[name].read(name)).hexdigest() == expected, name
        if args.pixels:
            with tempfile.TemporaryDirectory(prefix='water-world-r21-replay-') as folder:
                temporary = Path(folder)
                for name in sources:
                    relative = PurePosixPath(name)
                    assert not relative.is_absolute() and '..' not in relative.parts and ':' not in name
                    if name.endswith('.py') and name.startswith(('tools/', 'behavior_pack/', '.agents/')):
                        path = temporary / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(contents[name].read(name))
                sys.path.insert(0, str(temporary / 'tools'))
                import numpy as np
                from PIL import Image, ImageFilter
                import analyze_product_water as analysis
                import analyze_liquid_workspace as workspace_analysis
                import analyze_water_acceptance_r16 as acceptance_analysis
                from analyze_water_acceptance_r16 import replay
                from camera_projection import project_points
                from water_native_projection import validate_calibration, validate_readings

                original_rgb = workspace_analysis.rgb
                decoded_paths = {}

                # Disk-backed copies retain exact int16 pixels without keeping all 92 PNGs resident.
                def decoded_rgb(path):
                    key = str(Path(path).resolve(strict=True))
                    if key not in decoded_paths:
                        destination = temporary / ('decoded-%d.npy' % len(decoded_paths))
                        np.save(destination, original_rgb(path), allow_pickle=False)
                        decoded_paths[key] = destination
                    return np.load(decoded_paths[key], mmap_mode='r', allow_pickle=False)

                analysis.rgb = workspace_analysis.rgb = acceptance_analysis.rgb = decoded_rgb

                for frame in captures(calibration['views']):
                    frame['path'] = str(ROOT / 'captures/calibration' / Path(frame['path']).name)
                validated = validate_calibration(calibration, world['session_binding'], contract)
                assert validated == fit['stone_calibration_validation']
                matrix, expected = [], []
                for view in calibration['views']:
                    reading = calibration['native_projection']['rows'][view['view'] + '_shown']['before']
                    size = view['shown']['width'], view['shown']['height']
                    projected = project_points(reading['world_points']['cube'],
                        view['camera']['position'], view['pose']['target'], size, 90.)
                    for point, actual in zip(projected, reading['projection']['cube']):
                        matrix.extend(((point['screenX'] - size[0] / 2., 1., 0.),
                                       (point['screenY'] - size[1] / 2., 0., 1.)))
                        expected.extend((actual['screenX'], actual['screenY']))
                solution = np.linalg.lstsq(matrix, expected, rcond=None)[0]
                assert np.allclose(solution, [fit['shared']['scale_relative_fov90']] +
                    fit['shared']['center_physical_pixels'], rtol=0., atol=1e-9)
                rebased_calibration = temporary / 'calibration.json'
                rebased_calibration.write_text(json.dumps(calibration), encoding='ascii')
                for name, report in (('world-full-public19', world), ('falling-native', falling)):
                    for frame in report['captures'].values():
                        frame['path'] = str(ROOT / 'captures' / name / Path(frame['path']).name)
                    report['camera_calibration'].update(path=str(rebased_calibration), sha256=sha(rebased_calibration))
                world_path = temporary / 'world.json'
                world_path.write_text(json.dumps(world), encoding='ascii')
                measured = replay(world_path)
                archived = read('world-full-public19-analysis.json')
                for key in ('evidence_valid', 'side_uv', 'analytic_side_uv_diagnostic', 'visibility', 'budgets', 'lifecycle', 'passed'):
                    assert measured[key] == archived[key], key
                product = analysis.analyze(world_path)
                for key in ('evidence_valid', 'geometry', 'transparency', 'alpha_controls', 'observed_product_gates'):
                    assert product[key] == archived_product[key], key
                assert len(measured['visibility']) == 18 and all(row['passed'] for row in measured['visibility'].values())
                assert len(measured['lifecycle']) == 54 and all(value is True for value in measured['lifecycle'].values())
                row = falling['rows']['full_falling_wet']
                size = falling['captures']['full_falling_wet']['width'], falling['captures']['full_falling_wet']['height']
                mapped = None
                for label, capture in falling['captures'].items():
                    record = native['rows'][Path(capture['path']).stem]
                    assert record['capture_sha256'] == capture['sha256'] and record['capture_size'] == list(size)
                    points = validate_readings(record, capture['camera_before'], row['ready']['origin'], native['point_sets'], size)
                    errors = []
                    for key, declared in native['point_sets'].items():
                        projected = project_points(np.asarray(declared) + np.asarray(row['ready']['origin']),
                            row['camera']['position'], row['camera']['target'], size, 90.)
                        basis = np.asarray([(point['screenX'] - size[0] / 2.,
                                             point['screenY'] - size[1] / 2.) for point in projected])
                        fitted_xy = basis * solution[0] + solution[1:]
                        errors.append(float(abs(fitted_xy - points[key]).max()))
                    assert abs(max(errors) - native_analysis['native_vs_stone_fit_maximum_pixels'][label]) < 1e-9
                    if label == 'full_falling_wet':
                        mapped = points
                expected_points = {}
                for index, (shape, polygon) in enumerate(analysis.water_polygons(row['ready']['shapes'])):
                    expected_points['water_' + str(index)] = [list(point) for point in polygon]
                for index, box in enumerate(analysis.fixture_solid_boxes(row)):
                    x0,y0,z0,x1,y1,z1 = box
                    corners = ((x0,y0,z0),(x1,y0,z0),(x1,y0,z1),(x0,y0,z1),
                               (x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1))
                    for face, indices in enumerate(analysis.FACE_INDICES):
                        expected_points['solid_%d_%d' % (index, face)] = [list(corners[item]) for item in indices]
                assert native['point_sets'] == expected_points
                eye = np.asarray(row['camera']['position']) - np.asarray(row['ready']['origin'])
                direction = np.asarray(row['camera']['target']) - np.asarray(row['camera']['position'])
                direction /= np.linalg.norm(direction)
                water = np.full((size[1], size[0]), np.inf)
                solid = np.full_like(water, np.inf)
                for key, points in expected_points.items():
                    depths = [float(np.dot(np.asarray(point) - eye, direction)) for point in points]
                    analysis.raster_depth(water if key.startswith('water_') else solid, mapped[key], depths, True)
                original = analysis.expected_mask(row, falling, size)
                selected = np.asarray(Image.fromarray((original * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17))) > 0
                selected[size[1] // 2 - 6:size[1] // 2 + 6, size[0] // 2 - 6:size[0] // 2 + 6] = False
                actual = analysis.difference_mask(analysis.rgb(falling['captures']['full_falling_wet']['path']),
                    analysis.rgb(falling['captures']['full_falling_dry']['path']), selected, analysis.LIMITS['rgb_delta'])
                masks = {'original': original & selected,
                    'analytic_support_depth': analysis.unoccluded_neighbor_mask(row, falling, size) & selected,
                    'native_union': np.isfinite(water) & selected,
                    'native_support_depth': np.isfinite(water) & (water <= solid + 1e-5) & selected}
                assert {name: analysis.product_geometry(actual, mask) for name, mask in masks.items()} == native_analysis['geometry']
                negative = actual.copy()
                negative[300:450, 890:1100] = False
                negatives = {'blank': analysis.product_geometry(np.zeros_like(actual), masks['native_support_depth']),
                    'removed_fixed_rectangle': analysis.product_geometry(negative, masks['native_support_depth'])}
                assert negatives == native_analysis['negative_controls']
                assert all(not result['passed'] for result in negatives.values())
        print(json.dumps({'verified': True, 'pixels_replayed': args.pixels, 'captures': count,
            'source_files': len(sources), 'original_falling_boundary_pixels': 88,
            'native_diagnostic': native_analysis['geometry']['native_support_depth'],
            'performance_without_intervention': False, 'production_qualified': False}))
    finally:
        for archive in archives:
            archive.close()


if __name__ == '__main__':
    main()
