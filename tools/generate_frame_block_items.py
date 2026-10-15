"""Exact-version full-cube frame candidates; source identity is not pixel acceptance."""
import argparse
from collections import Counter
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

from generate_item_sprite_resources import FACE_VERTICES, NORMALS, encoded

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry

VERSION = '3.10.0.420447'
ASSET = 'modern_projection/frame_block_items'
PREFIX = 'modern_projection_frame_block_'
CATALOG = ROOT / 'tools/data' / ('frame_block_item_catalog_nemc_' + VERSION + '.json')
SHAPE_EXCLUSIONS = frozenset(('beacon', 'mob_spawner', 'trial_spawner', 'vault',
    'honey_block', 'camera', 'barrier', 'allow', 'deny', 'chemical_heat',
    'client_request_placeholder_block', 'unknown', 'reserved6', 'info_update',
    'info_update2', 'netherreactor', 'structure_block', 'jigsaw'))
DEFINITION_ALIASES = {'grass_block': 'grass', 'sea_lantern': 'seaLantern'}
POSE = {'schema': 1, 'shape': 'full_cube', 'scale_blocks': .5,
        'center_offset_blocks': [0., 0., .1875], 'accepted': False,
        'status': 'provisional_3d_pose_requires_native_six_face_rotation_depth_controls'}
MATERIALS = ('opaque', 'cutout', 'translucent')


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Unsupported(ValueError):
    pass


def load(path):
    return json.loads(path.read_bytes())


def source_records(install):
    if install.name != VERSION:
        raise ValueError('Frame block assets require the measured target engine')
    packs = install / 'data/resource_packs'
    blocks, terrain, sources, animations = {}, {}, {}, []
    for pack in ('vanilla_base', 'vanilla', 'vanilla_netease'):
        for filename, target in (('blocks.json', blocks), ('textures/terrain_texture.json', terrain)):
            path = packs / pack / filename
            if path.is_file():
                data = load(path)
                values = data.get('texture_data', {}) if filename.startswith('textures/') else data
                target.update((key, {'pack': pack, 'value': value})
                              for key, value in values.items() if key != 'format_version')
                sources[pack + '/' + filename] = sha(path.read_bytes())
        flipbook = packs / pack / 'textures/flipbook_textures.json'
        if flipbook.is_file():
            rows = load(flipbook)
            if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
                raise ValueError('Native flipbook metadata must be a list of records')
            animations.extend({'pack': pack, 'value': row} for row in rows)
            sources[pack + '/textures/flipbook_textures.json'] = sha(flipbook.read_bytes())
    for key, record in terrain.items():
        try:
            relative = texture_entry(record['value'])['path']
        except Unsupported:
            relative = None
        record['animations'] = [row for row in animations if
            row['value'].get('atlas_tile') == key or
            (relative is not None and row['value'].get('flipbook_texture') == relative)]
    return packs, blocks, terrain, sources


def face_keys(definition):
    selection = 'carried_textures' if 'carried_textures' in definition else 'textures'
    textures = definition.get(selection)
    if isinstance(textures, str):
        return selection, dict.fromkeys(FACE_VERTICES, textures)
    if not isinstance(textures, dict):
        raise Unsupported('missing_six_face_texture_definition')
    keys = {face: textures.get(face, textures.get('side')) for face in FACE_VERTICES}
    if not all(isinstance(value, str) for value in keys.values()):
        raise Unsupported('incomplete_six_face_texture_definition')
    return selection, keys


def texture_entry(record):
    if set(record) - {'textures', 'additive'} or record.get('additive', False):
        raise Unsupported('unsupported_atlas_entry_modifier')
    values = record.get('textures')
    if isinstance(values, list):
        # Geometry variants are resolved to a modern block name before this step.
        # Multiple entries can represent biome/state selection, not item aux.
        if len(values) != 1:
            raise Unsupported('ambiguous_atlas_variant_selection')
        values = values[0]
    if isinstance(values, str):
        values = {'path': values}
    if not isinstance(values, dict) or set(values) - {'path', 'tint_color', 'overlay_color'}:
        raise Unsupported('unsupported_texture_modifier')
    if not isinstance(values.get('path'), str):
        raise Unsupported('missing_texture_path')
    return values


def color(value):
    if (not isinstance(value, str) or len(value) != 7 or not value.startswith('#') or
            any(char not in '0123456789abcdefABCDEF' for char in value[1:])):
        raise Unsupported('unsupported_texture_color')
    return np.array([int(value[index:index + 2], 16) / 255. for index in (1, 3, 5)])


