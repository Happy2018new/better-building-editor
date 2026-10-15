"""Replay owner-bound native water side oracles without starting a game."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'manifest.json').read_bytes())
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == expected['bytes'] and sha(path) == expected['sha256'], name
    launch = json.loads((ROOT / 'launch-inputs.json').read_bytes())
    sources = launch['source_sha256']
    base = (ROOT / manifest['base_source_archive']['path']).resolve(strict=True)
    assert sha(base) == manifest['base_source_archive']['sha256']
    calibration = json.loads((ROOT / 'calibration.json').read_bytes())
    reports = {name: json.loads((ROOT / (name + '.json')).read_bytes()) for name in ('pool', 'editor-pool')}
    frames = [capture for report in reports.values() for capture in report['captures'].values()]
    frames += [row[state] for row in calibration['views'] for state in ('shown', 'hidden')]
    for frame in frames:
        path = ROOT / 'captures' / Path(frame['path']).name
        assert sha(path) == frame['sha256']
        receipt = json.loads(path.with_suffix('.capture.json').read_bytes())
        assert receipt['sha256'] == frame['sha256'] and receipt['reliable'] is True
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert receipt['guarded_no_activation'] is True
        assert all(receipt[key] == reports['pool']['session_binding'][key]
                   for key in ('session_file', 'game_pid', 'game_identity'))
    for report in reports.values():
        assert all(report[key] is True for key in ('completed', 'restored', 'source_unchanged'))
        assert not report['cleanup_errors']
        assert report['source_file_sha256_before'] == report['source_file_sha256_after'] == sources
        assert max(row['handles'] for row in report['measurements']) < 250000
    with zipfile.ZipFile(base) as original, zipfile.ZipFile(ROOT / 'launch-input-delta.zip') as delta:
        assert not set(delta.namelist()) - set(sources)
        for name, expected in sources.items():
            archive = delta if name in delta.namelist() else original
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
        if args.pixels:
            with tempfile.TemporaryDirectory(prefix='water-native-r20-replay-') as folder:
                temporary = Path(folder)
                for name in sources:
                    relative = PurePosixPath(name)
                    assert not relative.is_absolute() and '..' not in relative.parts and ':' not in name
                    if name.endswith('.py') and name.startswith(('tools/', 'behavior_pack/', '.agents/')):
                        destination = temporary / name
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        archive = delta if name in delta.namelist() else original
                        destination.write_bytes(archive.read(name))
                sys.path.insert(0, str(temporary / 'tools'))
                from analyze_product_water import analyze
                from analyze_water_acceptance_r16 import budget_checks, replay
                from water_native_projection import validate_calibration
                for row in calibration['views']:
                    for state in ('shown', 'hidden'):
                        row[state]['path'] = str(ROOT / 'captures' / Path(row[state]['path']).name)
                calibration_path = temporary / 'calibration-rebased.json'
                calibration_path.write_text(json.dumps(calibration), encoding='ascii')
                validate_calibration(calibration, reports['pool']['session_binding'], launch['source_contract_sha256'])
                samples = {}
                for name, report in reports.items():
                    for frame in report['captures'].values():
                        frame['path'] = str(ROOT / 'captures' / Path(frame['path']).name)
                    if 'camera_calibration' in report:
                        report['camera_calibration'].update(path=str(calibration_path), sha256=sha(calibration_path))
                    path = temporary / (name + '-rebased.json')
                    path.write_text(json.dumps(report), encoding='ascii')
                    measured = replay(path)
                    archived = json.loads((ROOT / (name + '-analysis.json')).read_bytes())
                    assert measured['evidence_valid'] and analyze(path)['evidence_valid']
                    for key in ('side_uv', 'visibility', 'lifecycle', 'budgets'):
                        assert measured[key] == archived[key], (name, key)
                    assert all(measured['lifecycle'].values())
                    if name == 'pool':
                        assert all(row['passed'] for row in measured['side_uv'].values())
                        assert all(row['passed'] for row in measured['visibility'].values())
                        assert len(measured['side_uv']) == 4
                        assert all(not row['passed'] for row in measured['analytic_side_uv_diagnostic'].values())
                    else:
                        assert all(not row['passed'] for row in measured['side_uv'].values())
                        assert all(not row['passed'] and row['independently_visible_water_pixels'] == 0
                                   for row in measured['visibility'].values())
                    for method, values in report['owner_timing_ms'].items():
                        samples.setdefault(method, []).extend(values)
                budgets = budget_checks({'owner_timing_ms': samples})
                assert len(budgets) == 4 and all(row['passed'] for row in budgets.values())
    print(json.dumps({'verified': True, 'pixels_replayed': args.pixels,
        'valid_world_captures': 12, 'rejected_editor_captures': 6, 'calibration_captures': 6, 'native_sides_passed': 4,
        'analytic_side_failures_preserved': 4, 'production_qualified': False}))


if __name__ == '__main__':
    main()
