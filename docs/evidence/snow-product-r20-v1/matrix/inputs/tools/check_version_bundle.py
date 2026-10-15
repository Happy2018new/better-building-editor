"""Check matching native observations and generated assets through one entry point."""
import argparse
import ast
import hashlib
import json
from pathlib import Path, PureWindowsPath
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_native_actor_materials import check as check_actor_materials
from configure_development_runtime import load_target
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
    'liquid_render_target_data',
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
                'FRAME_ITEMS', 'EVIDENCE', 'RUNTIME', 'RESOURCES', 'FROZEN_MODELS',
                'RESOURCE_CONTRACT_SHA256', 'PRODUCTION_QUALIFIED', 'QUALIFICATION_SHA256',
                'QUALIFICATION_RESOURCE_CONTRACT_SHA256', 'FLOWING_TOP_RESOURCES', 'FROZEN_FLOWING_TOP_MODELS'}
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


def check_liquid_deployment(manifest, root=ROOT):
    """Validate checked-in resources without the original installation or runtime bundle."""
    path = root / 'tools/data/liquid_deployment_r12_contract.json'
    payload = path.read_bytes()
    contract = json.loads(payload)
    if type(contract.get('schema')) is not int or contract['schema'] != 1:
        raise ValueError('Liquid deployment resource contract has an unknown schema')
    generated_path = root / 'behavior_pack/modern_projection/projection/liquid_resource_data.py'
    generated = module_constants(generated_path)
    if generated.get('RESOURCE_CONTRACT_SHA256') != hashlib.sha256(payload).hexdigest():
        raise ValueError('Generated liquid deployment differs from its resource contract')
    resources = generated.get('RESOURCES')
    if not isinstance(resources, dict) or resources.get('schema_version') != 2:
        raise ValueError('Generated liquid deployment has an unknown resource schema')
    provenance_matches('liquid_resource_data', resources.get('game_version'),
                       resources.get('palette_sha256'), manifest)
    from generate_liquid_deployment import resource_profile
    if (resources != resource_profile(contract) or
            generated.get('FROZEN_MODELS') != resource_profile(contract, frozen=True)['models']):
        raise ValueError('Generated liquid deployment differs from the current shape and texture sources')
    flow_files = []
    candidate = contract.get('flow_top_candidate')
    if candidate is not None:
        from generate_liquid_flow_top import DEFAULT_SOURCE, validate, runtime_source, digest as flow_digest
        if candidate.get('source_file') != DEFAULT_SOURCE.relative_to(ROOT).as_posix():
            raise ValueError('Liquid flow top needs its versioned relative source file')
        source_file = root / candidate['source_file']
        flow_generator = root / 'tools/generate_liquid_flow_top.py'
        flow_data_file = root / 'behavior_pack/modern_projection/projection/liquid_flow_top_data.py'
        flow_implementation = root / 'behavior_pack/modern_projection/projection/liquid_flow_top.py'
        data = validate(json.loads(source_file.read_bytes()), manifest)
        if (hashlib.sha256(source_file.read_bytes()).hexdigest() != candidate['source_sha256']
                or flow_digest(data) != candidate['candidate_sha256']
                or data['native_source_sha256'] != candidate['native_source_sha256']
                or hashlib.sha256(flow_generator.read_bytes()).hexdigest() != candidate['generator_sha256']
                or hashlib.sha256(flow_implementation.read_bytes()).hexdigest() != candidate['implementation_sha256']
                or flow_data_file.read_text(encoding='ascii') != runtime_source(data)):
            raise ValueError('Liquid flow top source, generator or generated candidate differs')
        if (generated.get('FLOWING_TOP_RESOURCES') != resource_profile(contract, flowing_top=True)
                or generated.get('FROZEN_FLOWING_TOP_MODELS') != resource_profile(contract, True, True)['models']):
            raise ValueError('Generated liquid flow top differs from the current shape and texture sources')
        flow_files = [str(path.relative_to(root)) for path in
                      (source_file, flow_generator, flow_data_file, flow_implementation)]
    generator = root / 'tools/generate_liquid_skeleton_resources.py'
    if hashlib.sha256(generator.read_bytes()).hexdigest() != contract.get('generator_sha256'):
        raise ValueError('Liquid deployment resource generator changed; regenerate the bundle')
    header = root / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'
    headers = [fingerprint for reference, fingerprint in contract.get('source_sha256', {}).items()
               if PureWindowsPath(reference).name == header.name]
    if headers != [hashlib.sha256(header.read_bytes()).hexdigest()]:
        raise ValueError('Liquid deployment preview-depth source differs from its resource bundle')
    models = contract.get('models')
    if not isinstance(models, dict) or not models:
        raise ValueError('Liquid deployment resource bindings are missing')
    installed_models = json.loads((root / 'resource_pack/models/netease_models.json').read_bytes())
    installed_materials = json.loads((root / 'resource_pack/materials/entity.material').read_bytes())['materials']
    for name, expected in models.items():
        if installed_models.get(name) != expected:
            raise ValueError('Installed liquid model binding differs: ' + name)
        option = contract['model_options'][name]
        material = installed_materials.get(expected['material'] + ':entity_for_skeleton_alpha')
        expected_material = {'vertexShader': 'shaders/glsl/' + option['vertex_shader'],
                             'fragmentShader': 'shaders/glsl/' + option['fragment_shader'],
                             '+states': contract['blend_state_contract']['states'],
                             'blendSrc': contract['blend_state_contract']['source'],
                             'blendDst': contract['blend_state_contract']['destination']}
        if material != expected_material:
            raise ValueError('Installed liquid material binding differs: ' + name)
    # Shared registries may contain other modules' entries; independent assets retain exact hashes.
    shared = {'resource_pack/materials/entity.material', 'resource_pack/models/netease_models.json'}
    for relative, fingerprint in contract['output_sha256'].items():
        if relative not in shared and hashlib.sha256((root / relative).read_bytes()).hexdigest() != fingerprint:
            raise ValueError('Installed liquid resource bytes differ: ' + relative)
    if type(generated.get('PRODUCTION_QUALIFIED')) is not bool:
        raise ValueError('Liquid production qualification flag must be explicit')
    if generated['PRODUCTION_QUALIFIED']:
        evidence = generated.get('QUALIFICATION_SHA256')
        if (not isinstance(evidence, str) or len(evidence) != 64 or
                any(value not in '0123456789abcdef' for value in evidence) or
                generated.get('QUALIFICATION_RESOURCE_CONTRACT_SHA256') != generated['RESOURCE_CONTRACT_SHA256']):
            raise ValueError('Liquid production qualification belongs to missing or different resources')
    elif (generated.get('QUALIFICATION_SHA256') is not None or
          generated.get('QUALIFICATION_RESOURCE_CONTRACT_SHA256') is not None):
        raise ValueError('Disabled liquid deployment must retain empty qualification fingerprints')
    return [str(path.relative_to(root)), str(generated_path.relative_to(root)),
            str(generator.relative_to(root)), str(header.relative_to(root))] + flow_files + list(contract['output_sha256'])


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
    checked.extend(check_liquid_deployment(manifest, root=root))
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
    from generate_liquid_product_resources import verify_contract, runtime_source
    path = root / 'tools/data/liquid_product_resource_contract_v1.json'
    verify_contract(json.loads(path.read_bytes()), root, sources=root)
    generated = root / 'behavior_pack/modern_projection/projection/liquid_product_resource_data.py'
    if generated.read_text(encoding='ascii') != runtime_source(path):
        raise ValueError('Generated product water differs from its versioned resources')
    checked.extend((str(path.relative_to(root)), str(generated.relative_to(root))))
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
        ['tools/audit_native_animated_blocks.py', '--check'],
        ['tools/generate_liquid_shapes.py', '--check'],
        ['tools/generate_liquid_flow_top.py', '--check'],
        ['tools/generate_liquid_product_shapes.py', '--check'],
        ['tools/generate_liquid_product_owner_contract.py', '--check'],
        ['tools/generate_item_sprite_resources.py', '--check'],
        ['tools/generate_native_pot_sherds.py', '--check'],
        ['tools/generate_skull_proxies.py', '--check'],
        ['tools/generate_flat_item_proxies.py', '--check'],
        ['tools/check_snow_blueprints.py', '--check'],
        ['tools/generate_static_plant_proxies.py', '--check'],
        ['tools/generate_centered_plant_profiles.py', '--check'],
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
        target = load_target()
        report.update(engine_version=target['engine_version'], resource_version=target['resource_version'],
                      registry_update_deferred=target['block_registry_update_deferred'],
                      transforms_update_deferred=target['transforms_update_deferred'])
        report['checks'].append({'name': 'development_runtime_target', 'passed': True})
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
