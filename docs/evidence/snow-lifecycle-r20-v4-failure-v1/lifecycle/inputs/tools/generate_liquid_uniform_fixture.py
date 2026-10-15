"""Generate an isolated four-cell uniform liquid carrier with native UVs."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from generate_liquid_native_input_fixture import plane
from generate_liquid_payload_poc import install_overlay, source_snapshot, wrapped_shader, NATIVE_KEYS
from generate_shulker_proxies import behavior

ROOT = Path(__file__).resolve().parents[1]
TAG = 39686.0
DIRECT_ENTITY = 'modern_projection:liquid_uniform_direct_r9'
ENTITY_VERTEX = '''// __multiversion__
precision highp float;
#include "entityVertexUtil.h"
uniform highp vec4 EXTRA_ACTOR_UNIFORM1;
uniform highp vec4 EXTRA_ACTOR_UNIFORM2;
uniform highp vec4 EXTRA_ACTOR_UNIFORM3;
uniform highp vec4 EXTRA_ACTOR_UNIFORM4;
varying highp vec3 liquidDirectDiagnostic;
void main() {
    float slot = floor((POSITION.x + 8.0) / 16.0);
    vec2 payloadCodes;
    if (slot < 0.5) payloadCodes = EXTRA_ACTOR_UNIFORM2.xy;
    else if (slot < 1.5) payloadCodes = EXTRA_ACTOR_UNIFORM2.zw;
    else if (slot < 2.5) payloadCodes = EXTRA_ACTOR_UNIFORM3.xy;
    else payloadCodes = EXTRA_ACTOR_UNIFORM3.zw;
    liquidDirectDiagnostic = vec3(mod(payloadCodes.x,256.0),floor(payloadCodes.x/256.0),
                                  mod(payloadCodes.y,256.0)) / 255.0;
    gl_Position = WORLDVIEWPROJ * vec4(POSITION.xyz,1.0);
    gl_PointSize = 1.0;
}
'''
ENTITY_FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
varying highp vec3 liquidDirectDiagnostic;
void main() { gl_FragColor = vec4(liquidDirectDiagnostic,1.0); }
'''
VERTEX = '''
void main() {
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39686.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    vec3 encoded = POSITION.xyz + vec3(0.5);
    vec3 carrier = floor(encoded);
    float u = step(0.5, fract(encoded.x));
    float v = step(0.5, fract(encoded.z));
    float slot = carrier.x;
    float kind = carrier.y;
    vec2 payloadCodes;
    float index;
    if (slot < 0.5) { payloadCodes = EXTRA_ACTOR_UNIFORM2.xy; index = EXTRA_ACTOR_UNIFORM1.x; }
    else if (slot < 1.5) { payloadCodes = EXTRA_ACTOR_UNIFORM2.zw; index = EXTRA_ACTOR_UNIFORM1.y; }
    else if (slot < 2.5) { payloadCodes = EXTRA_ACTOR_UNIFORM3.xy; index = EXTRA_ACTOR_UNIFORM1.z; }
    else { payloadCodes = EXTRA_ACTOR_UNIFORM3.zw; index = EXTRA_ACTOR_UNIFORM1.w; }
    vec4 heights = vec4(mod(payloadCodes.x,256.0),floor(payloadCodes.x/256.0),
                        mod(payloadCodes.y,256.0),floor(payloadCodes.y/256.0)) / 255.0;
    vec3 cell = vec3(mod(index,4.0),floor(index/16.0),mod(floor(index/4.0),4.0));
    vec3 point;
    if (kind < 0.5) {
        if (u < 0.5) point = vec3(0.0,heights.x,0.0);
        else if (v < 0.5) point = vec3(1.0,heights.y,0.0);
        else point = vec3(1.0,heights.z,1.0);
    } else if (kind < 1.5) {
        if (v < 0.5) point = vec3(0.0,heights.x,0.0);
        else if (u > 0.5) point = vec3(1.0,heights.z,1.0);
        else point = vec3(0.0,heights.w,1.0);
    } else if (kind > 5.5) {
        point = vec3(1.0-u,0.0,v);
    } else {
        float left;
        float right;
        if (kind < 2.5) { left=heights.x; right=heights.y; }
        else if (kind < 3.5) { left=heights.z; right=heights.w; }
        else if (kind < 4.5) { left=heights.w; right=heights.x; }
        else { left=heights.y; right=heights.z; }
        float height = v * mix(left,right,u);
        if (kind < 2.5) point = vec3(u,height,0.0);
        else if (kind < 3.5) point = vec3(1.0-u,height,1.0);
        else if (kind < 4.5) point = vec3(0.0,height,1.0-u);
        else point = vec3(1.0,height,u);
    }
    float mode = EXTRA_ACTOR_UNIFORM4.w;
    liquidPayloadDecoded = (cell+point)/4.0;
    vec3 position = cell+point-vec3(0.5);
    if (mode > 1.5) {
        position = POSITION.xyz - carrier + vec3(slot,0.0,0.0);
        if (mode < 2.5) liquidPayloadDecoded=heights.xyz;
        else if (mode < 3.5) liquidPayloadDecoded=vec3(u,v,1.0);
        else if (mode < 4.5) liquidPayloadDecoded=vec3(index/63.0,slot/3.0,kind/6.0);
        else liquidPayloadDecoded=vec3(heights.w,slot/3.0,kind/6.0);
    }
    gl_Position = WORLDVIEWPROJ * vec4(position,1.0);
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
    if (abs(EXTRA_ACTOR_UNIFORM4.x - 39686.0) > 0.25) {
        liquidPayloadFallback();
        return;
    }
    if (EXTRA_ACTOR_UNIFORM4.w > 0.5) {
        gl_FragColor = vec4(liquidPayloadDecoded,1.0);
        return;
    }
    float tint = EXTRA_ACTOR_UNIFORM4.z;
    vec3 rgb = vec3(floor(tint/65536.0),mod(floor(tint/256.0),256.0),mod(tint,256.0))/255.0;
    gl_FragColor = texture2D(TEXTURE_0,uv0) * vec4(rgb,EXTRA_ACTOR_UNIFORM4.y);
}
'''


def identifier(tile='still_water_grey'):
    return 'modern_projection:liquid_uniform_' + tile + '_r9'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(output, native, direct_entity=False):
    if output.exists():
        raise ValueError('Choose a fresh fixture output')
    sources = source_snapshot(native)
    blocks, files = {'format_version': [1, 1, 0]}, {}
    for tile in NATIVE_KEYS:
        name = identifier(tile)
        filename = name.split(':')[1] + '.json'
        files['behavior_pack/netease_blocks/' + filename] = behavior(name, 'blend')
        files['resource_pack/models/netease_block/' + filename] = plane(name, 8., tile, 16)
        blocks[name] = {'netease_model': name, 'sound': 'stone'}
    files['resource_pack/blocks.json'] = blocks
    material = {'vertexShader': 'shaders/glsl/liquid_uniform_r9.vertex',
                'fragmentShader': 'shaders/glsl/liquid_uniform_r9.fragment',
                '+states': ['DisableCulling']}
    files['resource_pack/materials/terrain.material'] = {'materials': {'version': '1.0.0'}}
    for key in ('netease_block_as_mesh_blend:netease_block_as_entity_mesh',
                'netease_block_as_mesh_blend_far:netease_block_as_mesh_blend',
                'netease_block_as_mesh_blend_no_culling:netease_block_as_mesh_blend',
                'netease_block_as_mesh_blend_enable_transparency:netease_block_as_mesh_blend'):
        files['resource_pack/materials/terrain.material']['materials'][key] = deepcopy(material)
    if direct_entity:
        entity = json.loads((ROOT / 'resource_pack/entity/modern_projection_anchor.entity.json').read_bytes())
        description = entity['minecraft:client_entity']['description']
        description.update(identifier=DIRECT_ENTITY,
                           materials={'default':'modern_projection_liquid_direct_r9'},
                           geometry={'default':'geometry.modern_projection.liquid_uniform_direct_r9'})
        entity_behavior = json.loads((ROOT / 'behavior_pack/entities/modern_projection_anchor.json').read_bytes())
        entity_behavior['minecraft:entity']['description']['identifier'] = DIRECT_ENTITY
        files['resource_pack/entity/liquid_uniform_direct_r9.entity.json'] = entity
        files['behavior_pack/entities/liquid_uniform_direct_r9.json'] = entity_behavior
        files['resource_pack/models/entity/liquid_uniform_direct_r9.geo.json'] = {
            'format_version':'1.12.0','minecraft:geometry':[{
                'description':{'identifier':'geometry.modern_projection.liquid_uniform_direct_r9',
                               'texture_width':2,'texture_height':2,'visible_bounds_width':8,
                               'visible_bounds_height':8,'visible_bounds_offset':[1.5,0,0]},
                'bones':[{'name':'root','pivot':[0,0,0],'cubes':[
                    {'origin':[slot*16-4,-1,-4],'size':[8,1,8],
                     'uv':{'up':{'uv':[0,0],'uv_size':[2,2]}}} for slot in range(4)]}]}]}
        files['resource_pack/materials/entity.material'] = {'materials':{'version':'1.0.0',
            'modern_projection_liquid_direct_r9:entity_static':{
                'vertexShader':'shaders/glsl/liquid_uniform_direct_r9.vertex',
                'fragmentShader':'shaders/glsl/liquid_uniform_direct_r9.fragment',
                '+states':['DisableCulling']}}}
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
        (shaders / ('liquid_uniform_r9.' + extension)).write_text(
            wrapped_shader(source, appended, vertex), encoding='ascii')
    if direct_entity:
        for extension, text in (('vertex',ENTITY_VERTEX),('fragment',ENTITY_FRAGMENT)):
            (shaders / ('liquid_uniform_direct_r9.' + extension)).write_text(text, encoding='ascii')
    report = dict(sources, schema_version=1, actor_tag=TAG, height_denominator=255,
                  generator_sha256=digest(Path(__file__)),
                  direct_entity_diagnostic=direct_entity,
                  cells_per_actor=4, max_actors_per_64_cells=16, max_carrier_indices_per_actor=28,
                  uniform_contract={'1':'four local cell indices in a four-cubed batch',
                                    '2':'slot 0/1: h00+256*h10, h11+256*h01',
                                    '3':'slot 2/3: h00+256*h10, h11+256*h01',
                                    '4':'tag, opacity, packed RGB tint, diagnostic mode'},
                  native_input_format_accepted=False, native_geometry_accepted=False,
                  native_pose_accepted=False, accuracy_accepted=False, production_memory_accepted=False,
                  scope='Four independently supplied heights and face masks; no native rules',
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
    parser.add_argument('--direct-entity', action='store_true')
    args = parser.parse_args()
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve(), args.direct_entity)
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({'files': len(report['output_sha256']), 'native_geometry_accepted': False}))


if __name__ == '__main__':
    main()
