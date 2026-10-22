"""Review-only by default; explicit root receipt gates official shared admission."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
FINAL = WORK.with_name('water-default-final-v1')
BRG = WORK.with_name('water-final-brg-v3')
PROJECT = ROOT / '.runtime/projects/water-r28-default-v1'
METADATA = ('tools/data/liquid_product_owner_contract_v1.json',
            'behavior_pack/modern_projection/projection/liquid_product_owner_data.py',
            'behavior_pack/modern_projection/projection/liquid_product_qualification_data.py')
PROVISIONAL_HOST_SHA = '38e34bc80fbdc44dd2c291a92b6fac545c5746269647885368d074dd542917b6'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    with path.open('x', encoding='ascii') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def loaded(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--inspect-only', action='store_true')
    mode.add_argument('--execute-final', action='store_true')
    parser.add_argument('--root-review', type=Path)
    parser.add_argument('--inspection', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists()
    os.environ['OPENBLAS_NUM_THREADS'] = '1'
    host_path = WORK / 'qualify_provisional_v2.py'
    assert sha(host_path) == PROVISIONAL_HOST_SHA
    host = loaded('unchanged_provisional_activation_host', host_path)
    sys.path.insert(0, str(ROOT / 'tools'))
    activation = host.activation()
    binding = json.loads((FINAL / 'final-source-binding-v1.json').read_bytes())
    hosts = json.loads((FINAL / 'prelaunch-host-binding-v1.json').read_bytes())
    assert Path(binding['project']).resolve() == PROJECT.resolve()
    assert all(sha(FINAL / name) == value for name, value in hosts['host_sha256'].items())
    assert all(sha(ROOT / name) == value for name, value in hosts['external_host_sha256'].items())
    calibration = loaded('reviewed_final_D_calibration_host', FINAL / 'calibration_host.py')
    camera_activation = calibration.activate()
    camera_reference = calibration.validate_report(FINAL / 'product-v2-camera-seam-v1.json', camera_activation)
    import qualify_water_product_r16 as qualifier
    import generate_liquid_product_owner_contract as generator
    for module, name in ((qualifier, 'qualify_water_product_r16.py'),
                         (generator, 'generate_liquid_product_owner_contract.py')):
        assert module.ROOT.resolve() == ROOT.resolve()
        assert Path(module.__file__).resolve() == ROOT / 'tools' / name
    assert qualifier.generated is generator.generated
    scope_path = WORK / 'root-scope-review-confirmed-v1.json'
    scope = json.loads(scope_path.read_bytes())
    assert scope['status'] == 'confirmed_by_root' and scope['reviewer'] == '/root'
    assert sha(Path(qualifier.__file__)) == scope['required_shared_qualifier_sha256']
    assert sha(Path(generator.__file__)) == scope['required_shared_generator_sha256']
    reports = dict(scope['reports'])
    reports['D'] = {'path': str(FINAL / 'default-r28-d.json'), 'sha256': sha(FINAL / 'default-r28-d.json')}
    assert all(sha(Path(row['path'])) == row['sha256'] for row in reports.values())
    release_path = FINAL / 'precise-release-audit-v1.json'
    release = json.loads(release_path.read_bytes())
    assert release['owner'] == binding['owner']
    assert release['all_six_exact_identities_absent'] is True
    assert release['same_handle_exit_completed'] is True
    exact_exit_path = FINAL / 'launch/exact-exit.json'
    exact_exit = json.loads(exact_exit_path.read_bytes())
    assert exact_exit['completed'] is True
    assert release['same_handle_exit_sha256'] == sha(exact_exit_path)
    analysis_path = WORK / 'default-analysis-v1/summary.json'
    default_analysis = json.loads(analysis_path.read_bytes())
    assert default_analysis['passed_original_default_path_requirements'] is True
    assert default_analysis['evidence_valid'] is True
    assert default_analysis['source_report_sha256'] == reports['D']['sha256']
    assert default_analysis['source_contract_sha256'] == binding['source_contract_sha256']
    expected = dict(binding['source_sha256'], **binding['auxiliary_sha256'])
    assert all(sha(PROJECT / name) == value for name, value in expected.items())
    contract = json.loads((PROJECT / qualifier.RESOURCE).read_bytes())
    qualifier.verify_contract(contract, PROJECT, ROOT)
    for report in reports.values():
        qualifier.source_closure(PROJECT, json.loads(Path(report['path']).read_bytes()), contract)
    generated_owner, generated_module = generator.generated()
    assert (PROJECT / METADATA[0]).read_bytes() == generated_owner
    assert (PROJECT / METADATA[1]).read_bytes() == generated_module
    # Shared generated metadata will deliberately change only after root approval.
    # Imported implementation dependencies must still equal their capture bytes.
    baseline = json.loads((BRG / 'final-source-binding-v1.json').read_bytes())
    shared_expected = dict(baseline['source_sha256'], **baseline['auxiliary_sha256'])
    import water_native_projection
    import verify_camera_projection
    dependencies = {}
    for name, module in sorted(sys.modules.items()):
        filename = getattr(module, '__file__', None)
        if filename is None:
            continue
        path = Path(filename).resolve()
        if not path.is_relative_to(ROOT.resolve()):
            continue
        relative = path.relative_to(ROOT.resolve()).as_posix()
        if relative.startswith('.runtime/'):
            continue
        assert relative in shared_expected, relative
        value = sha(path)
        if relative not in METADATA:
            assert value == shared_expected[relative], (name, relative)
        dependencies[name] = {'relative': relative, 'sha256': value}
    assert len(generator.SOURCES) == 39
    shared_production = {name: sha(ROOT / name) for name in generator.SOURCES}
    assert shared_production == {name: expected[name] for name in generator.SOURCES}
    shared_before = {name: sha(ROOT / name) for name in METADATA}
    project_before = {name: sha(PROJECT / name) for name in METADATA}
    accepted_scope = dict(scope['accepted_scope'],
        D='cold ordinary initialization, no profile assignment, three routes and three visible cases, visible animation and exact remove-one/restore-four occupancy')
    reviewed = {'schema': 1, 'host_sha256': sha(Path(__file__)),
        'project': str(PROJECT), 'scope_receipt_sha256': sha(scope_path),
        'source_binding_sha256': sha(FINAL / 'final-source-binding-v1.json'),
        'source_contract_sha256': binding['source_contract_sha256'],
        'preserved_FA_BRG_source_contract_sha256': scope['source_contract_sha256'],
        'reports': reports, 'default_analysis_sha256': sha(analysis_path),
        'precise_release_sha256': sha(release_path), 'same_handle_exit_sha256': sha(exact_exit_path),
        'shared_qualifier_sha256': sha(Path(qualifier.__file__)),
        'shared_generator_sha256': sha(Path(generator.__file__)),
        'shared_qualifier_ROOT': str(qualifier.ROOT), 'shared_generator_ROOT': str(generator.ROOT),
        'all_eight_source_closures_passed': True,
        'reviewed_host_activation': activation, 'reviewed_D_camera_activation': camera_activation,
        'reviewed_D_camera_reference': camera_reference,
        'shared_dependencies': dependencies, 'shared_production_39': shared_production,
        'shared_metadata_before': shared_before, 'disposable_metadata_before': project_before,
        'expected_shared_owner_sha256': hashlib.sha256(generated_owner).hexdigest(),
        'expected_shared_module_sha256': hashlib.sha256(generated_module).hexdigest(),
        'accepted_scope': accepted_scope,
        'preserved_generic_geometry_failures': scope['preserved_generic_geometry_failures'],
        'R_or_G_exact_per_case_geometry_accepted': False, 'old_failed_reports_regraded': False,
        'manual_closures_added': 0, 'MC_started': False, 'RPC_dispatched': False,
        'algorithms_thresholds_or_ROIs_changed': False}
    if args.inspect_only:
        assert {name: sha(ROOT / name) for name in METADATA} == shared_before
        assert {name: sha(PROJECT / name) for name in METADATA} == project_before
        write(args.output, dict(reviewed, mode='inspect_only', shared_admission_performed=False,
                               created_at_utc=datetime.now(timezone.utc).isoformat()))
        print(json.dumps({'inspected': True, 'path': str(args.output), 'sha256': sha(args.output)}))
        return
    assert args.root_review is not None and args.inspection is not None
    inspection = json.loads(args.inspection.read_bytes())
    assert all(inspection[key] == value for key, value in reviewed.items()), 'Reviewed inputs changed'
    review = json.loads(args.root_review.read_bytes())
    assert review['status'] == 'confirmed_by_root' and review['reviewer'] == '/root'
    assert review['shared_owner_generation_authorized'] is True
    assert review['shared_final_qualification_authorized'] is True
    assert review['original_D_pixels_reviewed'] is True
    assert review['reviewed_wrapper_sha256'] == sha(Path(__file__))
    assert review['reviewed_inspection_sha256'] == sha(args.inspection)
    assert review['default_analysis_sha256'] == sha(analysis_path)
    assert review['precise_release_sha256'] == sha(release_path)
    for key in ('reports', 'accepted_scope', 'preserved_generic_geometry_failures',
                'R_or_G_exact_per_case_geometry_accepted', 'old_failed_reports_regraded'):
        assert review[key] == reviewed[key], key
    # Invoke the official shared generator and its check without redirecting ROOT.
    commands = []
    for extra in ((), ('--check',)):
        command = [sys.executable, '-B', '-X', 'utf8', str(ROOT / 'tools/generate_liquid_product_owner_contract.py'), *extra]
        result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=True)
        commands.append({'argv': command, 'exit_code': result.returncode,
                         'stdout': result.stdout, 'stderr': result.stderr})
    assert (ROOT / METADATA[0]).read_bytes() == generated_owner
    assert (ROOT / METADATA[1]).read_bytes() == generated_module
    assert sha(ROOT / METADATA[2]) == shared_before[METADATA[2]]
    inputs = {name: Path(row['path']) for name, row in reports.items()}
    official = argparse.Namespace(project=PROJECT,
        frozen_report=[inputs['F-editor'], inputs['F-full'], inputs['F-missing']],
        animated_report=inputs['A'], biome_report=inputs['B'], reverse_report=inputs['R'],
        gallery_report=inputs['G'], default_report=inputs['D'], output=args.output,
        admit_candidate=False, accept_reviewed=True, native_world_geometry=True, native_editor_gui=True)
    manifest = qualifier.qualify(official)
    assert manifest['stage'] == 'product' and all(manifest['gates'].values())
    assert manifest['evidence']['default']['sha256'] == reports['D']['sha256']
    assert {name: sha(PROJECT / name) for name in METADATA} == project_before
    assert all(sha(PROJECT / name) == value for name, value in expected.items())
    assert {name: sha(ROOT / name) for name in generator.SOURCES} == shared_production
    gate = qualifier.load_module(ROOT, 'liquid_product_qualification_data')
    assert gate.PRODUCT_QUALIFIED is True and gate.QUALIFICATION_STAGE == 'product'
    assert gate.QUALIFICATION_SHA256 == sha(args.output / 'qualification.json')
    assert gate.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256 == sha(ROOT / METADATA[0])
    assert all(gate.GATES.values())
    receipt = dict(reviewed, mode='execute_final', shared_admission_performed=True,
        created_at_utc=datetime.now(timezone.utc).isoformat(),
        root_review_sha256=sha(args.root_review), inspection_sha256=sha(args.inspection),
        official_generator_commands=commands, manifest_sha256=sha(args.output / 'qualification.json'),
        shared_metadata_after={name: sha(ROOT / name) for name in METADATA},
        disposable_metadata_unchanged=True, original_source_contracts_preserved=True)
    write(args.output / 'reviewed-final-host-receipt-v1.json', receipt)
    print(json.dumps({'qualified': True, 'stage': manifest['stage'], 'gates': manifest['gates'],
                      'manifest_sha256': sha(args.output / 'qualification.json'),
                      'manual_closures_added': 0, 'MC_started': False}))


if __name__ == '__main__':
    main()
