"""Versioned four-cell skeleton candidate using original native liquid artwork."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

from PIL import Image

from generate_liquid_payload_poc import install_overlay, source_snapshot

PREFIX = 'modern_projection_liquid_'
ASSET_PATH = 'modern_projection/liquid'
VERTEX_NAME = 'modern_projection_liquid.vertex'
WORLD_VERTEX_NAME = 'modern_projection_liquid_world.vertex'
VERTEX = '''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
// LIQUID_PREVIEW_HEADER
varying highp vec2 liquidUv;
varying highp float liquidVisible;
varying highp float liquidClip;
void main() {
    float slot = floor(POSITION.x / 2.0);
    float face = floor(POSITION.y / 2.0);
    float u = mod(POSITION.x,2.0);
    float v = mod(POSITION.y,2.0);
    float code;
    vec2 pairCodes;
    if (slot < 0.5) { code=EXTRA_VECTOR1.x; pairCodes=EXTRA_VECTOR2.xy; }
    else if (slot < 1.5) { code=EXTRA_VECTOR1.y; pairCodes=EXTRA_VECTOR2.zw; }
    else if (slot < 2.5) { code=EXTRA_VECTOR1.z; pairCodes=EXTRA_VECTOR3.xy; }
    else { code=EXTRA_VECTOR1.w; pairCodes=EXTRA_VECTOR3.zw; }
    float address = mod(code,64.0);
    float faces = mod(floor(code/64.0),64.0);
    vec4 heights=vec4(mod(pairCodes.x,256.0),floor(pairCodes.x/256.0),
                       mod(pairCodes.y,256.0),floor(pairCodes.y/256.0))/255.0;
    vec3 cell=vec3(mod(address,4.0),floor(address/16.0),mod(floor(address/4.0),4.0));
    vec3 point;
    if (face < 0.5) {
        point=vec3(u,mix(mix(heights.x,heights.y,u),mix(heights.w,heights.z,u),v),v);
        liquidUv=vec2(u,v);
    } else if (face > 4.5) {
        point=vec3(1.0-u,0.0,v);
        liquidUv=vec2(u,v);
    } else {
        float left;
        float right;
        if (face < 1.5) { left=heights.x; right=heights.y; }
        else if (face < 2.5) { left=heights.z; right=heights.w; }
        else if (face < 3.5) { left=heights.w; right=heights.x; }
        else { left=heights.y; right=heights.z; }
        float height=v*mix(left,right,u);
        if (face < 1.5) point=vec3(u,height,0.0);
        else if (face < 2.5) point=vec3(1.0-u,height,1.0);
        else if (face < 3.5) point=vec3(0.0,height,1.0-u);
        else point=vec3(1.0,height,u);
        liquidUv=vec2(u,1.0-height);
    }
    liquidVisible=mod(floor(faces/pow(2.0,face)),2.0);
    bool payloadValid=abs(EXTRA_VECTOR4.x-39686.0)<0.25 || mod(EXTRA_VECTOR4.x,256.0)==134.0;
    if (!payloadValid || floor(code/4096.0)>0.5) liquidVisible=0.0;
    vec3 localPoint=cell+point-vec3(2.0);
    vec4 entityPoint=vec4(localPoint,1.0);
    // LIQUID_UI_COORDINATES
    // LIQUID_WORLD_BONE
    gl_Position=WORLDVIEWPROJ*entityPoint;
    liquidClip=-1.0;
    // LIQUID_PREVIEW_DEPTH
    gl_PointSize=1.0;
}
'''
FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformPerFrameConstants.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
#include "uniformWorldConstants.h"
uniform sampler2D TEXTURE_0;
varying highp vec2 liquidUv;
varying highp float liquidVisible;
varying highp float liquidClip;
const float FRAME_COUNT = %(frames)s;
const float FRAME_PIXELS = %(pixels)s;
const float TICKS_PER_FRAME = %(ticks)s;
const float DIAGNOSTIC_DEFAULT_OPACITY = %(diagnostic_opacity)s;
vec4 sampleFrame(float frame) {
    vec2 pixel=%(pixel_coordinates)s;
    return texture2D(TEXTURE_0,vec2(pixel.x/FRAME_PIXELS,(pixel.y/FRAME_PIXELS+frame)/FRAME_COUNT));
}
void main() {
    if (liquidVisible<0.5 || liquidClip>0.0) discard;
    float clock = %(clock)s;
    float frame=mod(floor(clock),FRAME_COUNT);
    vec4 texel=mix(sampleFrame(frame),sampleFrame(mod(frame+1.0,FRAME_COUNT)),%(blend)s);
    float tint=EXTRA_VECTOR4.z;
    vec3 rgb=vec3(floor(tint/65536.0),mod(floor(tint/256.0),256.0),mod(tint,256.0))/255.0;
    float defaultAlpha=DIAGNOSTIC_DEFAULT_OPACITY<0.0 ? texel.a : DIAGNOSTIC_DEFAULT_OPACITY;
    float alpha=EXTRA_VECTOR4.y<0.0 ? defaultAlpha : EXTRA_VECTOR4.y;
    if(abs(PROJ[3][3])>0.5) alpha*=CURRENT_COLOR.a;
    gl_FragColor=vec4(texel.rgb*rgb,alpha*EXTRA_VECTOR4.w);
}
'''
PACKET_FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformShaderConstants.h"
varying highp float liquidVisible;
void main() {
    if (liquidVisible<0.5) discard;
    gl_FragColor=vec4(CURRENT_COLOR.rgb,1.0);
}
'''
WORLD_BONE = '''#if defined(USE_SKINNING) && defined(NETEASE_SKINNING)
    entityPoint.z=-entityPoint.z;
    entityPoint=GetBoneMatForNetease(int(BONEID_0))*entityPoint;
#ifdef USE_INSTANCE
    entityPoint=GetInstanceWorldMatForNetease()*entityPoint;
#endif
#endif'''
UI_COORDINATES = '''entityPoint=vec4(-localPoint.x,-localPoint.z+1.5,-localPoint.y,1.0);'''
MATRIX_VERTEX = '''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
varying highp vec3 matrixColor;
varying highp float matrixIndex;
void main() {
    float column=floor(POSITION.x/2.0);
    float row=floor(POSITION.y/2.0);
    float index=column+row*4.0;
    matrixIndex=index;
    mat4 value=WORLDVIEWPROJ;
    float selected=EXTRA_VECTOR4.z;
    if (selected<0.5) value=WORLDVIEWPROJ;
    else if (selected<1.5) value=WORLDVIEW;
    else if (selected<2.5) value=PROJ;
    else if (selected<3.5) value=WORLD;
#if defined(USE_SKINNING) && defined(NETEASE_SKINNING)
    else value=GetBoneMatForNetease(int(BONEID_0));
#endif
    float col=floor(index/4.0);
    vec4 vector=value[0];
    if (col>0.5 && col<1.5) vector=value[1];
    else if (col>1.5 && col<2.5) vector=value[2];
    else if (col>2.5) vector=value[3];
    float component=mod(index,4.0);
    float number=vector.x;
    if (component>0.5 && component<1.5) number=vector.y;
    else if (component>1.5 && component<2.5) number=vector.z;
    else if (component>2.5) number=vector.w;
    if(index>15.5) number=0.0;
    if(index>15.5 && index<16.5) {
#ifdef USE_SKINNING
        number+=1.0;
#endif
#ifdef NETEASE_SKINNING
        number+=2.0;
#endif
#ifdef USE_INSTANCE
        number+=4.0;
#endif
#ifdef USE_ALPHA
        number+=8.0;
#endif
    }
    float code=clamp(floor(number*2048.0+8388608.0+0.5),0.0,16777215.0);
    matrixColor=vec3(floor(code/65536.0),mod(floor(code/256.0),256.0),mod(code,256.0))/255.0;
    vec2 point=vec2((column+mod(POSITION.x,2.0))/4.0,(row+mod(POSITION.y,2.0))/6.0);
    gl_Position=vec4(point.x*2.0-1.0,1.0-point.y*2.0,0.0,1.0);
}
'''
MATRIX_FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
varying highp vec3 matrixColor;
varying highp float matrixIndex;
uniform vec4 HIDE_COLOR_FRAGMENT;
void main() {
    vec3 color=matrixColor;
    if(matrixIndex>16.5 && matrixIndex<21.5) {
        float value=HIDE_COLOR_FRAGMENT.r;
        if(matrixIndex>17.5) value=HIDE_COLOR_FRAGMENT.g;
        if(matrixIndex>18.5) value=HIDE_COLOR_FRAGMENT.b;
        if(matrixIndex>19.5) value=HIDE_COLOR_FRAGMENT.a;
        if(matrixIndex>20.5) value=CURRENT_COLOR.a;
        float code=clamp(floor(value*2048.0+8388608.0+0.5),0.0,16777215.0);
        color=vec3(floor(code/65536.0),mod(floor(code/256.0),256.0),mod(code,256.0))/255.0;
    }
    gl_FragColor=vec4(color,EXTRA_VECTOR4.w);
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')


def sampling_region(atlas_entry):
    quad = atlas_entry.get('quad', 0)
    if type(quad) is not int or quad not in (0, 1):
        raise ValueError('Candidate needs a verified native atlas quadrant contract')
    if quad:
        return {'region': 'nw', 'source_frame_extent': [0., 0., .5, .5],
                'pixel_mapping': 'edges', 'native_sampling_accepted': False,
                'pixel_coordinates': 'clamp(liquidUv,0.0,1.0)*(FRAME_PIXELS*0.5)',
                'scope': 'Installed quad:1 source restriction; edge/filter accuracy remains a candidate'}
    return {'region': 'full', 'source_frame_extent': [0., 0., 1., 1.],
            'pixel_mapping': 'centers', 'native_sampling_accepted': False,
            'pixel_coordinates': 'clamp(liquidUv,0.0,1.0)*(FRAME_PIXELS-1.0)+0.5',
            'scope': 'Existing unaccepted full-frame sampling candidate'}


def mesh(texture):
    vertices, indices = [], []
    normals = ((0., 1., 0.), (0., 0., -1.), (0., 0., 1.),
               (-1., 0., 0.), (1., 0., 0.), (0., -1., 0.))
    for slot in range(4):
        for face, normal in enumerate(normals):
            start = len(vertices)
            for u, v in ((0., 0.), (1., 0.), (1., 1.), (0., 1.)):
                vertices.append({'pos': [slot * 2. + u, face * 2. + v, 0.],
                                 'normal': normal, 'uvcoord': [u, v], 'weight': [['root', 1.]]})
            indices.extend([[start, start + 2, start + 1], [start, start + 3, start + 2]])
    return {'mesh': [{'material': texture, 'vertices': vertices, 'indices': indices}]}


def generate(output, native, keys, world_bone=False, preview_depth=False, packet_control=False,
             diagnostic_flow=False, diagnostic_water_opacity=None):
    if output.exists():
        raise ValueError('Choose a fresh resource candidate directory')
    if diagnostic_water_opacity is not None and (isinstance(diagnostic_water_opacity, bool)
            or not isinstance(diagnostic_water_opacity, (int, float))
            or not math.isfinite(diagnostic_water_opacity) or not 0. < diagnostic_water_opacity < 1.):
        raise ValueError('Diagnostic water opacity must be an explicit finite value between zero and one')
    snapshot = source_snapshot(native)
    animations = dict((row['atlas_tile'], row) for row in snapshot['native_flipbook_entries'])
    if diagnostic_flow:
        keys=tuple(keys)+('flowing_water_grey',)
    example = native / 'resource_packs/vanilla_netease/models/for_developer'
    references = [example / 'mesh/ceshi_rightlegdown_mesh.json',
                  example / 'skeleton/ceshi_rightlegdown_skeleton.json',
                  native / 'resource_packs/vanilla_netease/materials/entity.material',
                  native / 'shaders/glsl/neteaseModelVertexUtil.h',
                  native / 'shaders/glsl/uniformPerFrameConstants.h']
    if not {'material', 'indices', 'vertices'} <= set(json.loads(references[0].read_bytes())['mesh'][0]):
        raise ValueError('Installed native skeleton mesh format changed')
    registry, materials, textures, model_options = {}, {'version': '1.0.0'}, {}, {}
    bounds = [[-2., -2., -2.], [2., 2., 2.]]
    skeleton = {'boundingbox': bounds, 'skeleton': [
        {'name': 'root', 'parent': 'root', 'initpos': [0., 0., 0.],
         'initquaternion': [0., 0., 0., 1.], 'initscale': [1., 1., 1.],
         'offmtx': [[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.]], 'boundingbox': bounds}]}
    write_json(output / ('resource_pack/models/' + ASSET_PATH + '/skeleton.json'), skeleton)
    shader_dir = output / 'resource_pack/shaders/glsl'
    shader_dir.mkdir(parents=True)
    vertex = VERTEX.replace('// LIQUID_WORLD_BONE', '').replace('// LIQUID_UI_COORDINATES', UI_COORDINATES)
    if preview_depth:
        header = Path(__file__).resolve().parents[1] / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'
        references.append(header)
        vertex = vertex.replace('// LIQUID_PREVIEW_HEADER', header.read_text(encoding='ascii'))
        vertex = vertex.replace('// LIQUID_PREVIEW_DEPTH',
            'liquidUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,liquidClip);')
    (shader_dir / VERTEX_NAME).write_text(vertex, encoding='ascii')
    targets = (('', VERTEX_NAME),)
    if world_bone:
        world_vertex = VERTEX.replace('// LIQUID_WORLD_BONE', WORLD_BONE).replace('// LIQUID_UI_COORDINATES', '')
        (shader_dir / WORLD_VERTEX_NAME).write_text(world_vertex, encoding='ascii')
        targets += (('_world', WORLD_VERTEX_NAME),)
    for key in keys:
        entry = animations.get(key)
        sampling = sampling_region(snapshot['native_atlas_entries'][key])
        frozen_only=diagnostic_flow and key=='flowing_water_grey'
        if entry is None or (not frozen_only and (not isinstance(entry.get('ticks_per_frame'), int) or entry['ticks_per_frame'] < 1)):
            raise ValueError('Candidate requires an explicit native ticks_per_frame: ' + key)
        if entry.get('frames') is not None or (not frozen_only and entry.get('replicate', 1) != 1):
            raise ValueError('Candidate needs a verified native frame/replicate implementation: ' + key)
        source = native / 'resource_packs/vanilla' / (entry['flipbook_texture'] + '.png')
        with Image.open(source) as image:
            width, height = image.size
            if height % width:
                raise ValueError('Native liquid artwork is not a square-frame strip')
            frames, alpha = height // width, image.convert('RGBA').getextrema()[3]
        texture = ASSET_PATH + '/' + key
        destination = output / ('resource_pack/textures/models/' + texture + '.png')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        write_json(output / ('resource_pack/models/' + ASSET_PATH + '/' + key + '_mesh.json'), mesh(texture))
        textures[key] = {'source': str(source.resolve()), 'sha256': digest(source),
                         'size': [width, height], 'frames': frames, 'alpha_range': alpha,
                         'flipbook': entry, 'frozen_diagnostic_only':frozen_only,
                         'native_sampling_accepted':False, 'sampling': sampling}
        variants=('frozen','packet') if frozen_only and packet_control else ('frozen',) if frozen_only else ('animated','frozen','packet') if packet_control else ('animated','frozen')
        for variant in variants:
            frozen = variant == 'frozen'
            stem = PREFIX + key + ('_' + variant if variant != 'animated' else '')
            fragment_name = stem + '.fragment'
            fragment = FRAGMENT % {'frames': str(float(frames)), 'pixels': str(float(width)),
                                   'pixel_coordinates': sampling['pixel_coordinates'],
                                   'ticks': '1.0' if frozen_only else str(float(entry['ticks_per_frame'])),
                                   'diagnostic_opacity': str(float(diagnostic_water_opacity))
                                       if diagnostic_water_opacity is not None and 'water' in key else '-1.0',
                                   'clock': '0.0' if frozen else 'TIME*20.0/TICKS_PER_FRAME',
                                   'blend': '0.0' if frozen or not entry.get('blend_frames', True) else 'fract(clock)'}
            (shader_dir / fragment_name).write_text(PACKET_FRAGMENT if variant == 'packet' else fragment, encoding='ascii')
            for suffix, vertex_name in targets:
                name = stem + suffix
                registry[name] = {'dy_load': True, 'mesh': ASSET_PATH + '/' + key + '_mesh.json',
                                  'skeleton': ASSET_PATH + '/skeleton.json', 'animation': {},
                                  'material': name, 'texture': {'tex0': texture}}
                materials[name + ':entity_for_skeleton_alpha'] = {
                    'vertexShader': 'shaders/glsl/' + vertex_name,
                    'fragmentShader': 'shaders/glsl/' + fragment_name,
                    '+states': ['Blending', 'DisableDepthWrite', 'DisableCulling'],
                    'blendSrc': 'SourceAlpha', 'blendDst': 'OneMinusSrcAlpha'}
                model_options[name] = {'texture': key, 'variant': variant, 'vertex_shader': vertex_name,
                                       'fragment_shader': fragment_name,
                                       'uv_rotations':[0],
                                       'transform': 'native_bone_after_reverse_z' if suffix else 'native_ui_neg_x_neg_z_neg_y_center1_5',
                                       'preview_depth': bool(preview_depth and not suffix)}
    if packet_control:
        name = PREFIX + 'matrix'
        registry[name] = dict(registry[PREFIX + keys[0]], material=name)
        (shader_dir / (name + '.vertex')).write_text(MATRIX_VERTEX, encoding='ascii')
        (shader_dir / (name + '.fragment')).write_text(MATRIX_FRAGMENT, encoding='ascii')
        materials[name + ':entity_for_skeleton_alpha'] = {
            'vertexShader': 'shaders/glsl/' + name + '.vertex',
            'fragmentShader': 'shaders/glsl/' + name + '.fragment', '+states': ['DisableCulling']}
        model_options[name] = {'variant': 'matrix', 'diagnostic': True}
    write_json(output / 'resource_pack/models/netease_models.json', registry)
    write_json(output / 'resource_pack/materials/entity.material', {'materials': materials})
    report = dict(snapshot, schema=1, payload_version=2, textures=textures, models=registry, model_options=model_options,
                  generator_sha256=digest(Path(__file__)),
                  source_sha256=dict((str(path.resolve()), digest(path)) for path in references),
                  output_sha256=dict((path.relative_to(output).as_posix(), digest(path))
                                    for path in sorted(output.rglob('*')) if path.is_file()),
                  vertex_count=96, triangle_count=48, cells_per_model=4,
                  face_order=['top', 'north', 'south', 'west', 'east', 'bottom'],
                  asset_path=ASSET_PATH, vertex_shader=VERTEX_NAME,
                  world_vertex_shader=WORLD_VERTEX_NAME if world_bone else None,
                  world_coordinate_contract={'native_units_per_block': 16, 'model_scale': 16.,
                                             'center_offset': [2., 2., 2.], 'rotation': [0., 0., 0.],
                                             'decoded_vertex_z_reversed': True,
                                             'native_placement_accepted': False} if world_bone else None,
                  world_bone_matrix=world_bone, preview_depth=preview_depth, packet_control=packet_control,
                  ui_coordinate_contract={'native_model_axes': ['-x', '-z+1.5', '-y'],
                                          'scale': 'logical_cell_unit/min(actual_paper_doll_size)',
                                          'control_top_offset': 'min(actual_paper_doll_size)/4',
                                          'native_alignment_accepted': False},
                  diagnostic_water_opacity=diagnostic_water_opacity,
                  blend_state_contract={'states':['Blending', 'DisableDepthWrite', 'DisableCulling'],
                                        'source':'SourceAlpha', 'destination':'OneMinusSrcAlpha',
                                        'active_native_blending_accepted':False},
                  opacity_contract='None sentinel samples original native image alpha unless an explicit diagnostic water default is requested; biome opacity replaces it',
                  ui_fade_contract='Orthographic native CURRENT_COLOR.a, matching existing block preview shader; native acceptance pending',
                  animation_contract='Original native square strip + parsed cadence/blend; engine TIME loops at 210 seconds',
                  scope='Supplied-shape skeleton artwork/animation candidate only',
                  native_shape_accepted=False, native_uv_accepted=False,
                  native_alpha_accepted=False, animation_accepted=False,
                  production_editor_accepted=False, production_memory_accepted=False)
    write_json(output / 'contract.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--texture', choices=('still_water_grey', 'still_lava'), action='append')
    parser.add_argument('--install-project', type=Path)
    parser.add_argument('--backup', type=Path)
    parser.add_argument('--world-bone', action='store_true')
    parser.add_argument('--preview-depth', action='store_true')
    parser.add_argument('--packet-control', action='store_true')
    parser.add_argument('--diagnostic-flow', action='store_true', help='Unaccepted frozen frame zero only, no guessed flow cadence')
    parser.add_argument('--diagnostic-water-opacity', type=float,
                        help='Unaccepted water-only fallback when the biome supplies no opacity')
    args = parser.parse_args()
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve(), tuple(args.texture or ('still_water_grey',)),
                      args.world_bone, args.preview_depth, args.packet_control,args.diagnostic_flow,
                      args.diagnostic_water_opacity)
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({'models': list(report['models']), 'native_shape_accepted': False}))


if __name__ == '__main__':
    main()
