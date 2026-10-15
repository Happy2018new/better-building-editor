"""Retain versioned nondefault native field observations without player inventory."""
import argparse
import base64
import hashlib
import json
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(report, source_bytes):
    if not report.get('completed') or not report.get('native_cleaned') or not report.get('client_cleaned'):
        raise ValueError('Use a completed and cleaned native appearance batch')
    setup = report['setup']
    fields = ('case', 'name', 'block', 'yaw', 'player_rotation', 'face', 'color',
              'observed_id', 'observed_rotation', 'observed_color', 'observed_type',
              'observed_item_rotation', 'fill_return', 'fill_observed', 'cell_nbt', 'palette')
    return {'schema': 1, 'game_version': setup['game_version'],
            'palette_sha256': setup['palette_sha256'],
            'source_sha256': hashlib.sha256(source_bytes).hexdigest(),
            'source_hash_format': 'raw_file_bytes',
            'scope': 'Native player placement and visible palettes; separate from visual acceptance',
            'rows': [{field: row[field] for field in fields if field in row}
                     for row in report['client']['rows']]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'tools/data/native_entity_appearances_nemc_3.9.0.401155.json')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--runtime-output', type=Path, default=ROOT / 'behavior_pack/modern_projection/projection/appearance_defaults_data.py')
    args = parser.parse_args()
    source_bytes = args.source.read_bytes()
    data = snapshot(json.loads(source_bytes), source_bytes)
    text = json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2) + '\n'
    packed = base64.b64encode(zlib.compress(json.dumps(data['rows'], ensure_ascii=True,
        sort_keys=True, separators=(',', ':')).encode('ascii'), 9)).decode('ascii')
    runtime = ('"""Generated native nondefault appearance fixtures; do not edit."""\n'
               'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
               'SOURCE_SHA256 = %r\nROWS = %r\n' %
               (data['game_version'], data['palette_sha256'], data['source_sha256'], packed))
    if args.check:
        if args.output.read_text(encoding='ascii') != text:
            raise SystemExit('Native appearance snapshot is stale')
        if args.runtime_output.read_text(encoding='ascii') != runtime:
            raise SystemExit('Native appearance runtime fixtures are stale')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding='ascii')
        args.runtime_output.write_text(runtime, encoding='ascii')
    print('Native appearance observations: %d cases, %s' % (len(data['rows']), data['game_version']))


if __name__ == '__main__':
    main()
