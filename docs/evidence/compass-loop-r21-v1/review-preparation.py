"""Freeze the bounded compass review without launching MC or touching the index."""
import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
VERSION = '3.10.0.420447'
KEY = '7061f07c69c447f1'
NAMES = {'minecraft:compass', 'minecraft:lodestone_compass'}
CATALOG = 'tools/data/item_icon_catalog_nemc_' + VERSION + '.json'
REGISTRATION = 'tools/data/item_icon_registrations_nemc_' + VERSION + '.json'
PROFILE = 'behavior_pack/modern_projection/projection/item_icon_data.py'
MODELS = 'resource_pack/models/netease_models.json'
MATERIALS = 'resource_pack/materials/entity.material'
LOOP = 'resource_pack/shaders/glsl/modern_projection_item_compass_loop.fragment'
MESH = 'resource_pack/models/modern_projection/item_icons/' + KEY + '_mesh.json'
ATLAS = 'resource_pack/textures/models/modern_projection/item_icons/' + KEY + '.png'
BASELINE_FILES = (CATALOG, REGISTRATION, PROFILE, MODELS, MATERIALS,
                  'tools/generate_item_icon_catalog.py', 'tools/verify_item_icon_shaders.py')
CURRENT_FILES = BASELINE_FILES + (LOOP, MESH, ATLAS,
    'tools/generate_item_icon_catalog.py', 'tools/generate_item_sprite_resources.py',
    'tools/generate_flat_item_proxies.py', 'tools/verify_item_icon_shaders.py',
    'tools/verify_compass_loop_r21.py', 'tools/verify_biome_shader.py',
    'tests/test_compass_loop_r21.py',
    'behavior_pack/modern_projection/projection/intrinsic_item_glint.py',
    'behavior_pack/modern_projection/projection/item_sprite_plan.py',
    'behavior_pack/modern_projection/projection/item_sprite_profile.py',
    'resource_pack/models/modern_projection/item_sprite/skeleton.json',
    'resource_pack/models/modern_projection/item_icons/skeleton.json',
    'resource_pack/textures/models/modern_projection/item_icons/enchanted_glint.png') + tuple(
        'resource_pack/shaders/glsl/modern_projection_' + name for name in (
            'item_sprite.vertex', 'item_sprite_world.vertex', 'item_sprite.fragment',
            'item_icon.vertex', 'item_icon_world.vertex', 'item_icon.fragment'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2) + '\n').encode('ascii')


