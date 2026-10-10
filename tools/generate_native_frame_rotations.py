"""Retain native frame Float-degree evidence with its version and palette hash."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(report, source_bytes):
    if not all(report.get(field) for field in ('completed', 'native_cleaned', 'client_cleaned')):
        raise ValueError('Use a completed and cleaned native appearance batch')
    captured = report['frame_rotations']
    if captured['schema'] != 1 or not captured['rotations_restored']:
        raise ValueError('Native frame rotation capture did not restore its fixtures')
    if any(captured[field] != report['setup'][field]
           for field in ('game_version', 'palette_sha256')):
        raise ValueError('Native frame rotation capture does not match its source registry')
    samples = captured['samples']
    if len(samples) != 16:
        raise ValueError('Expected ordinary and glowing frames at eight angles')
    expected = set((case, float(angle)) for case in ('frame_filled', 'glow_frame_filled')
                   for angle in range(0, 360, 45))
    observed = set()
    for row in samples:
        angle = row['api_requested_degrees']
        if row['api_observed_degrees'] != angle or row['nbt_item_rotation'] != {
                '__type__': 5, '__value__': angle}:
            raise ValueError('Frame rotations are not the observed native Float degrees')
        observed.add((row['case'], angle))
    if observed != expected:
        raise ValueError('Native frame rotations are incomplete')
    return {'schema': 1, 'game_version': captured['game_version'],
            'palette_sha256': captured['palette_sha256'],
            'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
            'source_hash_format': 'raw_file_bytes',
            'scope': 'Native Float clockwise degrees; face-plane geometry and GPU acceptance are separate',
            'samples': samples}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path,
        default=ROOT / 'tools/data/native_frame_rotations_nemc_3.9.0.401155.json')
    parser.add_argument('--runtime-output', type=Path,
        default=ROOT / 'behavior_pack/modern_projection/projection/frame_rotation_data.py')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    source = args.source.read_bytes()
    data = snapshot(json.loads(source), source)
    text = json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2) + '\n'
    runtime = ('"""Generated native frame rotation evidence; do not edit."""\n'
               'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
               'SOURCE_SHA256 = %r\nTAG_TYPE = 5\nUNITS = "clockwise_degrees"\n' %
               (data['game_version'], data['palette_sha256'], data['source_sha256']))
    if args.check:
        if args.output.read_text(encoding='ascii') != text:
            raise SystemExit('Native frame rotation snapshot is stale')
        if args.runtime_output.read_text(encoding='ascii') != runtime:
            raise SystemExit('Native frame rotation runtime evidence is stale')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='ascii')
        args.runtime_output.write_text(runtime, encoding='ascii')
    print('Native frame rotations: %d cases, %s' % (len(data['samples']), data['game_version']))


if __name__ == '__main__':
    main()
