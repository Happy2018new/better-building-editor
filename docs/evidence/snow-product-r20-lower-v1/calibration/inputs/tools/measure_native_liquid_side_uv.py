"""Measure fixed liquid-side artwork hypotheses on training and held-out pixels.

The camera, surfaces, sample grid, image identities and clock are inputs. Only
one constant photometric model per sequence and declared UV/clock hypotheses
are fitted. Synthetic success never establishes native or production accuracy.
"""
import argparse
from dataclasses import dataclass, asdict
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image

ORIENTATIONS = ('identity', 'rot90', 'rot180', 'rot270', 'flip_x', 'flip_y',
                'transpose', 'transverse')
REGIONS = ('full', 'nw', 'ne', 'sw', 'se')
SIDE_V = ('bottom', 'top', 'stretch')
FACE_CORNERS = {'north': (0, 1), 'south': (2, 3), 'west': (3, 0), 'east': (1, 2)}
DEFAULT_LIMITS = {'maximum_rgb_rmse': 3.0, 'minimum_explained_variance': .9,
                  'minimum_texture_rms': 2.0, 'minimum_property_margin_rmse': .5}
MAX_CLOCK_BATCH = 256


@dataclass(frozen=True)
class Hypothesis:
    region: str
    side_v: str
    orientation: str
    ticks_per_frame: float
    blend_frames: bool
    phase: float
    pixel_mapping: str = 'centers'

    def __post_init__(self):
        if (self.region not in REGIONS or self.side_v not in SIDE_V or
                self.orientation not in ORIENTATIONS or self.pixel_mapping not in ('centers', 'edges') or
                type(self.blend_frames) is not bool or not math.isfinite(self.phase) or
                not math.isfinite(self.ticks_per_frame) or self.ticks_per_frame <= 0):
            raise ValueError('Invalid fixed UV/clock hypothesis')

    @property
    def v_basis(self):
        return 'fraction' if self.side_v == 'stretch' else 'height'

    @property
    def region_scale(self):
        return 1 if self.region == 'full' else .5


def fingerprint(path):
    path = Path(path).resolve()
    payload = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(payload).hexdigest()}


def checked_file(record):
    observed = fingerprint(record['path'])
    if observed['sha256'] != record['sha256']:
        raise ValueError('Evidence fingerprint changed: ' + observed['path'])
    return Path(observed['path'])


def side_grid(origin, heights, side, u_values, vertical_fractions):
    """Use declared block-space points; screen pixels cannot move this grid."""
    origin, heights = np.asarray(origin, float), np.asarray(heights, float)
    if (origin.shape != (3,) or heights.shape != (4,) or not np.isfinite(origin).all() or
            not np.isfinite(heights).all() or np.any(heights <= 0) or np.any(heights > 1) or
            side not in FACE_CORNERS):
        raise ValueError('A finite, positive fixed side surface is required')
    u, fraction = np.meshgrid(np.asarray(u_values, float), np.asarray(vertical_fractions, float))
    u, fraction = u.ravel(), fraction.ravel()
    if not (len(u) and np.isfinite(u).all() and np.isfinite(fraction).all() and
            np.all((u >= .1) & (u <= .9)) and np.all((fraction >= .1) & (fraction <= .9))):
        raise ValueError('Declare an inset, finite sample grid before observing pixels')
    first, second = FACE_CORNERS[side]
    top = heights[first] * (1 - u) + heights[second] * u
    height = top * fraction
    if side == 'north':
        x, z = u, np.zeros_like(u)
    elif side == 'south':
        x, z = 1 - u, np.ones_like(u)
    elif side == 'west':
        x, z = np.zeros_like(u), 1 - u
    else:
        x, z = np.ones_like(u), u
    return {'world_points': np.column_stack((x, height, z)) + origin,
            'u': u, 'height': height, 'top': top}


