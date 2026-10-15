"""Reproduce derived Java-water research examples, without game/SDK execution.

These independently expressed rational examples summarize inspected algorithms.
They are not copied game source, a Java client execution, or Bedrock acceptance.
Input heights below describe non-falling source/low-water examples only.
"""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from projection.debug_blueprints import material
from projection.liquid_flow_top import candidate_flow_uv, rotation_code, top_uv
from projection.liquid_native_shapes import shape_provider
from projection.liquid_shape import LiquidHeightRule
from projection.liquid_shape_data import HEIGHT_RULES
from projection.model import Document


def height(depth):
    if depth is None:
        return Fraction(0)
    if type(depth) is not int or not 0 <= depth <= 7:
        raise ValueError('Research examples require non-falling depths 0..7')
    return Fraction(8 - depth, 9)


def reference_corner(depths, era):
    """C, orthogonal A/B, diagonal D; all absent cells are non-solid air."""
    if len(depths) != 4 or era not in ('java_1_12_2', 'java_1_16_5', 'java_1_21'):
        raise ValueError('An explicit four-cell case and inspected era are required')
    values = tuple(height(depth) for depth in depths)
    if depths[0] is None:
        raise ValueError('The target cell must contain water')
    indices = [0, 1, 2]
    if era != 'java_1_21' or values[1] > 0 or values[2] > 0:
        indices.append(3)
    heavy = 11 if era == 'java_1_12_2' else 10
    weights = tuple(heavy if values[index] >= Fraction(4, 5) else 1
                    for index in indices)
    return sum(values[index] * weight for index, weight in zip(indices, weights)) / sum(weights)


def scalar(value):
    byte = math.floor(float(value) * 255 + .5)
    return {'rational': str(value), 'height': float(value),
            'nearest_byte': byte, 'repeated_byte_uniform': byte * 257}


def java_top_uv(u, v, turn):
    """Normalized ideal-trigonometry template before atlas/UV shrink/filtering.

    Java's tesselator visits NW, SW, SE, NE. This is expressed in document x/z
    coordinates; it is not Java Mth's precise floating-point implementation.
    """
    angle = turn * 2 * math.pi / 256
    x, z = u - .5, v - .5
    return (.5 + .5 * (math.sin(angle) * x - math.cos(angle) * z),
            .5 + .5 * (math.cos(angle) * x + math.sin(angle) * z))


