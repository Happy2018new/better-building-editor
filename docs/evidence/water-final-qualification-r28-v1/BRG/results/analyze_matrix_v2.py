"""Read final-cohort reports without admission, fallback, pixel fitting or edits."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

WORK = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def activate_reviewed_hosts(project):
    import importlib
    private_scripts = project / '.agents/skills/pyreact-debugging/scripts'
    sys.path.insert(0, str(private_scripts))
    sessions = []
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    for name in ('_session', '_window'):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        assert path.parent == private_scripts.resolve()
        relative = path.relative_to(project.resolve()).as_posix()
        assert sha(path) == binding['source_sha256'][relative]
        sessions.append({'module': name, 'path': str(path), 'sha256': sha(path)})
    root = WORK.parents[2]
    contract_path = root / '.runtime/round-20261021/water-startup-protocol-v2/host-contract-v1.json'
    expected = json.loads((WORK / 'prelaunch-host-binding-v1.json').read_bytes())
    assert sha(contract_path) == expected['startup_contract_sha256']
    contract = json.loads(contract_path.read_bytes())
    assert all(sha(Path(name)) == value for name, value in contract['sources'].items())
    assert sha(Path(contract['binary']['path'])) == contract['binary']['sha256']
    candidate = Path(next(name for name in contract['sources']
                         if name.replace('\\', '/').endswith('/capture_native_burst.py'))).parent
    sys.path.insert(0, str(candidate))
    validators = []
    for name in ('capture_native_burst', 'capture_native_burst_deferred', 'capture_native_burst_startup'):
        module = importlib.import_module(name)
        path = Path(module.__file__).resolve()
        assert path.parent == candidate.resolve()
        validators.append({'module': name, 'path': str(path), 'sha256': sha(path)})
    sys.path.remove(str(candidate))
    import calibration_host
    assert sha(Path(calibration_host.__file__)) == expected['host_sha256']['calibration_host.py']
    activation = calibration_host.activate()
    reference = calibration_host.validate_report(WORK / 'product-v2-camera-seam-v1.json', activation)
    controls = root / '.runtime/round-20261022/water-camera-extractor-seam-candidate-v1/controls-v1/report.json'
    assert sha(controls) == '418aa0076a15767dc4fd05fa40b5d8e6dd1cfbac706a144a71370dd6d701dc7d'
    record = json.loads(controls.read_bytes())
    assert record['passed'] and record['original_inputs_unchanged']
    assert record['actual_raw_positive_cases'] == 3 and record['synthetic_negative_cases'] == 9
    assert all(row['candidate_passed'] is row['expected_passed'] for row in record['rows'])
    assert all(sha(Path(name)) == value for name, value in record['original_inputs_sha256'].items())
    return {'versioned_calibration_host': activation, 'new_calibration_source': reference,
            'candidate_controls_path': str(controls), 'candidate_controls_sha256': sha(controls),
            'private_session_modules': sessions, 'startup_validator_modules': validators,
            'startup_host_contract_sha256': sha(contract_path), 'source_bytes_modified': False,
            'algorithm_or_threshold_changes': False, 'new_RGB_or_speed_fit': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--available-only', action='store_true')
    parser.add_argument('--stage', action='append', choices=('F-editor', 'F-full', 'F-missing', 'A', 'B', 'R', 'G'))
    args = parser.parse_args()
    assert not args.output.exists()
    args.output.mkdir()
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    project = Path(binding['project'])
    sys.path.insert(0, str(project / 'tools'))
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    reviewed_hosts = activate_reviewed_hosts(project)
    import analyze_product_water as product
    import analyze_product_water_flow as flow
    import analyze_product_water_biome as biome
    import analyze_water_acceptance_r16 as acceptance
    import qualify_water_product_r16 as qualifier
    for module in (product, flow, biome, acceptance, qualifier):
        assert Path(module.__file__).resolve().parent == (project / 'tools').resolve()
    reports = {
        'F-editor': WORK / 'product-v2-f-editor-v1.json',
        'F-full': WORK / 'product-v2-f-full-v2.json',
        'F-missing': WORK / 'product-v2-f-missing-v2.json',
        'A': WORK / 'product-v2-a-v1.json',
        'B': WORK / 'product-v2-b-v1.json',
        'R': WORK / 'product-v2-r-v1.json',
        'G': WORK / 'product-v2-g-v1.json',
    }
    result = {'schema': 1, 'source_contract_sha256': binding['source_contract_sha256'],
              'root_head': binding['root_head'], 'reports': {}, 'errors': [],
              'native_editor_gui_requested': True, 'native_world_geometry_requested': True,
              'qualification_or_owner_changed': False, 'manual_closures_added': 0, 'MC_started': False}
    result['reviewed_host_activation'] = reviewed_hosts
    result['analysis_host_sha256'] = sha(Path(__file__))
    rows, measured = {}, {}

    def write(name, value):
        with (args.output / name).open('x', encoding='ascii') as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write('\n')

    contract = json.loads((project / 'tools/data/liquid_product_resource_contract_v1.json').read_bytes())
    for name, path in reports.items():
        if args.stage and name not in args.stage:
            continue
        if not path.exists() and args.available_only:
            continue
        try:
            raw = json.loads(path.read_bytes())
            if args.available_only and not raw.get('completed'):
                continue
            assert raw['source_contract_sha256'] == binding['source_contract_sha256'], name
            row, analysis = qualifier.collect(path, project, contract,
                                               native_world_geometry=True, native_editor_gui=True)
            rows[name], measured[name] = row, analysis
            write(name + '-product-analysis.json', analysis)
            result['reports'][name] = {'path': str(path), 'sha256': sha(path),
                'evidence_valid': analysis['evidence_valid'],
                'observed_product_gates': analysis['observed_product_gates'],
                'failed_geometry': [key for key, value in analysis['geometry'].items() if not value['passed']],
                'failed_alpha': [key for key, value in analysis['alpha_controls'].items() if not value['passed']],
                'failed_transparency': [key for key, value in analysis['transparency'].items() if not value['passed']]}
            if name.startswith('F-'):
                replay = acceptance.replay(path, native_editor_gui=True)
                write(name + '-side-visibility-analysis.json', replay)
                result['reports'][name]['side_visibility_acceptance'] = replay['passed']
            elif name == 'A':
                value = flow.analyze_flow(path, native_editor_gui=True)
                write('A-flow-analysis.json', value)
                result['reports'][name]['flow_passed'] = value['passed']
            elif name == 'B':
                value = biome.biome_analysis(path, native_editor_gui=True)
                write('B-biome-analysis.json', value)
                result['reports'][name]['biome_passed'] = value['passed']
                qualifier.occupancy(row)
                result['reports'][name]['occupancy_passed'] = True
        except Exception as error:
            result['errors'].append({'stage': name, 'type': type(error).__name__,
                                     'message': str(error), 'traceback': traceback.format_exc()})
    if all(name in rows for name in ('F-editor', 'F-full', 'F-missing')):
        try:
            names = ('F-editor', 'F-full', 'F-missing')
            coverage = qualifier.frozen_coverage([rows[name] for name in names])
            value = qualifier.frozen_matrix([reports[name] for name in names], [rows[name] for name in names], True)
            write('F-combined-frozen-matrix.json', value)
            result['combined_F'] = {'passed': value['passed'], 'coverage_cells': len(coverage)}
        except Exception as error:
            result['errors'].append({'stage': 'combined_F', 'type': type(error).__name__,
                                     'message': str(error), 'traceback': traceback.format_exc()})
    result['complete_capture_set_available'] = len(rows) == 7
    write('summary.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