def oriented_uv(u, v, orientation):
    if orientation == 'identity': return u, v
    if orientation == 'rot90': return v, 1 - u
    if orientation == 'rot180': return 1 - u, 1 - v
    if orientation == 'rot270': return 1 - v, u
    if orientation == 'flip_x': return 1 - u, v
    if orientation == 'flip_y': return u, 1 - v
    if orientation == 'transpose': return v, u
    if orientation == 'transverse': return 1 - v, 1 - u
    raise ValueError('Unknown orientation')


def bilinear(image, x, y):
    """Sample pixel centers, preserving fractional projected coordinates."""
    height, width = image.shape[:2]
    x, y = np.clip(x, 0, width - 1), np.clip(y, 0, height - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, width - 1), np.minimum(y0 + 1, height - 1)
    ax, ay = (x - x0)[..., None], (y - y0)[..., None]
    return ((1 - ax) * (1 - ay) * image[y0, x0] + ax * (1 - ay) * image[y0, x1] +
            (1 - ax) * ay * image[y1, x0] + ax * ay * image[y1, x1])


def spatial_templates(strip, grid, hypothesis):
    count, width, unused, channels = strip.shape
    if width != unused or channels != 3 or not np.isfinite(strip).all():
        raise ValueError('A finite RGB square-frame strip is required')
    u, height, top = (grid[key] for key in ('u', 'height', 'top'))
    v = {'bottom': lambda: 1 - height, 'top': lambda: height,
         'stretch': lambda: 1 - height / top}[hypothesis.side_v]()
    u, v = oriented_uv(u, v, hypothesis.orientation)
    quarter = hypothesis.region != 'full'
    span = width / 2 if quarter else width
    offset_x = span if hypothesis.region in ('ne', 'se') else 0
    offset_y = span if hypothesis.region in ('sw', 'se') else 0
    if hypothesis.pixel_mapping == 'centers':
        x, y = offset_x + u * (span - 1), offset_y + v * (span - 1)
    else:
        x, y = offset_x + u * span - .5, offset_y + v * span - .5
    return np.asarray([bilinear(frame, x, y) for frame in strip])


def timed_templates(templates, seconds, hypotheses):
    ticks = np.asarray([item.ticks_per_frame for item in hypotheses])[:, None]
    phase = np.asarray([item.phase for item in hypotheses])[:, None]
    clock = np.asarray(seconds)[None, :] * 20 / ticks + phase
    first = np.floor(clock).astype(np.int64) % len(templates)
    fraction = (clock - np.floor(clock)) * np.asarray([item.blend_frames for item in hypotheses])[:, None]
    return (templates[first] * (1 - fraction[..., None, None]) +
            templates[(first + 1) % len(templates)] * fraction[..., None, None])


def photo_models(templates, positive, background):
    """Batch one gain/bias per channel and one shared opacity per sequence."""
    batch = len(templates)
    t = templates.reshape(batch, -1, 3)
    b = np.asarray(background).reshape(-1, 3)
    y = np.asarray(positive).reshape(-1, 3) - b
    count = len(b)
    gram, rhs = np.zeros((batch, 7, 7)), np.zeros((batch, 7))
    for channel in range(3):
        tc, bc, yc = t[:, :, channel], b[:, channel], y[:, channel]
        bias = 4 + channel
        gram[:, channel, channel] = np.sum(tc * tc, axis=1)
        gram[:, channel, 3] = gram[:, 3, channel] = -np.sum(tc * bc, axis=1)
        gram[:, channel, bias] = gram[:, bias, channel] = np.sum(tc, axis=1)
        gram[:, 3, bias] = gram[:, bias, 3] = -np.sum(bc)
        gram[:, bias, bias] = count
        rhs[:, channel] = np.sum(tc * yc, axis=1)
        rhs[:, bias] = np.sum(yc)
    gram[:, 3, 3] = np.sum(b * b)
    rhs[:, 3] = -np.sum(b * y)
    coefficients = np.einsum('bij,bj->bi', np.linalg.pinv(gram, rcond=1e-12), rhs)
    opacity = np.clip(coefficients[:, 3], 0, 1)
    target = y[None, :, :] + opacity[:, None, None] * b[None, :, :]
    centered = t - t.mean(axis=1, keepdims=True)
    variance = np.sum(centered * centered, axis=1)
    gain = np.clip(np.sum(centered * target, axis=1) / np.maximum(variance, 1e-12), 0, 2)
    bias = target.mean(axis=1) - gain * t.mean(axis=1)
    return {'gain': gain, 'bias': bias, 'opacity': opacity}


