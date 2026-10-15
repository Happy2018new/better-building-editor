"""Host-only height intervals from explicit pixels and a fixed camera.

The pixel budget is declared, not measured accuracy. No camera fit, PNG corner
detector, capture, live API, control validation or native acceptance is performed.
"""
import argparse
import json
import math
from pathlib import Path

from camera_projection import project_points

CORNERS = ((0, 0), (1, 0), (1, 1), (0, 1))


def vector(values, size, label):
    if len(values) != size:
        raise ValueError(label + ' has the wrong dimension')
    result = tuple(float(value) for value in values)
    if not all(math.isfinite(value) for value in result):
        raise ValueError(label + ' must contain finite values')
    return result


def camera_arguments(camera):
    position = vector(camera['position'], 3, 'camera position')
    target = vector(camera['target'], 3, 'camera target')
    screen = vector(camera['screen'], 2, 'camera screen')
    fov, roll = float(camera['vertical_fov']), float(camera.get('roll', 0.))
    if not math.isfinite(fov) or not math.isfinite(roll):
        raise ValueError('Camera angles must be finite')
    return position, target, screen, fov, roll


def pixel_viewport(camera):
    """Map a complete engine viewport to a complete native PNG, without fitting."""
    engine = vector(camera['screen'], 2, 'engine viewport')
    native = camera.get('native_image_screen')
    screen = engine if native is None else vector(native, 2, 'native PNG viewport')
    if any(value <= 0 for value in engine + screen):
        raise ValueError('Engine and native PNG viewport dimensions must be positive')
    return {'engine_screen': engine, 'observation_screen': screen,
            'scale': tuple(screen[i] / engine[i] for i in range(2)),
            'declared_pixel_budget_units': 'engine_pixels' if native is None else 'native_png_pixels',
            'method': 'identity' if native is None else 'independent_xy_full_viewport_scale',
            'capture_binding_verified': False, 'crop_supported': False}


def projected_pixels(points, camera, viewport):
    projected = project_points(points, *camera_arguments(camera))
    scale = viewport['scale']
    for point in projected:
        point['screenX'] *= scale[0]
        point['screenY'] *= scale[1]
    return projected


def measure_height(camera, xz, base_y, pixel, pixel_budget, near=.05):
    """Invert a known X/Z height line; return an interval conditional on that X/Z."""
    x, z = vector(xz, 2, 'known X/Z')
    pixel = vector(pixel, 2, 'observed pixel')
    base_y, budget, near = (float(value) for value in (base_y, pixel_budget, near))
    if not all(math.isfinite(value) for value in (base_y, budget, near)) or budget < 0 or near <= 0:
        raise ValueError('Height origin, nonnegative budget and positive near plane must be finite')
    camera_arguments(camera)
    viewport = pixel_viewport(camera)
    units = viewport['declared_pixel_budget_units']
    screen = viewport['observation_screen']
    result = {'status': 'unobservable', 'known_xz': [x, z],
              'declared_pixel_budget': budget, 'declared_pixel_budget_units': units,
              'pixel_viewport': viewport}
    if not (0 <= pixel[0] < screen[0] and 0 <= pixel[1] < screen[1]):
        return dict(result, reason='pixel_outside_viewport')
    try:
        endpoints = projected_pixels(((x, base_y, z), (x, base_y + 1., z)), camera, viewport)
    except ValueError as error:
        return dict(result, reason='invalid_projection', error=str(error))
    d0, d1 = (point['depth'] for point in endpoints)
    if min(d0, d1) < near:
        return dict(result, reason='height_line_near_clipped', depths=[d0, d1])
    if not all(point['isInScreen'] for point in endpoints):
        return dict(result, reason='height_line_outside_viewport')
    first, last = (tuple(point[key] for key in ('screenX', 'screenY')) for point in endpoints)
    direction = tuple(last[i] - first[i] for i in range(2))
    length_squared = sum(value * value for value in direction)
    if length_squared <= 1e-12:
        return dict(result, reason='height_line_degenerate')
    offset = tuple(pixel[i] - first[i] for i in range(2))
    t = sum(offset[i] * direction[i] for i in range(2)) / length_squared
    residual = math.sqrt(sum((offset[i] - t * direction[i]) ** 2 for i in range(2)))
    result.update(perpendicular_residual_pixels=residual,
                  projected_height_span_pixels=math.sqrt(length_squared))
    if residual > budget + 1e-9:
        return dict(result, reason='pixel_inconsistent_with_known_xz')
    if t < 0. or t > 1.:
        return dict(result, reason='point_estimate_outside_unit_height')

    # Perspective maps the line to t = h*d1 / (d0 + h*(d1-d0)).
    def height(parameter):
        return parameter * d0 / (d1 - parameter * (d1 - d0))

    radius = math.sqrt(max(0., budget * budget - residual * residual) / length_squared)
    lower_t, upper_t = max(0., t - radius), min(1., t + radius)
    estimate = height(t)
    interval = (height(lower_t), height(upper_t))
    projected, = projected_pixels(((x, base_y + estimate, z),), camera, viewport)
    result.update(status='diagnostic', height_estimate=estimate, height_interval=interval,
                  interval_width=interval[1] - interval[0],
                  budget_intersects_unit_endpoint=lower_t == 0. or upper_t == 1.,
                  reprojection_error_pixels=math.hypot(projected['screenX'] - pixel[0],
                                                       projected['screenY'] - pixel[1]),
                  accuracy_accepted=False, interval_scope='declared_pixel_budget_only',
                  known_xz_verified_from_image=False, camera_uncertainty_included=False)
    return result


