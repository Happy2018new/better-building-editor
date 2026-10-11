"""Generate a reversible, unaccepted low-Y liquid transport fixture."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_liquid_native_input_fixture import CODES, plane
from generate_liquid_payload_poc import install_overlay, source_snapshot, wrapped_shader, NATIVE_KEYS
from generate_shulker_proxies import behavior

ROOT = Path(__file__).resolve().parents[1]
TAG = 39685.0
VERTEX = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39685.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    vec3 encoded = POSITION.xyz + vec3(0.5);
    vec3 carrier = floor(encoded);
    float u = step(0.5, fract(encoded.x));
    float v = step(0.5, fract(encoded.z));
    float third = floor(fract(encoded.y) * 256.0 + 0.5);
    float kind = EXTRA_ACTOR_UNIFORM4.y;
    vec3 point;
    if (kind < 0.5) {
        if (u < 0.5) point = vec3(0.0, third / 255.0, 0.0);
        else if (v < 0.5) point = vec3(1.0, carrier.x / 255.0, 0.0);
        else point = vec3(1.0, carrier.z / 255.0, 1.0);
    } else if (kind < 1.5) {
        if (v < 0.5) point = vec3(0.0, third / 255.0, 0.0);
        else if (u > 0.5) point = vec3(1.0, carrier.x / 255.0, 1.0);
        else point = vec3(0.0, carrier.z / 255.0, 1.0);
    } else if (kind > 5.5) {
        point = vec3(1.0-u, 0.0, v);
    } else {
        float height = v * mix(carrier.x, carrier.z, u) / 255.0;
        if (kind < 2.5) point = vec3(u, height, 0.0);
        else if (kind < 3.5) point = vec3(1.0-u, height, 1.0);
        else if (kind < 4.5) point = vec3(0.0, height, 1.0-u);
        else point = vec3(1.0, height, u);
    }
    float mode = EXTRA_ACTOR_UNIFORM4.z;
    if (mode > 0.5 && mode < 2.5) {
        gl_Position = WORLDVIEWPROJ * vec4(POSITION.xyz - vec3(carrier.x, 0.0, carrier.z), 1.0);
        liquidPayloadDecoded = mode < 1.5 ? vec3(carrier.x, third, carrier.z) / 255.0 : vec3(u, v, 1.0);
    } else {
        gl_Position = WORLDVIEWPROJ * vec4(point - vec3(0.5), 1.0);
        liquidPayloadDecoded = point;
    }
    gl_PointSize = 1.0;
    uv0 = TEXCOORD_0;
    uv1 = vec2(0.0);
    color = vec4(1.0);
    light = vec4(1.0);
    previewClip = -1.0;
    gridPosition = point.xz;
    outlineHue = 0.0;
    renderContext = vec4(0.0);
    #ifdef FOG
    fogColor = vec4(0.0);
    #endif
}
'''
FRAGMENT = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39685.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    if (EXTRA_ACTOR_UNIFORM4.z > 0.5) {
        gl_FragColor = vec4(liquidPayloadDecoded, 1.0);
        return;
    }
    gl_FragColor = texture2D(TEXTURE_0, uv0) * vec4(EXTRA_ACTOR_UNIFORM1.rgb, EXTRA_ACTOR_UNIFORM4.w);
}
'''


def identifier(code, tile='still_water_grey'):
    return 'modern_projection:liquid_separated_%s_y%03d_r9' % (tile, code)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output, native, all_codes=False):
    if output.exists():
        raise ValueError('Choose a fresh fixture output')
    sources = source_snapshot(native)
    codes = tuple(range(256)) if all_codes else CODES
    blocks, files = {'format_version': [1, 1, 0]}, {}
    for tile in NATIVE_KEYS:
        for code in codes:
            name = identifier(code, tile)
            filename = name.split(':')[1] + '.json'
            files['behavior_pack/netease_blocks/' + filename] = behavior(name, 'blend')
            files['resource_pack/models/netease_block/' + filename] = plane(name, code / 16., tile, 16)
            blocks[name] = {'netease_model': name, 'sound': 'stone'}
    files['resource_pack/blocks.json'] = blocks
    material = {'vertexShader': 'shaders/glsl/liquid_separated_r9.vertex',
                'fragmentShader': 'shaders/glsl/liquid_separated_r9.fragment',
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
        path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')
    shaders = output / 'resource_pack/shaders/glsl'
    shaders.mkdir(parents=True)
    source_paths = (ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.vertex',
                    ROOT / 'resource_pack/shaders/glsl/modern_projection_biome_blocks.fragment')
    for source, extension, appended, vertex in ((source_paths[0], 'vertex', VERTEX, True),
                                               (source_paths[1], 'fragment', FRAGMENT, False)):
        (shaders / ('liquid_separated_r9.' + extension)).write_text(
            wrapped_shader(source, appended, vertex), encoding='ascii')
    report = dict(sources, schema_version=1, codes=codes, actor_tag=TAG,
                  height_denominator=255, transport_denominator=256, carrier_y=0,
                  kind_source='EXTRA_ACTOR_UNIFORM4.y', cell_source='attachment offset',
                  modes={'native_tile': 0, 'height_and_address': 1, 'corner_phase': 2, 'decoded_position': 3},
                  max_per_mesh_volume_indices=65536, max_attachments_per_64_cells=448,
                  max_aggregate_palette_indices=29360128,
                  native_input_format_accepted=False, native_geometry_accepted=False,
                  native_pose_accepted=False, accuracy_accepted=False, production_memory_accepted=False,
                  scope='Explicit supplied heights only; no native liquid rule or production integration',
                  fallback_shader_sha256={str(path): digest(path) for path in source_paths})
    report['output_sha256'] = {path.relative_to(output).as_posix(): digest(path)
                              for path in sorted(output.rglob('*')) if path.is_file()}
    (output / 'contract.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--native-data', required=True, type=Path)
    parser.add_argument('--all-codes', action='store_true')
    parser.add_argument('--install-project', type=Path)
    parser.add_argument('--backup', type=Path)
    args = parser.parse_args()
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve(), args.all_codes)
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({'files': len(report['output_sha256']), 'native_geometry_accepted': False}))


if __name__ == '__main__':
    main()
