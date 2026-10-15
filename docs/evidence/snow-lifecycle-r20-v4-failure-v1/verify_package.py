"""Verify an immutable snow lifecycle failure package without a game."""
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
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    root = args.package.resolve(strict=True)
    manifest = json.loads((root / 'manifest.json').read_bytes())
    for relative, record in manifest['files'].items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root):
            raise ValueError('Snow lifecycle evidence escapes its package')
        if path.stat().st_size != record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Snow lifecycle evidence bytes changed: ' + relative)
    result = {'verified': True, 'files': len(manifest['files']), 'pixels_replayed': False,
              'workflow_accepted': False, 'production_accepted': False}
    if args.pixels:
        inputs = root / 'lifecycle/inputs'
        for folder in (inputs / '.agents/skills/pyreact-debugging/scripts',
                       inputs / 'behavior_pack/modern_projection', inputs / 'tools', inputs, root):
            sys.path.insert(0, str(folder))
        from analyze_snow_lifecycle_r20 import analyze
        mapping = manifest['original_to_package']
        report = remap(json.loads((root / 'lifecycle/report.json').read_bytes()), mapping, root)
        failure = remap(json.loads((root / 'lifecycle/report_saved_library_load_response_error.json').read_bytes()), mapping, root)
        replay = analyze(report, failure)
        if replay['workflow_accepted'] or replay['production_accepted']:
            raise ValueError('Failed snow acquisition cannot become an accepted workflow')
        result.update(pixels_replayed=replay['pixels_replayed'], capture_count=replay['capture_count'],
                      completed=replay['original_completed'], restored=replay['original_restored'],
                      failed_step=replay['failed_step']['label'])
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