def predict(templates, background, model):
    return (np.asarray(background)[None, ...] * (1 - model['opacity'][:, None, None, None]) +
            templates * model['gain'][:, None, None, :] + model['bias'][:, None, None, :])


def null_prediction(positive, background, calibration):
    b, y = background[calibration].reshape(-1, 3), positive[calibration].reshape(-1, 3)
    matrix = np.zeros((len(b) * 3, 4))
    for channel in range(3):
        matrix[channel::3, 0] = b[:, channel]
        matrix[channel::3, channel + 1] = 1
    coefficients = np.linalg.lstsq(matrix, y.ravel(), rcond=None)[0]
    return background * coefficients[0] + coefficients[1:]


def validate_sequence(sequence):
    seconds = np.asarray(sequence['seconds'], float)
    positive, background = (np.asarray(sequence[key], float) for key in ('positive', 'background'))
    roles = sequence['roles']
    if (seconds.ndim != 1 or len(seconds) != len(roles) or not np.isfinite(seconds).all() or
            np.any(np.diff(seconds) <= 0) or positive.shape != background.shape or
            positive.shape != (len(seconds), len(sequence['grid']['u']), 3) or
            not np.isfinite(positive).all() or not np.isfinite(background).all() or
            any(role not in ('calibration', 'training', 'holdout') for role in roles) or
            not any(role == 'calibration' for role in roles) or not any(role == 'holdout' for role in roles) or
            (sequence['geometry_role'] == 'training' and not any(role == 'training' for role in roles))):
        raise ValueError('A finite ordered sequence needs distinct calibration and held-out frames')
    if sequence['geometry_role'] not in ('training', 'holdout'):
        raise ValueError('Declare the geometry holdout before measurement')
    grid = sequence['grid']
    if (any(np.asarray(grid[key]).shape != (positive.shape[1],) for key in ('u', 'height', 'top')) or
            any(not np.isfinite(grid[key]).all() for key in ('u', 'height', 'top')) or
            np.any(np.asarray(grid['top']) <= 0) or np.any(np.asarray(grid['top']) > 1) or
            np.any(np.asarray(grid['height']) <= 0) or np.any(np.asarray(grid['height']) >= grid['top'])):
        raise ValueError('Each observation must bind one finite inset side-grid point')
    return seconds, positive, background, np.asarray(roles)


