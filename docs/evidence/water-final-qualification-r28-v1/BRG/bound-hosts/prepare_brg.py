"""Freeze a new same-source owner for the unmeasured B/R/G stages only."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import zipfile

WORK = Path(__file__).resolve().parent
ROOT = WORK.parents[2]
PREVIOUS = WORK.with_name('water-final-matrix-v1')
OWNER = 'water-r28-final-brg-v3'
PROJECT = ROOT / '.runtime/projects' / OWNER


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (WORK / name).open('x', encoding='ascii', newline='\n') as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write('\n')


def once(text, before, after):
    assert text.count(before) == 1, before
    return text.replace(before, after, 1)


def mapped_flow_preflight(path):
    """Execute only actual AST constant mappings, with no session imports/RPC."""
    tree = ast.parse(path.read_bytes(), filename=str(path))
    wanted = {'CASES', 'ROUTES', 'OUT', 'HANDLES', 'RECEIPT'}
    selected = [node for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id in wanted
                        for target in node.targets)]
    assert len(selected) == len(wanted)
    code = compile(ast.Module(body=selected, type_ignores=[]), str(path), 'exec')
    routes = ('editor', 'full', 'missing')
    cases = {'A': ('flow_east', 'flow_south', 'flow_west', 'flow_north', 'falling'),
             'B': ('wet_oak_fence', 'pool'),
             'R': ('neighbor_oak_slab', 'neighbor_oak_stairs', 'neighbor_glass_pane',
                   'neighbor_stone', 'transparent_overlap'), 'G': ('gallery',)}
    rows = []
    all_paths = []
    for stage in ('A', 'B', 'R', 'G'):
        scope = {'STAGE': stage, 'WORK': WORK}
        exec(code, scope)
        assert scope['CASES'] == cases[stage]
        assert scope['ROUTES'] == (('editor',) if stage == 'G' else routes)
        expected = WORK / ('product-v2-' + stage.lower() + '-v1.json')
        assert scope['OUT'] == expected
        assert scope['HANDLES'] == expected.with_name(expected.stem + '-handles.json')
        assert scope['RECEIPT'] == expected.with_name(expected.stem + '-host.json')
        paths = [scope[name] for name in ('OUT', 'HANDLES', 'RECEIPT')]
        assert all(not current.exists() for current in paths)
        all_paths.extend(paths)
        rows.append({'stage': stage, 'cases': scope['CASES'], 'routes': scope['ROUTES'],
                     'output': str(expected), 'paths_fresh': True})
    assert len(all_paths) == len(set(all_paths)) == 12
    return {'passed': True, 'actual_AST_assignments_executed': True, 'rows': rows,
            'unique_result_paths': 12, 'MC_started': False, 'RPC_dispatched': False}


def main():
    old = json.loads((PREVIOUS / 'final-source-binding-v1.json').read_bytes())
    old_hosts = json.loads((PREVIOUS / 'prelaunch-host-binding-v1.json').read_bytes())
    release = json.loads((PREVIOUS / 'precise-release-audit-v2.json').read_bytes())
    assert release['all_exact_identities_absent'] and release['restored']
    assert release['registry_finalize_exit_code'] == release['retire_helpers_exit_code'] == 0
    assert all(sha(PREVIOUS / name) == value for name, value in old_hosts['host_sha256'].items())
    assert not PROJECT.exists()
    record = old['source_provenance']
    expected = dict(old['source_sha256'], **old['auxiliary_sha256'])
    delta = set(record['added_files']) | set(record['changed_files'])
    base = Path(record['base']['path'])
    overlay = Path(record['overlay']['path'])
    assert sha(base) == record['base']['sha256']
    assert sha(overlay) == record['overlay']['sha256']
    PROJECT.mkdir()
    with zipfile.ZipFile(base) as previous_zip, zipfile.ZipFile(overlay) as overlay_zip:
        for name, value in sorted(expected.items()):
            raw = overlay_zip.read(name) if name in delta else previous_zip.read(name)
            assert hashlib.sha256(raw).hexdigest() == value
            target = PROJECT / name
            assert target.resolve().is_relative_to(PROJECT.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
    assert all(sha(PROJECT / name) == value for name, value in expected.items())
    binding = dict(old, owner=OWNER, project=str(PROJECT),
                   prepared_at_utc=datetime.now(timezone.utc).isoformat(),
                   current_shared_source_exactly_matches_frozen=all(
                       (ROOT / name).is_file() and sha(ROOT / name) == value
                       for name, value in old['source_sha256'].items()),
                   resumed_stages_only=['B', 'R', 'G'],
                   predecessor_binding_sha256=sha(PREVIOUS / 'final-source-binding-v1.json'),
                   predecessor_owner=old['owner'], source_cohort_unchanged=True,
                   inherited_results_rewritten=False)
    write('final-source-binding-v1.json', binding)
    write('product-v2-launch-inputs.json', {key: binding[key] for key in
          ('schema', 'project', 'owner', 'source_sha256', 'source_contract_sha256',
           'archive', 'source_provenance')})
    patches = []
    names = ('guard_policy.py', 'modal_guard.py', 'launch_r25.py', 'start_assert_watch.py',
             'watch_handles.py', 'retire_helpers.py', 'scene_game.py', 'scene_policy.py',
             'scene_restore.py', 'resize_adapter.py', 'resize_background.py',
             'observe_cold_default.py', 'flow_restore.py', 'world_readback.py',
             'scene_native_layout.py', 'run_camera.py', 'calibration_host.py',
             'run_flow.py', 'run_group_v2.py', 'source_provenance.py', 'analyze_matrix_v2.py')
    for name in names:
        before = (PREVIOUS / name).read_text('utf8')
        after = before.replace(old['owner'], OWNER).replace(Path(old['project']).name, PROJECT.name)
        if name == 'run_flow.py':
            after = once(after, "ROUTES = ('editor', 'full', 'missing')",
                         "ROUTES = ('editor',) if STAGE == 'G' else ('editor', 'full', 'missing')")
            after = once(after, "OUT = WORK / 'product-v2-a-v1.json'",
                         "OUT = WORK / ('product-v2-' + STAGE.lower() + '-v1.json')")
        elif name == 'run_group_v2.py':
            after = once(after, "    extension=json.loads((WORK/'prelaunch-host-extension-v2.json').read_bytes())\n"
                         "    assert all(sha(WORK/name)==expected for name,expected in extension['host_sha256'].items())\n"
                         "    assert sha(WORK/'prelaunch-host-binding-v1.json')==extension['previous_host_binding_sha256']\n",
                         "    host_binding=json.loads((WORK/'prelaunch-host-binding-v1.json').read_bytes())\n"
                         "    assert all(sha(WORK/name)==expected for name,expected in host_binding['host_sha256'].items())\n")
            after = once(after, "'plan-v2.json'", "'plan-v3.json'")
            start = after.index("        command('F-editor'")
            end = after.index("        command('B'", start)
            after = after[:start] + after[end:]
            assert "command('A'" not in after and "command('F-editor'" not in after
        ast.parse(after, filename=name)
        with (WORK / name).open('x', encoding='utf8', newline='\n') as stream:
            stream.write(after)
        patches.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                           fromfile=str(PREVIOUS / name), tofile=name))
    with (WORK / 'host-changes-v3.patch').open('x', encoding='utf8', newline='\n') as stream:
        stream.write(''.join(patches))
    from source_provenance import verify_source_provenance
    write('source-synthesis-v1.json', verify_source_provenance(binding))
    mapping = mapped_flow_preflight(WORK / 'run_flow.py')
    mapping['host_sha256'] = sha(WORK / 'run_flow.py')
    write('stage-mapping-preflight-v3.json', mapping)
    plan = json.loads((PREVIOUS / 'plan-v2.json').read_bytes())
    for key in ('F', 'A', 'F_world_per_capture_cutoff_utc'):
        plan.pop(key, None)
    plan.update(owner=OWNER, project=str(PROJECT), stage='formal_same_source_BRG_supplement',
                host_extension_version=3, previous_plan_sha256=sha(PREVIOUS / 'plan-v2.json'),
                created_at_utc=datetime.now(timezone.utc).isoformat(), estimated_minutes=[20, 45],
                no_repeat_of_F_or_A=True, source_cohort_unchanged=True,
                old_failed_group_and_reports_preserved=True,
                known_host_fixes=['stage-specific fresh result paths', 'G editor-only routes'],
                stage_mapping_preflight_sha256=sha(WORK / 'stage-mapping-preflight-v3.json'),
                new_same_session_native_stone_calibration_required=True,
                predecessor_release_sha256=sha(PREVIOUS / 'precise-release-audit-v2.json'))
    write('plan-v3.json', plan)
    write('stage-r25.json', {'schema': 1, 'owner': OWNER, 'plan_sha256': sha(WORK / 'plan-v3.json'),
                           'formal_A_accepted': False, 'manual_closures_added': 0,
                           'BRG_supplement_only': True})
    names = [path.name for path in WORK.iterdir() if path.is_file()
             and path.suffix in ('.py', '.json', '.patch')
             and path.name != 'final-source-binding-v1.json']
    write('prelaunch-host-binding-v1.json', {'schema': 1,
          'source_binding_sha256': sha(WORK / 'final-source-binding-v1.json'),
          'host_sha256': {name: sha(WORK / name) for name in names},
          'external_host_sha256': old_hosts['external_host_sha256'],
          'startup_contract_sha256': old_hosts['startup_contract_sha256'],
          'predecessor_host_binding_sha256': sha(PREVIOUS / 'prelaunch-host-binding-v1.json'),
          'MC_started': False, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    assert all(sha(PREVIOUS / name) == value for name, value in old_hosts['host_sha256'].items())
    print(json.dumps({'prepared': True, 'MC_started': False, 'owner': OWNER,
                      'source_contract_sha256': binding['source_contract_sha256'],
                      'same_source': binding['source_cohort_unchanged'],
                      'current_shared_source_exactly_matches_frozen': binding['current_shared_source_exactly_matches_frozen'],
                      'plan_sha256': sha(WORK / 'plan-v3.json'),
                      'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
                      'stage_mapping_preflight': mapping}))


if __name__ == '__main__':
    main()
