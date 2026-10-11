"""Generate explicit liquid rules without promoting candidate visual acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.liquid_render_plan import WATER_NAMES, LAVA_NAMES
from projection.liquid_shape import LiquidHeightRule

DEFAULT_SOURCE = ROOT / 'tools/data/native_liquid_shape_candidate_nemc_3.9.0.401155.json'
DEFAULT_OUTPUT = ROOT / 'behavior_pack/modern_projection/projection/liquid_shape_data.py'


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('ascii')).hexdigest()


def validate(data, manifest):
    if (data.get('schema_version') != 1 or data.get('game_version') != manifest['game_version']
            or not isinstance(data.get('palette_sha256'), str)
            or data['palette_sha256'].lower() != manifest['source_sha256'].lower()):
        raise ValueError('Liquid shape rules do not match the native registry')
    names = data.get('supported_names')
    rules = data.get('rules')
    if (not isinstance(names, list) or not names or any(not isinstance(name, str) for name in names)
            or len(set(names)) != len(names) or not set(names).issubset(WATER_NAMES | LAVA_NAMES)
            or not isinstance(rules, dict) or not rules or not set(rules).issubset(('water', 'lava'))):
        raise ValueError('Liquid shape rules need explicit families and unique supported names')
    families = {'water' if name in WATER_NAMES else 'lava' for name in names}
    if set(rules) != families:
        raise ValueError('Liquid rule families differ from the supported liquid names')
    for row in rules.values():
        if not isinstance(row, dict) or set(row) != {'heights', 'weights', 'empty_weight', 'above_height'}:
            raise ValueError('Each liquid family needs four explicit rule fields')
        LiquidHeightRule(row['heights'], row['weights'], row['empty_weight'], row['above_height'])
    if type(data.get('accepted')) is not bool or type(data.get('evidence', {}).get('production_accepted')) is not bool:
        raise ValueError('Liquid candidate must retain explicit acceptance flags')
    return data


def runtime_source(data):
    rows = {name: (tuple(row['heights']), tuple(row['weights']),
                   row['empty_weight'], row['above_height']) for name, row in data['rules'].items()}
    return ('"""Generated liquid shape candidate; native production acceptance is separate."""\n'
            'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
            'CANDIDATE_SHA256 = %r\nPRODUCTION_ACCEPTED = %r\n'
            'SUPPORTED_NAMES = frozenset(%r)\nHEIGHT_RULES = {\n%s}\n' %
            (data['game_version'], data['palette_sha256'], digest(data),
             data['accepted'] and data['evidence']['production_accepted'],
             tuple(sorted(data['supported_names'])),
             ''.join('    %r: %r,\n' % (name, row) for name, row in sorted(rows.items()))))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    data = validate(json.loads(args.source.read_text(encoding='utf8')), manifest)
    text = runtime_source(data)
    if args.check:
        if args.output.read_text(encoding='ascii') != text:
            raise ValueError('Generated liquid shape rules are stale')
    else:
        args.output.write_text(text, encoding='ascii')
    print('Liquid shape rules: %d names; production_accepted=%s' %
          (len(data['supported_names']), data['accepted'] and data['evidence']['production_accepted']))


if __name__ == '__main__':
    main()