def evaluate_batch(strip, sequences, hypotheses, include_holdouts=False):
    total, count, metrics = np.zeros(len(hypotheses)), 0, {}
    spatial = hypotheses[0]
    if any((item.region, item.side_v, item.orientation, item.pixel_mapping) !=
           (spatial.region, spatial.side_v, spatial.orientation, spatial.pixel_mapping) for item in hypotheses):
        raise ValueError('Clock batches must use one fixed spatial hypothesis')
    for sequence in sequences:
        if not include_holdouts and sequence['geometry_role'] != 'training':
            continue
        seconds, positive, background, roles = validate_sequence(sequence)
        templates = timed_templates(spatial_templates(strip, sequence['grid'], spatial), seconds, hypotheses)
        calibration = roles == 'calibration'
        model = photo_models(templates[:, calibration], positive[calibration], background[calibration])
        predictions = predict(templates, background, model)
        selected = roles == ('holdout' if include_holdouts else 'training')
        if not selected.any():
            if include_holdouts or sequence['geometry_role'] == 'training':
                raise ValueError('Every selected sequence needs declared scoring frames')
            continue
        residual = predictions[:, selected] - positive[None, selected]
        squared = np.sum(residual * residual, axis=(1, 2, 3))
        elements = residual[0].size
        total += squared
        count += elements
        baseline = null_prediction(positive, background, calibration)
        null_squared = np.sum((baseline[selected] - positive[selected]) ** 2)
        signal = templates[:, selected] * model['gain'][:, None, None, :]
        signal = signal.reshape(len(hypotheses), -1, 3)
        texture_rms = np.sqrt(np.mean((signal - signal.mean(axis=1, keepdims=True)) ** 2, axis=(1, 2)))
        metrics[sequence['id']] = {'rgb_rmse': np.sqrt(squared / elements),
            'explained_variance': 1 - squared / max(null_squared, 1e-12), 'texture_rms': texture_rms,
            'photometric': model, 'points': len(sequence['grid']['u']), 'frames': int(selected.sum())}
    if count == 0:
        raise ValueError('No training or holdout observations')
    return np.sqrt(total / count), metrics


def scalar_metrics(metrics, index):
    return {key: {'rgb_rmse': float(row['rgb_rmse'][index]),
                  'explained_variance': float(row['explained_variance'][index]),
                  'texture_rms': float(row['texture_rms'][index]),
                  'photometric': {name: values[index].tolist() for name, values in row['photometric'].items()},
                  'points': row['points'], 'frames': row['frames']}
            for key, row in metrics.items()}


def metrics_pass(metrics, limits):
    return all(row['rgb_rmse'] <= limits['maximum_rgb_rmse'] and
               row['explained_variance'] >= limits['minimum_explained_variance'] and
               row['texture_rms'] >= limits['minimum_texture_rms'] for row in metrics.values())


