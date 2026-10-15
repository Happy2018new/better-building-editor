"""Replay the optional native world oracle against the original frozen pixels."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import subprocess
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
    assert manifest['production_qualified'] is False
    for name, expected in manifest['files'].items():
        path = (ROOT / name).resolve(strict=True)
        assert path.is_relative_to(ROOT) and path.stat().st_size == expected['bytes']
        assert sha(path) == expected['sha256'], name
    actual = {path.relative_to(ROOT).as_posix() for path in ROOT.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files'])
    for name, reference in references.items():
        assert sha(ROOT / reference['path']) == reference['sha256'], name
    world_root = (ROOT / references['manifest.json']['path']).resolve(strict=True).parent
    checked = subprocess.run([sys.executable, '-X', 'utf8', str(world_root / 'verify_package.py')],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, encoding='utf-8')
    assert json.loads(checked.stdout)['verified'] is True
    result = read(ROOT / 'analysis.json')
    source = read(world_root / 'world-full-public19.json')
    calibration = read(world_root / 'calibration.json')
    original = read(world_root / 'world-full-public19-product-analysis.json')
    fit = read(world_root / 'native-calibration-fit.json')
    oracle = result['geometry_oracle']
    assert result['source_sha256'] == sha(world_root / 'world-full-public19.json')
    assert result['analyzer_sha256'] == sha(ROOT / 'analyzer/analyze_product_water.py')
    assert oracle['helper_sha256'] == sha(ROOT / 'analyzer/water_native_projection.py')
    assert oracle['calibration_sha256'] == sha(world_root / 'calibration.json')
    assert result['host_sha256'] == sha(ROOT / 'hosts/native-matrix.py')
    assert oracle['model']['session_binding'] == source['session_binding']
    assert oracle['model']['source_contract_sha256'] == source['source_contract_sha256']
    assert oracle['model']['scale_relative_fov90'] == fit['shared']['scale_relative_fov90']
    assert oracle['model']['center_physical_pixels'] == fit['shared']['center_physical_pixels']
    assert result['evidence_valid'] is True and result['capture_failures'] == []
    assert result['production_qualified'] is False and result['performance_without_intervention'] is False
    assert result['observed_product_gates'] == {'geometry': True, 'transparency': True, 'animation': False}
    assert len(result['geometry']) == 15 and all(row['passed'] for row in result['geometry'].values())
    assert max(row['maximum_boundary_pixels'] for row in result['geometry'].values()) == 3
    assert original['geometry']['full_falling_wet']['maximum_boundary_pixels'] == 88
    assert original['geometry']['full_falling_wet']['passed'] is False
    if args.pixels:
        with tempfile.TemporaryDirectory(prefix='water-native-world-r21-replay-') as directory:
            temporary = Path(directory)
            world_refs = read(world_root / 'references.json')
            archives = []
            try:
                for entry in world_refs['source_archives_in_precedence_order']:
                    path = (world_root / entry['path']).resolve(strict=True)
                    assert sha(path) == entry['sha256']
                    archives.append(zipfile.ZipFile(path))
                sources = source['launch_source_sha256']
                contents = {}
                for archive in archives:
                    for name in archive.namelist():
                        if name in sources:
                            contents[name] = archive
                assert set(contents) == set(sources)
                for name, expected in sources.items():
                    relative = PurePosixPath(name)
                    assert not relative.is_absolute() and '..' not in relative.parts and ':' not in name
                    assert hashlib.sha256(contents[name].read(name)).hexdigest() == expected
                    if name.endswith('.py') and name.startswith(('tools/', 'behavior_pack/', '.agents/')):
                        path = temporary / name
                        path.parent.mkdir(parents=True, exist_ok=True)
                        path.write_bytes(contents[name].read(name))
            finally:
                for archive in archives:
                    archive.close()
            for name in ('analyze_product_water.py', 'water_native_projection.py'):
                shutil.copy2(ROOT / 'analyzer' / name, temporary / 'tools' / name)
            for view in calibration['views']:
                for state in ('shown', 'hidden'):
                    view[state]['path'] = str(world_root / 'captures/calibration' / Path(view[state]['path']).name)
            calibration_path = temporary / 'calibration.json'
            calibration_path.write_text(json.dumps(calibration), encoding='ascii')
            for capture in source['captures'].values():
                capture['path'] = str(world_root / 'captures/world-full-public19' / Path(capture['path']).name)
            source['camera_calibration'].update(path=str(calibration_path), sha256=sha(calibration_path))
            source_path = temporary / 'source.json'
            source_path.write_text(json.dumps(source), encoding='ascii')
            sys.path.insert(0, str(temporary / 'tools'))
            import numpy as np
            import analyze_product_water as analysis
            original_rgb = analysis.rgb
            cache = {}

            def decoded_rgb(path):
                key = str(Path(path).resolve(strict=True))
                if key not in cache:
                    destination = temporary / ('decoded-%d.npy' % len(cache))
                    np.save(destination, original_rgb(path), allow_pickle=False)
                    cache[key] = destination
                return np.load(cache[key], mmap_mode='r', allow_pickle=False)

            analysis.rgb = decoded_rgb
            measured = analysis.analyze(source_path, native_world_geometry=True)
            for key in ('evidence_valid', 'capture_failures', 'limits', 'geometry', 'transparency',
                        'animation', 'alpha_controls', 'observed_product_gates'):
                assert measured[key] == result[key], key
            assert measured['geometry_oracle']['model'] == oracle['model']
            assert measured['geometry_oracle']['helper_sha256'] == oracle['helper_sha256']
            assert measured['analyzer_sha256'] == result['analyzer_sha256']
    print(json.dumps({'verified': True, 'pixels_replayed': args.pixels, 'source_captures': 92,
        'geometry_checks': len(result['geometry']), 'maximum_boundary_pixels': 3,
        'original_falling_boundary_pixels': 88, 'production_qualified': False}))


if __name__ == '__main__':
    main()
