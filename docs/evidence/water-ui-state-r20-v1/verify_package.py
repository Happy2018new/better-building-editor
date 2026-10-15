"""Verify frozen UI-water state evidence without a game or desktop input."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def captures(value):
    if isinstance(value, dict):
        if value.get('path', '').endswith('.png') and 'sha256' in value:
            yield value
        else:
            for row in value.values():
                for frame in captures(row):
                    yield frame
    elif isinstance(value, list):
        for row in value:
            for frame in captures(row):
                yield frame


def source_digest(sources):
    return hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    manifest = read('manifest.json')
    assert manifest['production_qualified'] is False
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == expected['bytes']
        assert sha(path) == expected['sha256'], name
    actual_files = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*')
                    if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual_files == set(manifest['files'])
    launch = read('launch-inputs.json')
    sources = launch['source_sha256']
    assert len(sources) == 3093 and source_digest(sources) == launch['source_contract_sha256']
    assert read('launch-plan.json')['launch_config_sha256'] == sha(ROOT / 'launch-mcdev.json')
    baseline = json.loads((ROOT / '../water-native-side-r20-v1/launch-inputs.json').read_bytes())
    resource_plan = read('resource-plan.json')
    delta_names = set(resource_plan['resource_delta'])
    assert len(delta_names) == 23 and all(name.startswith('resource_pack/') for name in delta_names)
    assert all(sources[name] == value for name, value in baseline['source_sha256'].items() if name not in delta_names)
    assert all(row['shared_entries_equal'] and not row['removed'] and len(row['added']) == 12
               for row in resource_plan['shared_entries'].values())
    archives = []
    try:
        for row in manifest['source_archives_in_precedence_order']:
            path = (ROOT / row['path']).resolve(strict=True)
            assert sha(path) == row['sha256']
            archives.append(zipfile.ZipFile(path))
        contents = {}
        for archive in archives:
            for name in archive.namelist():
                if name in sources:
                    contents[name] = archive
        assert set(contents) == set(sources)
        for name, expected in sources.items():
            assert hashlib.sha256(contents[name].read(name)).hexdigest() == expected, name
        for name, container in (('resource_pack/materials/entity.material', 'materials'),
                                ('resource_pack/models/netease_models.json', None)):
            old_archive = next(archive for archive in reversed(archives[:-1]) if name in archive.namelist())
            old = json.loads(old_archive.read(name))
            new = json.loads(contents[name].read(name))
            old, new = (old[container], new[container]) if container else (old, new)
            assert all(old[key] == new[key] for key in old) and len(set(new) - set(old)) == 12
        reports = {name: read(row['path']) for name, row in manifest['reports'].items()}
        host_binding = {'root-positive': 'cross-session.py', 'v6-cold': 'cross-session.py',
            'v6-primed': 'cross-session.py', 'v6-primed16': 'cross-session.py',
            'v7-splash-invalid': 'cross-session.py', 'v7-ready': 'cross-session.py',
            'v6-matched-pose': 'matched-pose.py', 'v6-entity': 'entity-control.py',
            'v7-parameters': 'native-parameters.py'}
        for name, report in reports.items():
            if name in host_binding:
                assert report['host_sha256'] == sha(ROOT / 'hosts' / host_binding[name]), name
            if name not in ('root-positive', 'v6-portal16'):
                assert report['source_contract_sha256'] == launch['source_contract_sha256'], name
            if isinstance(report.get('source_sha256'), dict) and not name.startswith('v7-editor-') and name != 'v6-portal16':
                if name != 'root-positive':
                    assert report['source_sha256'] == sources, name
                else:
                    assert source_digest(report['source_sha256']) == report['source_contract_sha256']
                    assert all(report['source_sha256'].get(path) == expected for path, expected in sources.items()
                               if path.startswith(('behavior_pack/', 'resource_pack/')))
        reference_requests = reports['root-positive']['rows']['wet']['ready']['liquid_control_requests']
        for name in ('v6-cold', 'v6-primed', 'v6-primed16', 'v7-ready'):
            assert reports[name]['rows']['wet']['ready']['liquid_control_requests'] == reference_requests, name
        capture_count = 0
        for name, report in reports.items():
            assert all(report[key] is True for key in ('completed', 'restored', 'source_unchanged')), name
            assert not report['cleanup_errors'], name
            frames = list(captures(report['captures']))
            assert len(frames) == manifest['reports'][name]['capture_count']
            identities = set()
            for frame in frames:
                path = ROOT / 'captures' / name / Path(frame['path']).name
                receipt = json.loads(path.with_suffix('.capture.json').read_bytes())
                assert sha(path) == receipt['sha256'] == frame['sha256']
                assert receipt['reliable'] and receipt['background_safe']
                if receipt['schema'] >= 3:
                    assert receipt['agent_activation_allowed'] is False
                    assert receipt['activation_fallback'] is False and receipt['guarded_no_activation']
                else:
                    assert receipt['background_only']
                    assert all(receipt['foreground_' + phase]['pid'] != receipt['game_pid']
                               for phase in ('before', 'after'))
                    assert receipt['foreground_unchanged'] == (receipt['foreground_before'] == receipt['foreground_after'])
                assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']
                identities.add((receipt['session_file'], receipt['game_pid'], receipt['game_identity']))
                capture_count += 1
            assert len(identities) == 1, name
            if 'session_binding' in report:
                binding = report['session_binding']
                assert identities == {(binding['session_file'], binding['game_pid'], binding['game_identity'])}
        assert manifest['invalid_target_scene_reports'] == ['v7-splash-invalid']
        assert manifest['v2_core_capture_bytes_included'] is False
        if args.pixels:
            with tempfile.TemporaryDirectory(prefix='water-ui-r20-replay-') as folder:
                temporary = Path(folder)
                for name in sources:
                    relative = PurePosixPath(name)
                    assert not relative.is_absolute() and '..' not in relative.parts and ':' not in name
                    if name.endswith('.py') and name.startswith(('tools/', 'behavior_pack/', '.agents/')):
                        destination = temporary / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        destination.write_bytes(contents[name].read(name))
                sys.path.insert(0, str(temporary / 'tools'))
                from analyze_water_acceptance_r16 import budget_checks, replay
                from analyze_product_water import analyze
                from PIL import Image
                import numpy as np

                def array(name, label):
                    frame = reports[name]['captures'][label]
                    path = ROOT / 'captures' / name / Path(frame['path']).name
                    result = np.asarray(Image.open(path).convert('RGB')).astype(float)
                    assert result.shape == (1105, 1994, 3)
                    return result[354:848, 470:1540]

                def difference(a, b):
                    return int(np.count_nonzero(np.max(abs(a-b), axis=2) >= 8))

                reference = array('root-positive', 'wet')
                assert difference(reference, array('root-positive', 'dry')) == 96436
                assert np.array_equal(reference, array('root-positive', 'restored'))
                for name in ('v6-cold', 'v6-primed', 'v6-primed16'):
                    assert difference(array(name, 'wet'), array(name, 'dry')) == 0
                    assert np.array_equal(array(name, 'wet'), array(name, 'restored'))
                pose = 'v6-matched-pose'
                assert np.array_equal(array(pose, 'baseline'), array(pose, 'restored'))
                assert difference(array(pose, 'baseline'), array(pose, 'skeleton_cow_pose')) == 0
                assert difference(array(pose, 'entity_exact_pose'), array(pose, 'baseline')) == 96436
                assert np.array_equal(array(pose, 'entity_exact_pose'), reference)
                splash = 'v7-splash-invalid'
                assert np.array_equal(array(splash, 'wet'), array(splash, 'dry'))
                assert np.array_equal(array(splash, 'wet'), array(splash, 'restored'))
                assert not np.array_equal(array(splash, 'wet'), reference)
                assert np.array_equal(array('v7-ready', 'wet'), reference)
                assert difference(array('v7-ready', 'wet'), array('v7-ready', 'dry')) == 96436
                for label in reports['v7-parameters']['captures']:
                    assert np.array_equal(array('v7-parameters', label), reference)
                report = reports['v7-editor-pool']
                assert report['source_file_sha256_before'] == report['source_file_sha256_after'] == sources
                for frame in report['captures'].values():
                    frame['path'] = str(ROOT / 'captures/v7-editor-pool' / Path(frame['path']).name)
                rebased = temporary / 'editor-pool.json'
                rebased.write_text(json.dumps(report), encoding='ascii')
                measured = replay(rebased)
                archived = read('v7-editor-pool-analysis.json')
                for key in ('evidence_valid', 'side_uv', 'visibility', 'budgets', 'passed'):
                    assert measured[key] == archived[key], key
                assert measured['evidence_valid'] and not measured['passed']
                assert all(row['passed'] for row in measured['side_uv'].values())
                assert all(row['passed'] and row['independently_visible_water_pixels'] == 96000
                           for row in measured['visibility'].values())
                assert abs(measured['budgets']['LiquidPreview.advance']['maximum_ms'] - 230.00001907348633) < 1e-8
                core = read('v2-core-timing-and-state.json')
                core_budgets = budget_checks(core)
                assert core_budgets == read('v2-core-analysis.json')['budgets']
                assert not core_budgets['LiquidProjection.advance']['passed']
                assert abs(core_budgets['LiquidProjection.advance']['maximum_ms'] - 168.99991035461426) < 1e-8
                for name in ('timing-granular-v2.json', 'timing-thread-unsupported-v3.json'):
                    row = read(name)
                    assert all(row[key] is True for key in ('completed', 'restored', 'source_unchanged'))
                    assert not row['cleanup_errors'] and not row['timing']['outliers']
                    assert 'not CPU time' in row['timing']['clock_semantics']
                assert read('timing-thread-unsupported-v3.json')['timing']['thread_cpu_supported'] is False
                first_world = read('timing-world-v1.json')
                assert all(first_world[key] is True for key in ('completed', 'restored', 'source_unchanged'))
                assert not first_world['cleanup_errors'] and len(first_world['rows']) == 24
                assert first_world['timing']['stats']['LiquidProjection.advance']['maximum_wall_ms'] > 32.
                world = read('timing-world-detail-v2.json')
                assert all(world[key] is True for key in ('completed', 'restored', 'source_unchanged'))
                assert not world['cleanup_errors'] and not world['visual_acceptance_claimed']
                assert world['screenshots'] == world['window_actions'] == []
                assert world['source_contract_sha256'] == launch['source_contract_sha256']
                assert world['host_sha256'] == sha(ROOT / 'hosts/world-granular-v2.py')
                assert world['granular_parent_host_sha256'] == sha(ROOT / 'hosts/granular-current-v3.py')
                assert len(world['rows']) == 24 and max(row['metrics']['handles'] for row in world['rows']) < 220000
                assert world['timing']['thread_cpu_supported'] is False
                assert world['timing']['thread_cpu_failure'] == "ImportError('No module named ctypes',)"
                public = reports['v7-editor-public19']
                assert len(public['cases']) == 19 and public['routes'] == ['editor']
                assert len(public['captures']) == 92 and len(public['rows']) == 54
                assert public['source_file_sha256_before'] == public['source_file_sha256_after'] == sources
                assert public['launch_source_sha256'] == sources
                assert max(row['handles'] for row in public['measurements']) < 220000
                for frame in public['captures'].values():
                    frame['path'] = str(ROOT / 'captures/v7-editor-public19' / Path(frame['path']).name)
                public_path = temporary / 'editor-public19.json'
                public_path.write_text(json.dumps(public), encoding='ascii')
                public_replay = replay(public_path)
                public_analysis = read('v7-editor-public19-analysis.json')
                for key in ('evidence_valid', 'side_uv', 'visibility', 'budgets', 'passed'):
                    assert public_replay[key] == public_analysis[key], ('public19', key)
                public_product = analyze(public_path)
                archived_product = read('v7-editor-public19-product-analysis.json')
                for key in ('evidence_valid', 'geometry', 'transparency', 'alpha_controls', 'observed_product_gates'):
                    assert public_product[key] == archived_product[key], ('public19 product', key)
                assert public_replay['evidence_valid'] and public_product['evidence_valid']
                assert not public_replay['passed'] and not public['production_default_requested']
                assert public['alpha_controls_requested'] is False and not public['flow_bursts']
                assert len(public_replay['visibility']) == 18 and all(row['passed'] for row in public_replay['visibility'].values())
                assert len(public_product['geometry']) == 15 and all(row['passed'] for row in public_product['geometry'].values())
                assert public_product['observed_product_gates'] == {'geometry': True, 'transparency': True, 'animation': False}
                assert abs(public_replay['budgets']['LiquidControls.update']['maximum_ms'] - 434.999942779541) < 1e-8
                assert not public_replay['budgets']['LiquidControls.update']['passed']
                assert public['owner_timing_details']['outliers'] == [{'started': 1792077074.389,
                    'pending_renderers': 0, 'fixture': 'water_style_flow_east_wet', 'requested_groups': 4,
                    'elapsed_ms': 434.999942779541, 'registry_entries': 4, 'method': 'LiquidControls.update'}]
                alpha = reports['v7-editor-alpha4']
                assert len(alpha['cases']) == 4 and alpha['routes'] == ['editor']
                assert len(alpha['captures']) == 56 and len(alpha['rows']) == 24
                assert alpha['source_file_sha256_before'] == alpha['source_file_sha256_after'] == sources
                assert alpha['launch_source_sha256'] == sources and alpha['alpha_controls_requested']
                assert not alpha['production_default_requested'] and not alpha['flow_bursts']
                for frame in alpha['captures'].values():
                    frame['path'] = str(ROOT / 'captures/v7-editor-alpha4' / Path(frame['path']).name)
                alpha_path = temporary / 'editor-alpha4.json'
                alpha_path.write_text(json.dumps(alpha), encoding='ascii')
                alpha_replay = replay(alpha_path)
                archived_alpha = read('v7-editor-alpha4-analysis.json')
                for key in ('evidence_valid', 'side_uv', 'visibility', 'budgets', 'passed'):
                    assert alpha_replay[key] == archived_alpha[key], ('alpha4', key)
                alpha_product = analyze(alpha_path)
                archived_alpha_product = read('v7-editor-alpha4-product-analysis.json')
                for key in ('evidence_valid', 'geometry', 'transparency', 'alpha_controls', 'observed_product_gates'):
                    assert alpha_product[key] == archived_alpha_product[key], ('alpha4 product', key)
                assert alpha_replay['evidence_valid'] and alpha_product['evidence_valid']
                assert len(alpha_product['alpha_controls']) == 4
                assert all(row['passed'] and row['complete'] and row['geometry_unchanged']
                           for row in alpha_product['alpha_controls'].values())
                assert abs(alpha_replay['budgets']['LiquidControls.update']['maximum_ms'] - 370.00012397766113) < 1e-8
                assert not alpha_replay['budgets']['LiquidControls.update']['passed'] and not alpha_replay['passed']
                assert alpha['owner_timing_details']['outliers'] == [{'started': 1792077519.254,
                    'pending_renderers': 0, 'fixture': 'water_style_wet_oak_slab_wet', 'requested_groups': 0,
                    'elapsed_ms': 370.00012397766113, 'registry_entries': 0, 'method': 'LiquidControls.update'}]
        print(json.dumps({'verified': True, 'pixels_replayed': args.pixels,
            'captures': capture_count, 'source_files': len(sources),
            'invalid_loading_captures': 3, 'failed_maxima_ms_preserved': [169, 230, 370, 435],
            'production_qualified': False}))
    finally:
        for archive in archives:
            archive.close()


if __name__ == '__main__':
    main()