def measure(strip, sequences, hypotheses, limits=None, required_properties=('v_basis', 'region_scale', 'ticks_per_frame')):
    limits = dict(DEFAULT_LIMITS, **(limits or {}))
    if (set(limits) != set(DEFAULT_LIMITS) or any(not math.isfinite(value) for value in limits.values()) or
            limits['maximum_rgb_rmse'] <= 0 or limits['maximum_rgb_rmse'] > DEFAULT_LIMITS['maximum_rgb_rmse'] or
            any(limits[key] < DEFAULT_LIMITS[key] for key in DEFAULT_LIMITS if key != 'maximum_rgb_rmse')):
        raise ValueError('Measurement limits can be tightened but cannot relax the fixed contract')
    if (not hypotheses or not sequences or len({row['id'] for row in sequences}) != len(sequences) or
            not any(row['geometry_role'] == 'holdout' for row in sequences)):
        raise ValueError('Distinct training and geometry holdout sequences are required')
    if any(name not in set(Hypothesis.__dataclass_fields__) | {'v_basis', 'region_scale'} or name == 'phase'
           for name in required_properties):
        raise ValueError('Unknown required identification property')
    grouped = {}
    for hypothesis in hypotheses:
        key = (hypothesis.region, hypothesis.side_v, hypothesis.orientation, hypothesis.pixel_mapping)
        grouped.setdefault(key, []).append(hypothesis)
    scores, property_scores = [], {name: {} for name in required_properties}
    for spatial_batch in grouped.values():
        for start in range(0, len(spatial_batch), MAX_CLOCK_BATCH):
            batch = spatial_batch[start:start + MAX_CLOCK_BATCH]
            errors, unused = evaluate_batch(strip, sequences, batch)
            best = int(np.argmin(errors))
            scores.append((float(errors[best]), batch[best]))
            for name in required_properties:
                values = {getattr(item, name) for item in batch}
                for value in values:
                    indices = [index for index, item in enumerate(batch) if getattr(item, name) == value]
                    index = min(indices, key=lambda index: errors[index])
                    candidate = (float(errors[index]), batch[index])
                    previous = property_scores[name].get(value)
                    if previous is None or candidate[0] < previous[0]:
                        property_scores[name][value] = candidate
    scores.sort(key=lambda row: row[0])
    best_error, best = scores[0]
    unused, training = evaluate_batch(strip, sequences, [best])
    holdout_error, holdouts = evaluate_batch(strip, sequences, [best], True)
    training, holdouts = scalar_metrics(training, 0), scalar_metrics(holdouts, 0)
    identification = {}
    for property_name in required_properties:
        alternatives = [candidate for value, candidate in property_scores[property_name].items()
                        if value != getattr(best, property_name)]
        alternatives.sort(key=lambda row: row[0])
        if not alternatives:
            identification[property_name] = {'identified': False, 'reason': 'no_declared_wrong_property_control'}
            continue
        alternative_error, alternative = alternatives[0]
        unused, alternative_metrics = evaluate_batch(strip, sequences, [alternative], True)
        alternative_metrics = scalar_metrics(alternative_metrics, 0)
        identification[property_name] = {'identified': alternative_error - best_error >= limits['minimum_property_margin_rmse'],
            'training_margin_rgb_rmse': alternative_error - best_error,
            'alternative': asdict(alternative), 'alternative_holdout': alternative_metrics,
            'alternative_rejected_on_holdout': not metrics_pass(alternative_metrics, limits)}
        identification[property_name]['identified'] &= identification[property_name]['alternative_rejected_on_holdout']
    passed = (metrics_pass(training, limits) and metrics_pass(holdouts, limits) and
              all(row['identified'] for row in identification.values()))
    return {'schema_version': 1, 'selected': asdict(best), 'training_rgb_rmse': best_error,
            'holdout_rgb_rmse': float(holdout_error[0]), 'training': training, 'holdouts': holdouts,
            'identification': identification, 'limits': limits, 'passed': passed,
            'hypotheses_tested': len(hypotheses), 'native_geometry_accepted': False,
            'native_uv_accepted': False, 'production_accepted': False,
            'scope': 'Fixed-grid source-artwork/clock discrimination; native binding and production acceptance are separate',
            'orientation_identification_scope': 'Top versus bottom anchoring is equivalent under a vertical UV flip; v_basis identifies height versus stretched fraction, and selected orientation describes the compound mapping'}


def hypotheses_from_plan(plan, frame_count):
    required = ('regions', 'side_v', 'orientations', 'ticks_per_frame', 'blend_frames', 'pixel_mapping')
    if any(key not in plan or not plan[key] for key in required):
        raise ValueError('All spatial and clock hypothesis sets must be explicit')
    phases = plan.get('phases')
    if phases is None:
        steps = plan['phase_steps_per_frame']
        if type(steps) is not int or not 1 <= steps <= 16:
            raise ValueError('Declare a finite phase-grid resolution')
        phases = np.arange(frame_count * steps) / steps
    return [Hypothesis(region, v, orientation, float(ticks), blend, float(phase), mapping)
            for region, v, orientation, ticks, blend, mapping, phase in itertools.product(
                *(plan[key] for key in required), phases)]


