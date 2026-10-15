"""Detect isolated raster speckles inside the native brown book-cover artwork.

This narrow regression is independent of book pose, brightness and body-height
acceptance. Use an unobscured close-up and inspect the image alongside its score.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

MAX_ISOLATED_PIXELS = 8
MIN_ARTWORK_PIXELS = 8000
MAX_DARK_FRACTION_DEVIATION = .15
ENGINE_VERSION = '3.10.0.420447'
OWNER_ROUTES = ('editor', 'full', 'missing')


def logical_document(value):
    """Decode MCDK's typed tuple receipts without executing their contents.

    The v2 host returned a deeply nested document as an object. MCDK represents
    tuples beyond its object-depth limit with a complete literal receipt.
    Subsequent captures JSON-encode on the game side to avoid that conversion.
    """
    if isinstance(value, dict):
        if set(value) == {'__type__', '__repr__'} and value['__type__'] == 'tuple':
            decoded = ast.literal_eval(value['__repr__'])
            if not isinstance(decoded, tuple):
                raise ValueError('Invalid MCDK document tuple receipt')
            return logical_document(decoded)
        return {key: logical_document(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [logical_document(item) for item in value]
    return value


def capture_receipt(label, row):
    """Verify pixels before either an appearance or an owner assertion uses them."""
    capture = row['capture']
    path = Path(capture['path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != capture['sha256']:
        raise ValueError('Book image no longer matches its capture receipt: '+str(path))
    if not capture.get('reliable'):
        raise ValueError('Book capture is unreliable: '+str(path))
    if not isinstance(capture.get('frame', {}).get('frame_qpc_100ns'), int):
        raise ValueError('Book capture has no native frame timestamp: '+label)
    return capture, path


def owner_matrix(report):
    """Read the independent owner contract without granting pixel qualification.

    A count alone cannot identify a correct model. The initial editor readback
    supplies UI model identities; every world frame supplies model and opacity
    identities. Hidden and empty cases deliberately own no visible group.
    """
    if report.get('owner_path') != 'independent_book':
        return None
    captures = report.get('captures', {})
    checks = {
        'report_identity': (report.get('schema_version') == 2 and
                            report.get('engine') == ENGINE_VERSION and
                            report.get('owner_matrix') is True and
                            report.get('model_prefix') == ''),
        'restoration': (all(report.get(key) is True for key in
                            ('completed', 'restored', 'source_unchanged')) and
                        report.get('cleanup_errors') == []),
    }
    if report.get('stage') == 'production_default':
        default = report.get('default_profile', {})
        checks['profile_path'] = (report.get('production_default_requested') is True and
            report.get('profile_assignment_performed') is False and
            default.get('qualified') is True and default.get('engine') == ENGINE_VERSION)
    else:
        checks['profile_path'] = (report.get('candidate_setup') is True and
                                 report.get('candidate_restoration') is True)
    expected_models = {'enchanting_table': 'modern_projection_book_enchanting_table',
                       'lectern.book': 'modern_projection_book_lectern',
                       'lectern.empty': None}
    for case, model in expected_models.items():
        ready = report.get('rows', {}).get(case, {}).get('ready', {}).get('book', {})
        groups = ready.get('groups', [])
        checks['editor_model_'+case] = (ready.get('owned') is True and
            ready.get('ready') is True and not ready.get('pending') and
            not ready.get('error') and len(groups) == int(model is not None) and
            (not groups or all(len(group) > 1 and group[1] == model for group in groups)))
        suffixes = ['yaw35', 'yaw215']
        if model is not None:
            suffixes += ['yaw35_pitch75_zoom3', 'yaw215_pitch25_zoom1',
                         'yaw35_pitch25_zoom2', 'section_layer2', 'section_layer3',
                         'single_layer2', 'single_layer3', 'full_layer3', 'hidden', 'restored']
        for suffix in suffixes:
            label = 'editor_'+case+'_'+suffix
            state = captures.get(label, {}).get('book_models', {})
            visible = model is not None and suffix not in ('section_layer2', 'single_layer2', 'hidden')
            checks[label] = (state.get('active') is False and
                state.get('preview_owned') is True and state.get('models') == [] and
                state.get('preview_groups') == int(visible))
        for route in ('full', 'missing'):
            suffixes = ['motion0', 'opacity0.35', 'opacity0.7', 'opacity1.0']
            if case == 'enchanting_table':
                suffixes += ['motion1', 'motion2']
            for suffix in suffixes:
                label = route+'_'+case+'_'+suffix
                state = captures.get(label, {}).get('book_models', {})
                opacity = float(suffix[len('opacity'):]) if suffix.startswith('opacity') else 1.
                checks[label] = (state.get('active') is True and
                    state.get('preview_owned') is False and state.get('preview_groups') == 0 and
                    state.get('models') == ([model+'_world'] if model else []) and
                    state.get('world_opacity') == ([opacity] if model else []))
        if model is not None and report.get('occupancy_matrix') is True:
            source = report.get('rows', {}).get(case, {})
            occupancy = source.get('occupancy', {})
            original = source.get('source_document')
            for suffix, expected in (('occupied', []), ('restored', [model+'_world'])):
                label = 'missing_'+case+'_'+suffix
                state = captures.get(label, {}).get('book_models', {})
                server = occupancy.get(suffix, [])
                checks[label] = (state.get('active') is True and state.get('models') == expected and
                    original is not None and
                    logical_document(occupancy.get(suffix+'_source_document')) == logical_document(original) and
                    len(server) == 1 and server[0].get('after', {}).get('name') ==
                    ('minecraft:stone' if suffix == 'occupied' else 'minecraft:air'))
    # Additional captures may extend the matrix, but must retain valid receipts.
    for label, row in captures.items():
        capture_receipt(label, row)
    return {'checks': checks, 'capture_count': len(captures),
            'occupancy_included': report.get('occupancy_matrix') is True,
            'passed': bool(checks) and all(checks.values())}


def cover_pixels(image):
    r, g, b = np.moveaxis(image, -1, 0)
    return (r > g*1.25) & (g > b*1.3) & (g > 25) & (r < 220)


def isolated_cover_pixels(image):
    image = np.asarray(image, dtype=np.int16)
    center = image[1:-1, 1:-1]
    neighbors = np.stack((image[:-2, 1:-1], image[2:, 1:-1],
                          image[1:-1, :-2], image[1:-1, 2:]))
    # Texture regions and diagonals may change color; the failure consists of
    # individual fragments with a different color inside a uniform region.
    agree = np.max(np.ptp(neighbors, axis=0), axis=2) <= 3
    contrast = np.max(abs(center-neighbors.mean(axis=0)), axis=2) >= 12
    return cover_pixels(center) & np.all(cover_pixels(neighbors), axis=0) & agree & contrast


def artwork_distribution(image):
    """Reject the inside face of the native cover, independent of its exposure.

    This close-up fixture uses native references at the same camera. The outer
    artwork has a narrow dark border; a wrongly culled inside face is mostly
    dark. Only sufficiently broad cover views can establish this distinction.
    """
    pixels = image[cover_pixels(image)]
    if len(pixels) < MIN_ARTWORK_PIXELS:
        return None
    luma = pixels @ np.array((.2126, .7152, .0722))
    return float(np.mean(luma < np.percentile(luma, 90) * .75))


def analyze(source, output):
    raw = source.read_bytes()
    report = json.loads(raw)
    owners = owner_matrix(report)
    rows = []
    for label, row in report['captures'].items():
        if 'enchanting' not in label or 'attached' in label:
            continue
        capture, path = capture_receipt(label, row)
        with Image.open(path) as image:
            w, h = image.size
            bounds = (w//2-180, h//2-150, w//2+180, h//2+95)
            pixels = np.array(image.convert('RGB').crop(bounds), dtype=np.int16)
        count = int(isolated_cover_pixels(pixels).sum())
        rows.append({'label': label, 'crop': bounds, 'isolated_cover_pixels': count,
                     'cover_pixels': int(cover_pixels(pixels).sum()),
                     'artwork_dark_fraction': artwork_distribution(pixels),
                     'below_noise_limit': count <= MAX_ISOLATED_PIXELS,
                     'frame_qpc_100ns': capture['frame']['frame_qpc_100ns']})
    prefixes = tuple(route+'_' for route in OWNER_ROUTES) if owners is not None else ('candidate_',)
    candidate = [row for row in rows if row['label'].startswith(prefixes)]
    elapsed = ((max(row['frame_qpc_100ns'] for row in candidate)-
                min(row['frame_qpc_100ns'] for row in candidate))/1e7) if candidate else 0.
    scale = bool(candidate) and max(row['cover_pixels'] for row in candidate) >= 2000
    valid = (report.get('completed') and report.get('restored') and report.get('source_unchanged')
             and not report.get('cleanup_errors') and len(candidate) >= 16 and elapsed >= 16.)
    native_artwork = [row['artwork_dark_fraction'] for row in rows
                      if row['label'].startswith('native_') and row['artwork_dark_fraction'] is not None]
    candidate_artwork = [row['artwork_dark_fraction'] for row in candidate
                         if row['artwork_dark_fraction'] is not None]
    artwork_valid = len(native_artwork) >= 2 and len(candidate_artwork) >= 6
    artwork_limits = ([max(0., min(native_artwork)-MAX_DARK_FRACTION_DEVIATION),
                       min(1., max(native_artwork)+MAX_DARK_FRACTION_DEVIATION)]
                      if artwork_valid else None)
    artwork_passed = bool(artwork_valid and all(artwork_limits[0] <= value <= artwork_limits[1]
                                               for value in candidate_artwork))
    surface_passed = bool(valid and scale and all(row['below_noise_limit'] for row in candidate))
    result = {'schema': 2, 'source': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Cover fragments and native outside/inside artwork distribution; pose, silhouette, occlusion and brightness need separate checks.',
              'requires_unobscured_fixture_review': True, 'product_qualified': False,
              'owner_path': report.get('owner_path'), 'owner_matrix': owners,
              'owner_matrix_passed': owners['passed'] if owners is not None else None,
              'timeline_valid': bool(valid), 'scale_valid': scale, 'candidate_duration_seconds': elapsed,
              'candidate_count': len(candidate),
              'maximum_isolated_pixels': MAX_ISOLATED_PIXELS, 'rows': rows,
              'artwork_reference_valid': artwork_valid, 'artwork_dark_fraction_limits': artwork_limits,
              'artwork_distribution_passed': artwork_passed,
              'surface_regression_passed': surface_passed,
              'raster_regression_passed': surface_passed and artwork_passed}
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({key: result[key] for key in ('owner_matrix_passed', 'timeline_valid', 'surface_regression_passed',
                                                  'artwork_distribution_passed', 'raster_regression_passed')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.source, args.output)
