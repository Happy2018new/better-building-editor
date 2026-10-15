"""Freeze two measured cube pose candidates without changing shared resources."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import generate_frame_block_items as generator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import frame_block_item_data as source

ITEMS = (('minecraft:stone', 0), ('minecraft:quartz_block', 0))
POSE = deepcopy(generator.MEASURED_POSE)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def resources(pose=POSE):
    catalog = json.loads(generator.CATALOG.read_bytes())
    assert not catalog['production_qualified'] and not source.PRODUCTION_QUALIFIED
    files, entries, meshes = {}, {}, []
    for item in ITEMS:
        row = next(row for row in catalog['items'] if (row['name'], row['aux']) == item)
        entry = catalog['resources'][row['resource']]
        texture = generator.ASSET + '/' + row['resource']
        relative = 'resource_pack/models/' + texture + '_mesh.json'
        files[relative] = generator.encoded(generator.cube_mesh(entry['rectangles'], texture, pose))
        entries[item] = deepcopy(source.ITEMS[item])
        meshes.append({'item': list(item), 'path': relative, 'resource': row['resource']})
    face_uv = generator.FACE_GLINT_UV % (','.join(repr(value) for value in pose['center_offset_blocks']),
                                        repr(pose['scale_blocks']))
    for suffix in ('', '_world'):
        relative = 'resource_pack/shaders/glsl/modern_projection_frame_block' + suffix + '.vertex'
        current = (ROOT / relative).read_text(encoding='ascii')
        start, end = current.index('vec2 blockFaceUv('), current.index('void main() {')
        files[relative] = (current[:start] + face_uv + current[end:]).encode('ascii')
    for material in generator.MATERIALS:
        relative = 'resource_pack/shaders/glsl/modern_projection_frame_block_' + material + '.fragment'
        files[relative] = (ROOT / relative).read_bytes()
    contract = digest(b''.join(path.encode('ascii') + data for path, data in sorted(files.items())))
    values = {'SCHEMA_VERSION': 1, 'LAYOUT_VERSION': 1, 'ENGINE_VERSION': source.ENGINE_VERSION,
              'PALETTE_SHA256': source.PALETTE_SHA256, 'RESOURCE_SHA256': contract,
              'PRODUCTION_QUALIFIED': False, 'QUALIFICATION_SHA256': None,
              'QUALIFICATION_RESOURCE_SHA256': None, 'QUALIFIED_MATERIALS': (),
              'POSE': pose, 'ITEMS': entries, 'UNSUPPORTED': {}}
    files['behavior_pack/modern_projection/projection/frame_block_item_data.py'] = (
        '"""Isolated measured stone/quartz block pose candidates; unqualified."""\n' +
        ''.join(key + ' = ' + repr(value) + '\n' for key, value in values.items())).encode('ascii')
    return files, meshes, contract


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    fit = json.loads(args.fit.read_bytes())
    assert fit['schema'] == 1 and fit['production_qualified'] is False
    assert fit['analyzer_sha256'] == digest((ROOT / 'tools/analyze_frame_block_pose_r21.py').read_bytes())
    assert fit['routes']['native']['quarter_cube_max_support_pixels'] < 2.
    captured = Path(fit['source'])
    assert digest(captured.read_bytes()) == fit['source_sha256']
    original = json.loads(captured.read_bytes())
    assert original['completed'] and not original['cleanup_errors'] and original['source_unchanged']
    assert original['cases'][0]['source']['item'] == ['minecraft:stone', 0]
    assert original['cases'][0]['native_reference']['restored']
    files, meshes, contract = resources()
    manifest = {'schema': 1, 'production_qualified': False, 'pose': POSE,
                'items': [list(item) for item in ITEMS], 'meshes': meshes,
                'resource_sha256': contract, 'fit_sha256': digest(args.fit.read_bytes()),
                'generator_sha256': digest(Path(__file__).read_bytes()),
                'base_generator_sha256': digest(Path(generator.__file__).read_bytes()),
                'base_resource_sha256': source.RESOURCE_SHA256,
                'mesh_sha256': {row['path']: digest(files[row['path']]) for row in meshes},
                'files': {path: digest(data) for path, data in sorted(files.items())},
                'limits': ['Single native stone camera only; geometry depth remains unaccepted',
                           'Quartz block uses transferred candidate pose; no native block glint pixels yet',
                           'Install only into a new frozen diagnostic clone; no production resource edits']}
    args.output.mkdir(parents=True, exist_ok=False)
    for relative, data in files.items():
        path = args.output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (args.output / 'candidate.json').write_bytes(generator.encoded(manifest))
    print(json.dumps({'prepared': True, 'output': str(args.output.resolve()),
                      'items': manifest['items'], 'resource_sha256': contract, 'production_qualified': False}))


if __name__ == '__main__':
    main()