def load_artwork(source):
    blocks = json.loads(checked_file(source['blocks']).read_text(encoding='utf8'))
    atlas = json.loads(checked_file(source['atlas']).read_text(encoding='utf8'))['texture_data']
    flips = json.loads(checked_file(source['flipbook']).read_text(encoding='utf8'))
    key = blocks['water']['textures']['side']
    if source['native_name'] != 'minecraft:water' or key != 'flowing_water_grey':
        raise ValueError('Only exact native water side artwork is eligible; aliases are not normalized')
    rows = [row for row in flips if row['atlas_tile'] == key]
    if len(rows) != 1 or atlas[key]['textures'] != rows[0]['flipbook_texture'] or rows[0].get('frames') is not None:
        raise ValueError('Native texture lookup or explicit frame-order source changed')
    expected_png = checked_file(source['blocks']).parent / (rows[0]['flipbook_texture'] + '.png')
    if checked_file(source['png']) != expected_png.resolve():
        raise ValueError('The bitmap must be the original file resolved by the native flipbook metadata')
    with Image.open(checked_file(source['png'])) as image:
        rgba = np.asarray(image.convert('RGBA'))
    height, width, unused = rgba.shape
    if height % width or width % 2:
        raise ValueError('A square-frame, quarter-divisible strip is required')
    return rgba[:, :, :3].reshape(height // width, width, width, 3).astype(float), {
        'atlas_key': key, 'terrain': atlas[key], 'flipbook': rows[0],
        'ticks_per_frame_explicit': 'ticks_per_frame' in rows[0],
        'alpha_range': [int(rgba[:, :, 3].min()), int(rgba[:, :, 3].max())],
        'source': source}


def validate_control_cells(plan):
    controls = plan['controls']
    if set(controls) != {'supported_positive', 'supported_negative', 'liquid_only', 'empty'}:
        raise ValueError('Four exact native source controls are required')
    reserved = {tuple(pos) for pos in plan['reserved']}
    parsed = {}
    for control, row in controls.items():
        cells = {}
        for entry in row['cells']:
            if not isinstance(entry, (list, tuple)) or len(entry) != 2:
                raise ValueError('Native control cells must be explicit position/value pairs')
            pos, value = entry
            if (not isinstance(pos, (list, tuple)) or len(pos) != 3 or
                    any(type(coordinate) is not int for coordinate in pos) or
                    not isinstance(value, (list, tuple)) or len(value) != 2 or
                    not isinstance(value[0], str) or type(value[1]) is not int or
                    value[0] == 'minecraft:flowing_water'):
                raise ValueError('Native control cells must contain exact names and integer auxiliary values')
            pos, value = tuple(pos), list(value)
            if pos in cells or pos not in reserved:
                raise ValueError('Every native source position must be unique and reserved')
            cells[pos] = value
        parsed[control] = cells
    fluids = {pos: value for pos, value in parsed['supported_positive'].items() if value[0] == 'minecraft:water'}
    if not fluids or any(not 0 <= value[1] <= 15 for value in fluids.values()):
        raise ValueError('Exact static-water depth cells are required')
    for positive, negative in (('supported_positive', 'supported_negative'), ('liquid_only', 'empty')):
        actual = {pos: value for pos, value in parsed[positive].items() if value[0] == 'minecraft:water'}
        difference = {pos: value for pos, value in parsed[positive].items() if pos not in fluids}
        if (actual != fluids or any(parsed[negative].get(pos, ['minecraft:air', 0]) != ['minecraft:air', 0]
                                    for pos in fluids) or difference != parsed[negative]):
            raise ValueError('Water must be the sole difference in both positive/negative control pairs')
    return set(fluids)


