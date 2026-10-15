"""Verify retained item-plane bytes and optionally replay frozen pixel analysis."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def rebase(value, original, current):
    if isinstance(value, dict):
        return {key: rebase(child, original, current) for key, child in value.items()}
    if isinstance(value, list):
        return [rebase(child, original, current) for child in value]
    if isinstance(value, str) and value.replace('\\', '/').startswith(original + '/'):
        return str(current / value.replace('\\', '/')[len(original) + 1:])
    return value


def measurements(value):
    return {key: child for key, child in value.items() if key not in ('source_sha256', 'contact_sheet')}


def verify(package, pixels):
    manifest = json.loads((package / 'manifest.json').read_bytes())
    if manifest['schema'] != 1 or manifest['production_qualified'] is not False:
        raise ValueError('Unexpected item-plane manifest')
    for relative, expected in manifest['files'].items():
        path = (package / relative).resolve()
        if not path.is_relative_to(package):
            raise ValueError('Manifest path escapes the retained package')
        raw = path.read_bytes()
        if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('Retained bytes changed: ' + relative)
    summary = json.loads((package / 'summary.json').read_bytes())
    results = {}
    if pixels:
        original = manifest['original_package_root'].replace('\\', '/')
        for label in summary['captures']:
            report = rebase(json.loads((package / label / 'report.json').read_bytes()), original, package)
            with tempfile.TemporaryDirectory(prefix='item-plane-replay-') as directory:
                temporary = Path(directory)
                source = temporary / 'report.json'
                source.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
                result = subprocess.run([sys.executable, '-B', '-X', 'utf8',
                    str(package / 'source/tools/analyze_visible_items_r16.py'), str(source),
                    str(temporary / 'analysis'), '--world-plain-only'], check=True,
                    capture_output=True, text=True, encoding='utf8')
                actual = json.loads((temporary / 'analysis/analysis.json').read_bytes())
                expected = json.loads((package / label / 'analysis/analysis.json').read_bytes())
                if measurements(actual) != measurements(expected):
                    raise ValueError('Frozen pixel replay differs: ' + label)
                results[label] = {'evidence_valid': actual['evidence_valid'],
                                 'static_pose_accepted': actual['static_pose_accepted']}
    print(json.dumps({'manifest_files_verified': len(manifest['files']), 'pixel_replay': results,
                      'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    verify(args.package.resolve(), args.pixels)