def bake_texture(image, entry):
    rgba = np.asarray(image.convert('RGBA'), dtype=np.float64).copy()
    operations = []
    if 'tint_color' in entry:
        rgba[:, :, :3] *= color(entry['tint_color'])
        operations.append('rgb_tint')
    if 'overlay_color' in entry:
        # Native terrain TGA alpha selects the untinted base versus tinted overlay.
        # This candidate recipe remains gated on actual carried-texture pixels.
        mask = rgba[:, :, 3:4] / 255.
        rgba[:, :, :3] *= mask + (1. - mask) * color(entry['overlay_color'])
        rgba[:, :, 3] = 255.
        operations.append('alpha_mask_overlay_pending_native_pixels')
    return Image.fromarray(np.rint(rgba).clip(0, 255).astype(np.uint8)), operations


def resolve_face(packs, terrain, key):
    record = terrain.get(key)
    if record is None:
        raise Unsupported('missing_terrain_atlas_key')
    entry = texture_entry(record['value'])
    relative = entry['path']
    if not relative.startswith('textures/') or '..' in Path(relative).parts:
        raise Unsupported('invalid_native_texture_path')
    path = next((packs / pack / (relative + extension)
                 for pack in ('vanilla_netease', 'vanilla', 'vanilla_base')
                 for extension in ('.tga', '.png')
                 if (packs / pack / (relative + extension)).is_file()), None)
    if path is None:
        raise Unsupported('missing_native_bitmap')
    with Image.open(path) as source:
        image = source.convert('RGBA')
    source_size = list(image.size)
    degradation = []
    if record['animations']:
        degradation.append('animated_texture_frozen_source_snapshot')
    if image.width != image.height:
        if image.height % image.width or image.width > 64:
            raise Unsupported('unsupported_bitmap_layout')
        image = image.crop((0, 0, image.width, image.width))
        degradation.append('animated_texture_frozen_first_frame')
    if image.width > 64 or image.width < 1:
        raise Unsupported('unsupported_bitmap_size')
    image, operations = bake_texture(image, entry)
    return image, {'atlas_key': key, 'atlas_pack': record['pack'], 'entry': record['value'],
                   'path': path.relative_to(packs).as_posix(), 'sha256': sha(path.read_bytes()),
                   'size': list(image.size), 'source_size': source_size,
                   'operations': operations, 'degradation': degradation,
                   'native_flipbooks': record['animations']}


def shape_reason(name, info, metadata):
    short = name.removeprefix('minecraft:')
    if info.get('itemType') != 'block':
        return 'not_native_block_item'
    if info.get('itemCategory') == 'education' or short.startswith('element_'):
        return 'education_excluded'
    if short in SHAPE_EXCLUSIONS or 'slab' in short:
        return 'special_or_separate_geometry_adapter'
    if metadata.get(name, {}).get('solid') is True:
        return None
    if short == 'glass' or short.endswith('_stained_glass'):
        return None
    return 'full_cube_geometry_not_established'


def material_kind(images):
    alpha = {value for image in images.values() for value in image.getchannel('A').getdata()}
    if not alpha or alpha == {0}:
        raise Unsupported('empty_native_bitmap')
    if alpha == {255}:
        return 'opaque'
    return 'cutout' if alpha <= {0, 255} else 'translucent'


def atlas_image(images):
    size = max(max(image.size) for image in images.values())
    # One-texel edge padding also protects later linear-filter diagnostics.
    pitch = size + 2
    atlas = Image.new('RGBA', (pitch * 3, pitch * 2))
    rectangles = {}
    for index, (face, image) in enumerate(images.items()):
        if image.size != (size, size):
            image = image.resize((size, size), Image.Resampling.NEAREST)
        x, y = index % 3 * pitch + 1, index // 3 * pitch + 1
        atlas.paste(image, (x, y))
        atlas.paste(image.crop((0, 0, 1, size)), (x - 1, y))
        atlas.paste(image.crop((size - 1, 0, size, size)), (x + size, y))
        atlas.paste(image.crop((0, 0, size, 1)), (x, y - 1))
        atlas.paste(image.crop((0, size - 1, size, size)), (x, y + size))
        for dx, sx in ((-1, 0), (size, size - 1)):
            for dy, sy in ((-1, 0), (size, size - 1)):
                atlas.putpixel((x + dx, y + dy), image.getpixel((sx, sy)))
        rectangles[face] = [x / atlas.width, y / atlas.height,
                            (x + size) / atlas.width, (y + size) / atlas.height]
    output = BytesIO()
    atlas.save(output, format='PNG', optimize=False)
    return output.getvalue(), rectangles


