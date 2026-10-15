"""Census exact-version public glint rules without mistaking absence for false.

Most vanilla items are implemented in the engine, not the shipped item JSON.
Each loaded identifier remains unresolved until a public rule or native
observation establishes its behavior. Projectile materials prove no item rule.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from audit_native_nbt_inventory import read_json

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.10.0.420447'
INSTALL = Path('D:/MCStudioDownload/game/MinecraftPE_Netease') / VERSION
BASIC = ROOT / '.runtime/item-catalog-info-r16/catalog.json'
CATALOG = ROOT / 'tools/data' / ('item_icon_catalog_nemc_' + VERSION + '.json')
OUTPUT = ROOT / 'tools/data' / ('intrinsic_glint_census_nemc_' + VERSION + '.json')
GLINT_COMPONENTS = ('minecraft:foil', 'minecraft:glint')


def source(path, data_root):
    raw = path.read_bytes()
    return {'path': path.relative_to(data_root).as_posix(),
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def walk(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield path + (key,), item
            for row in walk(item, path + (key,)):
                yield row
    elif isinstance(value, list):
        for index, item in enumerate(value):
            for row in walk(item, path + (index,)):
                yield row


def scan_item_definitions(data_root):
    definitions, components = [], []
    for kind in ('behavior_packs', 'resource_packs'):
        for path in sorted((data_root / kind).glob('*/items/*.json')):
            value = read_json(path).get('minecraft:item')
            if not isinstance(value, dict):
                continue
            record = source(path, data_root)
            record['identifier'] = value.get('description', {}).get('identifier')
            definitions.append(record)
            for component, rule in value.get('components', {}).items():
                if component not in GLINT_COMPONENTS:
                    continue
                components.append(dict(record, component=component, value=rule,
                                       scope='item_definition'))
    return definitions, components


def scan_render_rules(data_root):
    """Collect every render branch mentioning glint, including conditional ones."""
    relevant, scanned = [], []
    roots = [data_root / 'definitions']
    roots.extend(sorted((data_root / 'resource_packs').iterdir()))
    for pack in roots:
        for folder in ('attachables', 'entity', 'render_controllers', 'materials'):
            directory = pack / folder
            if not directory.is_dir():
                continue
            for path in sorted(directory.rglob('*')):
                if not path.is_file() or path.suffix not in ('.json', '.material'):
                    continue
                record = source(path, data_root)
                scanned.append(record)
                raw = path.read_text(encoding='utf-8-sig')
                if not any(token in raw.lower() for token in ('glint', 'is_enchanted', 'minecraft:foil')):
                    continue
                value = read_json(path)
                entries = [{'path': list(key), 'value': item} for key, item in walk(value)
                           if isinstance(item, (str, bool)) and
                           (any(token in str(key[-1]).lower() for token in
                                ('glint', 'enchanted', 'foil')) or
                            isinstance(item, str) and any(token in item.lower() for token in
                                                         ('glint', 'is_enchanted')))]
                description = (value.get('minecraft:attachable') or
                               value.get('minecraft:client_entity') or {}).get('description', {})
                relevant.append(dict(record, asset_scope=folder,
                                     identifier=description.get('identifier'), entries=entries,
                                     inference='render_branch_not_an_intrinsic_item_rule'))
    return scanned, relevant


def build(install, basic_path, catalog_path):
    basic, catalog = read_json(basic_path), read_json(catalog_path)
    if (basic.get('engine_version') != VERSION or not basic.get('completed') or
            catalog.get('engine_version') != VERSION):
        raise ValueError('Exact-version complete native basic information is required')
    basic_sha = hashlib.sha256(basic_path.read_bytes()).hexdigest()
    basic_semantic_sha = hashlib.sha256((json.dumps(basic, indent=2, ensure_ascii=True) + '\n').encode('ascii')).hexdigest()
    if catalog.get('source_basic_catalog_sha256') != basic_semantic_sha:
        raise ValueError('The measured item catalog does not bind the supplied basic census')
    data_root = install / 'data'
    definitions, explicit = scan_item_definitions(data_root)
    scanned, render_rules = scan_render_rules(data_root)
    by_name, rules_by_name = defaultdict(list), defaultdict(list)
    for row in definitions:
        by_name[row['identifier']].append(row['path'])
    for row in explicit:
        rules_by_name[row['identifier']].append(row)
    flat_pairs = Counter(row['name'] for row in catalog['items'])
    rows = []
    for item in sorted(basic['rows'], key=lambda value: value['name']):
        name = item['name']
        rules = rules_by_name[name]
        boolean_rules = set(row['value'] for row in rules if isinstance(row['value'], bool))
        if len(boolean_rules) == 1:
            status = 'public_definition_true' if True in boolean_rules else 'public_definition_false'
        elif rules:
            status = 'public_rule_requires_resolution'
        else:
            status = 'native_item_rule_unresolved'
        rows.append({'name': name, 'native_aux': item['aux'],
                     'native_basic_info_available': isinstance(item['value'], dict),
                     'flat_icon_candidate_pairs': flat_pairs[name],
                     'item_definition_sources': by_name[name],
                     'public_glint_rules': rules, 'classification': status,
                     'visual_qualification': False})
    loaded = {row['name'] for row in rows}
    return {'schema': 1, 'engine_version': VERSION,
            'minecraft_version': '1.21.130.0', 'production_qualified': False,
            'full_intrinsic_glint_census_complete': False,
            'coverage': {'loaded_ids': len(loaded), 'rows': len(rows),
                         'item_definition_files': len(definitions),
                         'render_source_files': len(scanned),
                         'public_component_rules': len(explicit),
                         'classifications': dict(sorted(Counter(row['classification'] for row in rows).items()))},
            'limitations': [
                'Missing JSON foil/glint components do not mean a native item has no glint.',
                'A glint material or variable.is_enchanted branch does not establish an intrinsic item rule.',
                'A projectile entity using a glint material does not establish the inventory/frame item rule.',
                'Legacy definition identifiers require native alias confirmation before canonical-name application.',
                'Neither public rules nor item dictionary flags qualify actual editor/world pixels.'],
            'inputs': {'basic_catalog_sha256': basic_sha,
                       'basic_catalog_normalized_sha256': basic_semantic_sha,
                       'item_catalog_sha256': hashlib.sha256(catalog_path.read_bytes()).hexdigest()},
            'item_definition_sources': definitions, 'public_component_rules': explicit,
            'public_rules_without_loaded_identifier': [row for row in explicit if row['identifier'] not in loaded],
            'render_source_manifest': scanned, 'render_glint_branches': render_rules,
            'rows': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path, default=INSTALL)
    parser.add_argument('--basic', type=Path, default=BASIC)
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report = build(args.install, args.basic, args.catalog)
    encoded = (json.dumps(report, ensure_ascii=True, indent=2) + '\n').encode('ascii')
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding='ascii') != encoded.decode('ascii'):
            raise SystemExit('Intrinsic glint census does not match its current sources')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(encoded)
    print(json.dumps({'output': str(args.output), **report['coverage']}))
