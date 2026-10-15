"""Verify the portable R20 snow evidence without opening a game."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def remap(value, mapping, root):
    if isinstance(value, dict):
        return {key: remap(child, mapping, root) for key, child in value.items()}
    if isinstance(value, list):
        return [remap(child, mapping, root) for child in value]
    if isinstance(value, str) and value in mapping:
        return str(root / mapping[value])
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    root = args.package.resolve(strict=True)
    manifest = json.loads((root / 'manifest.json').read_bytes())
    for relative, record in manifest['files'].items():
        path = (root / relative).resolve(strict=True)
        assert path.is_relative_to(root), 'Evidence path escapes its package'
        if path.stat().st_size != record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Snow evidence bytes changed: ' + relative)
    result = {'verified': True, 'files': len(manifest['files']), 'pixels_replayed': False,
              'production_accepted': False, 'complete_executable_acquisition_replay': False}
    if args.pixels:
        inputs = root / 'matrix/inputs'
        sys.path.insert(0, str(inputs / '.agents/skills/pyreact-debugging/scripts'))
        sys.path.insert(0, str(inputs / 'behavior_pack/modern_projection'))
        sys.path.insert(0, str(inputs / 'tools'))
        sys.path.insert(0, str(root))
        from analyze_snow_product_r20 import analyze
        from water_native_projection import validate_calibration
        mapping = manifest['original_to_package']
        calibration = remap(json.loads((root / 'calibration/report.json').read_bytes()), mapping, root)
        native = calibration['native_projection']
        result['calibration'] = validate_calibration(calibration, native['session_binding'], native['source_contract_sha256'])
        report = remap(json.loads((root / 'matrix/report.json').read_bytes()), mapping, root)
        result['matrix'] = analyze(report)
        result['pixels_replayed'] = result['matrix']['pixels_replayed']
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps({key: result[key] for key in ('verified', 'files', 'pixels_replayed', 'production_accepted')}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
