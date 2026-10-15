"""Generate a small, unaccepted native liquid visibility discriminator."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_liquid_payload_poc import (ENTITY_CONTROL, FRAGMENT, POSE_BLOCK, VERTEX,
                                         install_overlay, pose_resources, wrapped_shader)
from generate_shulker_proxies import behavior

ROOT = Path(__file__).resolve().parents[1]
DIRECT = 'modern_projection:liquid_visibility_native_shulker_r8'
STATIC = 'modern_projection:liquid_visibility_static_shulker_r8'
POINT = 'modern_projection:liquid_visibility_point_r8'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output, native, mode, static_mode='shulker', plain_entity=False, payload_shader=False):
    if output.exists():
        raise ValueError('Choose a fresh fixture directory')
    sources = {
        'entity': native / 'resource_packs/vanilla/entity/shulker.entity.json',
        'geometry': native / 'resource_packs/vanilla/models/entity/shulker.geo.json',
        'static': ROOT / 'resource_pack/models/netease_block/preview_shulker_white_1.json',
        'entity_behavior': ROOT / 'behavior_pack/entities/modern_projection_anchor.json',
    }
    native_entity = json.loads(sources['entity'].read_bytes())
    block, _, thin = pose_resources()
    native_geometry = json.loads(sources['geometry'].read_bytes())['geometry.shulker.v1.8']
    thin_specification = thin['minecraft:geometry'][0]
    thin_specification['description'].update(texture_width=native_geometry['texturewidth'],
                                             texture_height=native_geometry['textureheight'],
                                             visible_bounds_offset=[0, .5, 0])
    thin_specification['bones'] = [{'name': 'base', 'pivot': [0, 0, 0], 'cubes': [
        {'origin': [-8, 0, -8], 'size': [16, 1, 16], 'uv': [0, 0]}]}]
    entity = deepcopy(native_entity)
    description = entity['minecraft:client_entity']['description']
    description['identifier'] = POSE_BLOCK
    if plain_entity:
        for key in ('animations', 'animation_controllers', 'scripts', 'spawn_egg'):
            description.pop(key, None)
        description['materials'] = {'default': 'entity_alphatest'}
        description['textures'] = {'default': 'textures/blocks/preview_shulker_white_closed'}
        description['render_controllers'] = ['controller.render.modern_projection.anchor']
    if mode == 'thin':
        description['geometry']['default'] = thin['minecraft:geometry'][0]['description']['identifier']
    elif mode == 'legacy-thin':
        description['geometry']['default'] = 'geometry.modern_projection.liquid_payload_pose_poc'
    elif mode != 'shulker':
        raise ValueError('Unknown fixture geometry mode')
    entity_behavior = json.loads(sources['entity_behavior'].read_bytes())
    entity_behavior['minecraft:entity']['description']['identifier'] = POSE_BLOCK
    control = deepcopy(entity)
    control['minecraft:client_entity']['description']['identifier'] = ENTITY_CONTROL
    control['minecraft:client_entity']['description']['geometry']['default'] = 'geometry.shulker.v1.8'
    control_behavior = deepcopy(entity_behavior)
    control_behavior['minecraft:entity']['description']['identifier'] = ENTITY_CONTROL
    direct_behavior = deepcopy(block)
    direct_behavior['minecraft:block']['description']['identifier'] = DIRECT
    static_model = json.loads(sources['static'].read_bytes())
    static_model['netease:block_geometry']['description']['identifier'] = STATIC
    if static_mode in ('carrier', 'point'):
        top = deepcopy(static_model['netease:block_geometry']['bones'][0]['cubes'][0]['uv']['up'])
        if static_mode == 'point':
            top['uv_size'] = [0, 0]
        static_model['netease:block_geometry']['bones'] = [{
            'name': 'payload', 'pivot': [0, 0, 0], 'cubes': [
                {'origin': [-12, 7, 4], 'size': [8, 1, 8], 'uv': {'up': top}}]}]
    elif static_mode != 'shulker':
        raise ValueError('Unknown static geometry mode')
    blocks = {'format_version': [1, 1, 0]}
    for identifier, client_identifier in ((POSE_BLOCK, POSE_BLOCK), (DIRECT, 'minecraft:shulker')):
        blocks[identifier] = {'sound': 'stone', 'client_entity': {
            'identifier': client_identifier, 'hand_model_use_client_entity': True,
            'block_icon': 'quartz_block_top'}}
    blocks[STATIC] = {'netease_model': STATIC, 'sound': 'stone'}
    files = {
        'behavior_pack/netease_blocks/liquid_payload_pose_poc.json': block,
        'behavior_pack/netease_blocks/liquid_visibility_native_shulker_r8.json': direct_behavior,
        'behavior_pack/netease_blocks/liquid_visibility_static_shulker_r8.json': behavior(STATIC, 'blend'),
        'behavior_pack/entities/liquid_payload_pose_poc.json': entity_behavior,
        'behavior_pack/entities/liquid_payload_entity_control_poc.json': control_behavior,
        'resource_pack/entity/liquid_payload_pose_poc.entity.json': entity,
        'resource_pack/entity/liquid_payload_entity_control_poc.entity.json': control,
        'resource_pack/models/netease_block/liquid_visibility_static_shulker_r8.json': static_model,
        'resource_pack/blocks.json': blocks,
    }
    if static_mode == 'carrier':
        point_model = deepcopy(static_model)
        point_model['netease:block_geometry']['description']['identifier'] = POINT
        point_model['netease:block_geometry']['bones'][0]['cubes'][0]['uv']['up']['uv_size'] = [0, 0]
        files['behavior_pack/netease_blocks/liquid_visibility_point_r8.json'] = behavior(POINT, 'blend')
        files['resource_pack/models/netease_block/liquid_visibility_point_r8.json'] = point_model
        blocks[POINT] = {'netease_model': POINT, 'sound': 'stone'}
    if payload_shader:
        material = {'vertexShader': 'shaders/glsl/liquid_payload_poc.vertex',
                    'fragmentShader': 'shaders/glsl/liquid_payload_poc.fragment',
                    '+states': ['DisableCulling']}
        files['resource_pack/materials/terrain.material'] = {'materials': {
            'version': '1.0.0',
            'netease_block_as_mesh_blend:netease_block_as_entity_mesh': deepcopy(material),
            'netease_block_as_mesh_blend_far:netease_block_as_mesh_blend': deepcopy(material),
            'netease_block_as_mesh_blend_no_culling:netease_block_as_mesh_blend': deepcopy(material),
            'netease_block_as_mesh_blend_enable_transparency:netease_block_as_mesh_blend': deepcopy(material),
        }}
    if mode == 'thin':
        files['resource_pack/models/entity/liquid_payload_pose_poc.geo.json'] = thin
    elif mode == 'legacy-thin':
        specification = deepcopy(thin['minecraft:geometry'][0])
        geometry_description = specification.pop('description')
        specification.update(texturewidth=geometry_description['texture_width'],
                             textureheight=geometry_description['texture_height'],
                             visible_bounds_width=geometry_description['visible_bounds_width'],
                             visible_bounds_height=geometry_description['visible_bounds_height'])
        specification['bones'][0]['cubes'][0]['uv'] = [0, 0]
        files['resource_pack/models/entity/liquid_payload_pose_poc.geo.json'] = {
            'format_version': '1.8.0', geometry_description['identifier']: specification}
    for relative, value in files.items():
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    if payload_shader:
        shaders = output / 'resource_pack/shaders/glsl'
        shaders.mkdir(parents=True, exist_ok=True)
        (shaders / 'liquid_payload_poc.vertex').write_text(wrapped_shader(
            ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex', VERTEX, True), encoding='ascii')
        (shaders / 'liquid_payload_poc.fragment').write_text(wrapped_shader(
            ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment', FRAGMENT), encoding='ascii')
    report = {
        'schema_version': 1, 'mode': mode, 'static_mode': static_mode, 'plain_entity': plain_entity,
        'payload_shader': payload_shader,
        'scope': 'Isolated visibility registration discriminator; no liquid backend acceptance',
        'source_sha256': {key: {'path': str(path.resolve()), 'sha256': digest(path)}
                          for key, path in sources.items()},
        'output_sha256': {path.relative_to(output).as_posix(): digest(path)
                          for path in sorted(output.rglob('*')) if path.is_file()},
        'native_geometry_accepted': False, 'native_pose_accepted': False,
        'accuracy_accepted': False, 'animated_sampling_accepted': False,
        'production_memory_accepted': False,
    }
    (output / 'contract.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    return report


def restore(project, backup):
    report = json.loads((backup / 'installation.json').read_bytes())
    if project.resolve() != Path(report['project']).resolve():
        raise ValueError('Backup belongs to a different project')
    for relative, expected in report['installed_sha256'].items():
        if digest(project / relative) != expected:
            raise ValueError('An installed fixture changed; refusing restoration: ' + relative)
    for relative in report['installed_sha256']:
        original, target = backup / relative, project / relative
        if original.exists():
            target.write_bytes(original.read_bytes())
        else:
            target.unlink()
    return {'restored': True, 'files': len(report['installed_sha256'])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--native-data', type=Path)
    parser.add_argument('--mode', choices=('shulker', 'thin', 'legacy-thin'), default='shulker')
    parser.add_argument('--static-mode', choices=('shulker', 'carrier', 'point'), default='shulker')
    parser.add_argument('--plain-entity', action='store_true')
    parser.add_argument('--payload-shader', action='store_true')
    parser.add_argument('--install-project', type=Path)
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    if args.restore:
        if not args.install_project or not args.backup:
            parser.error('Restoration requires --install-project and --backup')
        print(json.dumps(restore(args.install_project, args.backup)))
        return
    if not args.output or not args.native_data:
        parser.error('Generation requires --output and --native-data')
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve(), args.mode,
                      args.static_mode, args.plain_entity, args.payload_shader)
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({'mode': report['mode'], 'files': len(report['output_sha256']),
                      'native_geometry_accepted': False}))


if __name__ == '__main__':
    main()
