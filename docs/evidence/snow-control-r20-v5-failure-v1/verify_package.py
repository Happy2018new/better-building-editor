"""Verify rejected snow control bytes, clocks, geometry and exact process exits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image


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
            raise ValueError('Snow control evidence escapes package')
        if path.stat().st_size != record['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
            raise ValueError('Snow control evidence changed: ' + relative)
    mapping = manifest['original_to_package']

    def remap(value):
        if isinstance(value, dict):
            return {key: remap(child) for key, child in value.items()}
        if isinstance(value, list):
            return [remap(child) for child in value]
        return str(root / mapping[value]) if isinstance(value, str) and value in mapping else value

    report = remap(json.loads((root / 'lifecycle/report.json').read_bytes()))
    failure = remap(json.loads((root / 'lifecycle/report_control_snow_response_error.json').read_bytes()))
    receipt = json.loads((root / 'lifecycle/receipt.json').read_bytes())
    if (report['completed'] or report['passed'] or not report['restored'] or report['cleanup_errors']
            or report['steps'] or failure['passed'] or receipt['returncode'] != 1
            or not receipt['process_completed'] or not receipt['source_unchanged']):
        raise ValueError('Snow failure or restoration state changed')
    if hashlib.sha256((root / 'lifecycle/report.json').read_bytes()).hexdigest() != receipt['report_sha256']:
        raise ValueError('Wrapper no longer binds original report')
    exits = json.loads((root / 'control/process-exits.json').read_bytes())
    if not exits['completed'] or exits['owner'] != report['owner']:
        raise ValueError('Exact snow lifecycle exit record incomplete')
    for kind in ('game', 'mcdk'):
        row = exits['processes'][kind]
        if row['state'] != 'exited' or row['exit_code_hex'] != '0x%08X' % row['exit_code']:
            raise ValueError('Exact process exit code changed')
    if (exits['processes']['game']['pid'] != report['game_pid']
            or exits['processes']['game']['identity'] != report['game_identity']):
        raise ValueError('Exited game does not own the captures')
    captures = {str(path): path for path in (root / 'lifecycle').glob('*_native.png')}
    for path in captures.values():
        metadata = json.loads(path.with_suffix('.capture.json').read_bytes())
        if (not metadata['ok'] or not metadata['reliable']
                or metadata['owner'] != report['owner'] or metadata['game_pid'] != report['game_pid']
                or metadata['game_identity'] != report['game_identity']
                or metadata['agent_activation_allowed'] is not False or metadata['activation_fallback'] is not False
                or metadata['frame']['frame_qpc_100ns'] < metadata['frame']['request_qpc_100ns']):
            raise ValueError('Snow native capture receipt changed')
        if hashlib.sha256(path.read_bytes()).hexdigest() != metadata['sha256']:
            raise ValueError('Snow native image no longer matches its receipt')
    result = {'verified': True, 'files': len(manifest['files']), 'capture_count': len(captures),
              'completed': False, 'restored': True, 'pixels_replayed': False,
              'workflow_accepted': False, 'production_accepted': False}
    if args.pixels:
        sys.path.insert(0, str(root))
        from analyze_snow_control_failure_r20 import replay
        diagnostic = replay(root, report, failure)
        with Image.open(failure['reference']['path']) as source:
            width, height = source.size
            reference_clock = source.convert('RGB').crop((int(width*.3), int(height*.065),
                                                         int(width*.7), int(height*.095)))
        if hashlib.sha256(reference_clock.tobytes()).hexdigest() != failure['reference_clock']['sha256']:
            raise ValueError('Snow reference native clock changed')
        for attempt in failure['attempts']:
            picture = attempt['capture']
            with Image.open(picture['path']) as source:
                width, height = source.size
                clock = source.convert('RGB').crop((int(width*.3), int(height*.065),
                                                   int(width*.7), int(height*.095)))
            if (hashlib.sha256(clock.tobytes()).hexdigest() != attempt['clock']['sha256']
                    or not attempt['native_clock_advanced']
                    or attempt['clock']['sha256'] == failure['reference_clock']['sha256']
                    or attempt['render_frames']['after'] < attempt['render_frames']['before'] + 2):
                raise ValueError('Snow response native clock or frames changed')
        expected = json.loads((root / 'diagnosis/diagnosis.json').read_bytes())
        if json.loads(json.dumps(diagnostic)) != expected:
            raise ValueError('Snow control pixel attribution changed')
        result.update(pixels_replayed=True, attributed_outside_pixels=[
            row['removed_baseline_ink_pixels'] for row in diagnostic['attempts']],
            unattributed_outside_pixels=[row['unattributed_outside_pixels'] for row in diagnostic['attempts']])
    print(json.dumps(result))


if __name__ == '__main__':
    main()
