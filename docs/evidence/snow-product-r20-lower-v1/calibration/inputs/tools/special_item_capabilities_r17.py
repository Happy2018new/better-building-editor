"""Audit exact-version special item sources without granting render support.

Item texture observations are pair-specific. A rejected auxiliary value must
not turn an identifier with valid flat-icon observations into a missing family.
Held attachables are asset evidence, not proof of an item-frame model or pose.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from audit_native_nbt_inventory import read_json

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VERSION = '3.10.0.420447'
SCHEMA_VERSION = 1
DEFAULT_INSTALL = Path('D:/MCStudioDownload/game/MinecraftPE_Netease') / ENGINE_VERSION
DEFAULT_OUTPUT = ROOT / 'tools/data' / ('special_item_capabilities_nemc_' + ENGINE_VERSION + '.json')
PACKS = ('vanilla', 'vanilla_base', 'vanilla_netease')
SPECIAL_REASONS = frozenset(('patterned_geometry', 'special_geometry', 'map_surface', 'content_geometry'))
SKULL_NAMES = frozenset(('minecraft:skull', 'minecraft:skeleton_skull', 'minecraft:wither_skeleton_skull',
                        'minecraft:zombie_head', 'minecraft:player_head', 'minecraft:creeper_head',
                        'minecraft:dragon_head', 'minecraft:piglin_head'))
HELD_ONLY_NAMES = frozenset(('minecraft:bow', 'minecraft:spyglass', 'minecraft:mace'))
COMMON_GATES = ('authentic_item_userdata_readback', 'native_frame_pose_reference',
                'editor_full_missing_routes', 'section_layers_occupancy_restore',
                'zoom_side_silhouette_and_lighting', 'resource_bound_pixel_qualification')


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_record(path, base):
    return {'path': path.relative_to(base).as_posix(), 'sha256': sha256(path)}


def _validate_catalog(catalog):
    if catalog.get('schema') != 1 or catalog.get('engine_version') != ENGINE_VERSION:
        raise ValueError('Special item census requires the exact measured engine catalog')
    if not isinstance(catalog.get('items'), list) or not isinstance(catalog.get('unsupported'), dict):
        raise ValueError('Measured catalog items and rejection reasons are required')
    pairs = [(row['name'], row['aux']) for row in catalog['items']]
    if len(pairs) != len(set(pairs)):
        raise ValueError('Measured flat item catalog has duplicate identifier/aux pairs')


def item_pair_census(catalog):
    """Keep auxiliary-specific positive observations and legacy rejections apart."""
    _validate_catalog(catalog)
    accepted = defaultdict(set)
    for row in catalog['items']:
        accepted[row['name']].add(row['aux'])
    rejected = catalog['unsupported']
    names = sorted(set(accepted) | set(rejected))
    rows = [{'name': name, 'accepted_flat_aux': sorted(accepted.get(name, ())),
             'rejection_reason_for_at_least_one_probe': rejected.get(name),
             'fully_absent_from_flat_candidates': not bool(accepted.get(name))} for name in names]
    return {'rows': rows, 'loaded_ids': catalog.get('loaded_vanilla_ids'),
            'accepted_flat_ids': len(accepted), 'accepted_flat_pairs': len(catalog['items']),
            'legacy_rejection_ids': len(rejected),
            'legacy_rejection_ids_with_flat_pairs': len(set(accepted) & set(rejected)),
            'legacy_rejection_ids_without_flat_pairs': len(set(rejected) - set(accepted)),
            'rejection_semantics': 'at_least_one_rejected_probe_not_whole_identifier',
            'flat_support_semantics': 'unqualified_candidate_not_production_support'}


def _sources(packs, relative):
    return [packs / pack / relative for pack in PACKS if (packs / pack / relative).is_file()]


def _definition_sources(packs, folder, root_key):
    definitions = defaultdict(list)
    for pack in PACKS:
        directory = packs / pack / folder
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob('*.json')):
            data = read_json(path).get(root_key)
            if not isinstance(data, dict):
                continue
            description = data.get('description', {})
            name = description.get('identifier')
            if isinstance(name, str) and name.startswith('minecraft:'):
                definitions[name].append((path, description))
    return definitions


def _geometry_sources(packs):
    geometries = defaultdict(list)
    for pack in PACKS:
        directory = packs / pack / 'models/entity'
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob('*.json')):
            data = read_json(path)
            for geometry in data.get('minecraft:geometry', ()):
                description = geometry.get('description', {})
                name = description.get('identifier')
                if isinstance(name, str):
                    geometries[name].append((path, geometry))
            # Legacy Bedrock geometry keeps the identifier as the root key.
            for name, geometry in data.items():
                if name.startswith('geometry.') and isinstance(geometry, dict):
                    geometries[name].append((path, geometry))
    return geometries


def _geometry_record(path, geometry, packs):
    bones = geometry.get('bones', ())
    description = geometry.get('description', geometry)
    result = source_record(path, packs)
    result.update(texture_size=[description.get('texture_width'), description.get('texture_height')],
                  bone_count=len(bones), cube_count=sum(len(bone.get('cubes', ())) for bone in bones),
                  has_engine_bone_binding=any('binding' in bone for bone in bones),
                  has_parent_bones=any('parent' in bone for bone in bones),
                  has_static_rotation=any('rotation' in bone or any('rotation' in cube for cube in
                                          bone.get('cubes', ())) for bone in bones),
                  qualification='source_only_not_frame_geometry')
    return result


def _definition_record(path, description, geometries, packs):
    result = source_record(path, packs)
    result['materials'] = description.get('materials', {})
    result['textures'] = description.get('textures', {})
    result['geometry'] = description.get('geometry', {})
    result['render_controllers'] = description.get('render_controllers', ())
    result['animations'] = description.get('animations', {})
    result['dynamic_atlas_dependencies'] = sorted(set(value for value in result['textures'].values()
                                                     if isinstance(value, str) and value.startswith('atlas.')))
    result['geometry_sources'] = {
        key: [_geometry_record(asset, geometry, packs) for asset, geometry in geometries.get(value, ())]
        for key, value in result['geometry'].items()}
    result['texture_sources'] = {
        key: [source_record(asset, packs) for suffix in ('.png', '.tga') for asset in
              _sources(packs, value + suffix)]
        for key, value in result['textures'].items()
        if isinstance(value, str) and value.startswith('textures/')}
    return result


def _extra_assets(name, packs):
    relatives = []
    if name == 'minecraft:shield':
        relatives += ['render_controllers/shield.render_controllers.json', 'materials/entity.material']
        directory = packs / 'vanilla/textures/entity/shield_patterns'
        if directory.is_dir():
            relatives += [path.relative_to(packs / 'vanilla').as_posix()
                          for path in sorted(directory.glob('*.png'))]
    if name in ('minecraft:filled_map', 'minecraft:empty_map'):
        relatives += ['textures/map/map_background.png', 'textures/map/map_icons.png']
    if name == 'minecraft:crossbow':
        relatives += ['models/entity/crossbow.geo.json', 'render_controllers/crossbow.render_controllers.json',
                      'animations/crossbow.animation.json']
    if name == 'minecraft:trident':
        relatives += ['models/entity/trident.geo.json', 'animations/trident.animation.json']
    return [source_record(path, packs) for relative in relatives for path in _sources(packs, relative)]


def family_plan(name, legacy_reason, has_flat_pairs):
    """Plans deliberately leave schema and pose unknown until physical readback."""
    family, route, blockers = 'held_model_uncertain', 'existing_flat_candidate_then_native_reference', []
    if name in SKULL_NAMES:
        family, route = 'skull_block_item', 'reuse_versioned_head_block_item_adapter'
        blockers = ['actual_item_to_head_variant_mapping', 'player_skin_source_and_frame_pose']
    elif name == 'minecraft:filled_map':
        family, route = 'filled_map', 'native_map_surface_if_pixel_source_is_available'
        blockers = ['map_pixel_source_not_in_static_item_icon', 'cross_world_map_data_reference',
                    'authentic_map_frame_userdata_and_surface_pose']
    elif name == 'minecraft:empty_map':
        family, route = 'empty_map', 'static_flat_icon_after_native_empty_map_reference'
        blockers = ['no_filled_map_surface_assumption']
    elif name == 'minecraft:banner':
        family, route = 'patterned_banner_item', 'reuse_qualified_banner_body_with_separate_frame_pose'
        blockers = ['authentic_banner_item_userdata', 'item_geometry_not_standing_block_assumption']
    elif name == 'minecraft:shield':
        family, route = 'patterned_shield', 'source_geometry_and_native_pattern_atlas_candidate'
        blockers = ['authentic_shield_pattern_userdata', 'native_atlas_shield_binding',
                    'pattern_material_contract', 'native_frame_model_and_pose']
    elif name == 'minecraft:crossbow':
        family, route = 'content_crossbow', 'flat_icon_or_source_geometry_selected_by_native_frame_evidence'
        blockers = ['loaded_projectile_item_userdata', 'native_charged_frame_appearance']
    elif name == 'minecraft:trident' or name.endswith('_spear'):
        family, route = 'weapon_special_model', 'source_geometry_only_if_native_frame_reference_requires_it'
        blockers = ['held_model_does_not_establish_frame_model']
    elif name.endswith('_harness'):
        family, route = 'harness_special_model', 'flat_icon_or_source_geometry_selected_by_native_frame_evidence'
        blockers = ['worn_model_does_not_establish_frame_model']
    return {'family': family, 'candidate_route': route, 'blocking_evidence': blockers,
            'has_existing_flat_candidates': has_flat_pairs, 'legacy_reason': legacy_reason,
            'production_qualified': False, 'qualification': 'offline_asset_evidence_only',
            'required_gates': list(COMMON_GATES)}


def build(catalog, install):
    census = item_pair_census(catalog)
    if install.name != ENGINE_VERSION:
        raise ValueError('Installed assets must come from the measured engine version directory')
    packs = install / 'data/resource_packs'
    if not packs.is_dir():
        raise ValueError('Installed exact-version resource packs are missing')
    attachables = _definition_sources(packs, 'attachables', 'minecraft:attachable')
    entities = _definition_sources(packs, 'entity', 'minecraft:client_entity')
    geometries = _geometry_sources(packs)
    by_name = {row['name']: row for row in census['rows']}
    names = sorted({name for name, reason in catalog['unsupported'].items() if reason in SPECIAL_REASONS} |
                   (SKULL_NAMES & set(by_name)) | (HELD_ONLY_NAMES & set(by_name)))
    rows = []
    for name in names:
        measured = by_name[name]
        row = dict(measured, **family_plan(name, measured['rejection_reason_for_at_least_one_probe'],
                                         bool(measured['accepted_flat_aux'])))
        row['attachable_sources'] = [_definition_record(path, description, geometries, packs)
                                     for path, description in attachables.get(name, ())]
        if name in SKULL_NAMES:
            row['native_head_sources'] = [_definition_record(path, description, geometries, packs)
                                         for path, description in entities.get('minecraft:skull', ())]
        row['additional_source_assets'] = _extra_assets(name, packs)
        rows.append(row)
    return {'schema': SCHEMA_VERSION, 'engine_version': ENGINE_VERSION,
            'source_lookup_semantics': 'all_matching_installed_sources_not_assumed_pack_priority',
            'production_qualified': False, 'pair_census': census,
            'special_family_counts': dict(sorted(Counter(row['family'] for row in rows).items())),
            'rows': rows,
            'limitations': ['texture_presence_is_not_native_render_support',
                            'held_or_worn_attachable_is_not_frame_geometry_or_pose',
                            'dynamic_atlas_is_not_a_static_bitmap',
                            'map_background_is_not_world_map_pixels',
                            'item_userdata_schema_requires_authentic_physical_readback']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'tools/data' /
                        ('item_icon_catalog_nemc_' + ENGINE_VERSION + '.json'))
    parser.add_argument('--install', type=Path, default=DEFAULT_INSTALL)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    report = build(read_json(args.catalog), args.install)
    report['source_catalog'] = source_record(args.catalog, ROOT)
    payload = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode('ascii')
    if args.check:
        if not args.output.is_file() or args.output.read_bytes() != payload:
            raise SystemExit('Special-item capability census needs exact-version regeneration')
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(payload)
    print(json.dumps({'output': str(args.output), 'special_ids': len(report['rows']),
                      'overlapping_rejection_ids': report['pair_census']['legacy_rejection_ids_with_flat_pairs'],
                      'families': report['special_family_counts'], 'production_qualified': False}))


if __name__ == '__main__':
    main()
