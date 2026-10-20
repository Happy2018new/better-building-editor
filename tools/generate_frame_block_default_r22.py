"""Install three independently named measured cubes without qualifying pixels."""
import argparse
import json
from pathlib import Path

import generate_frame_block_items as generator
import prepare_frame_block_measured_r21 as measured

PROFILE = 'behavior_pack/modern_projection/projection/frame_block_measured_data.py'
REGISTRATIONS = 'tools/data/frame_block_measured_item_registrations_r22.json'
CATALOG = 'tools/data/frame_block_measured_item_catalog_r22.json'
REPLACEMENTS = ((b'modern_projection_frame_block', b'modern_projection_measured_frame_block'),
                (b'modern_projection/frame_block_items/', b'modern_projection/frame_block_measured/'))


def rename(data):
    for before, after in REPLACEMENTS:
        data = data.replace(before, after)
    return data


def resources(install):
    files, catalog = measured.resources(generator.load(generator.CATALOG), install)
    old_profile = 'behavior_pack/modern_projection/projection/frame_block_item_data.py'
    old_registry = 'tools/data/frame_block_item_registrations_nemc_' + generator.VERSION + '.json'
    result = {}
    for relative, data in files.items():
        if relative in (old_profile, measured.CATALOG_PATH):
            continue
        target = REGISTRATIONS if relative == old_registry else rename(relative.encode('ascii')).decode('ascii')
        result[target] = data if relative.endswith('.png') else rename(data)
    result[CATALOG] = generator.encoded(catalog)
    contract = generator.sha(b''.join(path.encode('ascii') + data for path, data in sorted(result.items())))
    namespace = {}
    exec(rename(files[old_profile]), namespace)
    values = {key: namespace[key] for key in ('SCHEMA_VERSION', 'LAYOUT_VERSION', 'ENGINE_VERSION',
               'PALETTE_SHA256', 'POSE', 'ITEMS')}
    values.update(RESOURCE_SHA256=contract, PRODUCTION_QUALIFIED=False, QUALIFICATION_SHA256=None,
                  QUALIFICATION_RESOURCE_SHA256=None, QUALIFIED_ITEMS=(), QUALIFIED_ENCHANTMENTS=(),
                  QUALIFIED_FRAME_POSES={})
    result[PROFILE] = ('"""Three measured frame cubes; plain and enchantment qualification are independent."""\n' +
        ''.join(key + ' = ' + repr(value) + '\n' for key, value in values.items())).encode('ascii')
    return result


def registered(files, root):
    result = dict(files)
    registration = json.loads(files[REGISTRATIONS])
    for relative, section, rows in (('resource_pack/models/netease_models.json', None, registration['models']),
            ('resource_pack/materials/entity.material', 'materials', registration['materials'])):
        existing = generator.load(root / relative)
        (existing[section] if section else existing).update(rows)
        result[relative] = generator.encoded(existing)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--register-from', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    files = resources(args.install)
    if args.register_from:
        files = registered(files, args.register_from)
    if not args.check and args.output.exists():
        raise ValueError('Use a fresh output directory')
    for relative, data in files.items():
        path = args.output / relative
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                raise ValueError('Stale measured cube resource: ' + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(json.dumps({'files': len(files), 'items': [list(item) for item in measured.ITEMS],
                      'production_qualified': False, 'output': str(args.output.resolve())}))


if __name__ == '__main__':
    main()