def analyze_cell(data):
    """Keep all four corners, including missing, occluded and unattributed ones."""
    origin = vector(data['cell_origin'], 3, 'world cell origin')
    budget = float(data['declared_pixel_budget'])
    if not math.isfinite(budget) or budget < 0:
        raise ValueError('Declared pixel budget must be finite and nonnegative')
    camera_arguments(data['camera'])
    viewport = pixel_viewport(data['camera'])
    supplied = {}
    for observation in data.get('observations', ()):
        corner = tuple(observation['corner'])
        if corner not in CORNERS or corner in supplied:
            raise ValueError('Corner identity must be unique and use unit-cell X/Z offsets')
        supplied[corner] = observation
    rows = []
    for corner in CORNERS:
        observation = supplied.get(corner)
        result = {'status': 'unobservable', 'reason': 'no_explicit_observation'}
        if observation is not None:
            if not observation.get('source'):
                result['reason'] = 'observation_source_missing'
            elif observation.get('visibility') != 'visible_boundary':
                result['reason'] = 'boundary_visibility_not_established'
            else:
                result = measure_height(data['camera'], (origin[0] + corner[0], origin[2] + corner[1]),
                                        origin[1], observation['pixel'], budget,
                                        float(data.get('near', .05)))
        result.update(corner=corner, source=observation.get('source') if observation else None)
        rows.append(result)
    source = data.get('source')
    context_changed = source.get('context_changed') if isinstance(source, dict) else None
    return {'schema_version': 1, 'status': 'diagnostic_only', 'native_geometry_accepted': False,
            'accuracy_accepted': False, 'public_controls_eligible': False,
            'context_changed': context_changed,
            'source': data.get('source'), 'camera': data['camera'], 'cell_origin': origin,
            'declared_pixel_budget': budget, 'declared_pixel_budget_units': viewport['declared_pixel_budget_units'],
            'pixel_viewport': viewport, 'corners': rows,
            'four_corners_observed': all(row['status'] == 'diagnostic' for row in rows),
            'unobservable_corners': [row['corner'] for row in rows if row['status'] == 'unobservable'],
            'limits': {'pixel_budget_is_verified_accuracy': False, 'camera_fit_performed': False,
                       'control_pixels_verified': False, 'png_identity_verified': False,
                       'source_snapshot_binding_verified': False, 'viewport_capture_binding_verified': False,
                       'corner_assignment': 'caller-supplied visible boundary with explicit source',
                       'flatness_inferred': False, 'hidden_corners_filled': False}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Explicit observations and fixed camera JSON')
    parser.add_argument('output', type=Path, help='Fresh diagnostic JSON path')
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error('Output exists; choose a fresh diagnostic path')
    data = json.loads(args.input.read_text(encoding='utf8'))
    result = analyze_cell(data)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2) + '\n',
                           encoding='utf8')
    print(json.dumps({'status': result['status'], 'four_corners_observed': result['four_corners_observed'],
                      'native_geometry_accepted': False, 'output': str(args.output.resolve())}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
