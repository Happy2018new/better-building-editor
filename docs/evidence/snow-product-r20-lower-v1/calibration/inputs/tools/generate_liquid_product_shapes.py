"""Generate a separately versioned Java-style water snapshot policy."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.liquid_render_plan import WATER_NAMES
from projection.liquid_shape import ModernLiquidHeightRule, LiquidSnapshotFlowRule

DEFAULT_SOURCE = ROOT / 'tools/data/product_liquid_shape_style_nemc_3.9.0.401155.json'
DEFAULT_OUTPUT = ROOT / 'behavior_pack/modern_projection/projection/liquid_product_shape_data.py'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=True).encode('ascii')).hexdigest()


def validate(data, manifest, references):
    if (data.get('schema_version') != 1
            or data.get('product_style_version') != 'java_snapshot_water_v1'
            or data.get('game_version') != manifest['game_version']
            or not isinstance(data.get('palette_sha256'), str)
            or data['palette_sha256'].lower() != manifest['source_sha256'].lower()
            or data.get('height_policy') != 'conditional_diagonal_weighted_v1'
            or data.get('flow_policy') != 'horizontal_and_below_snapshot_v1'
            or data.get('occlusion_policy') != 'opaque_full_cube_names_v1'):
        raise ValueError('Product liquid style needs its versioned registry and explicit policies')
    names = data.get('supported_names')
    if (not isinstance(names, list) or set(names) != WATER_NAMES or len(names) != len(WATER_NAMES)
            or data.get('native_parity_claimed') is not False
            or data.get('top_template') != 'candidate_water_top_center_turn256_v1'
            or type(data.get('top_rotation_offset')) is not int or data['top_rotation_offset'] != -64
            or type(data.get('rotation_steps')) is not int or data['rotation_steps'] != 256):
        raise ValueError('Product water names and UV policy must remain distinct from native parity')
    row = data.get('water')
    if not isinstance(row, dict) or set(row) != {
            'heights', 'weights', 'empty_weight', 'above_height', 'flow_below_drop', 'falling_depth_policy'}:
        raise ValueError('Product water needs all sixteen saved depth states and explicit falling policy')
    ModernLiquidHeightRule(row['heights'], row['weights'], row['empty_weight'], row['above_height'])
    LiquidSnapshotFlowRule(row['heights'], row['flow_below_drop'])
    expected_heights = [(8 - depth) / 9. if depth < 8 else 8. / 9. for depth in range(16)]
    expected_weights = [10 if height >= .8 else 1 for height in expected_heights]
    if (row['heights'] != expected_heights or row['weights'] != expected_weights
            or type(row['empty_weight']) is not int or row['empty_weight'] != 1
            or type(row['above_height']) is not int or row['above_height'] != 1
            or row['flow_below_drop'] != 8. / 9.
            or row['falling_depth_policy'] != 'saved_depth_8_to_15_own_height_8_over_9'):
        raise ValueError('Product water values differ from this independently declared style version')
    reference = data.get('reference', {})
    if (reference.get('sources_canonical_sha256') != digest(references)
            or reference.get('sources') != 'tools/data/java_liquid_reference_sources_20261013.json'
            or reference.get('report') != 'docs/LIQUID_JAVA_REFERENCE_STUDY_20261013.md'
            or reference.get('java_versions') != ['1.21.1', '1.21.11']
            or not set(reference['java_versions']).issubset(
                item['version'] for item in references['official_distributions'])
            or references.get('game_code_in_repository') is not False):
        raise ValueError('Product water reference metadata has changed; review and regenerate its provenance')
    return data


def runtime_source(data):
    row = data['water']
    return ('"""Generated product water policy; native parity and visual acceptance are separate."""\n'
            'SCHEMA_VERSION = 1\nPRODUCT_STYLE_VERSION = %r\nPRODUCT_RULES_SHA256 = %r\n'
            'SOURCE_VERSION = %r\nPALETTE_SHA256 = %r\nSUPPORTED_NAMES = frozenset(%r)\n'
            'HEIGHT_POLICY = %r\nFLOW_POLICY = %r\nOCCLUSION_POLICY = %r\n'
            'HEIGHT_RULE = %r\nFLOW_OWN_HEIGHTS = %r\nFLOW_BELOW_DROP = %r\n'
            'FALLING_DEPTH_POLICY = %r\nTOP_TEMPLATE = %r\nTOP_ROTATION_OFFSET = %r\n'
            'ROTATION_STEPS = %r\nNATIVE_PARITY_CLAIMED = False\nREFERENCE_SOURCES_SHA256 = %r\n' %
            (data['product_style_version'], digest(data), data['game_version'], data['palette_sha256'],
             tuple(sorted(data['supported_names'])), data['height_policy'], data['flow_policy'],
             data['occlusion_policy'], (tuple(row['heights']), tuple(row['weights']),
                                       row['empty_weight'], row['above_height']),
             tuple(row['heights']), row['flow_below_drop'], row['falling_depth_policy'],
             data['top_template'], data['top_rotation_offset'], data['rotation_steps'],
             data['reference']['sources_canonical_sha256']))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    references = json.loads((ROOT / 'tools/data/java_liquid_reference_sources_20261013.json').read_text(encoding='utf8'))
    data = validate(json.loads(args.source.read_text(encoding='utf8')), manifest, references)
    result = runtime_source(data)
    if args.check:
        if args.output.read_text(encoding='ascii') != result:
            raise ValueError('Generated product water policy is stale')
    else:
        args.output.write_text(result, encoding='ascii')
    print('Product water style: %s; rules=%s; native_parity_claimed=False' %
          (data['product_style_version'], digest(data)))


if __name__ == '__main__':
    main()
