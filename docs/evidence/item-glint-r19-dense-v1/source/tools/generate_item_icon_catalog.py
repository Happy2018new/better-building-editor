"""Generate deduplicated flat-item silhouettes from measured engine resolution.

GetItemTexture alone is not proof of a flat renderer: special item families are
classified separately, and block items remain on their native 3-D content route.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from PIL import Image
from generate_item_sprite_resources import encoded, mesh, VERTEX, UI_COORDINATES, UI_DEPTH, WORLD_COORDINATES, FRAGMENT

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.10.0.420447'
PREFIX = 'modern_projection_item_icon_'
ASSET = 'modern_projection/item_icons'
SPECIAL_TYPES = {'block': 'block_geometry', 'potion': 'tinted_potion',
                 'clock': 'dynamic_clock', 'compass': 'dynamic_compass',
                 'trident': 'special_geometry', 'crossbow': 'content_geometry'}
SPECIAL_IDS = {'minecraft:banner': 'patterned_geometry', 'minecraft:shield': 'patterned_geometry',
               'minecraft:filled_map': 'map_surface', 'minecraft:empty_map': 'map_surface',
               'minecraft:lodestone_compass': 'dynamic_compass',
               'minecraft:recovery_compass': 'dynamic_compass',
               'minecraft:firework_star': 'tinted_icon', 'minecraft:tipped_arrow': 'tinted_icon'}
SPECIAL_TAGS = {'minecraft:spawn_egg': 'tinted_spawn_egg',
                'minecraft:leather_tier': 'tinted_leather'}
POSE = {'size_pixels': 8., 'thickness_pixels': .5, 'front_z_pixels': 15.,
        'upward_base_rotation_degrees': 180., 'rotation_sign': -1.,
        'side_uv': 'opaque_texel_center_v1'}
LAYOUT = '''float itemLayout=EXTRA_VECTOR2.x;
    if(slot>0.5) itemLayout=EXTRA_VECTOR2.y;
    if(slot>1.5) itemLayout=EXTRA_VECTOR2.z;
    if(slot>2.5) itemLayout=EXTRA_VECTOR2.w;
    if(itemLayout>0.5 && itemLayout<3.5) {
        point.xy*=0.5;
        point.x+=(itemLayout-2.0)*0.3;
        point.z=0.3125;
    } else if(itemLayout>3.5) {
        float index=itemLayout-4.0;
        point.xy*=0.6;
        point.x+=(mod(index,2.0)-0.5)*0.5;
        point.y+=(floor(index/2.0)-0.5)*0.5;
        point.z=0.05;
    }'''
GLINT_TEXTURE = 'textures/misc/enchanted_item_glint'
GLINT_RESOURCE = 'modern_projection/item_icons/enchanted_glint'
GLINT = {'schema': 1, 'uv_scale': .5, 'rotations_degrees': (30., -30.),
         'cycles_per_second': (.2, -.1), 'color': (.38, .19, .61),
         'unscaled_offset_per_second': (.4, -.2),
         'transform_order': 'center_rotate_offset_recenter_scale',
         'clock_wrap_seconds': 210., 'blend': 'squared_two_native_texture_layers'}
ICON_GLINT = '''vec2 centered=itemUv-vec2(0.5);
        float clock=mod(TIME,210.0);
        // The 3.10 entity path scales after rotation, offset and recentering.
        // These TIME offsets retain .2/-.1 texture cycles per second at scale .5;
        // engine-owned UV_OFFSET / UV_ROTATION are not available on this route.
        vec2 firstUv=mat2(0.866025403784439,-0.5,0.5,0.866025403784439)*centered;
        vec2 secondUv=mat2(0.866025403784439,0.5,-0.5,0.866025403784439)*centered;
        firstUv=(firstUv+vec2(clock*0.4,0.0)+vec2(0.5))*0.5;
        secondUv=(secondUv-vec2(clock*0.2,0.0)+vec2(0.5))*0.5;
        float first=texture2D(TEXTURE_1,fract(firstUv)).r;
        float second=texture2D(TEXTURE_1,fract(secondUv)).r;
        vec3 glint=vec3(0.38,0.19,0.61)*(first+second);
        rgb=clamp(rgb+glint*glint,0.0,1.0);'''


def sha(data):
    return hashlib.sha256(data).hexdigest()


def icon_mesh(image,pose,texture):
    generated = mesh(image,pose,texture)
    vertices = generated['mesh'][0]['vertices']
    for index in range(0,len(vertices),4):
        face = vertices[index:index+4]
        if face[0]['normal'][2]:
            continue
        center = [sum(vertex['uvcoord'][axis] for vertex in face)/4. for axis in range(2)]
        for vertex in face:
            vertex['uvcoord'] = list(center)
    return generated


def classify(name, info, texture):
    if not isinstance(info, dict):
        return 'missing_basic_info'
    kind = info.get('itemType')
    if kind in SPECIAL_TYPES:
        return SPECIAL_TYPES[kind]
    if name in SPECIAL_IDS:
        return SPECIAL_IDS[name]
    for tag in info.get('tags', ()):
        if tag in SPECIAL_TAGS:
            return SPECIAL_TAGS[tag]
    if not isinstance(texture, str) or not texture.startswith('textures/items/'):
        return 'non_item_texture'
    if 'chemistry' in texture or info.get('itemCategory') == 'education':
        return 'education_excluded'
    if name.endswith('_spear') or name.endswith('_harness'):
        return 'special_geometry'
    return 'flat_icon_candidate'


def build_catalog(raw, basic, install):
    if any(row.get('schema') != 1 or row.get('completed') is not True or
           row.get('engine_version') != VERSION for row in (raw, basic)):
        raise ValueError('Catalog inputs must be complete observations from the target engine')
    infos = {row['name']: row['value'] for row in basic['rows']}
    items, resources, unsupported = [], {}, {}
    packs = install / 'data/resource_packs'
    atlases = [(path, json.loads(path.read_text(encoding='utf8')))
               for pack in ('vanilla', 'vanilla_base', 'vanilla_netease')
               if (path := packs / pack / 'textures/item_texture.json').is_file()]
    for row in raw['rows']:
        name, aux = row['name'], row['aux']
        texture = row.get('texture', row.get('value'))
        family = classify(name, infos.get(name), texture)
        if family != 'flat_icon_candidate':
            unsupported.setdefault(name, family)
            continue
        atlas = next(((path, value) for path, value in atlases
                      if any(texture in texture_paths(entry)
                             for entry in value['texture_data'].values())), None)
        bitmap = next((packs / pack / (texture+'.png') for pack in
                       ('vanilla', 'vanilla_base', 'vanilla_netease')
                       if (packs / pack / (texture+'.png')).is_file()), None)
        if atlas is None or bitmap is None:
            unsupported.setdefault(name, 'missing_versioned_bitmap_or_atlas')
            continue
        data = bitmap.read_bytes()
        with Image.open(bitmap) as image:
            alpha = image.convert('RGBA').getchannel('A')
            if set(alpha.getdata()) - {0, 255} or not alpha.getbbox():
                unsupported.setdefault(name, 'intermediate_alpha_or_empty_bitmap')
                continue
            if image.width != image.height or image.width > 64:
                unsupported.setdefault(name, 'non_square_or_oversized_bitmap')
                continue
            digest, size = sha(data), list(image.size)
        key = digest[:16]
        old = resources.get(key)
        if old and old['sha256'] != digest:
            raise ValueError('Texture resource identity collision')
        resources[key] = {'sha256': digest, 'size': size, 'texture_path': texture,
                          'source_pack': bitmap.relative_to(packs).parts[0],
                          'atlas_sha256': sha(atlas[0].read_bytes())}
        info = infos[name]
        items.append({'name': name, 'aux': aux, 'resource': key,
                      'max_durability': info.get('maxDurability', 0),
                      'item_type': info.get('itemType', '')})
    glint_path = packs / 'vanilla' / (GLINT_TEXTURE+'.png')
    glint = dict(GLINT, texture_sha256=sha(glint_path.read_bytes()), texture_path=GLINT_TEXTURE,
                 source_pack='vanilla')
    return {'schema': 1, 'engine_version': VERSION, 'pose': POSE, 'glint': glint,
            'source_texture_catalog_sha256': sha(encoded(raw)),
            'source_basic_catalog_sha256': sha(encoded(basic)),
            'measured_pairs': len(raw['rows']), 'loaded_vanilla_ids': len(infos),
            'items': items, 'resources': resources, 'unsupported': unsupported,
            'production_qualified': False, 'pixel_qualification': None}


def texture_paths(entry):
    value = entry['textures']
    values = value if isinstance(value, list) else [value]
    return [row['path'] if isinstance(row, dict) else row for row in values]


def outputs(catalog, install):
    for key,value in GLINT.items():
        expected=list(value) if isinstance(value,tuple) else value
        actual=catalog.get('glint',{}).get(key)
        actual=list(actual) if isinstance(actual,tuple) else actual
        if actual!=expected:
            raise ValueError('Glint catalog metadata differs from generated shader: '+key)
    if catalog.get('schema') != 1 or catalog.get('engine_version') != VERSION:
        raise ValueError('Item icon catalog requires target-engine regeneration')
    if catalog.get('pose') != POSE:
        raise ValueError('Item icon pose contract requires regeneration from measured catalogs')
    glint = catalog.get('glint',{})
    if any(json.dumps(glint.get(key)) != json.dumps(value) for key,value in GLINT.items()):
        raise ValueError('Item icon glint contract requires regeneration from measured catalogs')
    result, registry, materials, profiles = {}, {}, {}, {}
    # Own and fingerprint the actual skeleton used by these registrations.
    # Changing the legacy sprite skeleton must not silently change icon bounds.
    skeleton_path = 'resource_pack/models/'+ASSET+'/skeleton.json'
    result[skeleton_path] = (ROOT/'resource_pack/models/modern_projection/item_sprite/skeleton.json').read_bytes()
    vertex = VERTEX.replace('    point.xy=mat2', '    '+LAYOUT+'\n'
        '    if(facing>0.5 && facing<1.5 && itemLayout<0.5) point.xy=-point.xy;\n'
        '    if(itemLayout<0.5) rotation=-rotation;\n'
        '    point.xy=mat2')
    result['resource_pack/shaders/glsl/modern_projection_item_icon.vertex'] = vertex.replace(
        '// ITEM_COORDINATES', UI_COORDINATES).replace('// ITEM_DEPTH', UI_DEPTH).encode('ascii')
    result['resource_pack/shaders/glsl/modern_projection_item_icon_world.vertex'] = vertex.replace(
        '// ITEM_COORDINATES', WORLD_COORDINATES).replace('    // ITEM_DEPTH\n', '').encode('ascii')
    fragment = FRAGMENT.replace('uniform sampler2D TEXTURE_0;',
                                'uniform sampler2D TEXTURE_0;\nuniform sampler2D TEXTURE_1;')
    start, end = fragment.index('        // Period7'), fragment.index('\n    }',fragment.index('        // Period7'))
    fragment = fragment[:start]+'        '+ICON_GLINT+fragment[end:]
    result['resource_pack/shaders/glsl/modern_projection_item_icon.fragment'] = fragment.encode('ascii')
    glint_bitmap = (install/'data/resource_packs'/glint['source_pack']/(glint['texture_path']+'.png')).read_bytes()
    if sha(glint_bitmap) != glint['texture_sha256']:
        raise ValueError('Installed native glint texture differs from the measured contract')
    result['resource_pack/textures/models/'+GLINT_RESOURCE+'.png'] = glint_bitmap
    for key, resource in sorted(catalog['resources'].items()):
        path = install / 'data/resource_packs' / resource['source_pack'] / (resource['texture_path']+'.png')
        bitmap = path.read_bytes()
        if sha(bitmap) != resource['sha256']:
            raise ValueError('Installed item texture differs from measured source')
        texture = ASSET+'/'+key
        result['resource_pack/textures/models/'+texture+'.png'] = bitmap
        with Image.open(path) as image:
            result['resource_pack/models/'+texture+'_mesh.json'] = (json.dumps(
                icon_mesh(image, catalog['pose'], texture), separators=(',', ':'))+'\n').encode('ascii')
        for suffix in ('', '_world'):
            name = PREFIX+key+suffix
            registry[name] = {'dy_load': True, 'mesh': texture+'_mesh.json',
                              'skeleton': ASSET+'/skeleton.json',
                              'animation': {}, 'material': 'modern_projection_item_icon'+suffix,
                              'texture': {'tex0': texture, 'tex1': GLINT_RESOURCE}}
    for suffix in ('', '_world'):
        materials['modern_projection_item_icon'+suffix+':entity_for_skeleton_alpha'] = {
            'vertexShader': 'shaders/glsl/modern_projection_item_icon'+suffix+'.vertex',
            'fragmentShader': 'shaders/glsl/modern_projection_item_icon.fragment',
            '+states': ['Blending', 'DisableCulling'], 'blendSrc': 'SourceAlpha',
            '-states': ['DisableDepthWrite'],
            'blendDst': 'OneMinusSrcAlpha',
            '+samplerStates': [{'samplerIndex': 0, 'textureFilter': 'Point'},
                               {'samplerIndex': 1, 'textureFilter': 'Bilinear'}]}
    rows_by_name = {}
    for row in catalog['items']:
        rows_by_name.setdefault(row['name'], []).append(row)
    for name, rows in sorted(rows_by_name.items()):
        durable = rows[0]['max_durability'] if len({row['resource'] for row in rows}) == 1 else 0
        for resource in sorted({row['resource'] for row in rows}):
            observed = tuple(row['aux'] for row in rows if row['resource'] == resource)
            canonical = (name, min(observed))
            key = canonical
            profiles[key] = {'ui_model': PREFIX+resource, 'world_model': PREFIX+resource+'_world',
                             'texture_sha256': catalog['resources'][resource]['sha256'],
                             'family': 'flat_icon', 'sprite_size_pixels': catalog['pose']['size_pixels'],
                             'resource_key': canonical, 'observed_aux': observed,
                             'max_durability': durable}
    registrations = {'schema': 1, 'engine_version': VERSION, 'models': registry, 'materials': materials}
    result['tools/data/item_icon_registrations_nemc_'+VERSION+'.json'] = encoded(registrations)
    contract = sha(b''.join(path.encode('ascii')+data for path, data in sorted(result.items())))
    result['behavior_pack/modern_projection/projection/item_icon_data.py'] = (
        '"""Generated measured flat-icon candidates; source and pixel gates are separate."""\n'
        'SCHEMA_VERSION = 1\nLAYOUT_VERSION = 1\nENGINE_VERSION = '+repr(VERSION)+'\n'
        'RESOURCE_SHA256 = '+repr(contract)+'\nPRODUCTION_QUALIFIED = False\n'
        'QUALIFICATION_SHA256 = None\nQUALIFICATION_RESOURCE_SHA256 = None\n'
        'QUALIFIED_FAMILIES = ()\nMAX_GROUPS = 256\n'
        'ITEMS = '+repr(profiles)+'\nUNSUPPORTED = '+repr(catalog['unsupported'])+'\n').encode('ascii')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--texture-observations', type=Path)
    parser.add_argument('--basic-observations', type=Path)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, default=ROOT/'tools/data'/('item_icon_catalog_nemc_'+VERSION+'.json'))
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--register', action='store_true')
    args = parser.parse_args()
    if args.texture_observations or args.basic_observations:
        if not args.texture_observations or not args.basic_observations:
            parser.error('Both measured catalogs are required')
        catalog = build_catalog(json.loads(args.texture_observations.read_bytes()),
                                json.loads(args.basic_observations.read_bytes()), args.install)
        args.catalog.write_bytes(encoded(catalog))
    else:
        catalog = json.loads(args.catalog.read_bytes())
    result = outputs(catalog, args.install)
    if args.register:
        registration = json.loads(result['tools/data/item_icon_registrations_nemc_'+VERSION+'.json'])
        registry = json.loads((ROOT/'resource_pack/models/netease_models.json').read_bytes())
        materials = json.loads((ROOT/'resource_pack/materials/entity.material').read_bytes())
        registry.update(registration['models'])
        materials['materials'].update(registration['materials'])
        result['resource_pack/models/netease_models.json'] = encoded(registry)
        result['resource_pack/materials/entity.material'] = encoded(materials)
    stale = []
    for relative, data in result.items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if stale:
        raise SystemExit('Stale measured item icon resources: '+', '.join(stale))
    print(json.dumps({'item_pairs': len(catalog['items']), 'item_ids': len({row['name'] for row in catalog['items']}),
                      'bitmaps': len(catalog['resources']), 'unsupported_ids': len(catalog['unsupported']),
                      'output_bytes': sum(len(data) for data in result.values())}))


if __name__ == '__main__':
    main()