def analyze():
    cases = [('isolated_source', (0, None, None, None)),
             ('isolated_depth3', (3, None, None, None)),
             ('low_diagonal', (3, None, None, 3)),
             ('source_low_orthogonal', (0, 3, None, None))]
    rule = LiquidHeightRule(*HEIGHT_RULES['water'])
    rows = []
    for name, depths in cases:
        values = {era: reference_corner(depths, era)
                  for era in ('java_1_12_2', 'java_1_16_5', 'java_1_21')}
        current = rule.corner(tuple((depth, False, False) for depth in depths))
        if not math.isclose(current, float(values['java_1_12_2']), abs_tol=1e-14):
            raise AssertionError('Current rule changed; research example requires review')
        rows.append({'name': name, 'depths_c_a_b_d': depths,
                     'reference_heights': {era: scalar(value) for era, value in values.items()},
                     'current_height': current,
                     'current_matches_inspected_legacy_example': True})

    # Explicit known fractions prevent errors in a shared numerical derivation.
    expected = {
        ('isolated_source', 'java_1_12_2'): Fraction(44, 63),
        ('isolated_source', 'java_1_16_5'): Fraction(80, 117),
        ('isolated_source', 'java_1_21'): Fraction(20, 27),
        ('isolated_depth3', 'java_1_12_2'): Fraction(5, 36),
        ('isolated_depth3', 'java_1_21'): Fraction(5, 27),
        ('low_diagonal', 'java_1_12_2'): Fraction(5, 18),
        ('low_diagonal', 'java_1_21'): Fraction(5, 27),
        ('source_low_orthogonal', 'java_1_12_2'): Fraction(31, 42),
        ('source_low_orthogonal', 'java_1_21'): Fraction(85, 117),
    }
    for name, depths in cases:
        for era in ('java_1_12_2', 'java_1_16_5', 'java_1_21'):
            if (name, era) in expected and reference_corner(depths, era) != expected[name, era]:
                raise AssertionError('Derived height differs from its independent rational case')

    # Ideal Java template equals the current template after a quarter-turn shift.
    # This establishes a template difference, not the native Bedrock orientation.
    points = ((0., 0.), (0., 1.), (1., 1.), (1., 0.), (.137, .269), (.5, .5))
    max_error = 0.
    for turn in range(256):
        for u, v in points:
            actual, shifted = java_top_uv(u, v, turn), top_uv(u, v, (turn - 64) % 256)
            max_error = max(max_error, *(abs(a - b) for a, b in zip(actual, shifted)))
    if max_error > 1e-14:
        raise AssertionError('Quarter-turn relation between normalized templates changed')

    # Flat same-height plane with air on every side, water only BELOW north air.
    # Java's lateral-neighbor-below term is hC-(hBelow-8/9)=8/9 northwards.
    drain = height(0) - (height(0) - Fraction(8, 9))
    candidate = rotation_code(0, 0)
    if candidate is not None or drain != Fraction(8, 9):
        raise AssertionError('Flat-surface/lower-neighbor counterexample changed')
    target, water = (1, 1, 1), material('water', {'liquid_depth': 0})
    flow_documents = []
    for lower_water in (False, True):
        cells = {target: water}
        if lower_water:
            cells[(1, 0, 0)] = water
        document = Document((4, 3, 4), cells)
        surface = shape_provider(document).surface(document, target, 0, water)
        choice = candidate_flow_uv(document, target, 0, water, surface.heights)
        flow_documents.append({'water_below_north_air': lower_water,
                               'current_corner_heights': surface.heights,
                               'current_top_choice': choice})
    if (flow_documents[0]['current_corner_heights'] != flow_documents[1]['current_corner_heights']
            or any(row['current_top_choice'] != ('still_water_grey', None)
                   for row in flow_documents)):
        raise AssertionError('Production candidate no longer has the recorded flow counterexample')
    return {
        'schema_version': 1,
        'scope': 'Derived reference math and current-candidate comparison, not native acceptance',
        'java_game_executed': False, 'bedrock_game_executed': False,
        'production_modified': False, 'native_geometry_accepted': False,
        'uv_accepted': False, 'animation_accepted': False, 'production_accepted': False,
        'current_sources': [
            {'path': path, 'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
            for path in ('behavior_pack/modern_projection/projection/liquid_shape.py',
                         'behavior_pack/modern_projection/projection/liquid_shape_data.py',
                         'behavior_pack/modern_projection/projection/liquid_flow_top.py',
                         'behavior_pack/modern_projection/projection/liquid_flow_top_data.py',
                         'behavior_pack/modern_projection/projection/liquid_native_shapes.py')],
        'height_cases': rows,
        'top_uv': {'comparison_points': 256 * len(points),
                   'current_code_offset_for_ideal_java_template': -64,
                   'maximum_normalized_error': max_error,
                   'java_east_nw_uv_before_shrink': java_top_uv(0., 0., 0),
                   'current_east_nw_uv': top_uv(0., 0., 0),
                   'native_orientation_identified': False},
        'flow_counterexample': {'top_candidate_heights': [float(Fraction(44, 63))] * 4,
                                'current_corner_gradient_rotation': candidate,
                                'java_raw_xz_flow': [0., -float(drain)],
                                'java_top_material': 'flowing',
                                'actual_current_document_comparisons': flow_documents,
                                'neighborhood_difference': 'water below north adjacent air only',
                                'bedrock_rule_identified': False},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check', type=Path)
    args = parser.parse_args()
    report = analyze()
    if args.check:
        if json.loads(args.check.read_text(encoding='utf-8')) != json.loads(json.dumps(report)):
            raise SystemExit('Research report differs from current source-derived examples')
        print('Derived liquid reference examples match the saved research report')
    elif args.output:
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
        print('Saved derived examples; no game or SDK was used')
    else:
        print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
