"""Generate the centered bush's animated atlas sprite from frozen native inputs."""
import argparse
import copy
import hashlib
from io import BytesIO
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/data/firefly_bush_animation_nemc_3.10.0.420447'
KEY = 'modern_projection_centered_firefly_bush'
TEXTURE = 'textures/blocks/modern_projection_r23_firefly_composited'
ATLAS = 'resource_pack/textures/terrain_texture.json'
FLIPBOOK = 'resource_pack/textures/flipbook_textures.json'
STRIP = 'resource_pack/' + TEXTURE + '.png'
CADENCE = {'flipbook_texture': 'textures/blocks/firefly_bush_firefly',
           'atlas_tile': 'firefly_bush', 'atlas_index': 1, 'ticks_per_frame': 3}
DECLARATION = dict(CADENCE, flipbook_texture=TEXTURE, atlas_tile=KEY, atlas_index=0)


def load_json(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('Duplicate JSON field: ' + key)
            result[key] = value
        return result

    def finite(value):
        raise ValueError('Non-finite JSON constant: ' + value)

    return json.loads(path.read_text(encoding='utf-8-sig'),
                      object_pairs_hook=unique, parse_constant=finite)


def source_data(source=SOURCE):
    manifest = load_json(source / 'source.json')
    names = {'body.png', 'fireflies.png', 'carried.png', 'flipbook_textures.json'}
    if (manifest.get('schema') != 1 or manifest.get('resource_version') != 'NEMC 3.10.0.420447'
            or set(manifest['files']) != names or manifest['native_cadence'] != CADENCE):
        raise ValueError('Review the versioned firefly animation source contract')
    for name, row in manifest['files'].items():
        raw = (source / name).read_bytes()
        if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
            raise ValueError('Native animation source changed: ' + name)
    native = load_json(source / 'flipbook_textures.json')
    if not isinstance(native, list) or len(native) != 80:
        raise ValueError('Expected the complete 80-entry native animation baseline')
    if [row for row in native if row.get('atlas_tile') == 'firefly_bush'] != [CADENCE]:
        raise ValueError('Native bush animation policy changed')
    if any(row.get('atlas_tile') == KEY for row in native):
        raise ValueError('Native animation baseline collides with the project sprite')
    return manifest, native


def centered_texture(profile, source=SOURCE):
    """Keep the geometry/alpha profile authoritative while replacing its sprite."""
    manifest, unused = source_data(source)
    plant = profile['plants']['firefly_bush']
    if plant['texture_sha256'] != manifest['files']['carried.png']['sha256']:
        raise ValueError('Centered geometry and animation use different carried silhouettes')
    return TEXTURE


def merged_entries(native, current):
    if not isinstance(current, list) or any(not isinstance(row, dict) for row in current):
        raise ValueError('Local flipbooks must remain an ordered list of declarations')
    # Retain the shipped baseline verbatim, including intentional duplicate
    # atlas/variant declarations. Local overrides retain their later precedence.
    local = current[len(native):] if current[:len(native)] == native else current[:]
    own = [row for row in local if row.get('atlas_tile') == KEY]
    if own and own != [DECLARATION]:
        raise ValueError('Conflicting or duplicate bush animation declaration')
    local = [row for row in local if row.get('atlas_tile') != KEY]
    return copy.deepcopy(native + local + [DECLARATION])


def composited_strip(source=SOURCE):
    images = []
    for name in ('body.png', 'fireflies.png', 'carried.png'):
        with Image.open(source / name) as original:
            images.append(original.convert('RGBA'))
    body, fireflies, carried = images
    if body.size != (16, 16) or fireflies.size != (16, 160) or carried.size != (16, 16):
        raise ValueError('Unexpected native firefly texture dimensions')
    alpha = carried.getchannel('A').tobytes()
    strip = Image.new('RGBA', (16, 160))
    frames = []
    for index in range(10):
        overlay = fireflies.crop((0, 16 * index, 16, 16 * (index + 1)))
        frame = Image.alpha_composite(body, overlay)
        if frame.getchannel('A').tobytes() != alpha:
            raise ValueError('Animation changes the centered plant/snow silhouette')
        frames.append(frame.tobytes())
        strip.paste(frame, (0, 16 * index))
    if len(set(frames)) != 10:
        raise ValueError('Expected ten distinct native animation frames')
    result = BytesIO()
    strip.save(result, format='PNG', optimize=True)
    return result.getvalue()


def outputs(root=ROOT, source=SOURCE):
    manifest, native = source_data(source)
    profile = load_json(root / manifest['fixed_centered_geometry_source'])
    centered_texture(profile, source)
    atlas = load_json(root / ATLAS)
    if atlas['texture_data'][KEY] not in (
            {'textures': 'textures/items/firefly_bush'}, {'textures': TEXTURE}):
        raise ValueError('Unexpected centered firefly sprite override')
    atlas['texture_data'][KEY] = {'textures': TEXTURE}
    current = load_json(root / FLIPBOOK) if (root / FLIPBOOK).is_file() else []
    entries = merged_entries(native, current)
    # Preserve the exact Windows candidate bytes used in the cold captures.
    return {ATLAS: (json.dumps(atlas, ensure_ascii=True, indent=2) + '\n').replace('\n', '\r\n').encode('ascii'),
            FLIPBOOK: (json.dumps(entries, ensure_ascii=True, indent=2) + '\n').replace('\n', '\r\n').encode('ascii'),
            STRIP: composited_strip(source)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    resources = outputs()
    stale = []
    for relative, raw in resources.items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_bytes() != raw:
                stale.append(relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    if stale:
        raise SystemExit('Stale firefly animation resources: ' + ', '.join(stale))
    print(json.dumps({'checked' if args.check else 'generated': 3,
                      'native_entries_preserved': 80, 'frames': 10,
                      'independent_particles_implemented': False}))


if __name__ == '__main__':
    main()
