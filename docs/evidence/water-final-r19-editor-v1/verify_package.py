"""Verify final-source editor evidence; optional pixels use the frozen analyzers."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
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
        path = ROOT / name
        assert path.stat().st_size == expected['bytes'], name
        assert sha(path) == expected['sha256'], name
    launch = json.loads((ROOT / 'launch-inputs.json').read_bytes())
    with zipfile.ZipFile(ROOT / 'launch-inputs.zip') as archive:
        assert set(archive.namelist()) == set(launch['source_sha256'])
        for name, expected in launch['source_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected, name
    source = json.loads((ROOT / 'editor.json').read_bytes())
    assert source['source_contract_sha256'] == launch['source_contract_sha256']
    assert all(source[key] is True for key in ('completed', 'restored', 'source_unchanged'))
    assert not source['cleanup_errors'] and len(source['captures']) == 48
    assert source['source_file_sha256_before'] == source['source_file_sha256_after'] == launch['source_sha256']
    for frame in source['captures'].values():
        path = ROOT / 'captures' / Path(frame['path']).name
        assert sha(path) == frame['sha256']
        receipt = json.loads(path.with_suffix('.capture.json').read_bytes())
        assert receipt['sha256'] == frame['sha256']
        assert all(receipt[key] is True for key in ('ok', 'reliable', 'guarded_no_activation'))
        assert receipt['agent_activation_allowed'] is False
        assert receipt['activation_fallback'] is False
        assert receipt['game_pid'] == source['session_binding']['game_pid']
    readbacks = json.loads((ROOT / 'editor-native-readbacks.json').read_bytes())
    assert len(readbacks) == 48
    f32 = lambda value: struct.unpack('f', struct.pack('f', value))[0]
    banks = 0
    for state in readbacks.values():
        for group in state['groups']:
            for bank in group['banks']:
                if bank['cached_id'] is None:
                    continue
                banks += 1
                assert bank['actual_id'] == bank['cached_id']
                for index, values in bank['cached_uniforms'].items():
                    assert [f32(value) for value in values] == bank['actual_uniforms'][index]
    assert banks == 104
    if args.pixels:
        with tempfile.TemporaryDirectory(prefix='water-final-r19-replay-') as folder:
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
            replay_path = temporary / 'editor-rebased.json'
            replay_path.write_text(json.dumps(source), encoding='ascii')
            analysis, acceptance = analyze(replay_path), replay(replay_path)
            assert analysis['evidence_valid'] and acceptance['evidence_valid']
            assert all(row['passed'] for key in ('geometry', 'transparency', 'alpha_controls')
                       for row in analysis[key].values())
            assert len(analysis['geometry']) == 8 and len(analysis['alpha_controls']) == 1
            assert len(acceptance['visibility']) == 9 and len(acceptance['side_uv']) == 2
            assert all(row['passed'] for key in ('visibility', 'side_uv')
                       for row in acceptance[key].values())
            for method in ('LiquidControls.update', 'LiquidPreview.advance'):
                assert acceptance['budgets'][method]['passed']
            assert not acceptance['passed'] and not acceptance['lifecycle']
    print(json.dumps({'verified': True, 'captures': 48, 'native_banks': banks,
                      'frozen_source_files': len(launch['source_sha256']),
                      'pixels_replayed': args.pixels, 'production_qualified': False}))


if __name__ == '__main__':
    main()
