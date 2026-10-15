"""Publish original snow diagnostics and the exact inputs needed for pixel replay."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--matrix', type=Path, required=True)
    parser.add_argument('--calibration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    mapping = {}

    def copy(source, relative):
        source = source.resolve(strict=True)
        destination = args.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        key = str(source)
        if key in mapping:
            previous = args.output / mapping[key]
            assert previous.read_bytes() == destination.read_bytes()
        mapping[key] = relative.as_posix()

    for name, folder in (('matrix', args.matrix), ('calibration', args.calibration)):
        for source in sorted(folder.rglob('*')):
            if source.is_file():
                copy(source, Path(name) / source.relative_to(folder))
    report = json.loads((args.matrix / 'report.json').read_bytes())
    receipt = json.loads((args.matrix / 'receipt.json').read_bytes())
    for source in sorted((args.project / 'behavior_pack').rglob('*.py')):
        relative = source.relative_to(args.project)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == receipt['files'][relative.as_posix()]
        copy(source, Path('matrix/inputs') / relative)
    for name in ('preview_fern.json', 'preview_short_grass.json'):
        source = args.project / 'resource_pack/models/netease_block' / name
        copy(source, Path('matrix/inputs/resource_pack/models/netease_block') / name)
    for plant, asset in report['assets'].items():
        for kind in ('model', 'texture'):
            source = Path(asset[kind])
            assert hashlib.sha256(source.read_bytes()).hexdigest() == asset[kind + '_sha256']
            copy(source, Path('assets') / plant / (kind + source.suffix))
    for name in ('analyze_snow_product_r20.py', 'snow_native_projection_r20.py'):
        copy(ROOT / 'tools' / name, Path(name))
    copy(ROOT / 'tools/verify_snow_package_r20.py', Path('verify_package.py'))
    manifest = {'schema': 1, 'purpose': 'Original failed snow matrix and calibrated native pixel replay',
                'qualification_changed': False, 'production_accepted': False,
                'complete_executable_acquisition_replay': False,
                'acquisition_replay_limit': 'Pinned full source hashes plus complete business Python and used plant assets; unrelated product media is not duplicated',
                'original_to_package': mapping, 'files': {}}
    for path in sorted(args.output.rglob('*')):
        if path.is_file():
            manifest['files'][path.relative_to(args.output).as_posix()] = {
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
    (args.output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf8')
    print(json.dumps({'files': len(manifest['files']),
                       'bytes': sum(row['bytes'] for row in manifest['files'].values()),
                       'production_accepted': False}))


if __name__ == '__main__':
    raise SystemExit(main())