def constants(data):
    return {node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.parse(data).body if isinstance(node, ast.Assign)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--install', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Preserve previous bounded review')
    base_ref = subprocess.check_output(['git', 'rev-parse', args.base_ref], cwd=str(ROOT)).decode('ascii').strip()
    args.output.mkdir(parents=True)
    batch = subprocess.Popen(['git', 'cat-file', '--batch'], cwd=str(ROOT),
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def baseline(relative):
        batch.stdin.write((base_ref + ':' + relative + '\n').encode('utf8'))
        batch.stdin.flush()
        header = batch.stdout.readline().decode('utf8').strip().split()
        if len(header) != 3 or header[1] != 'blob':
            raise ValueError('Missing baseline blob: ' + relative)
        data = batch.stdout.read(int(header[2]))
        if len(data) != int(header[2]) or batch.stdout.read(1) != b'\n':
            raise ValueError('Short baseline blob: ' + relative)
        return data, header[0]

    def write(relative, data):
        destination = args.output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)

    try:
        baseline_data = {}
        for relative in BASELINE_FILES:
            data, unused = baseline(relative)
            baseline_data[relative] = data
            write('baseline/' + relative, data)
        for relative in CURRENT_FILES:
            write('current/' + relative, (ROOT / relative).read_bytes())
        difference = subprocess.check_output(['git', 'diff', '--binary', base_ref, '--'] + list(BASELINE_FILES),
                                             cwd=str(ROOT))
        for relative in (LOOP, MESH, 'tools/verify_compass_loop_r21.py', 'tests/test_compass_loop_r21.py'):
            difference += ''.join(difflib.unified_diff([], (ROOT / relative).read_text(encoding='ascii').splitlines(True),
                fromfile='/dev/null', tofile='b/' + relative)).encode('ascii')
        write('source.patch', difference)
        write('review-preparation.py', Path(__file__).read_bytes())
        old_catalog = json.loads(baseline_data[CATALOG])
        catalog = json.loads((ROOT / CATALOG).read_bytes())
        before = constants(baseline_data[PROFILE])
        after = constants((ROOT / PROFILE).read_bytes())
        if any(after['ITEMS'].get(key) != value for key, value in before['ITEMS'].items()):
            raise ValueError('An ordinary static item profile changed')
        added_profiles = set(after['ITEMS']) - set(before['ITEMS'])
        if added_profiles != {(name, 0) for name in NAMES}:
            raise ValueError('Unexpected profile expansion')
        for key in added_profiles:
            row = after['ITEMS'][key]
            if row['resource_key'] != ('minecraft:compass', 0) or row['observed_aux'] != tuple(range(16)):
                raise ValueError('Compass aliases exceed their measured variants')
        if [row for row in catalog['items'] if row['name'] not in NAMES] != old_catalog['items']:
            raise ValueError('An ordinary catalog item changed')
        if {key: value for key, value in catalog['resources'].items() if key != KEY} != old_catalog['resources']:
            raise ValueError('An ordinary texture resource contract changed')
        old_assets = []
        for key in sorted(old_catalog['resources']):
            old_assets.extend(('resource_pack/textures/models/modern_projection/item_icons/' + key + '.png',
                               'resource_pack/models/modern_projection/item_icons/' + key + '_mesh.json'))
        old_assets.extend(('resource_pack/models/modern_projection/item_icons/skeleton.json',
                           'resource_pack/textures/models/modern_projection/item_icons/enchanted_glint.png'))
        old_assets.extend('resource_pack/shaders/glsl/modern_projection_' + name for name in (
            'item_icon.vertex', 'item_icon_world.vertex', 'item_icon.fragment'))
        assets = []
        for relative in sorted(old_assets):
            original, blob = baseline(relative)
            current = (ROOT / relative).read_bytes()
            if current != original:
                raise ValueError('An ordinary static generated asset changed: ' + relative)
            assets.append({'path': relative, 'git_blob': blob, 'bytes': len(current),
                           'baseline_sha256': sha(original), 'current_sha256': sha(current)})
        additions = {}
        for relative in (REGISTRATION, MODELS, MATERIALS):
            original = json.loads(baseline_data[relative])
            current = json.loads((ROOT / relative).read_bytes())
            sections = ('models', 'materials') if relative == REGISTRATION else (
                ('materials',) if relative == MATERIALS else (None,))
            for section in sections:
                old = original[section] if section else original
                new = current[section] if section else current
                if any(new.get(key) != value for key, value in old.items()):
                    raise ValueError('An existing registration changed: ' + relative)
                additions[relative + ':' + str(section)] = sorted(set(new) - set(old))
        shader_report = json.loads((HERE / 'shader-compilation.json').read_bytes())
        pixel_report = json.loads((HERE / 'pixel-verification.json').read_bytes())
        if (len(shader_report['results']) != 24 or not shader_report['passed'] or
                not all(row['compiled'] and row['linked'] for row in shader_report['results'])):
            raise ValueError('Expected all 24 actual shader programs')
        if len(pixel_report['measurements']) != 20 or not pixel_report['passed']:
            raise ValueError('Expected all 20 actual fragment pixel samples')
        for name, expected in shader_report['shader_sha256'].items():
            if sha((ROOT / 'resource_pack/shaders/glsl' / name).read_bytes()) != expected:
                raise ValueError('Compiler report belongs to different shader bytes')
        for relative, expected in pixel_report['sources'].items():
            if sha((ROOT / relative).read_bytes()) != expected:
                raise ValueError('Pixel report belongs to different source bytes')
        if after['PRODUCTION_QUALIFIED'] is not False or catalog['production_qualified'] is not False:
            raise ValueError('Offline checks cannot qualify production')
        for filename in ('shader-compilation.json', 'pixel-verification.json'):
            write('reports/' + filename, (HERE / filename).read_bytes())
            replay = HERE / 'review-replay-v2' / filename
            if replay.is_file():
                write('reports/replay-v2-' + filename, replay.read_bytes())
        header_root = ROOT / 'docs/evidence/frame-block-appearance-r21-v1/headers'
        for path in sorted(header_root.rglob('*')):
            if path.is_file():
                write('headers/' + path.relative_to(header_root).as_posix(), path.read_bytes())
        native_pack = args.install / 'data/resource_packs/vanilla'
        source = native_pack / 'textures/items/compass_atlas.png'
        if source.read_bytes() != (ROOT / ATLAS).read_bytes():
            raise ValueError('Owned compass atlas differs from exact installed native source')
        for relative in ('textures/items/compass_atlas.png', 'textures/item_texture.json'):
            write('native/' + relative, (native_pack / relative).read_bytes())
        write('static-assets.json', encoded(assets))
        report = {'schema': 1, 'baseline_ref': base_ref,
            'review_scope': 'One opaque compass loop and lodestone aux 0-15 aliases',
            'native_atlas': {'path': str(source), 'sha256': sha(source.read_bytes()),
                             'size': [16, 512], 'frames': 32, 'same_alpha': True},
            'unchanged_static_profiles': len(before['ITEMS']),
            'unchanged_static_resources': len(old_catalog['resources']),
            'unchanged_static_asset_files': len(assets),
            'unchanged_static_asset_bytes': sum(row['bytes'] for row in assets),
            'static_asset_comparison_sha256': sha(encoded(assets)), 'registration_additions': additions,
            'compiler_programs': 24, 'fragment_pixel_samples': 20,
            'game_started': False, 'production_qualified': False,
            'native_frame_pixels_qualified': False, 'editor_pixels_qualified': False,
            'projection_pixels_qualified': False, 'ordinary_static_regression_findings': [],
            'limits': ['Offline fragment uses a fullscreen test vertex; native mesh pose is unqualified.',
                       '32 native atlas frames have 28 distinct bitmaps; the 2-second loop is intentionally arbitrary.',
                       'Static assets are compared byte-for-byte with immutable Git blobs; their 50 MB bodies are omitted.',
                       'No target, time, location NBT or unmeasured auxiliary values are admitted.']}
        write('review.json', encoded(report))
        write('verify_package.py', (HERE / 'verify_review_template.py').read_bytes())
        write('README.md', (HERE / 'review_README.md').read_bytes())
        files = {path.relative_to(args.output).as_posix(): {'sha256': sha(path.read_bytes()), 'bytes': path.stat().st_size}
                 for path in sorted(args.output.rglob('*')) if path.is_file()}
        write('manifest.json', encoded({'schema': 1, 'baseline_ref': base_ref, 'files': files,
              'file_count': len(files), 'bytes': sum(row['bytes'] for row in files.values()),
              'production_qualified': False, 'game_started': False}))
        print(json.dumps(report))
    finally:
        batch.stdin.close()
        batch.wait(timeout=10)
        if batch.returncode:
            raise RuntimeError(batch.stderr.read().decode('utf8'))


if __name__ == '__main__':
    main()
