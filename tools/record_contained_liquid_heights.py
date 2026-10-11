"""Bind explicit visible pixels to restored native contained-liquid diagnostics.

This does not detect corners, accept public geometry, or generate a height rule.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from capture_pure_liquid_native_controls import (
    CASES, CONTROLS, capture_native_gate, fixed_viewport, fixture_plan, validate_png)
from measure_native_liquid_surface import analyze_cell

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    return {'path': str(path.resolve()), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def record(report_path, observations_path, session_path):
    report = json.loads(report_path.read_text(encoding='utf8'))
    observations = json.loads(observations_path.read_text(encoding='utf8'))
    if (observations.get('schema_version') != 1 or observations.get('method') != 'manual_visible_outer_boundary'
            or observations.get('pixel_units') != 'original_full_native_png'):
        raise ValueError('Explicit visible observations must use the complete original PNG viewport')
    session = json.loads(session_path.read_text(encoding='utf8'))
    session['session_file'] = str(session_path.resolve())
    manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
    if (not report.get('completed') or not report.get('restored') or report.get('cleanup_errors')
            or not report.get('declared_context_controls_passed') or report.get('context_changed') is not True):
        raise ValueError('A completed, restored, contained diagnostic is required')
    if (Path(report['session_file']).resolve() != session_path.resolve()
            or report['owner'] != session['owner']):
        raise ValueError('Native report session binding differs')
    if (report['registry_version'] != manifest['game_version']
            or report['registry_fingerprint'].lower() != manifest['source_sha256'].lower()):
        raise ValueError('Native report registry differs from the current dump')
    calibration_path = Path(report['calibration']['path'])
    if fingerprint(calibration_path)['sha256'] != report['calibration']['sha256']:
        raise ValueError('Camera calibration fingerprint changed')
    calibration = json.loads(calibration_path.read_text(encoding='utf8'))
    if (not calibration.get('completed') or not calibration.get('passed') or not calibration.get('restored')
            or Path(calibration['session_file']).resolve() != session_path.resolve()):
        raise ValueError('A passed, restored, same-session calibration is required')
    pose, records, size = report['camera'], {}, None
    native_sources = []
    for case in report['cases']:
        if case['case'] not in CASES or case['case'] in records:
            raise ValueError('Only unique isolated source-water/lava cases are supported')
        plan = case['source']
        expected = fixture_plan(case['case'], plan['cell_origin'], plan['platform'],
                                plan['shell_value'][0].removeprefix('minecraft:'))
        if plan != json.loads(json.dumps(expected)):
            raise ValueError('Contained fixture differs from the exact public source')
        if set(case['controls']) != set(CONTROLS) or not case['declared_context_controls_passed']:
            raise ValueError('All four independent controls must have passed')
        for control in CONTROLS:
            row = case['controls'][control]
            gate = capture_native_gate(row['native_before_capture'], row['native_after_capture'],
                                       plan, plan['controls'][control]['cells'])
            if not row['completed'] or not gate['declared_context_state_passed']:
                raise ValueError('Native state or neighborhood changed')
            fixed_viewport(row['capture'], pose)
            for key in ('camera_before', 'camera_after'):
                if row['capture'][key] != pose['stable']:
                    raise ValueError('Native camera moved during capture')
            checked = validate_png(row['capture'], session, size)
            size = checked['size']
            native_sources.append({'case': case['case'], 'control': control,
                                   'png': fingerprint(Path(row['capture']['path']))})
        records[case['case']] = case
    camera = {'position': pose['stable']['position'], 'target': pose['target'],
              'screen': pose['stable']['screen'], 'native_image_screen': size,
              'vertical_fov': calibration['vertical_fov']}
    rows, seen = [], set()
    for supplied in observations['rows']:
        key = (supplied['case'], supplied['control'])
        if key in seen or key[0] not in records or key[1] not in ('supported_positive', 'liquid_only'):
            raise ValueError('Each observation must name a unique positive control')
        seen.add(key)
        case, control = records[key[0]], key[1]
        source = {'case': key[0], 'control': control, 'fixture': report['fixture'],
                  'context_changed': True, 'shell_value': case['source']['shell_value'],
                  'original_keep': case['source']['original_keep'], 'isolated_keep': case['source']['isolated_keep'],
                  'document_origin': case['source']['document_origin'],
                  'png': fingerprint(Path(case['controls'][control]['capture']['path'])),
                  'method': observations['method']}
        points = copy.deepcopy(supplied['observations'])
        for point in points:
            point.update(visibility='visible_boundary', source=source)
        measured = analyze_cell({'camera': camera, 'cell_origin': case['source']['cell_origin'],
                                 'declared_pixel_budget': observations['declared_pixel_budget'],
                                 'observations': points, 'source': source})
        rows.append({'case': key[0], 'control': control, 'input_pixels': supplied['observations'],
                     'diagnostic': measured})
    return {'schema_version': 1, 'game_version': manifest['game_version'],
            'palette_sha256': manifest['source_sha256'].lower(), 'completed': True, 'restored': True,
            'raw_report': fingerprint(report_path), 'observations': fingerprint(observations_path),
            'recorder': fingerprint(Path(__file__)), 'calibration': fingerprint(calibration_path),
            'session': {key: session[key] for key in ('id', 'owner', 'game_identity')},
            'native_source_controls': native_sources, 'rows': rows,
            'native_geometry_accepted': False, 'accuracy_accepted': False, 'public_controls_eligible': False,
            'scope': 'Explicit visible source-water/lava corner intervals in a changed contained context. '
                     'PNG identity, camera stability and native snapshot gates rechecked; '
                     'pixel budget is declared, camera uncertainty is excluded, no height rule or public acceptance.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('observations', type=Path)
    parser.add_argument('session', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Preserve evidence and choose a fresh output path')
    result = record(args.report, args.observations, args.session)
    args.output.write_text(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'controls': len(result['native_source_controls']), 'rows': len(result['rows']),
                      'observed_corners': sum(corner['status'] == 'diagnostic' for row in result['rows']
                                              for corner in row['diagnostic']['corners']),
                      'height_intervals': [[corner.get('height_interval') for corner in row['diagnostic']['corners']]
                                           for row in result['rows']], 'native_geometry_accepted': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
