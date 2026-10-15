"""Preserve finite poppy evidence and isolated resources without runtime promotion."""
import argparse
import hashlib
import json
from pathlib import Path

from generate_static_plant_proxies import CANDIDATES, ROOT
from verify_fungus_remaining_matrix import captures


INSTANCES = Path('C:/Users/Happy2018new/.pyreact-debug/instances')
VIEWS = {'public': [-2., .15, -2.5], 'right': [2., .15, -2.5]}
TARGET = [-47, 117, -70]
LIMITS = {'native_recall': .75, 'native_precision': .75,
          'native_edge_tolerance_pixels': 3}
ASSETS = {
    'behavior_pack/netease_blocks/preview_poppy.json':
        '3bde8f63760f8d5762fa0fed28f7a516410c1102ebe58c23aa70f5e736ba9ca9',
    'resource_pack/models/netease_block/preview_poppy.json':
        'bc932ecfcb8a3c0a0ed7fd07289467a6e23647974334e108154221deb50e07a2'}
RESOURCE_DIR = 'tools/data/plant_cross_candidate_r10b'
PARTITIONS = (
    ('h0', '61335279333c47118ba694f0439e576e', 'snow-cross-roots-poppy-screen-v1',
     '4d3f3751c1f25aff2f094ceeeadef364e34bca9faa6d1d520c122d12238c9fc7',
     '95a3e3cd12afc1a0a59a08958ef9f5d8bd0919d4faf6f9796f2eb11f952e8b45', [0], False),
    ('h1_h7', 'cb3974b48ff74f2ebb7f393a18eefc12', 'snow-poppy-seven-heights-r10d-v1',
     'fa16f51fad2ec5a21eeb028d7ebd563127b9a50ebff866fcfb705be6aac83caf',
     '612bd220f019b3b859321e8e382d0789601b2b015e297f50faead6abe42c98e9',
     list(range(1, 8)), True))
OTHER_SCREEN = ('9512c9895d48444580e48589f0f21812', 'snow-cross-other-four-screen-v2',
                '0d27322d965a632e7ca2de1607fb1132140909dd9a0c7d7880be72552d50222b',
                '8cfda86d5cdbe49fe75176b07f3675b62a61fecdf42da469404b13d3426c85b9')


def record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def checked(reference):
    actual = record(reference['path'])
    if actual['sha256'] != reference['sha256']:
        raise ValueError('Original evidence changed: '+reference['path'])
    return json.loads(Path(reference['path']).read_bytes())


def summary(row, view):
    return {'view': view, 'kind': row['kind'], 'height': row['height'],
            'world': row['comparisons'],
            'editor_controls': row.get('editor_controls'),
            'native_roi_boundary': row.get('native_roi_boundary'),
            'world_roi': {key: row['world_roi'][key] for key in
                          ('method', 'polygon', 'camera', 'screen', 'world_base', 'bounds')}}


def validate_report(report, view, heights):
    if (report['plants'] != ['poppy'] or report['view'] != view or
            report['heights'] != heights or report['limits'] != LIMITS or
            report['world_camera_offset'] != VIEWS[view] or
            report['native_target'] != TARGET or report['modes'] != ['full', 'missing']):
        raise ValueError('Poppy report measured scope or original gates changed')
    if not all(report[key] for key in ('completed', 'restored', 'passed',
                                      'source_assets_stable', 'native_resolution', 'near_player')):
        raise ValueError('Poppy report incomplete, failed or untrusted')
    if (report['cleanup_errors'] or report['binding_read_failures'] or
            not all(row['clean'] for row in report['native_cleanup'])):
        raise ValueError('Poppy fixture cleanup is incomplete')
    expected = {('plant', 0)} | {(kind, height) for height in heights
                               for kind in ('snow', 'covered')}
    rows = [row for row in report['rows'] if row['kind'] != 'blank']
    if len(rows) != len(expected) or {(row['kind'], row['height']) for row in rows} != expected:
        raise ValueError('Poppy dry, snow-only or covered controls are missing')
    for row in rows:
        roi = row['world_roi']
        if (roi['world_base'] != TARGET or
                roi['method'] != 'native-cube calibrated perspective projection'):
            raise ValueError('Fixed calibrated unit-cell ROI changed')
        for mode in ('full', 'missing'):
            comparison = row['comparisons'][mode]
            if not comparison['passed'] or not all(mask['passed'] for mask in comparison['masks'].values()):
                raise ValueError('An independent poppy mask failed')
            if row['kind'] == 'covered' and 'exposed_plant' not in comparison['masks']:
                raise ValueError('Independent exposed-plant mask is missing')
        if row['kind'] == 'plant' and not row['native_roi_boundary']['passed']:
            raise ValueError('Dry native plant touches the fixed ROI boundary')
        if row['kind'] == 'covered' and not row['editor_controls']['passed']:
            raise ValueError('Independent editor control failed')
    for capture in captures(report):
        metadata = capture['capture']
        if metadata.get('backend') != 'Windows.Graphics.Capture' or not metadata.get('reliable'):
            raise ValueError('Only reliable original WGC captures are evidence')
    return rows


