"""Snapshot installed vanilla water appearance and generate a versioned lookup.

Capture: --capture --vanilla-pack <game/data/resource_packs/vanilla>
Verify bundled data: --check (optionally also --vanilla-pack <same pack>)
This records resource definitions, not native pixel or fluid-rule acceptance.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / 'tools/data/biome_water_appearance_nemc_3.9.0.401155.json'
DEFAULT_OUTPUT = ROOT / 'behavior_pack/modern_projection/projection/biome_water_data.py'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('ascii')).hexdigest()


def water_fields(appearance):
    if not isinstance(appearance, dict):
        raise ValueError('Missing native water appearance component')
    color = appearance.get('surface_color')
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Expected explicit RGB water surface color')
    opacity = appearance.get('surface_opacity')
    if opacity is not None and (isinstance(opacity, bool)
                               or not isinstance(opacity, (int, float))
                               or not 0 <= opacity <= 1):
        raise ValueError('Water surface opacity must be in [0, 1]')
    # Missing opacity is an engine default, not an implicit opaque surface.
    return color[1:].upper(), opacity


def capture(pack, manifest):
    rows = []
    identifiers = set()
    for path in sorted((pack / 'biomes').glob('*.client_biome.json')):
        raw = path.read_bytes()
        document = json.loads(raw.decode('utf8'))
        biome = document['minecraft:client_biome']
        identifier = biome['description']['identifier']
        if (not isinstance(identifier, str) or not identifier.startswith('minecraft:')
                or identifier in identifiers):
            raise ValueError('Expected distinct vanilla biome identifiers')
        identifiers.add(identifier)
        color, opacity = water_fields(biome['components'].get('minecraft:water_appearance'))
        rows.append({'identifier': identifier, 'format_version': document['format_version'],
                     'surface_color': color, 'surface_opacity': opacity,
                     'source_file': path.relative_to(pack).as_posix(),
                     'source_sha256': hashlib.sha256(raw).hexdigest()})
    if not rows:
        raise ValueError('No installed client biome files found')
    rows.sort(key=lambda row: row['identifier'])
    return {'schema': 1, 'game_version': manifest['game_version'],
            'palette_sha256': manifest['source_sha256'],
            'resource_scope': 'Installed vanilla client_biome files; no other pack overrides',
            'acceptance_scope': 'Resource definitions only; no native water pixel acceptance',
            'missing_opacity': 'Preserve None; engine default has not been inferred',
            'rows_sha256': digest(rows), 'rows': rows}


def validate(data, manifest):
    if (data.get('schema') != 1 or data.get('game_version') != manifest['game_version']
            or str(data.get('palette_sha256', '')).lower() != manifest['source_sha256'].lower()):
        raise ValueError('Water appearance source does not match the current registry')
    rows = data.get('rows')
    if not isinstance(rows, list) or not rows or digest(rows) != data.get('rows_sha256'):
        raise ValueError('Water appearance rows are missing or have changed')
    names = set()
    for row in rows:
        name = row['identifier']
        if not isinstance(name, str) or not name.startswith('minecraft:') or name in names:
            raise ValueError('Duplicate or invalid water biome identifier')
        names.add(name)
        color, opacity = water_fields({'surface_color': '#' + row['surface_color'],
                                       'surface_opacity': row['surface_opacity']})
        if color != row['surface_color']:
            raise ValueError('Expected canonical uppercase RGB')
        source = Path(row['source_file'])
        if (source.is_absolute() or '..' in source.parts or source.parts[0] != 'biomes'
                or not source.name.endswith('.client_biome.json')
                or not re.fullmatch(r'[0-9a-f]{64}', row['source_sha256'])):
            raise ValueError('Invalid native biome source provenance')
    return data


def runtime_source(data):
    values = sorted((row['identifier'].split(':', 1)[1],
                     row['surface_color'], row['surface_opacity']) for row in data['rows'])
    return ('"""Generated vanilla water appearance; do not edit by hand."""\n'
            'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
            'RESOURCE_ROWS_SHA256 = %r\n'
            '# None means unspecified engine opacity, not 1.0.\n'
            'WATER_APPEARANCE = {\n%s}\n' %
            (data['game_version'], data['palette_sha256'], data['rows_sha256'],
             ''.join('    %r: (%r, %r),\n' % row for row in values)))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--manifest', type=Path, default=ROOT / 'tools/data/block_registry_manifest.json')
    parser.add_argument('--vanilla-pack', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.capture and (args.check or args.vanilla_pack is None):
        parser.error('--capture needs --vanilla-pack and cannot be combined with --check')
    manifest = json.loads(args.manifest.read_text(encoding='utf8'))
    if args.capture:
        data = capture(args.vanilla_pack, manifest)
    else:
        data = json.loads(args.source.read_text(encoding='utf8'))
    validate(data, manifest)
    if args.vanilla_pack is not None and capture(args.vanilla_pack, manifest) != data:
        raise ValueError('Installed vanilla water resources differ from the saved snapshot')
    runtime = runtime_source(data)
    if args.check:
        if args.output.read_text(encoding='ascii') != runtime:
            raise ValueError('Generated water appearance lookup is stale')
    else:
        if args.capture:
            args.source.write_text(json.dumps(data, ensure_ascii=True, sort_keys=True, indent=2)
                                   + '\n', encoding='ascii')
        args.output.write_text(runtime, encoding='ascii')
    print('Vanilla water appearance: %d biomes; unspecified opacity preserved' % len(data['rows']))


if __name__ == '__main__':
    main()
