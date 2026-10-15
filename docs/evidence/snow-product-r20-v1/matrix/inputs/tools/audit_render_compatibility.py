"""Audit appearance candidates without treating resource links as pixel proof."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import json5

from audit_native_animated_blocks import RESOURCES, inventory

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs/reference/native_animations/nemc_3.10.0.420447'
OUTPUT = ROOT / 'tools/data/render_compatibility_nemc_3.10.0.420447.json'
NBT_SOURCE = ROOT / 'tools/data/native_block_entity_defaults_nemc_3.9.0.401155.json'
SUPPLEMENTAL = {
    'chemistry': RESOURCES,
    'chemistry_1.20.50': RESOURCES[:2],
    'chemistry_1.20.60': RESOURCES[:2],
    'chemistry_1.21.30': RESOURCES[:2],
    'vanilla_netease': (RESOURCES[1],),
}

# State changes identify snapshot poses, not an obligation to run world physics.
POSE_KEYS = frozenset(('open_bit', 'big_dripleaf_tilt', 'head_piece_bit',
                       'extended_bit', 'sculk_sensor_phase', 'active',
                       'trial_spawner_state', 'vault_state', 'powered_shelf_type'))


def fingerprint(path):
    raw = path.read_bytes()
    return {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def build(palette, manifest, resources, defaults, supplemental=None):
    linked = inventory(palette, resources[RESOURCES[0]], resources[RESOURCES[1]],
                       resources[RESOURCES[2]])
    animated = {row['name']: row for row in linked['rows']}
    packs = {}
    resolved_elsewhere = set()
    for pack, values in sorted((supplemental or {}).items()):
        terrain = {'texture_data': dict(resources[RESOURCES[1]]['texture_data'])}
        terrain['texture_data'].update(values.get(RESOURCES[1], {}).get('texture_data', {}))
        extra = inventory(palette, values.get(RESOURCES[0], {}), terrain,
                          values.get(RESOURCES[2], resources[RESOURCES[2]]))
        packs[pack] = extra
        resolved_elsewhere.update(set(animated) | {
            row['name'] for row in extra['rows']})
        resolved_elsewhere.update({row['name'] for row in palette['blocks']} -
                                  set(extra['dump_names_without_direct_definition']))
        animated.update({row['name']: row for row in extra['rows']})
    entities = defaults['block_entities']
    scanned = defaultdict(lambda: {'aux_values': [], 'state_keys': set()})
    for state in palette['blocks']:
        row = scanned[state['name']]
        row['aux_values'].append(state['data'])
        row['state_keys'].update(field['name'] for field in state['states'])
    rows = []
    unmatched = set(linked['dump_names_without_direct_definition'])
    unmatched_all = unmatched - resolved_elsewhere
    for name, state in sorted(scanned.items()):
        native = entities.get(name, {}).get('nbt', {}).get('id', {}).get('__value__')
        rows.append({'name': name, 'aux_values': sorted(set(state['aux_values'])),
                     'state_keys': sorted(state['state_keys']), 'native_nbt_id': native,
                     'flipbook_candidate': name in animated,
                     'snapshot_pose_keys': sorted(state['state_keys'] & POSE_KEYS),
                     'direct_resource_definition_missing': name in unmatched,
                     'definition_missing_from_all_scanned_packs': name in unmatched_all,
                     'project_owned': not name.startswith('minecraft:'),
                     'pixel_qualified': False})
    ordinary = [row for row in rows if row['flipbook_candidate'] and not row['native_nbt_id']]
    nbt = [row for row in rows if row['flipbook_candidate'] and row['native_nbt_id']]
    return {'schema_version': 1, 'resource_version': 'NEMC 3.10.0.420447',
            'registry_version': manifest['game_version'],
            'registry_sha256': manifest['source_sha256'].lower(),
            'checked_names': len(rows), 'checked_states': len(palette['blocks']),
            'ordinary_flipbook_names': [row['name'] for row in ordinary],
            'ordinary_flipbook_states': sum(len(row['aux_values']) for row in ordinary),
            'nbt_flipbook_names': [row['name'] for row in nbt],
            'nbt_flipbook_states': sum(len(row['aux_values']) for row in nbt),
            'all_block_rows': rows, 'flipbook_inventory': linked,
            'supplemental_pack_inventories': packs,
            'unmapped_after_supplemental_packs': sorted(unmatched_all),
            'particles_required': False,
            'scope': 'All retained dump states scanned. Resource links and pose keys are '
                     'candidates only; native model/shader behavior still needs qualification. '
                     'No particles, world simulation, registry or transform migration.'}


def report(source, supplemental_root=None):
    supplemental_root = source if supplemental_root is None else supplemental_root
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
    palette_path = ROOT / manifest['source_file']
    if fingerprint(palette_path)['sha256'] != manifest['source_sha256'].lower():
        raise ValueError('Registry bytes differ from the retained manifest')
    palette = json.loads(palette_path.read_bytes())
    if (len(palette['blocks']) != manifest['record_count'] or
            len({row['name'] for row in palette['blocks']}) != manifest['name_count']):
        raise ValueError('Dump coverage differs from the retained manifest')
    defaults = json.loads(NBT_SOURCE.read_bytes())
    if (defaults['game_version'] != manifest['game_version'] or
            defaults['palette_sha256'].lower() != manifest['source_sha256'].lower()):
        raise ValueError('NBT source does not match the retained registry')
    resources = {relative: json5.loads((source / relative).read_text(encoding='utf8'),
                                      allow_duplicate_keys=False) for relative in RESOURCES}
    supplemental = {
        pack: {relative: json5.loads((supplemental_root / pack / relative).read_text(encoding='utf8'),
                                     allow_duplicate_keys=False) for relative in paths}
        for pack, paths in SUPPLEMENTAL.items()}
    data = build(palette, manifest, resources, defaults, supplemental)
    data['resources'] = {relative: fingerprint(source / relative) for relative in RESOURCES}
    data['supplemental_resources'] = {
        pack + '/' + relative: fingerprint(supplemental_root / pack / relative)
        for pack, paths in SUPPLEMENTAL.items() for relative in paths}
    data['nbt_source'] = dict(path=str(NBT_SOURCE.relative_to(ROOT)).replace('\\', '/'),
                              **fingerprint(NBT_SOURCE))
    old = ROOT / 'docs/reference/native_animations/nemc_3.9.0.401155'
    data['resource_bytes_equal_to_3_9'] = all(
        fingerprint(old / relative) == data['resources'][relative] for relative in RESOURCES)
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--vanilla-pack', type=Path)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.capture and (args.check or args.vanilla_pack is None):
        parser.error('--capture needs --vanilla-pack and cannot be combined with --check')
    if args.capture:
        for relative in RESOURCES:
            destination = args.source / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(args.vanilla_pack / relative, destination)
        for pack, paths in SUPPLEMENTAL.items():
            for relative in paths:
                destination = args.source / pack / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(args.vanilla_pack.parent / pack / relative, destination)
    data = report(args.source)
    if (args.vanilla_pack is not None and
            report(args.vanilla_pack, args.vanilla_pack.parent) != data):
        raise ValueError('Installed resources differ from the archived inventory')
    if args.check:
        if json.loads(args.output.read_bytes()) != data:
            raise ValueError('Appearance inventory needs regeneration')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(data, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print('%d names / %d states scanned; %d ordinary + %d NBT flipbook candidates; %d unmapped names' % (
        data['checked_names'], data['checked_states'], len(data['ordinary_flipbook_names']),
        len(data['nbt_flipbook_names']),
        len(data['unmapped_after_supplemental_packs'])))


if __name__ == '__main__':
    main()