def cube_mesh(rectangles, texture, pose=POSE):
    vertices, indices = [], []
    for slot in range(4):
        for face, corners in FACE_VERTICES.items():
            start = len(vertices)
            u0, v0, u1, v1 = rectangles[face]
            for corner, uv in zip(corners, ((u0, v0), (u1, v0), (u1, v1), (u0, v1))):
                point = [(corner[axis] - .5) * pose['scale_blocks'] +
                         pose['center_offset_blocks'][axis] for axis in range(3)]
                point[0] += slot * 2. + .5
                point[1] += .5
                vertices.append({'pos': point, 'normal': list(NORMALS[face]),
                                 'uvcoord': list(uv), 'weight': [['root', 1.]]})
            indices.extend(((start, start + 1, start + 2), (start, start + 2, start + 3)))
    return {'mesh': [{'material': texture, 'vertices': vertices, 'indices': indices}]}


def resolve_block(packs, blocks, terrain, name, cache):
    if name in cache:
        return cache[name]
    short = name.removeprefix('minecraft:')
    definition_key = DEFINITION_ALIASES.get(short, short)
    definition = blocks.get(definition_key)
    if definition is None:
        raise Unsupported('missing_native_block_definition')
    selection, keys = face_keys(definition['value'])
    images, faces = {}, {}
    for face, key in keys.items():
        images[face], faces[face] = resolve_face(packs, terrain, key)
    kind = material_kind(images)
    if short == 'glass' or short.endswith('_stained_glass'):
        kind = 'cutout' if kind != 'translucent' else kind
    bitmap, rectangles = atlas_image(images)
    resource = sha(encoded({'bitmap_sha256': sha(bitmap), 'material': kind, 'pose': POSE}))[:16]
    entry = {'bitmap_sha256': sha(bitmap), 'rectangles': rectangles,
             'material': kind, 'faces': faces, 'definition': definition,
             'definition_key': definition_key, 'texture_selection': selection}
    cache[name] = (resource, entry, bitmap)
    return cache[name]


def observe(raw, basic, install):
    if any(value.get('schema') != 1 or value.get('completed') is not True or
           value.get('engine_version') != VERSION for value in (raw, basic)):
        raise ValueError('Frame block items require complete exact-version native observations')
    packs, blocks, terrain, sources = source_records(install)
    metadata_path = ROOT / 'tools/data/native_block_metadata_nemc_3.9.0.401155.json'
    metadata_source = load(metadata_path)
    metadata = metadata_source['blocks']
    infos = {row['name']: row['value'] for row in basic['rows'] if isinstance(row['value'], dict)}
    items, unsupported, resources, resolved = [], {}, {}, {}
    for observation in raw['rows']:
        name, aux = observation['name'], observation['aux']
        info = infos.get(name, {})
        if info.get('itemType') != 'block':
            continue
        original = (name, aux)
        canonical = block_registry.try_canonical(original)
        reason = 'unmapped_item_aux' if canonical is None else shape_reason(canonical[0], info, metadata)
        if reason:
            unsupported.setdefault(name, set()).add(reason)
            continue
        try:
            resource, entry, bitmap = resolve_block(packs, blocks, terrain, canonical[0], resolved)
            observed = observation.get('texture', observation.get('value'))
            paths = {Path(face['path']).with_suffix('').as_posix().split('/', 1)[1]
                     for face in entry['faces'].values()}
            if observed not in paths:
                raise Unsupported('observed_item_texture_not_in_resolved_faces')
            previous = resources.setdefault(resource, entry)
            if previous['bitmap_sha256'] != sha(bitmap) or previous['material'] != entry['material']:
                raise ValueError('Frame block resource identity collision')
            items.append({'name': name, 'aux': aux, 'block_material': list(canonical),
                          'observed_item_texture': observed, 'resource': resource,
                          'definition_key': entry['definition_key'],
                          'texture_selection': entry['texture_selection'],
                          'shape_evidence': ('native_3_9_solid_metadata_plus_3_10_asset_candidate'
                              if metadata.get(canonical[0], {}).get('solid') is True else
                              'explicit_full_cube_glass_candidate'),
                          'degradation': ['fixed_default_item_axes'] + sorted({reason for face in entry['faces'].values()
                              for reason in face['degradation']})})
        except Unsupported as error:
            unsupported.setdefault(name, set()).add(str(error))
    return {'schema': 1, 'engine_version': VERSION, 'pose': POSE,
            'palette_version': block_registry.source_version(),
            'palette_sha256': block_registry.fingerprint(), 'source_sha256': sources,
            'observation_sha256': {'texture': sha(encoded(raw)), 'basic': sha(encoded(basic))},
            'shape_metadata': {'path': metadata_path.relative_to(ROOT).as_posix(),
                'sha256': sha(metadata_path.read_bytes()), 'version': metadata_source['game_version'],
                'scope': 'Candidate shape sieve only; not 3.10 native visual acceptance'},
            'native_items': {name: {field: info.get(field) for field in ('itemType', 'itemCategory', 'id_aux')}
                             for name, info in sorted(infos.items()) if info.get('itemType') == 'block'},
            'resources': resources, 'items': items,
            'unsupported': {name: sorted(reasons) for name, reasons in sorted(unsupported.items())},
            'production_qualified': False, 'qualification_sha256': None,
            'qualification_resource_sha256': None, 'qualified_materials': [],
            'required_native_gates': ['six_faces', 'eight_rotations', 'three_dimensional_thickness',
                'frame_body_depth', 'editor_shared_depth', 'world_full_missing', 'material_specific_alpha']}


