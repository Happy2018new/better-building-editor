"""Reproduce the valid final-source world pool UV failures without a game."""
import argparse
import hashlib
import json
from pathlib import Path
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
    for name, row in manifest['files'].items():
        path = ROOT / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    launch = json.loads((ROOT / 'launch-inputs.json').read_bytes())
    with zipfile.ZipFile(ROOT / 'launch-inputs.zip') as archive:
        assert set(archive.namelist()) == set(launch['source_sha256'])
        for name, expected in launch['source_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    source = json.loads((ROOT / 'world.json').read_bytes())
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert not source['cleanup_errors'] and len(source['captures']) == 12
    assert source['source_file_sha256_before'] == source['source_file_sha256_after'] == launch['source_sha256']
    calibration = json.loads((ROOT / 'calibration.json').read_bytes())
    assert all(calibration[key] is True for key in ('completed', 'restored', 'passed'))
    assert not calibration['cleanup_errors'] and len(calibration['views']) == 3
    frames = list(source['captures'].values())
    frames += [frame for row in calibration['views'] for frame in (row['shown'], row['hidden'])]
    for frame in frames:
        path = ROOT / 'captures' / Path(frame['path']).name
        assert sha(path) == frame['sha256']
        receipt = json.loads(path.with_suffix('.capture.json').read_bytes())
        assert receipt['sha256'] == frame['sha256']
        assert receipt['guarded_no_activation'] is True and receipt['reliable'] is True
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert receipt['game_pid'] == source['session_binding']['game_pid']
    assert max(row['handles'] for row in source['measurements']) < 250000
    if args.pixels:
        with tempfile.TemporaryDirectory(prefix='water-r19-world-replay-') as folder:
            temporary = Path(folder)
            with zipfile.ZipFile(ROOT / 'launch-inputs.zip') as archive:
                for name in archive.namelist():
                    if name.startswith(('tools/', 'behavior_pack/')) and name.endswith('.py'):
                        archive.extract(name, temporary)
            sys.path.insert(0, str(temporary / 'tools'))
            from analyze_product_water import analyze
            from analyze_water_acceptance_r16 import replay
            for frame in source['captures'].values():
                frame['path'] = str(ROOT / 'captures' / Path(frame['path']).name)
            path = temporary / 'world-rebased.json'
            path.write_text(json.dumps(source), encoding='ascii')
            base, result = analyze(path), replay(path)
            archived = json.loads((ROOT / 'world-acceptance.json').read_bytes())
            assert base['evidence_valid'] and result['evidence_valid']
            assert all(row['passed'] for row in base['geometry'].values())
            assert len(result['side_uv']) == 4
            for name, measured in result['side_uv'].items():
                assert measured == archived['side_uv'][name]
                assert measured['passed'] is False
                assert all(measured[key]['passed'] is False for key in
                           ('negative_mirrored', 'negative_constant', 'negative_wrong_phase'))
            assert len(result['visibility']) == 2 and all(row['passed'] for row in result['visibility'].values())
            assert len(result['lifecycle']) == 4 and all(result['lifecycle'].values())
            for name in ('LiquidProjection.advance', 'WorldLiquidRenderer.advance'):
                assert result['budgets'][name]['passed']
            assert result['passed'] is False
    print(json.dumps({'verified': True, 'world_captures': 12, 'calibration_captures': 6,
                      'uv_failures_preserved': 4, 'pixels_replayed': args.pixels,
                      'production_qualified': False}))


if __name__ == '__main__':
    main()
