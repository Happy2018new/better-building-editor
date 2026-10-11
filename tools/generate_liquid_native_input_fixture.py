"""Generate unaccepted native POSITION precision and liquid tile probes."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_liquid_payload_poc import install_overlay, source_snapshot, wrapped_shader
from generate_shulker_proxies import behavior

ROOT = Path(__file__).resolve().parents[1]
CODES = (0, 1, 15, 16, 63, 64, 127, 128, 254, 255)
INPUT_TAG = 39684.
VERTEX = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39684.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    liquidPayloadDecoded = POSITION.xyz + vec3(0.5);
    gl_Position = WORLDVIEWPROJ * vec4(POSITION.xyz, 1.0);
    gl_PointSize = 1.0;
    uv0 = TEXCOORD_0;
    uv1 = vec2(0.0);
    color = vec4(1.0);
    light = vec4(1.0);
    previewClip = -1.0;
    gridPosition = vec2(0.0);
    outlineHue = 0.0;
    renderContext = vec4(0.0);
    #ifdef FOG
    fogColor = vec4(0.0);
    #endif
}
'''
FRAGMENT = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39684.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    gl_FragColor = vec4(fract(liquidPayloadDecoded), 1.0);
}
'''


def identifier(code):
    return 'modern_projection:liquid_native_input_y%03d_r8' % code


def tile_identifier(tile):
    return 'modern_projection:liquid_native_tile_' + tile + '_r8'


def plane(name, top, texture, texture_size, width=8):
    return {'format_version': '1.13.0', 'netease:block_geometry': {
        'description': {'identifier': name, 'textures': [texture],
                        'textures_descriptions': [{'width': texture_size, 'length': texture_size}],
                        'use_ao': False},
        'bones': [{'name': 'payload', 'pivot': [0, 0, 0], 'cubes': [{
            'origin': [-8 - width / 2., top - 1., 8 - width / 2.], 'size': [width, 1, width],
            'uv': {'up': {'uv': [0, 0], 'uv_size': [texture_size, texture_size]}}}]}]}}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output, native):
    if output.exists():
        raise ValueError('Choose a fresh fixture output')
    native_sources = source_snapshot(native)
    blocks, files = {'format_version': [1, 1, 0]}, {}
    for code in CODES:
        name = identifier(code)
        filename = name.split(':')[1] + '.json'
        files['behavior_pack/netease_blocks/' + filename] = behavior(name, 'blend')
        model = plane(name, code / 16., 'modern_projection_shulker_white', 64)
        model['netease:block_geometry']['bones'][0]['cubes'][0]['uv']['up']['uv'] = [16, 0]
        model['netease:block_geometry']['bones'][0]['cubes'][0]['uv']['up']['uv_size'] = [16, 16]
        files['resource_pack/models/netease_block/' + filename] = model
        blocks[name] = {'netease_model': name, 'sound': 'stone'}
    for tile in ('still_water_grey', 'still_lava'):
        name = tile_identifier(tile)
        filename = name.split(':')[1] + '.json'
        files['behavior_pack/netease_blocks/' + filename] = behavior(name, 'blend')
        files['resource_pack/models/netease_block/' + filename] = plane(name, 8., tile, 16, 16)
        blocks[name] = {'netease_model': name, 'sound': 'stone'}
    files['resource_pack/blocks.json'] = blocks
    material = {'vertexShader': 'shaders/glsl/liquid_native_input_r8.vertex',
                'fragmentShader': 'shaders/glsl/liquid_native_input_r8.fragment',
                '+states': ['DisableCulling']}
    files['resource_pack/materials/terrain.material'] = {'materials': {'version': '1.0.0'}}
    for key in ('netease_block_as_mesh_blend:netease_block_as_entity_mesh',
                'netease_block_as_mesh_blend_far:netease_block_as_mesh_blend',
                'netease_block_as_mesh_blend_no_culling:netease_block_as_mesh_blend',
                'netease_block_as_mesh_blend_enable_transparency:netease_block_as_mesh_blend'):
        files['resource_pack/materials/terrain.material']['materials'][key] = deepcopy(material)
    for relative, value in files.items():
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    shaders = output / 'resource_pack/shaders/glsl'
    shaders.mkdir(parents=True)
    source_paths = (ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
                    ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment')
    for source, extension, appended, vertex in ((source_paths[0], 'vertex', VERTEX, True),
                                                 (source_paths[1], 'fragment', FRAGMENT, False)):
        (shaders / ('liquid_native_input_r8.' + extension)).write_text(
            wrapped_shader(source, appended, vertex), encoding='ascii')
    report = dict(native_sources, schema_version=1, codes=CODES, actor_tag=INPUT_TAG,
                  model_top_y_units={str(code): code / 16. for code in CODES},
                  proposed_fractional_height=256,
                  native_input_format_accepted=False, native_geometry_accepted=False,
                  native_pose_accepted=False, accuracy_accepted=False,
                  production_memory_accepted=False,
                  scope='Isolated shader input precision and native tile controls; no inferred liquid rules',
                  fallback_shader_sha256={str(path): digest(path) for path in source_paths})
    report['output_sha256'] = {path.relative_to(output).as_posix(): digest(path)
                               for path in sorted(output.rglob('*')) if path.is_file()}
    (output / 'contract.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--native-data', required=True, type=Path)
    parser.add_argument('--install-project', type=Path)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve())
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({'files': len(report['output_sha256']), 'native_geometry_accepted': False}))


if __name__ == '__main__':
    main()