def outputs(catalog, install):
    if (catalog.get('schema') != 1 or catalog.get('engine_version') != VERSION or
            catalog.get('pose') != POSE or catalog.get('palette_sha256') != block_registry.fingerprint()):
        raise ValueError('Frame block catalog version, pose or palette requires regeneration')
    packs, blocks, terrain, sources = source_records(install)
    if sources != catalog['source_sha256']:
        raise ValueError('Native block definitions or terrain atlas changed')
    metadata_path = ROOT / catalog['shape_metadata']['path']
    if sha(metadata_path.read_bytes()) != catalog['shape_metadata']['sha256']:
        raise ValueError('Native shape sieve source changed')
    metadata = load(metadata_path)['blocks']
    resolved, seen = {}, set()
    for row in catalog['items']:
        item = (row['name'], row['aux'])
        block = block_registry.try_canonical(item)
        if (item in seen or block is None or list(block) != row['block_material'] or
                shape_reason(block[0], catalog['native_items'].get(item[0], {}), metadata)):
            raise ValueError('Unverified or duplicate native item-to-cube mapping')
        seen.add(item)
        resource, entry, unused_bitmap = resolve_block(packs, blocks, terrain, block[0], resolved)
        observed_paths = {Path(face['path']).with_suffix('').as_posix().split('/', 1)[1]
                          for face in entry['faces'].values()}
        if (row['resource'] != resource or row['definition_key'] != entry['definition_key'] or
                row['texture_selection'] != entry['texture_selection'] or
                row['observed_item_texture'] not in observed_paths):
            raise ValueError('Native item-to-carried-face mapping changed')
    result, registry, materials, profiles = {}, {}, {}, {}
    result['resource_pack/models/' + ASSET + '/skeleton.json'] = (
        ROOT / 'resource_pack/models/modern_projection/item_icons/skeleton.json').read_bytes()
    for route in ('', '_world'):
        result['resource_pack/shaders/glsl/modern_projection_frame_block' + route + '.vertex'] = (
            ROOT / ('resource_pack/shaders/glsl/modern_projection_item_icon' + route + '.vertex')).read_bytes()
    fragment = (ROOT / 'resource_pack/shaders/glsl/modern_projection_item_icon.fragment').read_text(encoding='ascii')
    for kind in MATERIALS:
        source = fragment.replace('if(texel.a<0.5)', 'if(texel.a<=0.0)') if kind == 'translucent' else fragment
        result['resource_pack/shaders/glsl/modern_projection_frame_block_' + kind + '.fragment'] = source.encode('ascii')
    for resource, entry in sorted(catalog['resources'].items()):
        definition = blocks.get(entry['definition_key'])
        if definition != entry['definition']:
            raise ValueError('Native carried block definition changed')
        images = {}
        for face, saved in entry['faces'].items():
            images[face], current = resolve_face(packs, terrain, saved['atlas_key'])
            if current != saved:
                raise ValueError('Native carried face source changed: ' + resource + '/' + face)
        bitmap, rectangles = atlas_image(images)
        if sha(bitmap) != entry['bitmap_sha256'] or rectangles != entry['rectangles']:
            raise ValueError('Native carried face atlas changed')
        texture = ASSET + '/' + resource
        result['resource_pack/textures/models/' + texture + '.png'] = bitmap
        result['resource_pack/models/' + texture + '_mesh.json'] = encoded(cube_mesh(rectangles, texture))
        for suffix in ('', '_world'):
            model = PREFIX + resource + suffix
            material = 'modern_projection_frame_block_' + entry['material'] + suffix
            registry[model] = {'dy_load': True, 'mesh': texture + '_mesh.json',
                'skeleton': ASSET + '/skeleton.json', 'animation': {}, 'material': material,
                'texture': {'tex0': texture, 'tex1': 'modern_projection/item_icons/enchanted_glint'}}
    for kind in MATERIALS:
        for route in ('', '_world'):
            materials['modern_projection_frame_block_' + kind + route + ':entity_for_skeleton_alpha'] = {
                'vertexShader': 'shaders/glsl/modern_projection_frame_block' + route + '.vertex',
                'fragmentShader': 'shaders/glsl/modern_projection_frame_block_' + kind + '.fragment',
                '+states': ['Blending', 'DisableCulling'], '-states': ['DisableDepthWrite'],
                'blendSrc': 'SourceAlpha', 'blendDst': 'OneMinusSrcAlpha',
                '+samplerStates': [{'samplerIndex': 0, 'textureFilter': 'Point'},
                                  {'samplerIndex': 1, 'textureFilter': 'Bilinear'}]}
    grouped = {}
    for row in catalog['items']:
        grouped.setdefault((row['name'], row['resource']), []).append(row['aux'])
    for (name, resource), auxiliaries in sorted(grouped.items()):
        key = (name, min(auxiliaries))
        profiles[key] = {'ui_model': PREFIX + resource, 'world_model': PREFIX + resource + '_world',
            'resource_key': key, 'observed_aux': tuple(sorted(set(auxiliaries))), 'max_durability': 0,
            'family': 'frame_block_cube', 'content_families': ('frame',),
            'supports_enchantment': False, 'material': catalog['resources'][resource]['material'],
            'texture_sha256': catalog['resources'][resource]['bitmap_sha256']}
    result['tools/data/frame_block_item_registrations_nemc_' + VERSION + '.json'] = encoded(
        {'schema': 1, 'engine_version': VERSION, 'models': registry, 'materials': materials})
    contract = sha(b''.join(path.encode('ascii') + data for path, data in sorted(result.items())))
    if catalog.get('production_qualified'):
        raise ValueError('Native frame block acceptance has not been implemented; keep this candidate disabled')
    result['behavior_pack/modern_projection/projection/frame_block_item_data.py'] = (
        '"""Generated full-cube frame candidates; all native visual gates remain closed."""\n'
        'SCHEMA_VERSION = 1\nLAYOUT_VERSION = 1\nENGINE_VERSION = ' + repr(VERSION) + '\n'
        'PALETTE_SHA256 = ' + repr(block_registry.fingerprint()) + '\n'
        'RESOURCE_SHA256 = ' + repr(contract) + '\nPRODUCTION_QUALIFIED = False\n'
        'QUALIFICATION_SHA256 = None\nQUALIFICATION_RESOURCE_SHA256 = None\nQUALIFIED_MATERIALS = ()\n'
        'POSE = ' + repr(POSE) + '\nITEMS = ' + repr(profiles) + '\n'
        'UNSUPPORTED = ' + repr(catalog['unsupported']) + '\n').encode('ascii')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--install', type=Path, required=True)
    parser.add_argument('--catalog', type=Path, default=CATALOG)
    parser.add_argument('--texture-observations', type=Path)
    parser.add_argument('--basic-observations', type=Path)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--register', action='store_true')
    args = parser.parse_args()
    if args.texture_observations or args.basic_observations:
        if not args.texture_observations or not args.basic_observations or args.check:
            parser.error('Rebuilding requires both observation catalogs and cannot use --check')
        catalog = observe(load(args.texture_observations), load(args.basic_observations), args.install)
        args.catalog.write_bytes(encoded(catalog))
    else:
        catalog = load(args.catalog)
    generated = outputs(catalog, args.install)
    if args.register:
        registration = json.loads(generated['tools/data/frame_block_item_registrations_nemc_' + VERSION + '.json'])
        for relative, section, rows in (('resource_pack/models/netease_models.json', None, registration['models']),
                ('resource_pack/materials/entity.material', 'materials', registration['materials'])):
            existing = load(ROOT / relative)
            (existing[section] if section else existing).update(rows)
            generated[relative] = encoded(existing)
    stale = []
    for relative, data in generated.items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_bytes() != data:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    if stale:
        raise SystemExit('Stale frame block item resources: ' + ', '.join(stale))
    supported_names = {row['name'] for row in catalog['items']}
    print(json.dumps({'item_pairs': len(catalog['items']),
        'item_ids': len(supported_names), 'resources': len(catalog['resources']),
        'materials': dict(Counter(row['material'] for row in catalog['resources'].values())),
        'fully_excluded_ids': len(set(catalog['native_items']) - supported_names),
        'partially_excluded_ids': len(set(catalog['unsupported']) & supported_names),
        'production_qualified': False}))


if __name__ == '__main__':
    main()
