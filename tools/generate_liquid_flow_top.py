"""Generate the versioned opt-in flow-top hypothesis without native qualification."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import liquid_shape_data

DEFAULT_SOURCE = ROOT / 'tools/data/native_liquid_flow_top_candidate_nemc_3.9.0.401155.json'
DEFAULT_OUTPUT = ROOT / 'behavior_pack/modern_projection/projection/liquid_flow_top_data.py'
TEMPLATE = 'candidate_water_top_center_turn256_v1'
RULE = 'four_corner_downhill_gradient_v1'
SAMPLING = {'region': 'full', 'pixel_mapping': 'edges', 'center': [.5, .5],
            'uv_span': .5, 'rotation_steps': 256, 'native_sampling_accepted': False}


def digest(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('ascii')).hexdigest()


def validate(data, manifest):
    if (data.get('schema_version') != 1 or data.get('game_version') != manifest['game_version']
            or data.get('palette_sha256', '').lower() != manifest['source_sha256'].lower()
            or data.get('shape_candidate_sha256') != liquid_shape_data.CANDIDATE_SHA256):
        raise ValueError('Flow top candidate differs from the versioned registry or shape source')
    if (data.get('template') != TEMPLATE or data.get('direction_rule') != RULE
            or data.get('sampling') != SAMPLING or data.get('rotation_codes') != list(range(256))
            or data.get('zero_gradient') != 'unknown_native_direction_keep_still_candidate'):
        raise ValueError('Flow top candidate has an unsupported direction or UV contract')
    if (data.get('native_direction_verified') is not False or data.get('native_uv_accepted') is not False
            or data.get('production_accepted') is not False):
        raise ValueError('Flow top hypothesis cannot manufacture native or production qualification')
    fingerprints = data.get('native_source_sha256')
    if not isinstance(fingerprints, dict) or set(fingerprints) != {
            'resource_packs/vanilla/blocks.json', 'resource_packs/vanilla/textures/terrain_texture.json',
            'resource_packs/vanilla/textures/flipbook_textures.json'}:
        raise ValueError('Flow top candidate needs the three installed native material metadata sources')
    for name, fingerprint in fingerprints.items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or not isinstance(fingerprint, str)
                or len(fingerprint) != 64 or any(char not in '0123456789abcdef' for char in fingerprint)):
            raise ValueError('Flow top candidate native source fingerprint is invalid')
    if not data.get('source_limits') or not data.get('native_acceptance_plan'):
        raise ValueError('Flow top candidate must preserve source limits and native acceptance work')
    return data


def verify_native(data, native):
    for relative, expected in data['native_source_sha256'].items():
        if hashlib.sha256((native / relative).read_bytes()).hexdigest() != expected:
            raise ValueError('Flow top metadata changed; regenerate and requalify: ' + relative)


def runtime_source(data):
    return ('"""Generated flow-top hypothesis; native direction and UV acceptance remain false."""\n'
            'SCHEMA_VERSION = 1\nSOURCE_VERSION = %r\nPALETTE_SHA256 = %r\n'
            'SHAPE_CANDIDATE_SHA256 = %r\nCANDIDATE_SHA256 = %r\n'
            'TEMPLATE = %r\nROTATION_STEPS = 256\nUV_SPAN = 0.5\n'
            'NATIVE_DIRECTION_VERIFIED = False\nNATIVE_UV_ACCEPTED = False\n'
            'PRODUCTION_ACCEPTED = False\n' %
            (data['game_version'], data['palette_sha256'], data['shape_candidate_sha256'],
             digest(data), data['template']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--native-data', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_bytes())
    data = validate(json.loads(args.source.read_bytes()), manifest)
    if args.native_data:
        verify_native(data, args.native_data)
    expected = runtime_source(data)
    if args.check:
        if args.output.read_text(encoding='ascii') != expected:
            raise ValueError('Generated flow top candidate is stale')
    else:
        args.output.write_text(expected, encoding='ascii')
    print('Flow top candidate: 256 angle codes, native direction/UV/production flags false')


if __name__ == '__main__':
    main()
