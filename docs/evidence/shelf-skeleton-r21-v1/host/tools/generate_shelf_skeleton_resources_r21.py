"""Generate isolated shelf-body skeletons with explicit geometric normals.

The native fancy axis-light expression is a candidate, not appearance acceptance.
No product routing, content renderer, or shared lifecycle is changed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

from generate_item_sprite_resources import FACE_VERTICES, NORMALS
from generate_liquid_skeleton_resources import UI_COORDINATES, WORLD_BONE
from generate_shelf_resources_r17 import ENGINE_VERSION, FRONTS, WOODS, shelf_cubes, write_json


ROOT = Path(__file__).resolve().parents[1]
ASSET = 'modern_projection/shelf_r21'
PREFIX = 'modern_projection_shelf_skeleton_r21_'
MODES = {'0': 'native_fancy_axis_candidate', '1': 'document_normal',
         '2': 'world_normal', '3': 'axis_intensity', '4': 'tile_light',
         '5': 'magenta_material_selector', '6': 'unlit_artwork', '7': 'flags'}

FUNCTIONS = '''vec3 shelfTurn(vec3 point, float direction) {
    point.xz=mat2(cos(direction),sin(direction),-sin(direction),cos(direction))*point.xz;
    return point;
}
float shelfAxisIntensity(vec3 normal, float lightDirection) {
    vec3 N=normalize(normal);
    N.y*=lightDirection;
    return (1.0+N.y)*0.275-N.x*N.x*0.1+N.z*N.z*0.1+0.45;
}
'''

VERTEX = '''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
// HEADER
varying highp vec2 shelfUv;
varying highp vec3 shelfDocumentNormal;
varying highp vec3 shelfWorldNormal;
varying highp float shelfIntensity;
varying highp float shelfVisible;
varying highp float shelfClip;
// FUNCTIONS
void main() {
    float slot=floor(POSITION.z/4.0);
    float code=EXTRA_VECTOR1.x;
    if(slot>0.5) code=EXTRA_VECTOR1.y;
    if(slot>1.5) code=EXTRA_VECTOR1.z;
    if(slot>2.5) code=EXTRA_VECTOR1.w;
    float address=mod(code,64.0);
    float direction=floor(code/4096.0)*6.283185307179586/256.0;
    bool tagged=abs(EXTRA_VECTOR4.x-39686.0)<0.25 || mod(EXTRA_VECTOR4.x,256.0)==134.0;
    shelfVisible=tagged && mod(floor(code/64.0),64.0)>0.5 ? 1.0 : 0.0;
    vec3 point=shelfTurn(vec3(POSITION.x,POSITION.y,mod(POSITION.z,4.0)-1.0),direction);
    shelfDocumentNormal=shelfTurn(NORMAL.xyz,direction);
    vec3 cell=vec3(mod(address,4.0),floor(address/16.0),mod(floor(address/4.0),4.0));
    vec3 localPoint=cell+vec3(0.5,0.0,0.5)+point-vec3(2.0);
    vec4 entityPoint=vec4(localPoint,1.0);
    vec4 entityNormal=vec4(shelfDocumentNormal,0.0);
    // UI
    // BONE
    // WORLD_NORMAL
    gl_Position=WORLDVIEWPROJ*entityPoint;
    shelfClip=-1.0;
    // DEPTH
    shelfUv=TEXCOORD_0;
    // LIGHT
    gl_PointSize=1.0;
}
'''

FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
#include "uniformEntityConstants.h"
#include "uniformWorldConstants.h"
uniform sampler2D TEXTURE_0;
varying highp vec2 shelfUv;
varying highp vec3 shelfDocumentNormal;
varying highp vec3 shelfWorldNormal;
varying highp float shelfIntensity;
varying highp float shelfVisible;
varying highp float shelfClip;
void main() {
    if(shelfVisible<0.5 || shelfClip>0.0 || EXTRA_VECTOR4.w<=0.0) discard;
    float mode=EXTRA_VECTOR2.x;
    vec4 texel=texture2D(TEXTURE_0,shelfUv);
    vec3 rgb=texel.rgb*TILE_LIGHT_COLOR.rgb*shelfIntensity;
    if(mode>0.5 && mode<1.5) rgb=normalize(shelfDocumentNormal)*0.5+0.5;
    else if(mode>1.5 && mode<2.5) rgb=normalize(shelfWorldNormal)*0.5+0.5;
    else if(mode>2.5 && mode<3.5) rgb=vec3(shelfIntensity);
    else if(mode>3.5 && mode<4.5) rgb=TILE_LIGHT_COLOR.rgb;
    else if(mode>4.5 && mode<5.5) rgb=vec3(1.0,0.0,1.0);
    else if(mode>5.5 && mode<6.5) rgb=texel.rgb;
    else if(mode>6.5) {
        rgb=vec3(0.0);
#ifdef FANCY
        rgb.r=1.0;
#endif
#ifdef RNGL_UNLIT
        rgb.g=1.0;
#endif
#ifdef RNGL_LIGHT
        rgb.b=1.0;
#endif
    }
    float alpha=EXTRA_VECTOR4.w;
    if(mode<0.5 || (mode>5.5 && mode<6.5)) alpha*=texel.a;
    if(abs(PROJ[3][3])>0.5) alpha*=CURRENT_COLOR.a;
    if(alpha<=0.0) discard;
    gl_FragColor=vec4(rgb,alpha);
}
'''

WORLD_NORMAL = '''#if defined(USE_SKINNING) && defined(NETEASE_SKINNING)
    entityNormal.z=-entityNormal.z;
    entityNormal=GetBoneMatForNetease(int(BONEID_0))*entityNormal;
#ifdef USE_INSTANCE
    entityNormal=GetInstanceWorldMatForNetease()*entityNormal;
#endif
#endif
    shelfWorldNormal=normalize((WORLD*entityNormal).xyz);'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(reference, front, material):
    vertices, indices = [], []
    for slot in range(4):
        for cube in shelf_cubes(reference, front):
            for face, uv in cube['uv'].items():
                start = len(vertices)
                for corner, (u, v) in zip(FACE_VERTICES[face], ((0, 0), (1, 0), (1, 1), (0, 1))):
                    point = [cube['origin'][axis]+cube['size'][axis]*corner[axis] for axis in range(3)]
                    point = [(point[0]+16.)/16.-.5, point[1]/16., point[2]/16.-.5+1.+slot*4.]
                    vertices.append({'pos': point, 'normal': list(NORMALS[face]),
                                     'uvcoord': [(uv['uv'][0]+u*uv['uv_size'][0])/32.,
                                                 (uv['uv'][1]+v*uv['uv_size'][1])/32.],
                                     'weight': [['root', 1.]]})
                indices.extend(((start, start+1, start+2), (start, start+2, start+3)))
    return {'mesh': [{'material': material, 'vertices': vertices, 'indices': indices}]}


def shaders(world=False):
    header = (ROOT/'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h').read_text(encoding='ascii')
    vertex = VERTEX.replace('// HEADER', '' if world else header).replace('// FUNCTIONS', FUNCTIONS)
    vertex = vertex.replace('// UI', '' if world else UI_COORDINATES)
    vertex = vertex.replace('// BONE', WORLD_BONE if world else '')
    vertex = vertex.replace('// WORLD_NORMAL', WORLD_NORMAL if world else
                            'shelfWorldNormal=shelfDocumentNormal;')
    vertex = vertex.replace('// DEPTH', '' if world else
        'liquidUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,shelfClip);')
    vertex = vertex.replace('// LIGHT', 'shelfIntensity=shelfAxisIntensity('+
        ('shelfWorldNormal' if world else 'shelfDocumentNormal')+',TILE_LIGHT_COLOR.w);')
    return vertex, FRAGMENT


def generate(args):
    if args.output.exists():
        raise ValueError('Choose a fresh shelf skeleton candidate directory')
    if args.native_data.parent.name != ENGINE_VERSION:
        raise ValueError('Shelf artwork must come from the target engine')
    reference = json.loads(args.reference.read_bytes())
    if reference.get('schema_version') != 1 or set(reference['models']) != set(('body',)+FRONTS):
        raise ValueError('Incomplete shelf model reference')
    args.output.mkdir(parents=True)
    models, materials, sources = {}, {}, {}
    for front in args.fronts:
        write_json(args.output/('resource_pack/models/'+ASSET+'/'+front+'_mesh.json'),
                   mesh(reference, front, ASSET+'/'+front))
    for wood in args.woods:
        source = args.native_data/('resource_packs/vanilla/textures/blocks/'+wood+'_shelf.png')
        with Image.open(source) as image:
            if image.size != (32, 32):
                raise ValueError('Native shelf atlas dimensions changed: '+wood)
        sources[source.relative_to(args.native_data).as_posix()] = digest(source)
        texture = args.output/('resource_pack/textures/models/'+ASSET+'/'+wood+'.png')
        texture.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, texture)
        for front in args.fronts:
            for world in (False, True):
                suffix = '_world' if world else ''
                name, material = PREFIX+wood+'_'+front+suffix, PREFIX+'body'+suffix
                models[name] = {'dy_load': True, 'mesh': ASSET+'/'+front+'_mesh.json',
                    'skeleton': ASSET+'/skeleton.json', 'animation': {}, 'material': material,
                    'texture': {'tex0': ASSET+'/'+wood}}
    skeleton = ROOT/'resource_pack/models/modern_projection/liquid/skeleton.json'
    write_json(args.output/('resource_pack/models/'+ASSET+'/skeleton.json'), json.loads(skeleton.read_bytes()))
    for world in (False, True):
        suffix = '_world' if world else ''
        vertex, fragment = shaders(world)
        directory = args.output/'resource_pack/shaders/glsl'
        directory.mkdir(parents=True, exist_ok=True)
        vertex_name, fragment_name = PREFIX+'body'+suffix+'.vertex', PREFIX+'body.fragment'
        (directory/vertex_name).write_text(vertex, encoding='ascii', newline='\n')
        (directory/fragment_name).write_text(fragment, encoding='ascii', newline='\n')
        materials[PREFIX+'body'+suffix+':entity_for_skeleton_alpha'] = {
            'vertexShader': 'shaders/glsl/'+vertex_name, 'fragmentShader': 'shaders/glsl/'+fragment_name,
            '+states': ['Blending', 'DisableCulling'], '-states': ['DisableDepthWrite'],
            'blendSrc': 'SourceAlpha', 'blendDst': 'OneMinusSrcAlpha',
            '+samplerStates': [{'samplerIndex': 0, 'textureFilter': 'Point'}]}
    write_json(args.output/'resource_pack/models/netease_models.json', models)
    write_json(args.output/'resource_pack/materials/entity.material', {'materials': dict(materials, version='1.0.0')})
    write_json(args.output/'reference.json', reference)
    contract = {'schema_version': 1, 'engine_version': ENGINE_VERSION,
        'product_qualified': False, 'native_light_equivalence_qualified': False,
        'native_shape_uv_qualified': False, 'native_depth_lifecycle_qualified': False,
        'woods': args.woods, 'fronts': args.fronts, 'slots': 4,
        'coordinate_system': 'document XYZ, Y up, unrotated front north (-Z)',
        'direction_codes': {'north': 0, 'east': 64, 'south': 128, 'west': 192},
        'payload': 'Existing liquid RenderGroup; address6 + faces6 + rotation8; EXTRA_VECTOR2.x is diagnostic mode',
        'depth': 'Existing liquid preview tag134 and shared depth header; depth writing retained',
        'culling': 'disabled until native front/back evidence; indexed geometric winding independently checked',
        'light': 'Native entity fancy axis formula only; no RNGL/unlit/overlay branch emulation or scalar fitting',
        'ui_light_space': 'document normals; camera rotation must not rotate physical light',
        'world_light_space': 'normal follows position Z reflection, bone, instance and WORLD matrices',
        'modes': MODES, 'reference_sha256': digest(args.reference), 'native_texture_sha256': sources,
        'generator_sha256': digest(Path(__file__)),
        'shared_depth_sha256': digest(ROOT/'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h'),
        'limits': ['No native rendering or appearance acceptance.',
                   'No shelf routing, contents, item glint, state mapping or new renderer owner.',
                   'World normal transform requires the caller to supply uniform scale; the shared owner only checks positive axes.',
                   'The current world probe explicitly supplies scale (16,16,16).'],
        'output_sha256': {path.relative_to(args.output).as_posix(): digest(path)
                          for path in sorted(args.output.rglob('*')) if path.is_file()}}
    write_json(args.output/'contract.json', contract)
    print(json.dumps({'models': len(models), 'meshes': len(args.fronts),
                      'production_qualified': False, 'output': str(args.output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-data', type=Path, required=True)
    parser.add_argument('--reference', type=Path, default=ROOT/'tools/data/shelf_body_java_1.21.9_reference.json')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--woods', nargs='+', choices=WOODS, default=['oak'])
    parser.add_argument('--fronts', nargs='+', choices=FRONTS, default=['unpowered'])
    generate(parser.parse_args())


if __name__ == '__main__':
    main()
