"""Check matching native observations and generated assets through one entry point."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_native_actor_materials import check as check_actor_materials
MODULES = (
    'block_registry_data', 'block_traits_data', 'entity_defaults_data',
    'appearance_defaults_data', 'frame_rotation_data', 'native_appearance',
    'item_contents_data',
    'native_sign_data', 'native_pot_data', 'native_pot_sherd_data',
    'water_interaction_data', 'plant_proxy_data',
    'static_neighbor_data', 'rail_neighbor_data',
    'native_palette_actor_data',
    'native_entity_write_data',
    'static_bed_data',
    'static_skull_data',
    'static_chest_data',
    'static_shulker_data',
    'scaffold_support_data',
    'biome_water_data',
    'liquid_face_texture_data',
    'liquid_shape_data',
    'static_frame_item_data',
)
SNAPSHOTS = (
    'native_block_metadata', 'native_water_overlays', 'native_snow_overlays',
    'native_paired_snow', 'native_block_entity_defaults',
    'native_entity_appearances', 'native_entity_renderers',
    'native_item_contents',
    'native_frame_rotations', 'native_signs', 'native_pot_poses', 'native_pot_sherds', 'native_pot_faces',
    'native_water_item_use', 'native_water_extinguish', 'native_water_source_stability',
    'native_water_flow_spread',
    'native_snow_states', 'static_plant_sources',
    'native_static_neighbors',
    'native_palette_actors',
    'native_bed_capture',
    'native_liquid_materials',
    'native_liquid_geometry_support',
    'native_entity_writes',
    'native_dripstone_holdout',
    'native_liquid_surface_diagnostics',
    'native_liquid_shape_candidate',
    'native_liquid_neighbor_shape',
    'native_liquid_alias_observations',
    'native_liquid_face_textures',
    'native_scaffold_supports',
    'native_scaffold_topology',
    'flat_item_sources',
)


def provenance_matches(label, version, fingerprint, manifest):
    if (version != manifest['game_version'] or not isinstance(fingerprint, str)
            or fingerprint.lower() != manifest['source_sha256'].lower()):
        raise ValueError('%s: observations do not match the current registry' % label)


def module_constants(path):
    selected = {'SOURCE_VERSION', 'SOURCE_SHA256', 'PALETTE_SHA256', 'SCHEMA_VERSION',
                'FRAME_ITEMS', 'EVIDENCE', 'RUNTIME'}
    result = {}
    for node in ast.parse(path.read_text(encoding='utf8'), filename=str(path)).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in selected:
                    result[target.id] = ast.literal_eval(node.value)
    return result


def check_rail_provenance(manifest, root=ROOT):
    path = root / 'behavior_pack/modern_projection/projection/rail_neighbor_data.py'
    values = module_constants(path)
    if type(values.get('SCHEMA_VERSION')) is not int or values['SCHEMA_VERSION'] != 1:
        raise ValueError('Native rail source table has an unknown schema')
    provenance_matches('rail_neighbor_data', values.get('SOURCE_VERSION'),
                       values.get('PALETTE_SHA256'), manifest)
    version = manifest['game_version'].removeprefix('NEMC ')
    filenames = tuple(name + '_nemc_' + version + '.json' for name in
                      ('native_neighbor_actions_r11', 'native_neighbor_actions_r11_axes'))
    evidence = values.get('EVIDENCE')
    if (not isinstance(evidence, (tuple, list)) or len(evidence) != len(filenames) or
            any(not isinstance(row, (tuple, list)) or len(row) != 2 for row in evidence) or
            tuple(row[0] for row in evidence) != filenames or
            not isinstance(values.get('RUNTIME'), str) or not values['RUNTIME']):
        raise ValueError('Native rail source table differs from its declared frozen evidence')
    checked = []
    for filename, fingerprint in evidence:
        path = root / 'tools/data' / filename
        payload = path.read_bytes()
        if (not isinstance(fingerprint, str) or len(fingerprint) != 64 or
                hashlib.sha256(payload).hexdigest() != fingerprint.lower()):
            raise ValueError('Native rail original evidence bytes changed: ' + filename)
        data = json.loads(payload)
        if not isinstance(data, dict) or type(data.get('schema')) is not int or data['schema'] != 1:
            raise ValueError('Native rail evidence has an unknown schema: ' + filename)
        provenance_matches(filename, data.get('game_version'), data.get('palette_sha256'), manifest)
        start, native, cleanup = (data.get(key, {}) for key in ('start', 'native', 'cleanup'))
        if not all(isinstance(value, dict) for value in (start, native, cleanup)):
            raise ValueError('Native rail evidence has malformed capture metadata: ' + filename)
        provenance_matches(filename + ' start', start.get('game_version'), start.get('palette_sha256'), manifest)
        plans, rows = data.get('plans'), native.get('rows')
        if (data.get('completed') is not True or data.get('restored') is not True or
                data.get('error') or data.get('cleanup_error') or cleanup.get('restored') is not True or
                native.get('done') is not True or native.get('error') or
                start.get('runtime') != values['RUNTIME'] or
                not isinstance(plans, list) or not plans or not isinstance(rows, list) or
                start.get('cases') != len(plans) or native.get('case') != len(plans)):
            raise ValueError('Native rail evidence is incomplete, unrestored or has a mismatching runtime: ' + filename)
        if (any(not isinstance(plan, dict) or not isinstance(plan.get('id'), str) or
                not isinstance(plan.get('actions'), list) or not plan['actions'] or
                any(not isinstance(action, (tuple, list)) or len(action) != 2 or
                    not isinstance(action[0], str) for action in plan['actions']) for plan in plans) or
                any(not isinstance(row, dict) for row in rows)):
            raise ValueError('Native rail evidence has malformed action coverage: ' + filename)
        expected = [(plan['id'], action[0]) for plan in plans for action in plan['actions']]
        if [(row.get('case'), row.get('action')) for row in rows] != expected:
            raise ValueError('Native rail evidence did not complete its declared action coverage: ' + filename)
        checked.append(str(path.relative_to(root)))
    return checked


def check_provenance(root=ROOT):
    manifest = json.loads((root / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    source = root / manifest['source_file']
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual != manifest['source_sha256'].lower():
        raise ValueError('Native source dump does not match its manifest SHA-256')
    version = manifest['game_version'].removeprefix('NEMC ')
    if version == manifest['game_version'] or not version:
        raise ValueError('Expected a versioned NEMC source manifest')
    checked = [str(source.relative_to(root))]
    for name in MODULES:
        path = root / 'behavior_pack/modern_projection/projection' / (name + '.py')
        values = module_constants(path)
        fingerprint = values.get('PALETTE_SHA256', values.get('SOURCE_SHA256'))
        provenance_matches(name, values.get('SOURCE_VERSION'), fingerprint, manifest)
        checked.append(str(path.relative_to(root)))
    for name in SNAPSHOTS:
        path = root / 'tools/data' / (name + '_nemc_' + version + '.json')
        data = json.loads(path.read_text(encoding='utf8'))
        provenance_matches(name, data.get('game_version'), data.get('palette_sha256'), manifest)
        checked.append(str(path.relative_to(root)))
    checked.extend(check_rail_provenance(manifest, root=root))
    path = root / 'tools/data/bed_static_model_v1.json'
    data = json.loads(path.read_text(encoding='utf8'))
    provenance_matches('bed_static_model', data.get('game_version'), data.get('palette_sha256'), manifest)
    checked.append(str(path.relative_to(root)))
    for name in ('copper_chest_static_model_v1', 'shulker_static_model_v1', 'skull_static_model_v1'):
        path = root / 'tools/data' / (name + '.json')
        data = json.loads(path.read_text(encoding='utf8'))
        provenance_matches(name, data.get('game_version'), data.get('palette_sha256'), manifest)
        checked.append(str(path.relative_to(root)))
    path = root / 'tools/data' / ('native_actor_materials_nemc_' + version + '.json')
    check_actor_materials(json.loads(path.read_text(encoding='utf8')), manifest, root=root)
    checked.append(str(path.relative_to(root)))
    from generate_biome_water import validate as validate_water_appearance
    path = root / 'tools/data' / ('biome_water_appearance_nemc_' + version + '.json')
    validate_water_appearance(json.loads(path.read_text(encoding='utf8')), manifest)
    checked.append(str(path.relative_to(root)))
    from generate_flat_item_proxies import source_path as flat_source_path, validate_source as validate_flat_items, profile_table
    path = flat_source_path(root)
    data = json.loads(path.read_text(encoding='utf8'))
    validate_flat_items(data, manifest)
    generated = module_constants(root / 'behavior_pack/modern_projection/projection/static_frame_item_data.py')
    expected_hash = hashlib.sha256(json.dumps(data, sort_keys=True).encode('utf8')).hexdigest()
    if (generated.get('SCHEMA_VERSION') != 1 or generated.get('SOURCE_SHA256') != expected_hash or
            generated.get('FRAME_ITEMS') != profile_table(data)):
        raise ValueError('Generated flat frame item profiles do not match the current versioned resources')
    from generate_native_item_contents import validate as validate_items, runtime as item_runtime
    path = root / 'tools/data' / ('native_item_contents_nemc_' + version + '.json')
    data = validate_items(json.loads(path.read_bytes()), root=root)
    path = root / 'behavior_pack/modern_projection/projection/item_contents_data.py'
    if path.read_text(encoding='ascii') != item_runtime(data, root=root):
        raise ValueError('Generated native item controls differ from independent raw source evidence')
    checked.extend((data['source_report_file'], data['source_session_manifest_file']))
    session = json.loads((root / data['source_session_manifest_file']).read_bytes())
    checked.append(session['startup_log']['file'])
    return manifest, checked


def commands(manifest, tests=False):
    version = manifest['game_version'].removeprefix('NEMC ')
    rows = [
        ['tools/check_block_registry.py', manifest['source_file']],
        ['tools/generate_block_traits.py', 'tools/data/native_block_metadata_nemc_' + version + '.json', '--check'],
        ['tools/generate_entity_blueprints.py', 'tools/data/native_block_entity_defaults_nemc_' + version + '.json', '--check'],
        ['tools/generate_shulker_proxies.py', '--check'],
        ['tools/generate_copper_chest_proxies.py', '--check'],
        ['tools/generate_water_interactions.py', '--check'],
        ['tools/generate_static_neighbor_rules.py', '--check'],
        ['tools/generate_native_palette_adapter.py', '--check'],
        ['tools/generate_native_entity_writes.py', '--check'],
        ['tools/generate_native_item_contents.py', '--check'],
        ['tools/generate_liquid_materials.py', '--check'],
        ['tools/generate_liquid_face_textures.py', '--check'],
        ['tools/generate_liquid_shapes.py', '--check'],
        ['tools/generate_native_pot_sherds.py', '--check'],
        ['tools/generate_skull_proxies.py', '--check'],
        ['tools/generate_flat_item_proxies.py', '--check'],
        ['tools/check_snow_blueprints.py', '--check'],
        ['tools/generate_static_plant_proxies.py', '--check'],
        ['tools/generate_bed_proxies.py', '--check'],
        ['tools/generate_scaffold_support.py', '--check'],
        ['tools/generate_biome_water.py', '--source',
         'tools/data/biome_water_appearance_nemc_' + version + '.json', '--check'],
    ]
    if tests:
        rows.append(['-m', 'unittest', 'discover', '-s', 'tests', '-q'])
    return [[sys.executable, '-X', 'utf8'] + row for row in rows]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--provenance-only', action='store_true')
    parser.add_argument('--tests', action='store_true', help='Also run the complete offline test suite')
    parser.add_argument('--output', type=Path, help='Write the structured check report')
    args = parser.parse_args()
    report = {'schema_version': 1, 'passed': False, 'checks': [],
              'scope': 'Offline version consistency and generated assets; visual acceptance is separate.'}
    try:
        manifest, checked = check_provenance()
        report.update(game_version=manifest['game_version'], registry_sha256=manifest['source_sha256'], files=checked)
        report['checks'].append({'name': 'provenance', 'passed': True, 'files': len(checked)})
        if not args.provenance_only:
            for command in commands(manifest, args.tests):
                result = subprocess.run(command, cwd=ROOT, check=False)
                report['checks'].append({'command': command[3:], 'passed': result.returncode == 0,
                                         'exit_code': result.returncode})
        report['passed'] = all(row['passed'] for row in report['checks'])
    except (OSError, ValueError, SyntaxError) as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    if args.output:
        args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
