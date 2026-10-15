"""Check frozen downward-pose and editor body-brightness evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile


def brightness_measurements(value):
    return dict(value, rows=[{key: child for key, child in row.items()
                             if key not in ('original_report', 'original_report_sha256')}
                            for row in value['rows']])


def verify(package, pixels):
    sys.path.insert(0, str(package / 'source/tools'))
    from verify_item_plane_evidence_r20 import rebase, verify as verify_plane
    verify_plane(package, pixels)
    if not pixels:
        return
    manifest = json.loads((package / 'manifest.json').read_bytes())
    original = manifest['original_package_root'].replace('\\', '/')
    summary = json.loads((package / 'summary.json').read_bytes())
    with tempfile.TemporaryDirectory(prefix='item-brightness-replay-') as directory:
        temporary = Path(directory)
        command = [sys.executable, '-B', '-X', 'utf8',
                   str(package / 'source/tools/analyze_item_frame_brightness_r20.py')]
        for label in summary['brightness']:
            report = rebase(json.loads((package / 'brightness' / label / 'report.json').read_bytes()),
                            original, package)
            target = temporary / (label + '.json')
            target.write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n', encoding='ascii')
            command.extend(('--report', str(target)))
        command.extend(('--output', str(temporary / 'analysis')))
        subprocess.run(command, check=True, capture_output=True, text=True, encoding='utf8')
        actual = json.loads((temporary / 'analysis/analysis.json').read_bytes())
        expected = json.loads((package / 'brightness/analysis/analysis.json').read_bytes())
        if brightness_measurements(actual) != brightness_measurements(expected):
            raise ValueError('Frozen editor brightness replay differs')
        print(json.dumps({'brightness_replay_passed': actual['passed'], 'rows': len(actual['rows']),
            'maximum_rgb_change': max(row['maximum_rgb_change'] for row in actual['rows']),
            'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    verify(args.package.resolve(), args.pixels)
