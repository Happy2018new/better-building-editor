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
    'native_sign_data', 'native_pot_data', 'native_pot_sherd_data',
    'water_interaction_data', 'plant_proxy_data',
    'static_neighbor_data',
    'native_palette_actor_data',
    'native_entity_write_data',
    'static_bed_data',
    'scaffold_support_data',
    'biome_water_data',
)
SNAPSHOTS = (
    'native_block_metadata', 'native_water_overlays', 'native_snow_overlays',
    'native_paired_snow', 'native_block_entity_defaults',
    'native_entity_appearances', 'native_entity_renderers',
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
    'native_scaffold_supports',
    'native_scaffold_topology',
)


def provenance_matches(label, version, fingerprint, manifest):
    if (version != manifest['game_version'] or not isinstance(fingerprint, str)
            or fingerprint.lower() != manifest['source_sha256'].lower()):
        raise ValueError('%s: observations do not match the current registry' % label)


def module_constants(path):
    selected = {'SOURCE_VERSION', 'SOURCE_SHA256', 'PALETTE_SHA256'}
    result = {}
    for node in ast.parse(path.read_text(encoding='utf8'), filename=str(path)).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in selected:
                    result[target.id] = ast.literal_eval(node.value)
    return result


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
    path = root / 'tools/data/bed_static_model_v1.json'
    data = json.loads(path.read_text(encoding='utf8'))
    provenance_matches('bed_static_model', data.get('game_version'), data.get('palette_sha256'), manifest)
    checked.append(str(path.relative_to(root)))
    path = root / 'tools/data' / ('native_actor_materials_nemc_' + version + '.json')
    check_actor_materials(json.loads(path.read_text(encoding='utf8')), manifest, root=root)
    checked.append(str(path.relative_to(root)))
    from generate_biome_water import validate as validate_water_appearance
    path = root / 'tools/data' / ('biome_water_appearance_nemc_' + version + '.json')
    validate_water_appearance(json.loads(path.read_text(encoding='utf8')), manifest)
    checked.append(str(path.relative_to(root)))
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
        ['tools/generate_liquid_materials.py', '--check'],
        ['tools/generate_native_pot_sherds.py', '--check'],
        ['tools/generate_skull_proxies.py', '--check'],
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