def matrix_evidence(instance, stem, matrix_hash, audit_hash, expected_passed):
    directory = INSTANCES/instance/'artifacts'
    matrix_ref = {'path': str(directory/(stem+'.json')), 'sha256': matrix_hash}
    audit_ref = {'path': str(directory/(stem+'-audit.json')), 'sha256': audit_hash}
    matrix, audit = checked(matrix_ref), checked(audit_ref)
    if (not all(matrix[key] for key in ('completed', 'restored', 'source_assets_stable')) or
            matrix['passed'] is not expected_passed or matrix['source_errors'] or
            matrix['limits'] != LIMITS or matrix['profile_case']['native_target'] != TARGET or
            matrix['profile_case']['views'] != VIEWS):
        raise ValueError('Original matrix state, source or fixed gates changed')
    if (not audit['integrity_passed'] or audit['errors'] or
            audit['matrix']['sha256'] != matrix_hash or
            audit['matrix_passed'] is not expected_passed):
        raise ValueError('Independent audit does not match the original matrix')
    frozen = checked(matrix['frozen_source'])
    calibration = checked(matrix['calibration'])
    if (not all(calibration[key] for key in ('completed', 'restored', 'passed')) or
            calibration['cleanup_errors'] or calibration['runtime_minecraft_version'] != '1.21.120.0'):
        raise ValueError('Same-session camera calibration failed or changed version')
    session = json.loads(Path(matrix['session_file']).read_bytes())
    if session['state'] != 'stopped' or session['owner'] != matrix['owner']:
        raise ValueError('Owned native session is not stopped')
    for sheet in audit['inspection_sheets']:
        if record(sheet['path'])['sha256'] != sheet['sha256']:
            raise ValueError('Original inspection sheet changed')
    reports, failures = [], []
    for row in matrix['rows']:
        report = checked(row)
        reports.append(dict(record(row['path']), plant=row['plant'], view=row['view'],
                            completed=report['completed'], restored=report['restored'],
                            passed=report['passed']))
        failures.extend(dict(summary(item, row['view']), plant=row['plant'])
                        for item in report['rows'] if item['kind'] != 'blank' and
                        (not all(value['passed'] for value in item['comparisons'].values()) or
                         item.get('editor_controls') and not item['editor_controls']['passed']))
    result = {'matrix': record(matrix_ref['path']), 'audit': record(audit_ref['path']),
              'original_matrix_passed': matrix['passed'], 'completed': matrix['completed'],
              'restored': matrix['restored'], 'source_assets_stable': matrix['source_assets_stable'],
              'calibration': matrix['calibration'], 'frozen_source': matrix['frozen_source'],
              'owner': matrix['owner'], 'game_pid': matrix['game_pid'],
              'session_file': matrix['session_file'], 'instance_state_observed': 'stopped',
              'game_and_mcdk_alive_at_stop_check': False, 'force_stop_used': False,
              'reports': reports, 'failed_rows': failures,
              'unique_native_pngs_audited': audit['unique_native_pngs_audited'],
              'frozen_source_files_audited': audit['frozen_source_files_audited'],
              'inspection_sheets_actually_opened': audit['inspection_sheets'],
              'foreground_changes_are_diagnostics': True,
              'ordinary_other_application_switch_observations': audit['foreground_change_observations'],
              'capture_contract': audit['capture_contract']}
    return result, matrix, frozen


