"""Prepare a new, bounded F-editor run against the unchanged R27 source cohort."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
OLD = ROOT / '.runtime/round-20261022/water-merged-fullA-v2'
F_OLD = ROOT / '.runtime/round-20261021/water-final41-r25-v6'
OWNER = 'water-r28-formal-f-editor-v2'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (WORK / name).open('x', encoding='utf8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after)


def main():
    assert not (WORK / 'final-source-binding-v1.json').exists()
    original_binding = json.loads((OLD / 'final-source-binding-v1.json').read_bytes())
    old_hosts = json.loads((OLD / 'prelaunch-host-binding-v1.json').read_bytes())
    project = Path(original_binding['project'])
    source_checks = {}
    for section in ('source_sha256', 'auxiliary_sha256'):
        for relative, expected in original_binding[section].items():
            assert sha(project / relative) == expected, relative
            assert sha(ROOT / relative) == expected, relative
        source_checks[section] = len(original_binding[section])
    changes = []
    names = ('guard_policy.py', 'modal_guard.py', 'launch_r25.py', 'start_assert_watch.py',
             'watch_handles.py', 'retire_helpers.py', 'scene_game.py', 'scene_policy.py',
             'scene_restore.py', 'resize_adapter.py', 'resize_background.py',
             'observe_cold_default.py', 'flow_restore.py', 'run_group.py', 'world_readback.py')
    for name in names:
        original = (OLD / name).read_text('utf8')
        text = original.replace(original_binding['owner'], OWNER)
        text = text.replace('2026-10-21T23:20:00+00:00', '2026-10-22T23:20:00+00:00')
        if name == 'run_group.py':
            text = once(text, "        command('camera','run_camera.py',('camera',),timeout=480)\n"
                        "        independent_restore('after-camera')\n"
                        "        command('A','run_flow.py',('A',),timeout=1800)\n",
                        "        command('F-editor','run_frozen_editor.py',timeout=1800)\n")
        with (WORK / name).open('x', encoding='utf8', newline='\n') as stream:
            stream.write(text)
        if text != original:
            changes.extend(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                           fromfile='R27/' + name, tofile='R28/' + name))
    original = (F_OLD / 'run_product_v2_f_editor.py').read_text('utf8')
    text = original.replace('water-r25-final41-editor-v6', OWNER)
    text = once(text, "water-r25-final41-v2", project.name)
    text = once(text, "CASES = ('source', 'flow_east', 'wet_oak_fence', 'neighbor_stone', 'transparent_overlap')",
                "CASES = ('source', 'low', 'diagonal', 'drop_north', 'pool', 'falling',\n"
                "         'flow_east', 'flow_south', 'flow_west', 'flow_north',\n"
                "         'wet_oak_fence', 'wet_glass_pane', 'wet_oak_slab', 'wet_oak_stairs',\n"
                "         'neighbor_oak_slab', 'neighbor_oak_stairs', 'neighbor_glass_pane',\n"
                "         'neighbor_stone', 'transparent_overlap')")
    text = once(text, 'import ctypes\n', 'from datetime import datetime, timezone\nimport ctypes\n')
    text = once(text, '    original_capture = probe.base.capture\n',
                '    from scene_policy import describe_scene\n'
                '    import scene_game\n'
                '    geometry = []\n'
                '    active_check = [None]\n'
                "    receipt['native_geometry_observations'] = geometry\n"
                '    original_capture = probe.base.capture\n')
    text = once(text, '    def tracked_capture(session, owner, output, executable):\n',
                '    def tracked_capture(session, owner, output, executable):\n'
                "        assert datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-22T23:25:00+00:00'), '07:25 capture cutoff'\n")
    text = once(text, '    def tracked_run(check, code):\n',
                '    def tracked_run(check, code):\n        active_check[0] = check\n')
    text = once(text, '        label = Path(output).stem\n',
                '        label = Path(output).stem\n'
                '        observed = original_run(active_check[0], probe.SCENE_STATE + scene_game.EXTRA_STATE)\n'
                "        active = any(bank is not None and bank['declared_visible'] is True\n"
                "                     for entry in observed['native_water_controls'] for bank in entry['banks'])\n"
                '        verdict = describe_scene(observed, 2, active)\n'
                "        geometry.append({'label': label, 'state': observed, 'verdict': verdict})\n"
                '        save()\n'
                "        assert verdict['complete'], verdict\n")
    text = once(text, '        result = original_run(check, code)\n',
                "        is_scene = code == probe.SCENE_STATE\n"
                "        result = original_run(check, code + scene_game.EXTRA_STATE if is_scene else code)\n"
                )
    with (WORK / 'run_frozen_editor.py').open('x', encoding='utf8', newline='\n') as stream:
        stream.write(text)
    changes.extend(difflib.unified_diff(original.splitlines(True), text.splitlines(True),
                   fromfile='R26/run_product_v2_f_editor.py', tofile='R28/run_frozen_editor.py'))
    with (WORK / 'host-changes-v1.patch').open('x', encoding='utf8', newline='\n') as stream:
        stream.write(''.join(changes))
    binding = dict(original_binding, owner=OWNER, guard_deadline_utc='2026-10-22T23:40:00+00:00',
                   previous_successful_A_binding={'path': str(OLD / 'final-source-binding-v1.json'),
                     'sha256': sha(OLD / 'final-source-binding-v1.json')},
                   current_shared_source_exactly_matches_frozen=True,
                   current_shared_source_checked_at_utc=datetime.now(timezone.utc).isoformat())
    write('final-source-binding-v1.json', binding)
    write('product-v2-launch-inputs.json', {key: binding[key] for key in
         ('schema', 'project', 'owner', 'source_sha256', 'source_contract_sha256', 'archive')})
    plan = {'schema': 1, 'owner': OWNER, 'project': str(project), 'stage': 'F-editor',
            'created_at_utc': datetime.now(timezone.utc).isoformat(),
            'source_contract_sha256': binding['source_contract_sha256'],
            'source_checks': source_checks, 'source_archive_reused_without_copy': True,
            'case_count': 19, 'route': 'editor',
            'controls': ['wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty'],
            'visibility_controls': True, 'opaque_side_controls': True,
            'alpha_controls': True, 'measure_budgets': True,
            'native_gui': 2, 'physical_client_size': [1280, 720],
            'geometry_tolerance_logical': .02,
            'normal_cold_init_required': True, 'explicit_bootstrap_performed': False,
            'frozen_candidate_profile_for_controlled_pixels': True,
            'production_qualification_or_owner_changed': False,
            'minimum_available_commit_bytes': 6 * 1024 ** 3,
            'max_handles': 250000, 'maximum_adjacent_growth': 10000,
            'no_new_capture_after_utc': '2026-10-22T23:25:00+00:00',
            'restoration_deadline_utc': binding['guard_deadline_utc'],
            'estimated_minutes': [12, 20], 'failure_policy': 'No unchanged retry',
            'not_a_complete_water_release_qualification': True, 'manual_closures_added': 0}
    write('plan-v1.json', plan)
    write('stage-r25.json', {'schema': 1, 'owner': OWNER, 'plan_sha256': sha(WORK / 'plan-v1.json'),
                           'formal_A_accepted': False, 'manual_closures_added': 0})
    for path in WORK.glob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    write('prelaunch-host-binding-v1.json', {
        'schema': 1, 'source_binding_sha256': sha(WORK / 'final-source-binding-v1.json'),
        'host_sha256': {path.name: sha(path) for path in WORK.iterdir()
                       if path.is_file() and path.suffix in ('.py', '.patch', '.json')
                       and path.name != 'final-source-binding-v1.json'},
        'external_host_sha256': old_hosts['external_host_sha256'],
        'startup_contract_sha256': old_hosts['startup_contract_sha256'],
        'MC_started': False, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    print(json.dumps({'prepared': True, 'MC_started': False,
                      'plan_sha256': sha(WORK / 'plan-v1.json'), 'source_checks': source_checks}))


if __name__ == '__main__':
    main()
