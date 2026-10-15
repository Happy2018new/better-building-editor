"""Verify and optionally replay the preserved missing-world water controls."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    manifest, references = read(ROOT / 'manifest.json'), read(ROOT / 'references.json')
    assert manifest['production_qualified'] is False and manifest['diagnostic_only'] is True
    assert manifest['capture_host_suspensions'] == manifest['game_suspensions'] == manifest['window_actions'] == []
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == expected['bytes']
        assert sha(path) == expected['sha256'], name
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files'])
    for name, reference in references.items():
        assert sha(ROOT / reference['path']) == reference['sha256'], name
    launch = read(ROOT / references['launch_inputs']['path'])
    world_root = (ROOT / references['world_manifest']['path']).resolve(strict=True).parent
    world_manifest = read(world_root / 'manifest.json')
    calibration_path = ROOT / references['calibration']['path']
    assert sha(calibration_path) == world_manifest['files']['calibration.json']['sha256']
    sources = launch['source_sha256']
    contract = hashlib.sha256(json.dumps(sources, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
    assert len(sources) == 3093 and contract == launch['source_contract_sha256']
    source_path = ROOT / 'world-missing-public19.json'
    source = read(source_path)
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert source['cleanup_errors'] == [] and source['routes'] == manifest['routes'] == ['missing']
    assert source['cases'] == manifest['cases'] and len(source['cases']) == 19
    assert len(source['captures']) == manifest['captures'] == 92 and len(source['rows']) == 54
    assert source['launch_source_sha256'] == source['source_file_sha256_before'] == source['source_file_sha256_after'] == sources
    assert source['source_contract_sha256'] == contract and source['camera_calibration']['sha256'] == sha(calibration_path)
    assert source['frozen'] is True and not source['production_default_requested'] and not source['flow_bursts']
    execution = read(ROOT / 'world-missing-public19-execution.json')
    assert execution['returncode'] == 0 and execution['stderr'] == ''
    guard = execution['argv'].index('--max-handles')
    assert execution['argv'][guard + 1] == '210000'
    stopped = read(ROOT / 'stop-execution.json')
    assert stopped['returncode'] == 0 and '--force' not in stopped['argv']
    stopped_state = json.loads(stopped['stdout'])
    assert stopped_state['state'] == 'stopped' and stopped_state['ready'] is False
    first_stop = read(ROOT / 'stop-attempt1-execution.json')
    assert first_stop['returncode'] == 1 and 'Game has not closed' in first_stop['stderr']
    assert '--force' not in first_stop['argv']
    exit_record = read(ROOT / 'exit-observation.json')
    assert exit_record['force_used'] is False and exit_record['clean_game_exit_established'] is False
    assert exit_record['owned_process_count'] == 0 and exit_record['game_pid'] == source['session_binding']['game_pid']
    assert exit_record['game_identity'] == source['session_binding']['game_identity']
    wer_path = ROOT / exit_record['wer']['path']
    assert sha(wer_path) == exit_record['wer']['sha256']
    wer = dict(line.split('=', 1) for line in wer_path.read_text(encoding='utf-16').splitlines() if '=' in line)
    for key, field in (('ReportIdentifier', 'report_identifier'), ('EventTime', 'event_filetime'),
                       ('EventType', 'event_type'), ('AppSessionGuid', 'app_session_guid'),
                       ('Sig[3].Value', 'fault_module'), ('Sig[7].Value', 'exception_code')):
        assert wer[key] == exit_record['wer'][field], key
    assert int(wer['AppSessionGuid'].split('-')[0], 16) == source['session_binding']['game_pid']
    user_foreground = []
    for label, frame in source['captures'].items():
        path = ROOT / 'captures' / Path(frame['path']).name
        receipt = read(path.with_suffix('.capture.json'))
        assert sha(path) == frame['sha256'] == receipt['sha256']
        assert receipt['schema'] == 3 and receipt['reliable']
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert receipt['guarded_no_activation'] is True
        assert all(receipt[key]['window_noactivate'] is True for key in ('guard_before', 'guard_after'))
        if not receipt['background_safe']:
            assert receipt['foreground_policy'] == 'allow_user_foreground' and receipt['user_foreground_allowed'] is True
            assert receipt['foreground_unchanged'] is True
            assert receipt['foreground_before'] == receipt['foreground_after']
            assert receipt['foreground_before']['pid'] == source['session_binding']['game_pid']
            user_foreground.append(label)
        assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']
        for field in ('game_pid', 'game_identity', 'session_file'):
            assert receipt[field] == source['session_binding'][field]
    assert user_foreground == ['missing_wet_oak_slab_wet_section_restored']
    results = {name: read(ROOT / ('world-missing-public19-' + name + '.json'))
               for name in ('analysis', 'product-analysis', 'native-product-analysis')}
    for result in results.values():
        assert result['source_sha256'] == sha(source_path) and result['evidence_valid'] is True
        assert result.get('capture_failures', []) == [] and result['production_qualified'] is False
        assert result['host_sha256'] == sha(ROOT / 'hosts/offline-replay.py')
    for name in ('product-analysis', 'native-product-analysis'):
        assert results[name]['analyzer_sha256'] == sha(ROOT / 'analyzer/analyze_product_water.py')
    native = results['native-product-analysis']['geometry_oracle']
    assert native['helper_sha256'] == sha(ROOT / 'analyzer/water_native_projection.py')
    assert native['calibration_sha256'] == sha(calibration_path)
    assert native['model']['session_binding'] == source['session_binding']
    assert native['model']['source_contract_sha256'] == contract
    calibration = read(calibration_path)
    for view in calibration['views']:
        for state in ('shown', 'hidden'):
            frame = view[state]
            frame_path = world_root / 'captures/calibration' / Path(frame['path']).name
            assert sha(frame_path) == frame['sha256']
    archives = []
    try:
        world_references = read(ROOT / references['world_references']['path'])
        for reference in world_references['source_archives_in_precedence_order']:
            path = (world_root / reference['path']).resolve(strict=True)
            assert sha(path) == reference['sha256']
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
            with tempfile.TemporaryDirectory(prefix='water-missing-world-r21-replay-') as directory:
                temporary = Path(directory)
                for name in sources:
                    relative = PurePosixPath(name)
                    assert not relative.is_absolute() and '..' not in relative.parts and ':' not in name
                    if name.endswith('.py') and name.startswith(('tools/', 'behavior_pack/', '.agents/')):
                        path = temporary / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(contents[name].read(name))
                for path in (ROOT / 'analyzer').glob('*.py'):
                    shutil.copy2(path, temporary / 'tools' / path.name)
                for view in calibration['views']:
                    for state in ('shown', 'hidden'):
                        view[state]['path'] = str(world_root / 'captures/calibration' / Path(view[state]['path']).name)
                rebased_calibration = temporary / 'calibration.json'
                rebased_calibration.write_text(json.dumps(calibration), encoding='ascii')
                for frame in source['captures'].values():
                    frame['path'] = str(ROOT / 'captures' / Path(frame['path']).name)
                source['camera_calibration'].update(path=str(rebased_calibration), sha256=sha(rebased_calibration))
                rebased_source = temporary / 'source.json'
                rebased_source.write_text(json.dumps(source), encoding='ascii')
                sys.path.insert(0, str(temporary / 'tools'))
                import numpy as np
                import analyze_liquid_workspace as workspace
                import analyze_product_water as product
                import analyze_water_acceptance_r16 as acceptance
                original_rgb = product.rgb
                cache = {}

                def decoded_rgb(path):
                    key = str(Path(path).resolve(strict=True))
                    if key not in cache:
                        target = temporary / ('decoded-%d.npy' % len(cache))
                        np.save(target, original_rgb(path), allow_pickle=False)
                        cache[key] = target
                    return np.load(cache[key], mmap_mode='r', allow_pickle=False)

                product.rgb = workspace.rgb = acceptance.rgb = decoded_rgb
                replayed = {
                    'analysis': acceptance.replay(rebased_source),
                    'product-analysis': product.analyze(rebased_source),
                    'native-product-analysis': product.analyze(rebased_source, native_world_geometry=True),
                }
                for name, measured in replayed.items():
                    keys = (('evidence_valid', 'side_uv', 'analytic_side_uv_diagnostic', 'visibility',
                             'budgets', 'lifecycle', 'maximum_observed_groups', 'model_budget_passed', 'passed')
                            if name == 'analysis' else
                            ('evidence_valid', 'capture_failures', 'limits', 'geometry', 'transparency',
                             'animation', 'alpha_controls', 'observed_product_gates'))
                    for key in keys:
                        assert measured[key] == results[name][key], (name, key)
                assert replayed['native-product-analysis']['geometry_oracle']['model'] == native['model']
    finally:
        for archive in archives:
            archive.close()
    acceptance = results['analysis']
    print(json.dumps({'verified': True, 'pixels_replayed': args.pixels, 'captures': len(source['captures']),
        'background_safe_captures': len(source['captures']) - len(user_foreground), 'user_foreground_captures': user_foreground,
        'source_files': len(sources), 'visibility_checks': len(acceptance['visibility']),
        'lifecycle_checks': len(acceptance['lifecycle']), 'native_side_uv_checks': len(acceptance['side_uv']),
        'analytic_geometry_passes': sum(row['passed'] for row in results['product-analysis']['geometry'].values()),
        'native_geometry_passes': sum(row['passed'] for row in results['native-product-analysis']['geometry'].values()),
        'production_qualified': False}))


if __name__ == '__main__':
    main()
