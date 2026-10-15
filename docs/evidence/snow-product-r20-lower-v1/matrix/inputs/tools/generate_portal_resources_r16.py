"""Generate bounded portal surfaces from installed native starfield artwork.

The four-cell geometry payload reuses the existing transport and lifecycle.
The starfield is a declared project style, not exact native ray-plane parity.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

from generate_liquid_product_resources import merge_registry, write_json
from generate_liquid_skeleton_resources import VERTEX, UI_COORDINATES, WORLD_BONE, mesh

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'modern_projection_portal_'
ASSET_PATH = 'modern_projection/portal'
FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformInterFrameConstants.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
#include "uniformWorldConstants.h"
uniform sampler2D TEXTURE_0;
uniform sampler2D TEXTURE_1;
varying highp vec2 portalUv;
varying highp float portalVisible;
varying highp float portalClip;

vec3 starLayer(vec2 uv,float scale,float phase,float time) {
    float angle=phase+time*0.035;
    vec2 direction=vec2(cos(angle),sin(angle));
    vec2 point=uv*scale+direction*phase+vec2(time*0.031,time*0.019);
    float sparkle=smoothstep(0.58,0.72,texture2D(TEXTURE_0,fract(point)).r);
    vec2 lookup=vec2(mod(phase,4.0),floor(phase/4.0))*0.25+vec2(0.125);
    return sparkle*texture2D(TEXTURE_1,lookup).rgb;
}

void main() {
    if(portalVisible<0.5 || portalClip>0.0 || EXTRA_VECTOR4.w<=0.0) discard;
    float time=mod(TOTAL_REAL_WORLD_TIME,512.0);
    vec3 stars=starLayer(portalUv,1.0,0.0,time)*0.55+
               starLayer(portalUv,1.7,5.0,time)*0.48+
               starLayer(portalUv,2.6,10.0,time)*0.40;
    float alpha=EXTRA_VECTOR4.w;
    if(abs(PROJ[3][3])>0.5) alpha*=CURRENT_COLOR.a;
    if(alpha<=0.0) discard;
    gl_FragColor=vec4(min(vec3(0.015,0.025,0.035)+stars,vec3(1.0)),alpha);
}
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def vertices(world):
    header = (ROOT / 'resource_pack/shaders/glsl/modern_projection_liquid_preview_depth.h').read_text(encoding='ascii')
    source = VERTEX.replace('// LIQUID_PREVIEW_HEADER', '' if world else header)
    source = source.replace('// LIQUID_UI_COORDINATES', '' if world else UI_COORDINATES)
    source = source.replace('// LIQUID_WORLD_BONE', WORLD_BONE if world else '')
    source = source.replace('// LIQUID_PREVIEW_DEPTH', '' if world else
        'liquidUniformPreviewDepth(vec3(-localPoint.x,-localPoint.z,-localPoint.y),EXTRA_VECTOR4.x,gl_Position,liquidClip);')
    return source.replace('liquid', 'portal')


def generate(native, output):
    if output.exists():
        raise ValueError('Choose a fresh portal generation directory')
    shaders = output / 'resource_pack/shaders/glsl'
    shaders.mkdir(parents=True)
    for world in (False, True):
        suffix = '_world' if world else ''
        (shaders / (PREFIX+'geometry'+suffix+'.vertex')).write_text(vertices(world),encoding='ascii',newline='\n')
    (shaders / (PREFIX+'starfield.fragment')).write_text(FRAGMENT,encoding='ascii',newline='\n')
    skeleton = json.loads((ROOT/'resource_pack/models/modern_projection/liquid/skeleton.json').read_bytes())
    write_json(output/('resource_pack/models/'+ASSET_PATH+'/skeleton.json'),skeleton)
    models, materials, textures = {}, {}, {}
    for artwork,size in (('end_sky',(128,128)),('end_portal_colors',(4,4))):
        source = native / ('resource_packs/vanilla/textures/environment/'+artwork+'.png')
        with Image.open(source) as artwork:
            if artwork.size != size:
                raise ValueError('Native portal artwork changed dimensions')
        name=source.stem
        textures[name] = {'source':source.relative_to(native).as_posix(),
                          'sha256':digest(source),'size':size}
        destination=output/('resource_pack/textures/models/'+ASSET_PATH+'/'+name+'.png')
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)
    for family in ('end_portal','end_gateway'):
        texture = ASSET_PATH+'/'+family
        mesh_name = texture+'_mesh.json'
        write_json(output/('resource_pack/models/'+mesh_name),mesh(texture,top_only=family=='end_portal'))
        for world in (False,True):
            suffix = '_world' if world else ''
            name = PREFIX+family+suffix
            models[name] = {'dy_load':True,'mesh':mesh_name,'skeleton':ASSET_PATH+'/skeleton.json',
                            'animation':{},'material':name,'texture':{
                                'tex0':ASSET_PATH+'/end_sky','tex1':ASSET_PATH+'/end_portal_colors'}}
            materials[name+':entity_for_skeleton_alpha'] = {
                'vertexShader':'shaders/glsl/'+PREFIX+'geometry'+suffix+'.vertex',
                'fragmentShader':'shaders/glsl/'+PREFIX+'starfield.fragment',
                '+states':['Blending','DisableCulling'],
                '-states':['DisableDepthWrite'],
                'blendSrc':'SourceAlpha','blendDst':'OneMinusSrcAlpha',
                'samplerStates':[{'samplerIndex':0,'textureFilter':'Point','textureWrap':'Repeat'},
                                 {'samplerIndex':1,'textureFilter':'Point','textureWrap':'Repeat'}]}
    write_json(output/'resource_pack/models/netease_models.json',models)
    write_json(output/'resource_pack/materials/entity.material',{'materials':dict(materials,version='1.0.0')})
    contract = {'schema_version':1,'engine_version':'3.10.0.420447','payload_version':2,
        'style':'native_artwork_layered_starfield_v1','native_parity_claimed':False,
        'depth_write':True,
        'end_portal_height':.75,'end_gateway_faces':6,'clock':'TOTAL_REAL_WORLD_TIME',
        'textures':textures,'models':models,'materials':materials,'requires_visual_qualification':True,
        'limits':['Finite surfaces only; gateway cooldown and transient activation beam remain pending. No teleportation or particles.'],
        'output_sha256':{p.relative_to(output).as_posix():digest(p)
                         for p in sorted(output.rglob('*')) if p.is_file()}}
    write_json(output/'contract.json',contract)
    return contract


def install(output,project):
    for relative,nested in (('resource_pack/models/netease_models.json',False),
                            ('resource_pack/materials/entity.material',True)):
        values = json.loads((output/relative).read_bytes())
        if nested:
            values = dict((key,value) for key,value in values['materials'].items() if key!='version')
        merge_registry(project/relative,values,nested=nested)
    for source in (output/'resource_pack').rglob('*'):
        if source.is_file() and source.name not in ('netease_models.json','entity.material'):
            destination = project/source.relative_to(output)
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source,destination)
    shutil.copyfile(output/'contract.json',project/'tools/data/portal_resource_contract_nemc310_v1.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--native-data',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--install-project',type=Path)
    args = parser.parse_args()
    contract = generate(args.native_data,args.output)
    if args.install_project:
        install(args.output,args.install_project)
    print(json.dumps({'models':len(contract['models']),'style':contract['style']}))


if __name__=='__main__':
    main()
