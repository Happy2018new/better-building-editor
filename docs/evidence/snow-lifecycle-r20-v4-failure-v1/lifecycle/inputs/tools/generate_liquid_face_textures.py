"""Capture native liquid face textures; UV and native shape acceptance are separate."""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
NATIVE_PATH = 'blocks.json'
NAMES = ('flowing_lava', 'flowing_water', 'lava', 'water')
DEFAULT_SOURCE = ROOT / 'tools/data/native_liquid_face_textures_nemc_3.9.0.401155.json'
DEFAULT_OUTPUT = ROOT / 'behavior_pack/modern_projection/projection/liquid_face_texture_data.py'


def digest(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('ascii')).hexdigest()


def capture(pack, manifest):
    raw = (pack / NATIVE_PATH).read_bytes()
    blocks = json.loads(raw.decode('utf8'))
    rows = {}
    for name in NAMES:
        textures = blocks[name]['textures']
        if not isinstance(textures, dict) or set(textures) != {'up', 'down', 'side'}:
            raise ValueError('Native liquid face layout changed: ' + name)
        rows['minecraft:' + name] = textures
    return {'schema_version': 1, 'game_version': manifest['game_version'],
            'palette_sha256': manifest['source_sha256'], 'native_path': NATIVE_PATH,
            'native_sha256': hashlib.sha256(raw).hexdigest(), 'rows': rows,
            'rows_sha256': digest(rows),
            'scope': 'Native face texture definitions only; no UV, geometry or pixel acceptance.'}


def validate(data, manifest):
    if (data.get('schema_version') != 1 or data.get('game_version') != manifest['game_version']
            or str(data.get('palette_sha256', '')).lower() != manifest['source_sha256'].lower()
            or data.get('native_path') != NATIVE_PATH
            or not re.fullmatch(r'[0-9a-f]{64}', data.get('native_sha256', ''))):
        raise ValueError('Liquid face textures do not match the native registry source')
    rows = data.get('rows')
    if (not isinstance(rows, dict) or set(rows) != {'minecraft:' + name for name in NAMES}
            or digest(rows) != data.get('rows_sha256')):
        raise ValueError('Liquid face texture rows have changed')
    for name, textures in rows.items():
        family = {'still_water_grey', 'flowing_water_grey'} if 'water' in name else {'still_lava', 'flowing_lava'}
        if (not isinstance(textures, dict) or set(textures) != {'up', 'down', 'side'}
                or any(value not in family for value in textures.values())):
            raise ValueError('Unsupported native liquid face texture: ' + name)
    return data


def runtime_source(data):
    return ('"""Generated native liquid face resources; do not edit by hand."""\n'
            'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
            'RESOURCE_SHA256 = %r\nRESOURCE_ROWS_SHA256 = %r\n'
            '# Resource keys do not establish UV transforms or shape equivalence.\n'
            'FACE_TEXTURES = {\n%s}\n' %
            (data['game_version'], data['palette_sha256'], data['native_sha256'], data['rows_sha256'],
             ''.join('    %r: %r,\n' % (name, tuple(rows[face] for face in ('up', 'down', 'side')))
                     for name, rows in sorted(data['rows'].items()))))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--vanilla-pack', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.capture and (args.check or args.vanilla_pack is None):
        parser.error('--capture needs --vanilla-pack and cannot be combined with --check')
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    data = capture(args.vanilla_pack, manifest) if args.capture else json.loads(args.source.read_text(encoding='utf8'))
    validate(data, manifest)
    if args.vanilla_pack is not None and capture(args.vanilla_pack, manifest) != data:
        raise ValueError('Installed liquid face textures differ from the saved snapshot')
    runtime = runtime_source(data)
    if args.check:
        if args.output.read_text(encoding='ascii') != runtime:
            raise ValueError('Generated liquid face texture lookup is stale')
    else:
        if args.capture:
            args.source.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
        args.output.write_text(runtime, encoding='ascii')
    print('Native liquid face textures: %d names; UV acceptance separate' % len(data['rows']))


if __name__ == '__main__':
    main()
