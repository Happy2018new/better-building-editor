"""Generate candidate idle/lectern books using the native 3.10 book artwork."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from PIL import Image

from generate_liquid_product_resources import merge_registry,write_json
from generate_liquid_skeleton_resources import WORLD_BONE,UI_COORDINATES
from book_model_geometry import GEOMETRY_VERSION,CLOSED_PAGE_CLEARANCE

ROOT=Path(__file__).resolve().parents[1]
PREFIX='modern_projection_book_'
PATH='modern_projection/book'
VERTEX='''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
#include "uniformInterFrameConstants.h"
// HEADER
varying highp vec2 bookUv;
varying highp float bookVisible;
varying highp float bookClip;
varying highp float bookLight;
void main() {
    float slot=floor(POSITION.z/4.0);
    float code=EXTRA_VECTOR1.x;
    if(slot>0.5) code=EXTRA_VECTOR1.y;
    if(slot>1.5) code=EXTRA_VECTOR1.z;
    if(slot>2.5) code=EXTRA_VECTOR1.w;
    float address=mod(code,64.0);
    float direction=floor(code/4096.0)*6.283185307179586/256.0;
    bookVisible=mod(floor(code/64.0),64.0)>0.5 ? 1.0 : 0.0;
    bool tagged=abs(EXTRA_VECTOR4.x-39686.0)<0.25 || mod(EXTRA_VECTOR4.x,256.0)==134.0;
    if(!tagged) bookVisible=0.0;
    vec3 point=vec3(POSITION.x,POSITION.y,mod(POSITION.z,4.0)-1.0);
    vec3 normal=NORMAL.xyz;
    // ANIMATION
    point.xz=mat2(cos(direction),sin(direction),-sin(direction),cos(direction))*point.xz;
    normal.xz=mat2(cos(direction),sin(direction),-sin(direction),cos(direction))*normal.xz;
    vec3 cell=vec3(mod(address,4.0),floor(address/16.0),mod(floor(address/4.0),4.0));
    vec3 localPoint=cell+vec3(0.5,0.0,0.5)+point-vec3(2.0);
    vec4 entityPoint=vec4(localPoint,1.0);
    // UI
    // BONE
    gl_Position=WORLDVIEWPROJ*entityPoint;
    bookClip=-1.0;
    // DEPTH
    bookUv=TEXCOORD_0;
    bookLight=0.65+0.35*max(0.0,normal.y);
    gl_PointSize=1.0;
}
'''
FRAGMENT='''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
#include "uniformWorldConstants.h"
uniform sampler2D TEXTURE_0;
varying highp vec2 bookUv;
varying highp float bookVisible;
varying highp float bookClip;
varying highp float bookLight;
void main() {
    if(bookVisible<0.5 || bookClip>0.0 || EXTRA_VECTOR4.w<=0.0) discard;
    vec4 texel=texture2D(TEXTURE_0,bookUv);
    float alpha=texel.a*EXTRA_VECTOR4.w;
    if(abs(PROJ[3][3])>0.5) alpha*=CURRENT_COLOR.a;
    if(alpha<=0.0) discard;
    gl_FragColor=vec4(texel.rgb*bookLight,alpha);
}
'''


def shape(family):
    from book_model_geometry import shape as hinged_shape
    return hinged_shape(family,PATH+"/"+family)


def generate(args):
    if args.output.exists():raise ValueError('Choose a fresh book candidate folder')
    args.output.mkdir(parents=True)
    header=(ROOT/'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h').read_text(encoding='ascii')
    models,materials={},{}
    for family in ('enchanting_table','lectern'):
        name=PREFIX+family
        mesh_name=PATH+'/'+family+'_mesh.json'
        write_json(args.output/('resource_pack/models/'+mesh_name),shape(family))
        for world in (False,True):
            suffix='_world' if world else ''
            vertex=VERTEX.replace('// HEADER','' if world else header)
            vertex=vertex.replace('// UI','' if world else UI_COORDINATES)
            vertex=vertex.replace('// BONE',WORLD_BONE if world else '')
            vertex=vertex.replace('// DEPTH','' if world else 'liquidUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,bookClip);')
            # Native R17 v9 rott readbacks: 0.397..0.404 radians/second.
            # Wrap by a complete angular period so wraparound cannot jump.
            animation='direction+=mod(TOTAL_REAL_WORLD_TIME,15.707963267948966)*0.4;point.y+=sin(TOTAL_REAL_WORLD_TIME*2.0)*0.01;' if family=='enchanting_table' else ''
            if args.animation_time_control is not None:
                animation=animation.replace('TOTAL_REAL_WORLD_TIME',str(float(args.animation_time_control)))
            vertex=vertex.replace('// ANIMATION',animation)
            shader='shaders/glsl/'+name+suffix+'.vertex'
            path=args.output/('resource_pack/'+shader);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(vertex,encoding='ascii',newline='\n')
            models[name+suffix]={'dy_load':True,'mesh':mesh_name,'skeleton':PATH+'/skeleton.json','animation':{},
                'material':name+suffix,'texture':{'tex0':PATH+'/native_book'}}
            # This skeleton/WVP convention renders exterior faces with inverted
            # culling, in both UI and world. Native close-ups reject the default
            # winding: it exposes inner page faces and the dark inside cover.
            materials[name+suffix+':entity_for_skeleton_alpha']={'vertexShader':shader,
                'fragmentShader':'shaders/glsl/'+PREFIX+'geometry.fragment','+states':['Blending','InvertCulling'],
                '-states':['DisableDepthWrite','DisableCulling'],
                'blendSrc':'SourceAlpha','blendDst':'OneMinusSrcAlpha'}
    path=args.output/('resource_pack/shaders/glsl/'+PREFIX+'geometry.fragment');path.write_text(FRAGMENT,encoding='ascii',newline='\n')
    skeleton=json.loads((ROOT/'resource_pack/models/modern_projection/liquid/skeleton.json').read_bytes())
    write_json(args.output/('resource_pack/models/'+PATH+'/skeleton.json'),skeleton)
    source=args.native_data/'resource_packs/vanilla/textures/entity/enchanting_table_book.png'
    with Image.open(source) as texture:
        if texture.size!=(64,32):
            raise ValueError('Native book atlas layout changed; review the hinged model UV contract')
    destination=args.output/('resource_pack/textures/models/'+PATH+'/native_book.png');destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
    write_json(args.output/'resource_pack/models/netease_models.json',models)
    write_json(args.output/'resource_pack/materials/entity.material',{'materials':dict(materials,version='1.0.0')})
    contract={'schema_version':1,'geometry_version':GEOMETRY_VERSION,'engine_version':'3.10.0.420447','product_qualified':False,
        'closed_page_clearance_model_pixels':CLOSED_PAGE_CLEARANCE,
        'depth_write':True,'raster_culling':'front','diagnostic_animation_time':args.animation_time_control,
        'geometry_reference':'Independent hinged construction; Java 1.21.1 book dimensions and renderer poses, checked against NEMC 3.10 captures.',
        'native_texture_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'models':models,'materials':materials,
        'limits':['Project book geometry using native artwork; no proximity reaction or page text.'],
        'output_sha256':{path.relative_to(args.output).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(args.output.rglob('*')) if path.is_file()}}
    write_json(args.output/'contract.json',contract)
    if args.install_project:
        project=args.install_project
        merge_registry(project/'resource_pack/models/netease_models.json',models)
        merge_registry(project/'resource_pack/materials/entity.material',materials,nested=True)
        for source in (args.output/'resource_pack').rglob('*'):
            if source.is_file() and source.name not in ('entity.material','netease_models.json'):
                destination=project/source.relative_to(args.output);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        contract_path=project/'tools/data/book_resource_contract_nemc310_v1.json'
        contract_path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(args.output/'contract.json',contract_path)
    print(json.dumps({'models':len(models),'product_qualified':False}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-data',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--install-project',type=Path)
    parser.add_argument('--animation-time-control',type=float,
                        help='Diagnostic: freeze the book pose for paired material controls.')
    generate(parser.parse_args())


if __name__=='__main__':main()
