"""Prepare an unqualified, item-only base-light experiment from frozen resources."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from item_sprite_capture_contract import snapshot_digest, snapshot_sources

BASE_LIGHT = .93
FRAGMENT = 'resource_pack/shaders/glsl/modern_projection_frame_block_opaque.fragment'
ORIGINAL = '    vec3 rgb=texel.rgb*itemLight;'
REPLACEMENT = '''    // Rounded empirical base-light experiment; native cause and holdouts remain open.
    float frameBlockBaseLight=itemFrame>0.5 ? 0.93 : 1.0;
    vec3 rgb=texel.rgb*itemLight*frameBlockBaseLight;'''


def correct_base_light(source):
    if source.count(ORIGINAL) != 1 or 'frameBlockBaseLight' in source:
        raise ValueError('Expected one unchanged frame-block base RGB expression')
    newline = '\r\n' if '\r\n' in source else '\n'
    return source.replace(ORIGINAL, REPLACEMENT.replace('\n', newline))


def prepare(source, source_sha256, output):
    before = snapshot_sources(source)
    assert snapshot_digest(before) == source_sha256
    output.mkdir(parents=True, exist_ok=False)
    paths = [relative for relative in before if relative.startswith(
        'resource_pack/shaders/glsl/modern_projection_frame_block')]
    paths += ['behavior_pack/modern_projection/projection/frame_block_item_data.py',
              'resource_pack/models/modern_projection/frame_block_items/1cc58135f7b22c54_mesh.json',
              'resource_pack/models/modern_projection/frame_block_items/0d8d479f3958fea7_mesh.json']
    files = {}
    for relative in paths:
        original = source / relative
        assert hashlib.sha256(original.read_bytes()).hexdigest() == before[relative]
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if relative == FRAGMENT:
            source_text = original.read_bytes().decode('ascii')
            destination.write_bytes(correct_base_light(source_text).encode('ascii'))
        else:
            shutil.copyfile(original, destination)
        files[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()
    assert snapshot_sources(source) == before
    result = {'schema': 1, 'production_qualified': False, 'native_pixels_accepted': False,
        'source_sha256': source_sha256, 'source_unchanged': True, 'base_light': BASE_LIGHT,
        'changed_paths': [FRAGMENT], 'files': files,
        'source_file_sha256': {path: before[path] for path in paths},
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'items': [['minecraft:stone', 0], ['minecraft:quartz_block', 0]],
        'scope': 'Opaque frame-block base RGB only; conditional itemFrame>0.5; vertex positions/normals and independent glint term unchanged',
        'factor_provenance': 'Rounded empirical 0.93 suggested by old flat-item absolute gain 1.0763 and current eight stone face ROI mean gains 1.0704-1.0776; not a discovered native constant',
        'native_cause_established': False,
        'training': 'All eight stone face ROIs in frame-block-appearance-r21-v1; none is a holdout',
        'required_holdouts': ['Different ordinary block items with new camera angles',
            'Same-session raw RGB and source texture samples without color normalization',
            'Changed world-light conditions with actual native item reference',
            'Frame-body and Shelf unchanged-source controls',
            'Separate artificial block glint animation comparison'],
        'limitations': ['No new native capture; no postcapture corrected screenshot accepted',
            'Native TILE_LIGHT_COLOR, vertex color and fog factors were not observed',
            'Other materials, flat items, frame-body resources and Shelf resources are not corrected',
            'Candidate directory is a resource override subset, not a prepared runnable project']}
    (output / 'candidate.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--source-sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source, args.source_sha256, args.output)
    print(json.dumps({key: result[key] for key in ('base_light', 'changed_paths', 'production_qualified')}))
