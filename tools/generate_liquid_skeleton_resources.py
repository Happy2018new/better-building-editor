"""Versioned four-cell skeleton candidate using original native liquid artwork."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

from generate_liquid_payload_poc import install_overlay, source_snapshot

PREFIX = 'modern_projection_liquid_'
VERTEX = '''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
varying highp vec2 liquidUv;
varying highp float liquidVisible;
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
    if (abs(EXTRA_VECTOR4.x-39686.0)>0.25 || floor(code/4096.0)>0.5) liquidVisible=0.0;
    gl_Position=WORLDVIEWPROJ*vec4(cell+point-vec3(2.0),1.0);
    gl_PointSize=1.0;
}
'''
FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformPerFrameConstants.h"
#include "uniformExtraVectorConstants.h"
uniform sampler2D TEXTURE_0;
varying highp vec2 liquidUv;
varying highp float liquidVisible;
const float FRAME_COUNT = %(frames)s;
const float FRAME_PIXELS = %(pixels)s;
const float TICKS_PER_FRAME = %(ticks)s;
vec4 sampleFrame(float frame) {
    vec2 pixel=clamp(liquidUv,0.0,1.0)*(FRAME_PIXELS-1.0)+0.5;
    return texture2D(TEXTURE_0,vec2(pixel.x/FRAME_PIXELS,(pixel.y/FRAME_PIXELS+frame)/FRAME_COUNT));
}
void main() {
    if (liquidVisible<0.5) discard;
    float clock = %(clock)s;
    float frame=mod(floor(clock),FRAME_COUNT);
    vec4 texel=mix(sampleFrame(frame),sampleFrame(mod(frame+1.0,FRAME_COUNT)),%(blend)s);
    float tint=EXTRA_VECTOR4.z;
    vec3 rgb=vec3(floor(tint/65536.0),mod(floor(tint/256.0),256.0),mod(tint,256.0))/255.0;
    float alpha=EXTRA_VECTOR4.y<0.0 ? texel.a : EXTRA_VECTOR4.y;
    gl_FragColor=vec4(texel.rgb*rgb,alpha*EXTRA_VECTOR4.w);
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')


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
            indices.extend([[start, start + 1, start + 2], [start, start + 2, start + 3]])
    return {'mesh': [{'material': texture, 'vertices': vertices, 'indices': indices}]}


def generate(output, native, keys):
    if output.exists():
        raise ValueError('Choose a fresh resource candidate directory')
    snapshot = source_snapshot(native)
    animations = dict((row['atlas_tile'], row) for row in snapshot['native_flipbook_entries'])
    example = native / 'resource_packs/vanilla_netease/models/for_developer'
    references = [example / 'mesh/ceshi_rightlegdown_mesh.json',
                  example / 'skeleton/ceshi_rightlegdown_skeleton.json',
                  native / 'resource_packs/vanilla_netease/materials/entity.material',
                  native / 'shaders/glsl/neteaseModelVertexUtil.h',
                  native / 'shaders/glsl/uniformPerFrameConstants.h']
    if not {'material', 'indices', 'vertices'} <= set(json.loads(references[0].read_bytes())['mesh'][0]):
        raise ValueError('Installed native skeleton mesh format changed')
    registry, materials, textures = {}, {'version': '1.0.0'}, {}
    bounds = [[-2., -2., -2.], [2., 2., 2.]]
    skeleton = {'boundingbox': bounds, 'skeleton': [
        {'name': 'root', 'parent': 'root', 'initpos': [0., 0., 0.],
         'initquaternion': [0., 0., 0., 1.], 'initscale': [1., 1., 1.],
         'offmtx': [[1., 0., 0., 0.], [0., 1., 0., 0.], [0., 0., 1., 0.]], 'boundingbox': bounds}]}
    write_json(output / 'resource_pack/models/liquid_candidate/skeleton.json', skeleton)
    shader_dir = output / 'resource_pack/shaders/glsl'
    shader_dir.mkdir(parents=True)
    (shader_dir / 'liquid_candidate.vertex').write_text(VERTEX, encoding='ascii')
    for key in keys:
        entry = animations.get(key)
        if entry is None or not isinstance(entry.get('ticks_per_frame'), int) or entry['ticks_per_frame'] < 1:
            raise ValueError('Candidate requires an explicit native ticks_per_frame: ' + key)
        if entry.get('frames') is not None or entry.get('replicate', 1) != 1:
            raise ValueError('Candidate needs a verified native frame/replicate implementation: ' + key)
        source = native / 'resource_packs/vanilla' / (entry['flipbook_texture'] + '.png')
        with Image.open(source) as image:
            width, height = image.size
            if height % width:
                raise ValueError('Native liquid artwork is not a square-frame strip')
            frames, alpha = height // width, image.convert('RGBA').getextrema()[3]
        texture = 'liquid_candidate/' + key
        destination = output / ('resource_pack/textures/models/' + texture + '.png')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        write_json(output / ('resource_pack/models/liquid_candidate/' + key + '_mesh.json'), mesh(texture))
        textures[key] = {'source': str(source.resolve()), 'sha256': digest(source),
                         'size': [width, height], 'frames': frames, 'alpha_range': alpha,
                         'flipbook': entry}
        for frozen in (False, True):
            name = PREFIX + key + ('_frozen' if frozen else '')
            registry[name] = {'dy_load': True, 'mesh': 'liquid_candidate/' + key + '_mesh.json',
                              'skeleton': 'liquid_candidate/skeleton.json', 'animation': {},
                              'material': name, 'texture': {'tex0': texture}}
            fragment_name = name + '.fragment'
            fragment = FRAGMENT % {'frames': str(float(frames)), 'pixels': str(float(width)),
                                   'ticks': str(float(entry['ticks_per_frame'])),
                                   'clock': '0.0' if frozen else 'TIME*20.0/TICKS_PER_FRAME',
                                   'blend': '0.0' if frozen or not entry.get('blend_frames', True) else 'fract(clock)'}
            (shader_dir / fragment_name).write_text(fragment, encoding='ascii')
            materials[name + ':entity_for_skeleton_alpha'] = {
                'vertexShader': 'shaders/glsl/liquid_candidate.vertex',
                'fragmentShader': 'shaders/glsl/' + fragment_name, '+states': ['DisableCulling']}
    write_json(output / 'resource_pack/models/netease_models.json', registry)
    write_json(output / 'resource_pack/materials/entity.material', {'materials': materials})
    report = dict(snapshot, schema=1, textures=textures, models=registry,
                  generator_sha256=digest(Path(__file__)),
                  source_sha256=dict((str(path.resolve()), digest(path)) for path in references),
                  output_sha256=dict((path.relative_to(output).as_posix(), digest(path))
                                    for path in sorted(output.rglob('*')) if path.is_file()),
                  vertex_count=96, triangle_count=48, cells_per_model=4,
                  face_order=['top', 'north', 'south', 'west', 'east', 'bottom'],
                  opacity_contract='None sentinel samples original native image alpha; explicit opacity replaces it',
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
    args = parser.parse_args()
    if bool(args.install_project) != bool(args.backup):
        parser.error('--install-project and --backup must be supplied together')
    report = generate(args.output.resolve(), args.native_data.resolve(), tuple(args.texture or ('still_water_grey',)))
    if args.install_project:
        install_overlay(args.output.resolve(), args.install_project.resolve(), args.backup.resolve())
    print(json.dumps({'models': list(report['models']), 'native_shape_accepted': False}))


if __name__ == '__main__':
    main()
