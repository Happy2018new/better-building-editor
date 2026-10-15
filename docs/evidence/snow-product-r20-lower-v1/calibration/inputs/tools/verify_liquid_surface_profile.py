"""Compare an explicit liquid height profile with frozen native silhouettes.

This host check does not validate UVs, animation, tint, hidden faces, a body
overlaid with water, or production resource lifetimes. Original failed gates
remain failed, and neither camera nor candidate parameters are fitted here.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

from analyze_frozen_liquid_surfaces import checked_fingerprint, difference_mask, fingerprint
from capture_frozen_liquid_controls import native_gate
from capture_pure_liquid_native_controls import CONTROLS, fixed_viewport, validate_png
from measure_native_liquid_surface import pixel_viewport, projected_pixels
from liquid_silhouette_raster import visible_liquid_mask
from projection import block_registry
from projection.block_traits import is_solid
from projection.cell import AIR, background, decode, foreground
from projection.liquid_render_plan import LIQUID_NAMES, iter_groups
from projection.liquid_shape import DocumentLiquidShapes, LiquidHeightRule
from projection.model import Document
from verify_camera_projection import fill_enclosed_holes
from verify_missing_neighbor_visuals import hull

ROOT = Path(__file__).resolve().parents[1]
FACE_CORNERS = ((4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
                (3, 0, 4, 7), (1, 2, 6, 5), (3, 2, 1, 0))


def shape_provider(document, profile):
    if (profile.get('schema_version') != 1 or
            profile.get('game_version') != block_registry.source_version() or
            profile.get('palette_sha256', '').lower() != block_registry.fingerprint().lower()):
        raise ValueError('Candidate profile must match the complete installed block registry')
    rules = dict((family, LiquidHeightRule(row['heights'], row['weights'],
                                         row['empty_weight'], row['above_height']))
                 for family, row in profile['rules'].items())
    def blocked(cell):
        return is_solid(foreground(cell)) or is_solid(background(cell))
    return DocumentLiquidShapes(document, rules, blocked, lambda cell, face: blocked(cell),
                                profile['supported_names'])


def surfaces(document, profile, origin):
    provider = shape_provider(document, profile)
    result = []
    for group in iter_groups(document, provider):
        for shape in group.surfaces:
            pos = tuple(shape.position[axis] + origin[axis] for axis in range(3))
            result.append((pos, shape))
    return result


def polygons(shapes):
    for (x, y, z), shape in shapes:
        points = [(x + dx, y, z + dz) for dx, dz in ((0, 0), (1, 0), (1, 1), (0, 1))]
        points.extend((x + dx, y + height, z + dz)
                      for (dx, dz), height in zip(((0, 0), (1, 0), (1, 1), (0, 1)), shape.heights))
        for face, corners in enumerate(FACE_CORNERS):
            if shape.faces & (1 << face):
                yield tuple(points[index] for index in corners)


def project_polygon(points, camera):
    projected = projected_pixels(points, camera, pixel_viewport(camera))
    if any(point['depth'] < .05 or not point['isInScreen'] for point in projected):
        raise ValueError('The complete declared geometry must be on screen in front of the near plane')
    return tuple((point['screenX'], point['screenY']) for point in projected)


def predicted_mask(shapes, camera):
    result = Image.new('L', tuple(camera['native_image_screen']))
    draw = ImageDraw.Draw(result)
    for polygon in polygons(shapes):
        draw.polygon(project_polygon(polygon, camera), fill=255)
    return result


def fixed_region(shapes, camera):
    result = Image.new('L', tuple(camera['native_image_screen']))
    draw = ImageDraw.Draw(result)
    for (x, y, z), unused in shapes:
        points = tuple((x + dx, y + dy, z + dz)
                       for dx in (0, 1) for dy in (0, 1) for dz in (0, 1))
        draw.polygon(hull(project_polygon(points, camera)), fill=255)
    return result


def compare(actual, expected, tolerance):
    """Measure fixed silhouette agreement; no refit or threshold relaxation."""
    intersection = ImageChops.multiply(actual, expected).histogram()[255]
    union = ImageChops.lighter(actual, expected).histogram()[255]
    first = actual.filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value else 0)
    second = expected.filter(ImageFilter.FIND_EDGES).point(lambda value: 255 if value else 0)
    kernel = tolerance * 2 + 1
    recall = ImageChops.multiply(first, second.filter(ImageFilter.MaxFilter(kernel))).histogram()[255]
    precision = ImageChops.multiply(second, first.filter(ImageFilter.MaxFilter(kernel))).histogram()[255]
    first_count, second_count = first.histogram()[255], second.histogram()[255]
    return {'actual_pixels': actual.histogram()[255], 'expected_pixels': expected.histogram()[255],
            'mask_iou': intersection / max(1, union),
            'outline_recall': recall / max(1, first_count),
            'outline_precision': precision / max(1, second_count),
            'outline_tolerance_pixels': tolerance,
            'actual_bounds': actual.getbbox(), 'expected_bounds': expected.getbbox()}


def source_document(plan, control):
    origin = tuple(plan['document_origin'])
    cells = plan['controls'][control]['cells']
    size = tuple(max([1] + [pos[axis] - origin[axis] + 1 for pos, unused in cells])
                 for axis in range(3))
    document = Document(size)
    for pos, value in cells:
        document.set_cell(tuple(pos[axis] - origin[axis] for axis in range(3)), decode(value))
    return document, origin


def check_remote_background(plan, fixed_neighbors=None):
    """A declared, identical backdrop is not a same-cell waterlogged body."""
    background_cells = plan.get('background_cells', [])
    declared = dict((tuple(pos), decode(value)) for pos, value in background_cells)
    fixed_neighbors = fixed_neighbors or {}
    if set(declared) & set(fixed_neighbors):
        raise ValueError('A held neighbor is not a remote background')
    if len(declared) != len(background_cells):
        raise ValueError('Declared background repeats a cell')
    for control in CONTROLS:
        cells = dict((tuple(pos), decode(value)) for pos, value in plan['controls'][control]['cells'])
        if any(cells.get(pos) != value for pos, value in declared.items()):
            raise ValueError('Every independent control needs the same declared background')
    fluid_cells = []
    for pos, value in plan['controls']['liquid_only']['cells']:
        cell = decode(value)
        has_fluid = any(material[0] in LIQUID_NAMES for material in (foreground(cell), background(cell)))
        has_body = any(material != AIR and material[0] not in LIQUID_NAMES
                       for material in (foreground(cell), background(cell)))
        if has_fluid:
            fluid_cells.append(tuple(pos))
        if has_body and (has_fluid or (declared.get(tuple(pos)) != cell
                                      and fixed_neighbors.get(tuple(pos)) != cell)):
            raise ValueError('Pure silhouette checks cannot attribute an overlaid or undeclared body')
    if any(max(abs(pos[axis] - fluid[axis]) for axis in range(3)) < 2
           for pos in declared for fluid in fluid_cells):
        raise ValueError('Background cannot modify the liquid height neighborhood')
    return declared


def check_fixed_neighbors(plan):
    """A held stone neighbor changes source context, not the liquid-only control."""
    rows = plan.get('fixed_neighbor_cells', [])
    if not rows:
        return {}
    contract = plan.get('fixed_neighbor_contract', {})
    if (contract.get('unchanged_in_all_four_controls') is not True
            or contract.get('same_cell_body') is not False
            or contract.get('distance_to_fluid') != 1):
        raise ValueError('Held neighbors need an explicit invariant adjacent-cell contract')
    neighbors = dict((tuple(pos), decode(value)) for pos, value in rows)
    if len(neighbors) != len(rows) or any(value != ('minecraft:stone', 0) for value in neighbors.values()):
        raise ValueError('Held neighbor occlusion currently accepts only distinct full stone cubes')
    for control in CONTROLS:
        cells = dict((tuple(pos), decode(value)) for pos, value in plan['controls'][control]['cells'])
        if any(cells.get(pos) != value for pos, value in neighbors.items()):
            raise ValueError('Held neighbors changed between native controls')
    fluid = [tuple(pos) for pos, value in plan['controls']['liquid_only']['cells']
             if any(material[0] in LIQUID_NAMES for material in (foreground(decode(value)), background(decode(value))))]
    if not fluid or any(min(max(abs(pos[axis] - target[axis]) for axis in range(3))
                               for target in fluid) != 1 for pos in neighbors):
        raise ValueError('Held neighbors must be adjacent to liquid and cannot occupy the same cell')
    return neighbors


def analyze(report_path, profile_path, output, selected=None, tolerance=3):
    if output.exists():
        raise ValueError('Choose a fresh output directory and preserve old evidence')
    report = json.loads(report_path.read_text(encoding='utf8'))
    profile = json.loads(profile_path.read_text(encoding='utf8'))
    if (report.get('schema') != 2 or not report.get('completed') or not report.get('restored') or
            report.get('cleanup_errors') or type(report.get('context_changed')) is not bool or
            not report.get('flow_freeze', {}).get('forbidden') or
            not report.get('flow_restore', {}).get('native_return_verified')):
        raise ValueError('Completed, restored, unmodified frozen native evidence is required')
    if (report['registry_version'] != block_registry.source_version() or
            report['registry_fingerprint'].lower() != block_registry.fingerprint().lower()):
        raise ValueError('Native evidence and candidate must match the installed block registry')
    session_path = Path(report['session_file']).resolve()
    session = json.loads(session_path.read_text(encoding='utf8'))
    session['session_file'] = str(session_path)
    if session['owner'] != report['owner']:
        raise ValueError('Native evidence differs from its session owner')
    calibration_source = checked_fingerprint(report['calibration'])
    calibration = json.loads(Path(calibration_source['path']).read_text(encoding='utf8'))
    if (not calibration.get('completed') or not calibration.get('passed') or not calibration.get('restored') or
            calibration.get('cleanup_errors') or Path(calibration['session_file']).resolve() != session_path):
        raise ValueError('Passed and restored same-session calibration is required')
    source_names = ('runner_source', 'diagnostic_fixture_source', 'public_fixture_source',
                    'reviewed_harness_source', 'neighbor_backdrop_fixture_source')
    sources = dict((name, checked_fingerprint(report[name])) for name in source_names if name in report)
    pose, rows = report['camera'], []
    output.mkdir(parents=True)
    selected = set(selected) if selected else {case['case'] for case in report['cases']}
    seen = set()
    for case in report['cases']:
        identity = case['case']
        if identity in seen:
            raise ValueError('Source report repeats a case')
        seen.add(identity)
        if identity not in selected:
            continue
        plan = case['source']
        if not case.get('completed') or plan.get('shell'):
            raise ValueError('Only completed no-shell cases are eligible')
        if plan.get('context_changed') is not False and not (
                plan.get('context_changed') is True and plan.get('background_changed') is True and
                plan.get('source_neighbor_context_changed') is False and plan.get('background_cells')):
            raise ValueError('Context changes must be an explicit remote background only')
        size, captures = None, {}
        for control in CONTROLS:
            item = case['controls'][control]
            gate = native_gate(item['native_before_capture'], item['native_after_capture'],
                               plan, plan['controls'][control]['cells'])
            if not item.get('completed') or not gate['public_snapshot_unchanged']:
                raise ValueError('Native source or neighborhood changed: ' + identity + '/' + control)
            fixed_viewport(item['capture'], pose)
            if any(item['capture'][name] != pose['stable'] for name in ('camera_before', 'camera_after')):
                raise ValueError('Camera changed during a native control')
            size = validate_png(item['capture'], session, size)['size']
            captures[control] = checked_fingerprint(item['capture'])
        camera = {'position': pose['stable']['position'], 'target': pose['target'],
                  'screen': pose['stable']['screen'], 'native_image_screen': size,
                  'vertical_fov': calibration['vertical_fov']}
        fixed_neighbors = check_fixed_neighbors(plan)
        check_remote_background(plan, fixed_neighbors)
        document, origin = source_document(plan, 'liquid_only')
        shapes = surfaces(document, profile, origin)
        expected = (visible_liquid_mask(polygons(shapes), fixed_neighbors, camera) if fixed_neighbors
                    else predicted_mask(shapes, camera))
        actual = ImageChops.multiply(difference_mask(captures['liquid_only']['path'],
                                                    captures['empty']['path'], 16), fixed_region(shapes, camera))
        actual = fill_enclosed_holes(actual)
        metrics = compare(actual, expected, tolerance)
        passed = (case.get('native_controls_passed') is True and metrics['actual_pixels'] >= 100 and
                  metrics['mask_iou'] >= .95 and metrics['outline_recall'] >= .95 and
                  metrics['outline_precision'] >= .95)
        files = {}
        for name, mask in (('actual', actual), ('expected', expected)):
            path = output / (identity + '_' + name + '.png')
            mask.save(path)
            files[name] = fingerprint(path)
        rows.append({'case': identity, 'original_pixel_controls_passed': case.get('native_controls_passed') is True,
                     'silhouette_passed': passed, 'metrics': metrics, 'pngs': files,
                     'raw_captures': captures, 'camera': camera,
                     'declared_remote_background': plan.get('background_cells', []),
                     'declared_fixed_neighbors': plan.get('fixed_neighbor_cells', []),
                     'original_context_changed': plan.get('context_changed'),
                     'surfaces': [{'position': pos, 'heights': shape.heights, 'faces': shape.faces}
                                  for pos, shape in shapes]})
    if not selected.issubset(seen):
        raise ValueError('Selected case is absent from the source report')
    result = {'schema_version': 1, 'report': fingerprint(report_path), 'profile': fingerprint(profile_path),
              'analyzer': fingerprint(Path(__file__)), 'calibration': calibration_source, 'sources': sources,
              'rows': rows, 'all_selected_silhouettes_passed': bool(rows) and all(row['silhouette_passed'] for row in rows),
              'native_geometry_accepted': False, 'accuracy_accepted': False,
              'scope': 'Explicit pure-fluid outer silhouettes only; no camera/profile fit, UV, tint, animation, '
                       'body occlusion, hidden-face or production acceptance.'}
    (output / 'report.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='ascii')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('profile', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append')
    parser.add_argument('--outline-tolerance', type=int, choices=(2, 3), default=3)
    args = parser.parse_args()
    result = analyze(args.report, args.profile, args.output, args.case, args.outline_tolerance)
    print(json.dumps({'cases': len(result['rows']), 'passed': result['all_selected_silhouettes_passed'],
                      'metrics': [dict(row['metrics'], case=row['case'], passed=row['silhouette_passed'])
                                  for row in result['rows']]}))
    return 0 if result['all_selected_silhouettes_passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
