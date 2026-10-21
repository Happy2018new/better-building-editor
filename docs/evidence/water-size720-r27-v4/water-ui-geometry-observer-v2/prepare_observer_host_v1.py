"""Prepare one SDK-only diagnostic cold session; source archive is reused."""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
BASE = WORK.with_name('water-anchor-calibration-v6')
OWNER = 'water-r27-ui-geometry-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(name, value):
    with (WORK / name).open('x', encoding='utf8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    assert not (WORK / 'plan-v1.json').exists()
    copied = ('bootstrap_payload.py', 'candidate_bootstrap.py', 'guard_policy.py',
        'modal_guard.py', 'retire_bootstrap_marker.py', 'run_candidate_bootstrap.py',
        'start_assert_watch.py', 'watch_handles.py', 'product-v2-launch-inputs.json',
        'diagnostic-source-v1.json')
    for name in copied:
        assert not (WORK / name).exists()
        (WORK / name).write_bytes((BASE / name).read_bytes())
    launch = (BASE / 'launch_r25.py').read_text('utf8').replace(
        "OWNER = 'water-r27-anchor-calibration-v4'", "OWNER = %r" % OWNER)
    (WORK / 'launch_r25.py').write_text(launch, encoding='utf8', newline='\n')
    group = (BASE / 'run_anchor_group.py').read_text('utf8')
    group = group.replace("    parser.add_argument('--capture-exe',type=Path,required=True)\n", '')
    group = group.replace('import anchor_game as game', 'import observer_game as game')
    group = group.replace("command('anchor','run_anchor_calibration.py',('--session',launch['session_file'],\n                '--capture-exe',str(args.capture_exe.resolve(strict=True)),'--root-grant',str(args.root_grant.resolve(strict=True))))", "command('geometry','run_geometry_observation.py',('--session',launch['session_file'],\n                '--root-grant',str(args.root_grant.resolve(strict=True))))")
    # A pre-Popen failure still leaves an exact-owner assertion helper to retire.
    group = group.replace("        try:\n            if launch and launch.get('session_file'):",
        "        try:\n            if not (launch and launch.get('session_file')) and (WORK/'assert-watch-start.json').exists():\n                command('retire-helpers','retire_helpers.py',guard=False)\n            if launch and launch.get('session_file'):")
    assert 'run_anchor_calibration.py' not in group and 'capture-exe' not in group
    (WORK / 'run_geometry_group.py').write_text(group, encoding='utf8', newline='\n')
    retire = (BASE / 'retire_helpers.py').read_text('utf8')
    retire = retire.replace('from _session import _kernel, _identity, process_identity',
                            'from _session import _kernel, _identity, process_identity, registry_dir')
    old = "    launch = json.loads((WORK / 'launch/launch.json').read_bytes())\n    for kind in ('game', 'mcdk'):\n        assert process_identity(launch[kind + '_pid']) != launch[kind + '_identity']"
    new = """    launch_path = WORK / 'launch/launch.json'
    launch = json.loads(launch_path.read_bytes()) if launch_path.exists() else {}
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    if all(launch.get(kind + '_pid') and launch.get(kind + '_identity') for kind in ('game', 'mcdk')):
        for kind in ('game', 'mcdk'):
            assert process_identity(launch[kind + '_pid']) != launch[kind + '_identity']
    else:
        # A missing launch receipt alone does not prove that no owner is live.
        # A malformed/unreadable manifest refuses helper retirement.
        for path in registry_dir().glob('*/session.json'):
            current = json.loads(path.read_bytes())
            if current.get('owner') == binding['owner']:
                for kind in ('game', 'mcdk'):
                    pid, identity = current.get(kind + '_pid'), current.get(kind + '_identity')
                    assert not (pid and identity and process_identity(pid) == identity)
"""
    assert old in retire
    (WORK / 'retire_helpers.py').write_text(retire.replace(old, new), encoding='utf8', newline='\n')
    binding = json.loads((BASE / 'final-source-binding-v1.json').read_bytes())
    binding.update(owner=OWNER, bootstrap_receipt_marker='_water_r27_ui_geometry_bootstrap_v1',
        guard_deadline_utc='2026-10-21T23:45:00+00:00',
        source_refrozen_at_utc=datetime.now(timezone.utc).isoformat(),
        previous_host_binding_sha256=sha(BASE / 'prelaunch-host-binding-v1.json'),
        previous_failed_attempt_review_sha256=sha(BASE / 'hidden-geometry-failure-review-v1.json'),
        new_source_bytes_created=False,
        diagnostic_scope='SDK-only native geometry of new Panel wrapper; no screenshots, water A or production qualification')
    write_json('final-source-binding-v1.json', binding)
    plan = {'schema': 1, 'owner': OWNER, 'project': binding['project'],
        'declared_at_utc': datetime.now(timezone.utc).isoformat(),
        'diagnostic_source_manifest_sha256': sha(WORK / 'diagnostic-source-v1.json'),
        'source_contract_sha256': binding['source_contract_sha256'],
        'scope': 'SDK-only native hidden/active geometry and renderer banks; diagnostic wrapper only',
        'MC_started': False, 'formal_A_accepted': False,
        'production_admission_performed': False, 'manual_closures_added': 0,
        'wrapper_structure_change': True, 'original_fixed_138_plan_unchanged': True,
        'phase_lifecycle': 'one mount: empty_before -> stone -> neutral15 -> empty_after; CLEAN/CLEAN_READY and independent restore before next resize',
        'phases': [dict(label=label, physical_client=size, expected_integer_gui=gui,
            rectangle_fractions=[.12,.19,.76,.62]) for label,size,gui in (
                ('gui4',[1994,1105],4), ('gui3',[1600,900],3), ('gui2',[1280,720],2))],
        'position': [1,1,1], 'pose': [0.,0.,0.], 'unit_fraction': .18,
        'state_sequence': [dict(label=label, mode=mode) for label,mode in (
            ('empty_before','empty'), ('stone','stone'), ('neutral15','neutral'), ('empty_after','empty'))],
        'observation': {'sample_interval_seconds': .2, 'logical_ready_deadline_seconds': 15,
            'samples_including_first_logical_ready': 6,
            'native_geometry_contradictions_are_recorded_not_redefined_as_product_pass': True,
            'raw_snapshot_from_first_post_configure_RPC': True,
            'hidden_zero_dimensions_are_observed_not_used_as_parent_measurement': True,
            'no_screenshots_or_matrix_decode_in_this_initial_observation': True},
        'resource_gates': {'min_available_commit_bytes': 6*1024**3,
            'max_handles': 250000, 'max_adjacent_growth': 10000},
        'estimated_exclusive_MC_minutes': 6,
        'host_code_sha256': {name: sha(WORK / name) for name in (
            'observer_game.py', 'geometry_observation.py', 'run_geometry_observation.py')},
        'synthetic_controls_path': str(WORK / 'geometry-synthetic-controls-v1.json'),
        'synthetic_controls_sha256': sha(WORK / 'geometry-synthetic-controls-v1.json'),
        'diagnostic_watcher': binding['diagnostic_watcher']}
    write_json('plan-v1.json', plan)
    write_json('stage-r25.json', {'schema': 1, 'owner': OWNER, 'label': 'sdk-native-geometry-observation',
        'plan_sha256': sha(WORK / 'plan-v1.json'), 'formal_A_accepted': False,
        'manual_closures_added': 0, 'source_scope_is_not_transitive_closure': True,
        'new_diagnostic_source_manifest_sha256': plan['diagnostic_source_manifest_sha256']})
    sys.path.insert(0, str(WORK))
    spec = importlib.util.spec_from_file_location('observer_bootstrap_prepare', WORK / 'run_candidate_bootstrap.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    code = module.dispatch_code((WORK / 'candidate_bootstrap.py').read_text('utf8'), binding)
    (WORK / 'dispatched-bootstrap-payload.py').write_bytes(code.encode('utf8'))
    import observer_game as game
    dummy = dict(position=[1,1,1],pose=[0.,0.,0.],rect=[10.,20.,200.,100.],
        unit_fraction=.18,mode='empty',model='modern_projection_r27_anchor_15',offset_factor=0.)
    for name in ('OPEN','CONFIGURE','STATUS','CLEAN','CLEAN_READY'):
        text = game.PREFIX + (game.CONFIGURE % (dummy,) if name == 'CONFIGURE' else getattr(game,name))
        (WORK / ('compile-' + name + '.py')).write_bytes(text.encode('utf8'))
    previous_hosts = json.loads((BASE / 'prelaunch-host-binding-v1.json').read_bytes())
    hosts = [path.name for path in WORK.iterdir() if path.suffix == '.py']
    hosts += ['plan-v1.json','stage-r25.json','product-v2-launch-inputs.json',
        'geometry-synthetic-controls-v1.json','observer-payload-binding-v1.json']
    write_json('prelaunch-host-binding-v1.json', {'schema': 1,
        'source_binding_sha256': sha(WORK / 'final-source-binding-v1.json'),
        'host_sha256': {name: sha(WORK / name) for name in sorted(hosts)},
        'external_host_sha256': previous_hosts['external_host_sha256'],
        'MC_started': False, 'frozen_at_utc': datetime.now(timezone.utc).isoformat(),
        'previous_host_binding_sha256': sha(BASE / 'prelaunch-host-binding-v1.json')})
    print(json.dumps({'prepared': True, 'MC_started': False, 'owner': OWNER,
        'plan_sha256': sha(WORK / 'plan-v1.json'),
        'binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
        'core_exact_LF_sha256': sha(WORK / 'candidate_bootstrap.py')}))


if __name__ == '__main__':
    main()
