"""Bind isolated visible-corner candidates to exact frozen native controls.

This report is diagnostic. It cannot accept a native height rule, hidden corner,
or production rendering, and does not change any source report or image.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops

from capture_frozen_liquid_controls import native_gate
from capture_pure_liquid_native_controls import CONTROLS, fixed_viewport, validate_png
from find_liquid_surface_corners import find_candidates
from projection.cell import AIR, actor_data, background, decode, foreground
from projection.debug_liquid_blueprints import NAMES

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    path = Path(path)
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def checked_fingerprint(record, source_archives=()):
    original = Path(record['path'])
    if original.is_file():
        actual = fingerprint(original)
        if actual['sha256'] == record['sha256']:
            return actual
    # An archived source is eligible only when its original bytes still match.
    # Keep the reported path as provenance; never amend the historical report.
    for archive in source_archives:
        actual = fingerprint(archive)
        if actual['sha256'] == record['sha256']:
            actual['reported_path'] = record['path']
            return actual
    raise ValueError('Liquid evidence fingerprint changed: ' + record['path'])


def isolated_source(plan):
    """Only one exact liquid cell with optional separate support is eligible."""
    if (plan.get('context_changed') is not False or plan.get('shell') or
            plan.get('shell_value') != list(AIR) or plan.get('layer') not in (0, 1)):
        raise ValueError('An exact isolated no-shell logical source is required')
    controls = plan['controls']
    if set(controls) != set(CONTROLS) or controls['empty']['cells']:
        raise ValueError('Four explicit controls including an empty negative are required')
    only = controls['liquid_only']['cells']
    if len(only) != 1 or only[0][0] != plan['cell_origin']:
        raise ValueError('Corner extraction supports only one declared isolated liquid cell')
    value = decode(only[0][1])
    front, back = foreground(value), background(value)
    liquid, other = (front, back) if plan['layer'] == 0 else (back, front)
    if liquid[0] not in NAMES or other != AIR or actor_data(value) is not None:
        raise ValueError('A liquid-only source cannot contain another layer or actor')
    support = controls['supported_negative']['cells']
    if not support or any(row[0] == plan['cell_origin'] for row in support):
        raise ValueError('Support controls must be separate from the liquid cell')
    positive = controls['supported_positive']['cells']
    if sorted(positive) != sorted(support + only):
        raise ValueError('Supported positive must contain only the declared liquid and support')
    return liquid


def difference_mask(positive, negative, threshold):
    with Image.open(positive) as image:
        first = image.convert('RGB')
    with Image.open(negative) as image:
        second = image.convert('RGB')
    if first.size != second.size:
        raise ValueError('Independent liquid controls have different viewport dimensions')
    red, green, blue = ImageChops.difference(first, second).split()
    maximum = ImageChops.lighter(ImageChops.lighter(red, green), blue)
    return maximum.point(lambda value: 255 if value > threshold else 0)


def analyze(report_path, selected=None, pixel_budget=3., threshold=16, minimum_pixels=100,
            source_archives=()):
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding='utf8'))
    if (report.get('schema') != 2 or not report.get('completed') or not report.get('restored') or
            report.get('cleanup_errors') or report.get('context_changed') is not False or
            not report.get('flow_freeze', {}).get('forbidden') or
            not report.get('flow_restore', {}).get('native_return_verified')):
        raise ValueError('A completed and restored schema-2 frozen native report is required')
    if not isinstance(threshold, int) or isinstance(threshold, bool) or not 0 <= threshold < 255:
        raise ValueError('Liquid pixel threshold must be an unsigned byte below 255')
    session_path = Path(report['session_file'])
    session = json.loads(session_path.read_text(encoding='utf8'))
    session['session_file'] = str(session_path.resolve())
    if session['owner'] != report['owner']:
        raise ValueError('Liquid report owner differs from the bound session')
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    if (report['registry_version'] != manifest['game_version'] or
            report['registry_fingerprint'].lower() != manifest['source_sha256'].lower()):
        raise ValueError('Liquid report differs from the current versioned block dump')
    calibration_source = checked_fingerprint(report['calibration'])
    calibration = json.loads(Path(calibration_source['path']).read_text(encoding='utf8'))
    if (not calibration.get('completed') or not calibration.get('passed') or not calibration.get('restored') or
            calibration.get('cleanup_errors') or Path(calibration['session_file']).resolve() != session_path.resolve()):
        raise ValueError('Passed and restored same-session camera calibration is required')
    sources = {'runner': checked_fingerprint(report['runner_source'], source_archives)}
    for name in ('diagnostic_fixture_source', 'public_fixture_source', 'reviewed_harness_source'):
        if name in report:
            sources[name] = checked_fingerprint(report[name], source_archives)
    pose, rows, seen = report['camera'], [], set()
    cases = report['cases']
    selected = set(selected) if selected else {case['case'] for case in cases}
    for case in cases:
        identity = case['case']
        if identity in seen:
            raise ValueError('Liquid source report repeats a case')
        seen.add(identity)
        if identity not in selected:
            continue
        if not case.get('completed'):
            raise ValueError('Selected liquid source did not complete')
        plan = case['source']
        liquid = isolated_source(plan)
        size, pngs = None, {}
        for control in CONTROLS:
            item = case['controls'][control]
            gate = native_gate(item['native_before_capture'], item['native_after_capture'],
                               plan, plan['controls'][control]['cells'])
            if not item.get('completed') or not gate['public_snapshot_unchanged']:
                raise ValueError('Liquid native state/neighborhood changed: ' + identity + '/' + control)
            fixed_viewport(item['capture'], pose)
            if any(item['capture'][name] != pose['stable'] for name in ('camera_before', 'camera_after')):
                raise ValueError('Liquid camera changed during control capture')
            size = validate_png(item['capture'], session, size)['size']
            pngs[control] = checked_fingerprint(item['capture'])
        camera = {'position': pose['stable']['position'], 'target': pose['target'],
                  'screen': pose['stable']['screen'], 'native_image_screen': size,
                  'vertical_fov': calibration['vertical_fov']}
        candidate_rows = {}
        for positive, negative in (('liquid_only', 'empty'), ('supported_positive', 'supported_negative')):
            mask = difference_mask(pngs[positive]['path'], pngs[negative]['path'], threshold)
            candidate_rows[positive] = find_candidates(mask, camera, plan['cell_origin'],
                                                        pixel_budget, minimum_pixels)
        rows.append({'case': identity, 'logical_layer': plan['layer'], 'liquid': liquid,
                     'source': plan, 'pngs': pngs, 'candidates': candidate_rows,
                     'original_pixel_controls_passed': case.get('native_controls_passed') is True,
                     'native_state_and_capture_gates_rechecked': True})
    if not selected.issubset(seen):
        raise ValueError('Selected liquid case is absent from the source report')
    return {'schema_version': 1, 'raw_report': fingerprint(report_path),
            'analyzer': fingerprint(Path(__file__)), 'candidate_tool': fingerprint(
                ROOT / 'tools/find_liquid_surface_corners.py'),
            'registry_version': manifest['game_version'], 'registry_fingerprint': manifest['source_sha256'],
            'calibration': calibration_source, 'sources': sources,
            'session': {key: session[key] for key in ('id', 'owner', 'game_pid', 'game_identity')},
            'threshold': threshold, 'minimum_pixels': minimum_pixels, 'declared_pixel_budget': pixel_budget,
            'rows': rows, 'native_geometry_accepted': False, 'accuracy_accepted': False,
            'public_controls_eligible': False,
            'scope': 'Visible corner candidates from exact isolated cells; original failed pixel gates remain failed. '
                     'No height rule, hidden-corner fill, calibration refit or production acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--case', action='append')
    parser.add_argument('--pixel-budget', type=float, default=3.)
    parser.add_argument('--threshold', type=int, default=16)
    parser.add_argument('--minimum-pixels', type=int, default=100)
    parser.add_argument('--source-archive', type=Path, action='append', default=[])
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh path and preserve existing evidence')
    result = analyze(args.report, args.case, args.pixel_budget, args.threshold, args.minimum_pixels,
                     args.source_archive)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'cases': len(result['rows']), 'visible_candidates': sum(
        corner['status'] == 'candidate' for row in result['rows'] for candidate in row['candidates'].values()
        for corner in candidate['corners']), 'native_geometry_accepted': False, 'output': str(args.output.resolve())}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
