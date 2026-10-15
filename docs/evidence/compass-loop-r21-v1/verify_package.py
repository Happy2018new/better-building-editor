"""Verify the portable compass review, optionally replaying actual GLES checks."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
VERSION = '3.10.0.420447'
KEY = '7061f07c69c447f1'
CATALOG = 'tools/data/item_icon_catalog_nemc_' + VERSION + '.json'
REGISTRATION = 'tools/data/item_icon_registrations_nemc_' + VERSION + '.json'
PROFILE = 'behavior_pack/modern_projection/projection/item_icon_data.py'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def constants(path):
    return {node.targets[0].id: ast.literal_eval(node.value)
            for node in ast.parse(path.read_bytes()).body if isinstance(node, ast.Assign)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser')
    parser.add_argument('--replay-output', type=Path)
    args = parser.parse_args()
    if bool(args.browser) != bool(args.replay_output):
        parser.error('Replay requires both --browser and fresh --replay-output')
    manifest = json.loads((HERE / 'manifest.json').read_bytes())
    actual = {path.relative_to(HERE).as_posix() for path in HERE.rglob('*')
              if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts}
    assert actual == set(manifest['files']), 'Package inventory changed'
    for relative, row in manifest['files'].items():
        path = (HERE / relative).resolve()
        assert HERE in path.parents, relative
        data = path.read_bytes()
        assert sha(data) == row['sha256'] and len(data) == row['bytes'], relative
    review = json.loads((HERE / 'review.json').read_bytes())
    assets = json.loads((HERE / 'static-assets.json').read_bytes())
    assert all(row['baseline_sha256'] == row['current_sha256'] for row in assets)
    assert len(assets) == review['unchanged_static_asset_files']
    assert sha((HERE / 'static-assets.json').read_bytes()) == review['static_asset_comparison_sha256']
    current, baseline = HERE / 'current', HERE / 'baseline'
    before, after = constants(baseline / PROFILE), constants(current / PROFILE)
    assert all(after['ITEMS'].get(key) == value for key, value in before['ITEMS'].items())
    assert set(after['ITEMS']) - set(before['ITEMS']) == {('minecraft:compass', 0), ('minecraft:lodestone_compass', 0)}
    for name in ('minecraft:compass', 'minecraft:lodestone_compass'):
        row = after['ITEMS'][(name, 0)]
        assert row['resource_key'] == ('minecraft:compass', 0)
        assert row['observed_aux'] == tuple(range(16)) and row['max_durability'] == 0
    old_catalog = json.loads((baseline / CATALOG).read_bytes())
    catalog = json.loads((current / CATALOG).read_bytes())
    assert [row for row in catalog['items'] if row['name'] not in ('minecraft:compass', 'minecraft:lodestone_compass')] == old_catalog['items']
    assert {key: value for key, value in catalog['resources'].items() if key != KEY} == old_catalog['resources']
    for relative in (REGISTRATION, 'resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material'):
        old = json.loads((baseline / relative).read_bytes())
        new = json.loads((current / relative).read_bytes())
        sections = ('models', 'materials') if relative == REGISTRATION else (
            ('materials',) if relative.endswith('entity.material') else (None,))
        for section in sections:
            old_rows, new_rows = (old[section], new[section]) if section else (old, new)
            assert all(new_rows.get(key) == value for key, value in old_rows.items())
            assert sorted(set(new_rows) - set(old_rows)) == review['registration_additions'][relative + ':' + str(section)]
    sys.path.insert(0, str(current / 'tools'))
    import generate_item_icon_catalog as generator
    from PIL import Image
    atlas_path = current / ('resource_pack/textures/models/modern_projection/item_icons/' + KEY + '.png')
    assert atlas_path.read_bytes() == (HERE / 'native/textures/items/compass_atlas.png').read_bytes()
    assert sha(atlas_path.read_bytes()) == review['native_atlas']['sha256']
    with Image.open(atlas_path) as atlas:
        assert list(atlas.size) == review['native_atlas']['size']
        reference = generator.compass_reference(atlas)
        mesh = generator.icon_mesh(reference, catalog['pose'], 'modern_projection/item_icons/' + KEY)
    stored_mesh = json.loads((current / ('resource_pack/models/modern_projection/item_icons/' + KEY + '_mesh.json')).read_bytes())
    assert json.loads(json.dumps(mesh)) == stored_mesh
    compiler = json.loads((HERE / 'reports/shader-compilation.json').read_bytes())
    pixels = json.loads((HERE / 'reports/pixel-verification.json').read_bytes())
    assert len(compiler['results']) == 24 and compiler['passed'] and compiler['no_regressions']
    assert all(row['compiled'] and row['linked'] for row in compiler['results'])
    for name, expected in compiler['shader_sha256'].items():
        assert sha((current / 'resource_pack/shaders/glsl' / name).read_bytes()) == expected
    assert len(pixels['measurements']) == 20 and pixels['passed']
    assert all(row['passed'] for row in pixels['measurements'])
    for relative, expected in pixels['sources'].items():
        assert sha((current / relative).read_bytes()) == expected
    assert after['PRODUCTION_QUALIFIED'] is False and catalog['production_qualified'] is False
    assert manifest['production_qualified'] is False and manifest['game_started'] is False
    for key in ('game_started', 'production_qualified', 'native_frame_pixels_qualified',
                'editor_pixels_qualified', 'projection_pixels_qualified'):
        assert review[key] is False, key
    if args.browser:
        assert not args.replay_output.exists(), 'Preserve previous replay output'
        args.replay_output.mkdir(parents=True)
        for script, filename in (('verify_item_icon_shaders.py', 'shader-compilation.json'),
                                 ('verify_compass_loop_r21.py', 'pixel-verification.json')):
            destination = args.replay_output / filename
            subprocess.run([sys.executable, '-B', '-X', 'utf8', str(current / 'tools' / script),
                '--headers', str(HERE / 'headers'), '--browser', args.browser,
                '--report', str(destination)], check=True, stdout=subprocess.PIPE)
            assert json.loads(destination.read_bytes())['passed']
    print(json.dumps({'verified_files': len(manifest['files']),
                      'unchanged_static_asset_files': len(assets),
                      'unchanged_static_profiles': len(before['ITEMS']),
                      'compiler_programs': 24, 'fragment_pixel_samples': 20,
                      'replayed': bool(args.browser), 'game_started': False, 'production_qualified': False}))


if __name__ == '__main__':
    main()
