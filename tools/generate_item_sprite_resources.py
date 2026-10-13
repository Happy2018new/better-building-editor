"""Generate owned icon-backed skeletons from the existing versioned item source."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image
from generate_flat_item_proxies import source_path, validate_source, silhouette_cubes

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'modern_projection_item_sprite_'
ASSET = 'modern_projection/item_sprite'

VERTEX = '''// __multiversion__
precision highp float;
#include "neteaseModelVertexUtil.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
varying highp vec2 itemUv;
varying highp float itemVisible;
varying highp float itemEnchanted;
varying highp float itemClip;
void main() {
    float slot=floor(POSITION.x/2.0);
    float code=EXTRA_VECTOR1.x;
    if(slot>0.5) code=EXTRA_VECTOR1.y;
    if(slot>1.5) code=EXTRA_VECTOR1.z;
    if(slot>2.5) code=EXTRA_VECTOR1.w;
    float address=mod(code,64.0);
    float facing=mod(floor(code/64.0),8.0);
    float rotation=mod(floor(code/512.0),8.0)*0.7853981633974483;
    itemEnchanted=floor(code/4096.0);
    bool tagged=abs(EXTRA_VECTOR4.x-39687.0)<0.25 || mod(EXTRA_VECTOR4.x,256.0)==135.0;
    itemVisible=tagged && slot<EXTRA_VECTOR4.y-0.5 && facing<5.5 ? 1.0 : 0.0;
    vec3 point=vec3(mod(POSITION.x,2.0)-0.5,POSITION.y-0.5,POSITION.z);
    point.xy=mat2(cos(rotation),sin(rotation),-sin(rotation),cos(rotation))*point.xy;
    if(facing<0.5) point=vec3(point.x,point.z,-point.y);
    else if(facing<1.5) point=vec3(point.x,-point.z,point.y);
    else if(facing>2.5 && facing<3.5) point=vec3(-point.x,point.y,-point.z);
    else if(facing>3.5 && facing<4.5) point=vec3(-point.z,point.y,point.x);
    else if(facing>4.5) point=vec3(point.z,point.y,-point.x);
    point.x=-point.x;
    vec3 cell=vec3(mod(address,4.0),floor(address/16.0),mod(floor(address/4.0),4.0));
    vec3 localPoint=cell+vec3(0.5)+point-vec3(2.0);
    vec4 entityPoint=vec4(localPoint,1.0);
    // ITEM_COORDINATES
    gl_Position=WORLDVIEWPROJ*entityPoint;
    itemClip=-1.0;
    // ITEM_DEPTH
    itemUv=TEXCOORD_0;
    gl_PointSize=1.0;
}
'''

UI_COORDINATES = 'entityPoint=vec4(-localPoint.x,-localPoint.z+1.5,-localPoint.y,1.0);'
UI_DEPTH = '''if(abs(PROJ[3][3])>0.5 && mod(EXTRA_VECTOR4.x,256.0)==135.0) {
        float distance=(floor(EXTRA_VECTOR4.x/256.0)-32768.0)/64.0;
        vec3 viewPoint=vec3(-localPoint.x,-localPoint.z,-localPoint.y);
        vec3 viewZ=vec3(WORLDVIEW[0][2],WORLDVIEW[1][2],WORLDVIEW[2][2]);
        itemClip=dot(normalize(viewZ),viewPoint)+distance;
        float centerDepth=PROJ[2][2]*(-350.0)+PROJ[3][2];
        gl_Position.z=(centerDepth+itemClip*PROJ[2][2]*0.04)/(1.0+abs(centerDepth));
    }'''
WORLD_COORDINATES = '''#if defined(USE_SKINNING) && defined(NETEASE_SKINNING)
    entityPoint.z=-entityPoint.z;
    entityPoint=GetBoneMatForNetease(int(BONEID_0))*entityPoint;
#ifdef USE_INSTANCE
    entityPoint=GetInstanceWorldMatForNetease()*entityPoint;
#endif
#endif'''

FRAGMENT = '''// __multiversion__
precision highp float;
#include "fragmentVersionCentroidUV.h"
#include "uniformPerFrameConstants.h"
#include "uniformExtraVectorConstants.h"
#include "uniformShaderConstants.h"
uniform sampler2D TEXTURE_0;
varying highp vec2 itemUv;
varying highp float itemVisible;
varying highp float itemEnchanted;
varying highp float itemClip;
void main() {
    if(itemVisible<0.5 || itemClip>0.0 || EXTRA_VECTOR4.w<=0.0) discard;
    vec4 texel=texture2D(TEXTURE_0,itemUv);
    if(texel.a<0.5) discard;
    vec3 rgb=texel.rgb;
    if(itemEnchanted>0.5) {
        // Period7 divides the engine's210-second clock wrap exactly.
        float phase=TIME*6.283185307179586/7.0;
        float first=pow(0.5+0.5*sin((itemUv.x+itemUv.y)*18.84955592153876+phase),8.0);
        float second=pow(0.5+0.5*sin((itemUv.x-itemUv.y)*12.56637061435917-phase),8.0);
        rgb=clamp(rgb+vec3(0.22,0.10,0.36)*(0.20+0.45*first+0.35*second),0.0,1.0);
    }
    float alpha=EXTRA_VECTOR4.w*texel.a;
    if(abs(PROJ[3][3])>0.5) alpha*=CURRENT_COLOR.a;
    gl_FragColor=vec4(rgb,alpha);
}
'''

FACE_VERTICES = {
    'north': ((0,1,0),(1,1,0),(1,0,0),(0,0,0)),
    'south': ((1,1,1),(0,1,1),(0,0,1),(1,0,1)),
    'west': ((0,1,1),(0,1,0),(0,0,0),(0,0,1)),
    'east': ((1,1,0),(1,1,1),(1,0,1),(1,0,0)),
    'up': ((0,1,1),(1,1,1),(1,1,0),(0,1,0)),
    'down': ((0,0,0),(1,0,0),(1,0,1),(0,0,1)),
}
NORMALS = {'north': (0,0,-1), 'south': (0,0,1), 'west': (-1,0,0),
           'east': (1,0,0), 'up': (0,1,0), 'down': (0,-1,0)}


def mesh(image, pose, texture):
    vertices, indices = [], []
    cubes = silhouette_cubes(image, pose)
    for slot in range(4):
        for cube in cubes:
            for face, uv in cube['uv'].items():
                start = len(vertices)
                for corner, (u,v) in zip(FACE_VERTICES[face], ((0,0),(1,0),(1,1),(0,1))):
                    point = [cube['origin'][axis]+cube['size'][axis]*corner[axis] for axis in range(3)]
                    # Match the pre-existing netease_block model's local axes.
                    point = [slot*2.+.5+(point[0]+8.)/16., .5+(point[1]-8.)/16., (point[2]-8.)/16.]
                    texcoord = [(uv['uv'][0]+u*uv['uv_size'][0])/image.width,
                                (uv['uv'][1]+v*uv['uv_size'][1])/image.height]
                    vertices.append({'pos': point, 'normal': list(NORMALS[face]),
                                     'uvcoord': texcoord, 'weight': [['root',1.]]})
                indices.extend(((start,start+1,start+2),(start,start+2,start+3)))
    return {'mesh': [{'material': texture, 'vertices': vertices, 'indices': indices}]}


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=True)+'\n').encode('ascii')


def outputs():
    spec = json.loads(source_path().read_text(encoding='utf8'))
    manifest = json.loads((ROOT/'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    validate_source(spec, manifest)
    profile_path=ROOT/'tools/data'/('item_sprite_profile_nemc_'+spec['game_version'].removeprefix('NEMC ')+'.json')
    deployment=json.loads(profile_path.read_text(encoding='utf8'))
    if (deployment.get('schema')!=1 or deployment.get('payload_version')!=1 or
            deployment.get('game_version')!=spec['game_version'] or
            deployment.get('palette_sha256')!=spec['palette_sha256'] or
            type(deployment.get('production_qualified')) is not bool or
            type(deployment.get('max_groups')) is not int or deployment['max_groups']<1):
        raise ValueError('Item sprite deployment belongs to a different version or payload')
    registry = json.loads((ROOT/'resource_pack/models/netease_models.json').read_text(encoding='utf8'))
    materials = json.loads((ROOT/'resource_pack/materials/entity.material').read_text(encoding='utf8'))
    result, profiles, owned_registry, owned_materials = {}, {}, {}, {}
    bounds = [[-2.,-2.,-2.],[2.,2.,2.]]
    skeleton = {'boundingbox': bounds, 'skeleton': [{'name':'root','parent':'root',
        'initpos':[0.,0.,0.],'initquaternion':[0.,0.,0.,1.],'initscale':[1.,1.,1.],
        'offmtx':[[1.,0.,0.,0.],[0.,1.,0.,0.],[0.,0.,1.,0.]],'boundingbox':bounds}]}
    result['resource_pack/models/'+ASSET+'/skeleton.json'] = encoded(skeleton)
    result['resource_pack/shaders/glsl/modern_projection_item_sprite.vertex'] = VERTEX.replace(
        '// ITEM_COORDINATES',UI_COORDINATES).replace('// ITEM_DEPTH',UI_DEPTH).encode('ascii')
    result['resource_pack/shaders/glsl/modern_projection_item_sprite_world.vertex'] = VERTEX.replace(
        '// ITEM_COORDINATES',WORLD_COORDINATES).replace('    // ITEM_DEPTH\n','').encode('ascii')
    result['resource_pack/shaders/glsl/modern_projection_item_sprite.fragment'] = FRAGMENT.encode('ascii')
    for item in spec['items']:
        key = (item['identifier'],item['aux'])
        name = item['identifier'].replace(':','_')+'_'+str(item['aux'])
        data = (ROOT/item['generated_texture']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=item['texture_sha256']:
            raise ValueError('Existing versioned item bitmap changed')
        with Image.open(ROOT/item['generated_texture']) as image:
            texture = ASSET+'/'+name
            result['resource_pack/models/'+ASSET+'/'+name+'_mesh.json'] = encoded(mesh(image,spec['frame_pose'],texture))
        result['resource_pack/textures/models/'+ASSET+'/'+name+'.png'] = data
        names = {}
        for suffix in ('','_world'):
            model = PREFIX+name+suffix
            registry[model] = {'dy_load':True,'mesh':ASSET+'/'+name+'_mesh.json',
                'skeleton':ASSET+'/skeleton.json','animation':{},'material':model,'texture':{'tex0':texture}}
            materials['materials'][model+':entity_for_skeleton_alpha'] = {
                'vertexShader':'shaders/glsl/modern_projection_item_sprite'+suffix+'.vertex',
                'fragmentShader':'shaders/glsl/modern_projection_item_sprite.fragment',
                '+states':['Blending','DisableCulling'],
                'blendSrc':'SourceAlpha','blendDst':'OneMinusSrcAlpha',
                '+samplerStates':[{'samplerIndex':0,'textureFilter':'Point'}]}
            owned_registry[model]=registry[model]
            owned_materials[model+':entity_for_skeleton_alpha']=materials['materials'][model+':entity_for_skeleton_alpha']
            names['world_model' if suffix else 'ui_model'] = model
        profiles[key] = dict(names, texture_sha256=item['texture_sha256'],
                            family='flat_icon', sprite_size_pixels=spec['frame_pose']['size_pixels'])
    contract_parts=dict(result, owned_registry=encoded(owned_registry),owned_materials=encoded(owned_materials))
    contract = hashlib.sha256(b''.join(path.encode('ascii')+data for path,data in sorted(contract_parts.items()))).hexdigest()
    if deployment['production_qualified'] and (
            deployment['qualification_resource_sha256']!=contract or
            not isinstance(deployment['qualification_sha256'],str) or
            len(deployment['qualification_sha256'])!=64 or
            any(value not in '0123456789abcdef' for value in deployment['qualification_sha256'])):
        raise ValueError('Item sprite production qualification does not match the generated resources')
    result['resource_pack/models/netease_models.json'] = encoded(registry)
    result['resource_pack/materials/entity.material'] = encoded(materials)
    result['behavior_pack/modern_projection/projection/item_sprite_data.py'] = (
        '"""Generated by tools/generate_item_sprite_resources.py; do not edit."""\n'
        'SCHEMA_VERSION = 1\nPAYLOAD_VERSION = 1\nSOURCE_VERSION = '+repr(spec['game_version'])+'\n'
        'PALETTE_SHA256 = '+repr(spec['palette_sha256'])+'\nRESOURCE_SHA256 = '+repr(contract)+'\n'
        'MAX_GROUPS = '+repr(deployment['max_groups'])+'\n'
        'PRODUCTION_QUALIFIED = '+repr(deployment['production_qualified'])+'\n'
        'QUALIFICATION_SHA256 = '+repr(deployment['qualification_sha256'])+'\n'
        'QUALIFICATION_RESOURCE_SHA256 = '+repr(deployment['qualification_resource_sha256'])+'\n'
        'ITEMS = '+repr(profiles)+'\n').encode('ascii')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    stale = []
    for relative,data in outputs().items():
        path = ROOT/relative
        if args.check:
            equal = path.exists() and (path.read_bytes()==data if path.suffix=='.png' else
                    path.read_text(encoding='utf8')==data.decode('ascii'))
            if not equal:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(data)
    if stale:
        raise SystemExit('Stale item sprite outputs: '+', '.join(stale))


if __name__=='__main__':
    main()