def load_native_contract(contract):
    from capture_pure_liquid_native_controls import matches, validate_png, fixed_viewport
    from measure_native_liquid_surface import projected_pixels, pixel_viewport
    if (contract.get('schema_version') != 1 or contract.get('native_name') != 'minecraft:water' or
            not contract.get('completed') or not contract.get('restored') or contract.get('cleanup_errors') or
            contract.get('setter') != 'SetBlockNew' or not contract.get('flow_freeze', {}).get('forbidden') or
            not contract.get('flow_restore', {}).get('native_return_verified')):
        raise ValueError('Completed, restored exact-water SetBlockNew evidence is required')
    calibration = json.loads(checked_file(contract['calibration']).read_text(encoding='utf8'))
    shape_report = json.loads(checked_file(contract['shape_analysis']).read_text(encoding='utf8'))
    frozen_source = json.loads(checked_file(shape_report['report']).read_text(encoding='utf8'))
    for record in [shape_report['analyzer'], shape_report['profile']] + list(shape_report['sources'].values()):
        checked_file(record)
    if (not all(calibration.get(key) for key in ('completed', 'passed', 'restored')) or
            calibration.get('cleanup_errors') or not shape_report.get('all_selected_silhouettes_passed') or
            shape_report['calibration']['sha256'] != contract['calibration']['sha256']):
        raise ValueError('Independent stone calibration and passed frozen silhouettes are required')
    session = contract['session_binding']
    manifest = json.loads(Path(session['session_file']).read_text(encoding='utf8'))
    if any(str(session[key]) != str(manifest[key]) for key in ('owner', 'game_pid', 'game_identity', 'id')):
        raise ValueError('Capture binding differs from its recorded owner process identity')
    if Path(calibration['session_file']).resolve() != Path(session['session_file']).resolve():
        raise ValueError('Calibration belongs to another native session')
    if Path(frozen_source['session_file']).resolve() != Path(session['session_file']).resolve():
        raise ValueError('Frozen shape source belongs to another native session')
    preflight = json.loads(checked_file(contract['preflight']).read_text(encoding='utf8'))
    if (preflight['sample_grid'] != contract['sample_grid'] or preflight['hypotheses'] != contract['hypotheses'] or
            type(preflight['created_qpc_100ns']) is not int or preflight['created_qpc_100ns'] <= 0 or
            preflight['session_binding'] != session):
        raise ValueError('Sample grid, hypothesis search and session must match the frozen preflight')
    sequences = []
    for item in contract['sequences']:
        plan, pose = item['source_plan'], item['camera_pose']
        shape_row = next((row for row in shape_report['rows'] if row['case'] == item['case']), None)
        source_case = next((row for row in frozen_source['cases'] if row['case'] == item['case']), None)
        declared = next((row for row in preflight['sequences'] if row['id'] == item['id']), None)
        if (shape_row is None or shape_row['camera'] != item['camera'] or source_case is None or
                source_case['source'] != plan or not shape_row['silhouette_passed'] or
                not shape_row['original_pixel_controls_passed']):
            raise ValueError('Fixed camera differs from the frozen shape evidence')
        if (declared is None or any(declared[key] != item[key] for key in
                                    ('id', 'case', 'geometry_role', 'surfaces', 'source_plan', 'camera', 'camera_pose',
                                     'temporal_control')) or
                declared['frame_roles'] != [frame['role'] for frame in item['frames']]):
            raise ValueError('Source geometry and frame roles must match the frozen preflight')
        if item['camera']['vertical_fov'] != calibration['vertical_fov']:
            raise ValueError('The liquid sequence cannot refit the independent camera')
        positions = plan['reserved']
        controls = plan['controls']
        fluid_positions = validate_control_cells(plan)
        def read_frame(record, control):
            expected = controls[control]['cells'] + [(plan['platform'], ['minecraft:stone', 0])]
            for label in ('native_before_capture', 'native_after_capture'):
                if not all(matches(record[label][side], expected, positions) for side in ('server', 'client')):
                    raise ValueError('Exact native source or neighborhood changed')
            fixed_viewport(record['capture'], pose)
            if any(record['capture'][label] != pose['stable'] for label in ('camera_before', 'camera_after')):
                raise ValueError('Native camera changed during the temporal frame')
            validate_png(record['capture'], session, item['camera']['native_image_screen'])
            with Image.open(checked_file(record['capture'])) as image:
                return np.asarray(image.convert('RGB'), float)
        if any(fingerprint(item['static_controls'][control]['capture']['path']) !=
               shape_row['raw_captures'][control] for control in controls):
            raise ValueError('Four static controls must be the exact frozen silhouette capture files')
        static = {control: read_frame(item['static_controls'][control], control) for control in controls}
        grids = []
        for surface in item['surfaces']:
            proof = next((row for row in shape_row['surfaces'] if row['position'] == surface['cell_origin']), None)
            face = surface['side']
            face_bit = {'north': 2, 'south': 4, 'west': 8, 'east': 16}.get(face, 0)
            if (proof is None or not proof['faces'] & face_bit or proof['heights'] != surface['corner_heights'] or
                    tuple(surface['cell_origin']) not in fluid_positions):
                raise ValueError('Sample surface differs from the frozen native silhouette source')
            origin, camera_position = surface['cell_origin'], item['camera']['position']
            facing = {'north': camera_position[2] < origin[2], 'south': camera_position[2] > origin[2] + 1,
                      'west': camera_position[0] < origin[0], 'east': camera_position[0] > origin[0] + 1}
            if not facing[face]:
                raise ValueError('A sampled side must face the fixed camera')
            grids.append(side_grid(surface['cell_origin'], surface['corner_heights'], surface['side'],
                                   contract['sample_grid']['u'], contract['sample_grid']['vertical_fraction']))
        if not grids:
            raise ValueError('Declare visible side surfaces before measurement')
        grid = {key: np.concatenate([part[key] for part in grids]) for key in grids[0]}
        points = projected_pixels(grid['world_points'], item['camera'], pixel_viewport(item['camera']))
        if any(not point['isInScreen'] or point['depth'] < .05 for point in points):
            raise ValueError('The complete declared grid must be visible in the fixed camera')
        x, y = (np.asarray([point[key] for point in points]) for key in ('screenX', 'screenY'))
        observed, background, seconds, roles = [], [], [], []
        for frame in item['frames']:
            control = frame['control']
            if control not in ('supported_positive', 'liquid_only') or control != item['temporal_control']:
                raise ValueError('A temporal frame must be an exact positive native control')
            observed.append(bilinear(read_frame(frame, control), x, y))
            negative = 'supported_negative' if control == 'supported_positive' else 'empty'
            background.append(bilinear(static[negative], x, y))
            stamp = frame['capture']['capture']['frame']['frame_qpc_100ns']
            if type(stamp) is not int or stamp <= preflight['created_qpc_100ns']:
                raise ValueError('Native temporal frames must be captured after the frozen preflight')
            seconds.append((stamp - contract['clock_origin_qpc_100ns']) / 1e7)
            roles.append(frame['role'])
        if len({frame['control'] for frame in item['frames']}) != 1:
            raise ValueError('One photometric sequence must use one unchanged positive control')
        sequences.append({'id': item['id'], 'geometry_role': item['geometry_role'], 'grid': grid,
                          'seconds': seconds, 'roles': roles,
                          'positive': np.asarray(observed), 'background': np.asarray(background)})
    return sequences


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('contract', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh report and preserve previous evidence')
    contract = json.loads(args.contract.read_text(encoding='utf8'))
    strip, artwork = load_artwork(contract['artwork'])
    sequences = load_native_contract(contract)
    result = measure(strip, sequences, hypotheses_from_plan(contract['hypotheses'], len(strip)),
                     contract.get('limits'), contract.get('required_properties', ('v_basis', 'region_scale', 'ticks_per_frame')))
    identified = {name for name, row in result['identification'].items() if row['identified']}
    result.update(contract=fingerprint(args.contract), analyzer=fingerprint(Path(__file__)), artwork=artwork,
                  native_binding_verified=True,
                  native_side_sampling_accepted=result['passed'] and {'v_basis', 'region_scale'}.issubset(identified),
                  native_cadence_accepted=result['passed'] and 'ticks_per_frame' in identified)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + '\n', encoding='ascii')
    print(json.dumps({'passed': result['passed'], 'selected': result['selected'],
                      'training_rmse': result['training_rgb_rmse'], 'holdout_rmse': result['holdout_rgb_rmse']}))
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