def build():
    partitions, measurements = {}, []
    for label, instance, stem, matrix_hash, audit_hash, heights, passed in PARTITIONS:
        evidence, matrix, frozen = matrix_evidence(instance, stem, matrix_hash, audit_hash, passed)
        if matrix['profile_case']['heights']['poppy'] != heights:
            raise ValueError('Disjoint poppy height partition changed')
        if any(frozen['hashes_sha256'][name] != expected for name, expected in ASSETS.items()):
            raise ValueError('Candidate poppy resources differ between height partitions')
        views, replays = set(VIEWS), []
        for case in matrix['rows']:
            if case['plant'] != 'poppy':
                continue
            view = case['view']
            if view not in views:
                raise ValueError('Duplicate or unexpected poppy view')
            views.remove(view)
            report = checked(case)
            rows = validate_report(report, view, heights)
            if report['proxy_assets']['poppy']['model_sha256'] != ASSETS['resource_pack/models/netease_block/preview_poppy.json']:
                raise ValueError('Report used a different candidate model')
            replay_path = Path(case['path']).with_name(Path(case['path']).stem+'-replay.json')
            replay = json.loads(replay_path.read_bytes())
            if replay['replayed_from']['sha256'] != case['sha256'] or not replay['passed']:
                raise ValueError('Independent original PNG replay failed')
            replays.append(dict(record(replay_path), passed=True))
            measurements.extend(summary(row, view) for row in rows)
        if views:
            raise ValueError('A measured poppy view is missing')
        evidence.update(snow_heights=heights, poppy_reports_passed=True,
                        offline_png_replays=replays)
        partitions[label] = evidence
    other, _, _ = matrix_evidence(*OTHER_SCREEN, expected_passed=False)
    archive = ROOT/'.runtime/cross-candidate-v3-source'
    files = {}
    asset_records = {}
    for relative, expected in ASSETS.items():
        raw = (archive/relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('Archived candidate changed: '+relative)
        kind = 'behavior' if relative.startswith('behavior_pack') else 'model'
        output = RESOURCE_DIR+'/preview_poppy.'+kind+'.json'
        files[output] = raw
        asset_records[relative] = {'isolated_resource': output, 'sha256': expected}
    blocks = json.loads((archive/'resource_pack/blocks.json').read_bytes())
    atlas = json.loads((archive/'resource_pack/textures/terrain_texture.json').read_bytes())
    registration = {'identifier': 'modern_projection:preview_poppy',
                    'appearance': blocks['modern_projection:preview_poppy'],
                    'texture_key': 'modern_projection_static_poppy',
                    'texture_entry': atlas['texture_data']['modern_projection_static_poppy'],
                    'production_default_enabled': False,
                    'runtime_position_scope_enforced': False}
    files[RESOURCE_DIR+'/registration.json'] = encoded(registration)
    snapshot = json.loads((archive/'snapshot.json').read_bytes())
    checked({'path': snapshot['clip_source_report'], 'sha256': snapshot['clip_source_report_sha256']})
    source = archive/'tools/data/static_plant_sources_nemc_3.9.0.401155.json'
    if record(source)['sha256'] != snapshot['source_manifest_sha256']:
        raise ValueError('Archived native source manifest changed')
    for relative, previous in snapshot['before'].items():
        current = ROOT/relative
        if previous is None:
            restored = not current.exists()
        else:
            restored = current.is_file() and current.read_bytes() == bytes.fromhex(previous)
        if not restored:
            raise ValueError('Candidate resource was not restored exactly: '+relative)
    inspected = []
    for height in (4, 5):
        for kind in ('native_native', 'full_world_closeup_native'):
            path = INSTANCES/PARTITIONS[1][1]/'artifacts'/(
                PARTITIONS[1][2]+'_poppy_right_poppy_covered_h%d_%s.png' % (height, kind))
            inspected.append(record(path))
    result = {
        'schema_version': 1, 'status': 'Limited measured candidate evidence',
        'production_acceptance': False, 'production_default_enabled': False,
        'runtime_position_scope_enforced': False,
        'production_blocking_reason': 'The runtime (name, aux) table cannot enforce the measured world-position scope; native mesh and random-offset contracts remain unrecovered',
        'measured_scope': {'plants': ['poppy'], 'native_target': TARGET, 'views': VIEWS,
                           'snow_heights': list(range(8)), 'dry_native_controls': True,
                           'world_modes': ['full', 'missing'], 'independent_editor_controls': True,
                           'all_eight_snow_heights_measured_passed': True,
                           'all_eight_snow_heights_accepted_for_production': False,
                           'other_positions_or_runtime_versions_accepted': False,
                           'native_mesh_authority': False, 'random_offset_contract_recovered': False},
        'environment': {'nemc_version': 'NEMC 3.9.0.401155',
                        'runtime_minecraft_version': '1.21.120.0'},
        'original_gates': LIMITS,
        'roi_contract': 'Fixed calibrated unit-cell convex hull; dry native boundary contact fails; no ROI expansion',
        'exposed_plant_contract': 'Independent native snow-only control with unchanged 3-pixel edge tolerance; exposed plant must separately pass or be absent in both images',
        'geometry_hypothesis': {'unit_cross_height': 1., 'xz_translation': snapshot['xz_clip_hypothesis'],
                                'native_mesh_or_offset_contract_recovered': False,
                                'clip_report': {'path': snapshot['clip_source_report'],
                                                'sha256': snapshot['clip_source_report_sha256']}},
        'candidate_assets': asset_records, 'isolated_registration': registration,
        'source_manifest_sha256': snapshot['source_manifest_sha256'],
        'source_archive': str(archive.resolve()), 'candidate_resources_restored_exactly': True,
        'burial_transition_original_pngs_actually_opened': inspected,
        'production_default_families': sorted(CANDIDATES),
        'evidence_partitions': partitions, 'rows': measurements,
        'preserved_failed_screen': other,
        'historical_rejected_roots': record(ROOT/'tools/data/snow-static-roots-rejected-screening-r8.json'),
        'union_rule': 'Disjoint h0 and h1-h7 poppy partitions only; original mixed-family matrices keep their failure verdicts'}
    return result, files


def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2)+'\n').encode('utf8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result, files = build()
    files[args.output] = encoded(result)
    for relative, raw in files.items():
        path = ROOT/relative
        if args.check:
            if not path.is_file() or path.read_bytes() != raw:
                parser.error('Generated candidate evidence differs: '+str(path))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
    print(json.dumps(record(ROOT/args.output)))


if __name__ == '__main__':
    main()
