"""Package rejected native static epochs without promoting a best failed fit."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from liquid_coordinate_markers import fingerprint, write
from liquid_static_coordinate_epochs import check


def read(path):
    return json.loads(Path(path).read_bytes())


def checked_ref(ref):
    if fingerprint(ref['path'])['sha256'] != ref['sha256']:
        raise ValueError('Evidence reference changed: ' + ref['path'])
    return ref


def package(plan_path, nominal_path, audit_path, grid_path, ramp_path, candidate, output):
    if output.exists():
        raise ValueError('Choose a fresh evidence package output')
    plan, nominal, audit, grid = map(read, (plan_path, nominal_path, audit_path, grid_path))
    check(plan)
    if (not audit['prerequisites']['passed'] or audit['prerequisites']['failures']
            or not audit['camera_robustness']['nominal_numerical_equivalence']['passed']):
        raise ValueError('Native prerequisite or independent nominal replay failed')
    plan_ref = fingerprint(plan_path)
    if nominal['plan'] != plan_ref or audit['plan'] != plan_ref or grid['original_plan'] != plan_ref:
        raise ValueError('Reports do not reference one exact immutable experiment')
    if grid['v1_audit'] != fingerprint(audit_path) or not grid['no_uv_labels_or_rgb_used']:
        raise ValueError('Interior derivation is not independent of water texture labels')
    epochs = []
    for ref in nominal['inputs']:
        native = read(checked_ref(ref)['path'])
        epoch = native['static_epoch']
        folder = plan_path.parent / epoch
        receipt = read(folder / 'session-receipt.json')
        session = read(receipt['session_file'])
        restore = read(folder / 'restored.json')
        if (session['state'] != 'stopped' or session['ready']
                or not restore['original_absence_restored']
                or not restore['full_resource_manifest_equals_baseline']):
            raise ValueError('Native session or original resource absence is not restored')
        captures = [control['capture'] for row in native['cases'] for control in row['controls'].values()]
        for capture in captures:
            checked_ref(capture)
        epochs.append({'epoch': epoch, 'native_report': ref, 'calibration': checked_ref(native['calibration']),
            'session': {key: receipt[key] for key in ('id', 'owner', 'game_pid', 'game_identity',
                                                     'mcdk_pid', 'mcdk_identity')},
            'stopped_session': fingerprint(receipt['session_file']),
            'lifecycle': {name: fingerprint(folder / name) for name in
                ('session-receipt.json', 'installed.json', 'restored.json', 'stop-stdout.txt',
                 'stop-stderr.txt', 'stop-attempt1-stdout.txt', 'stop-attempt1-stderr.txt')},
            'native_pngs': [checked_ref(capture) for capture in captures],
            'completed': native['completed'], 'restored': native['restored'],
            'cleanup_errors': native['cleanup_errors']})
    contract, gles = read(candidate / 'contract.json'), read(candidate / 'gles-v1.json')
    if not gles['passed'] or gles['contract_sha256'] != fingerprint(candidate / 'contract.json')['sha256']:
        raise ValueError('Corrected resource host shader checks did not pass')
    result = {'schema': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Four cold native static-side epochs; rejected source/filter fit and bounded standalone source-region correction',
        'frozen_plan': plan_ref, 'nominal': fingerprint(nominal_path), 'independent_audit': fingerprint(audit_path),
        'interior_geometry_derivation': fingerprint(grid_path), 'ramp_diagnostic': fingerprint(ramp_path),
        'epochs': epochs, 'native_water_png_count': sum(len(row['native_pngs']) for row in epochs),
        'prerequisites_passed': True, 'native_side_uv_observed': nominal['native_side_uv_observed'],
        'selected_spatial_candidate': {key: nominal['selected'][key] for key in
                                      ('region', 'side_v', 'orientation', 'pixel_mapping')},
        'sampler_candidate': nominal['sampler'], 'nominal_training_rgb_rmse': nominal['training_rgb_rmse'],
        'sequences': nominal['sequences'], 'stability': nominal['stability'],
        'identification': nominal['identification'], 'limits': nominal['limits'],
        'camera_robustness': {key: audit['camera_robustness'][key] for key in
            ('admitted_fovs', 'distinct_prediction_pairs', 'worst_training_rgb_rmse',
             'worst_property_margins', 'all_combinations_passed', 'nominal_numerical_equivalence')},
        'resource_candidate': {'contract': fingerprint(candidate / 'contract.json'),
            'host_gles': fingerprint(candidate / 'gles-v1.json'), 'host_gles_checks': gles['checks'],
            'flow_sampling': contract['textures']['flowing_water_grey']['sampling'],
            'scope': 'Installed quad:1 NW restriction replaces full-frame centers in diagnostic model; no accepted native accuracy'},
        'configuration': {'originally_absent': plan['original_configuration_absent'],
            'temporary_config': plan['configuration'], 'restoration_pending_next_owned_experiment': True},
        'native_uv_accepted': False, 'native_animation_accepted': False, 'production_accepted': False,
        'production_profile_enabled': False,
        'preservation': 'Original 512 samples per depth/side remain; one zero-spread footprint and all six RGB failures are retained. Strong wrong-property margins cannot accept a best failed fit.'}
    write(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'nominal', 'audit', 'grid', 'ramp', 'candidate', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = package(*(getattr(args, name).resolve() for name in
                     ('plan', 'nominal', 'audit', 'grid', 'ramp', 'candidate', 'output')))
    print(json.dumps({key: result[key] for key in ('native_water_png_count', 'prerequisites_passed',
        'nominal_training_rgb_rmse', 'native_uv_accepted', 'production_accepted')}))


if __name__ == '__main__':
    main()
