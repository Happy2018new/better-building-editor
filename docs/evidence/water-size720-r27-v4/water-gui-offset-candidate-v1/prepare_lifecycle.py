"""Bind a new private source and a single fixed three-GUI Scene lifecycle."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OLD = WORK.with_name('water-ui-geometry-observer-v2')
OWNER = 'water-r27-gui-offset-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    with (WORK / name).open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2)
        output.write('\n')


def replace_once(text, old, new):
    assert text.count(old) == 1, old
    return text.replace(old, new)


def main():
    manifest = json.loads((WORK / 'private-source-v1.json').read_bytes())
    project = Path(manifest['private_project'])
    assert not (WORK / 'final-source-binding-v1.json').exists()
    old_binding = json.loads((OLD / 'final-source-binding-v1.json').read_bytes())
    copied = ('candidate_bootstrap.py', 'bootstrap_payload.py', 'guard_policy.py', 'modal_guard.py',
              'launch_r25.py', 'start_assert_watch.py', 'watch_handles.py', 'run_candidate_bootstrap.py',
              'retire_bootstrap_marker.py', 'retire_helpers.py')
    patches = []
    for name in copied:
        raw = (OLD / name).read_bytes()
        revised = raw
        if name != 'candidate_bootstrap.py':
            text = raw.decode('utf-8')
            text = text.replace(old_binding['owner'], OWNER)
            if name == 'launch_r25.py':
                tree = ast.parse(text)
                node = next(node for node in tree.body if isinstance(node, ast.Assign)
                            and any(isinstance(target, ast.Name) and target.id == 'PROJECT' for target in node.targets))
                text = replace_once(text, ast.get_source_segment(text, node), 'PROJECT = Path(' + repr(str(project)) + ')')
            revised = text.encode('utf-8')
        (WORK / name).write_bytes(revised)
        if revised != raw:
            patches.extend(difflib.unified_diff(raw.decode('utf-8').splitlines(True), revised.decode('utf-8').splitlines(True),
                            fromfile='observer-v2/' + name, tofile='gui-offset-v1/' + name))
    # Keep the reviewed group finally/stop/helper retirement chain. Its only
    # execution task becomes the fixed Scene observer; the old root hold is removed.
    before = (OLD / 'run_geometry_group.py').read_text('utf-8')
    tree = ast.parse(before)
    main_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    independent = next(node for node in main_function.body if isinstance(node, ast.FunctionDef) and node.name == 'independent_restore')
    hold = next(node for node in main_function.body if isinstance(node, ast.FunctionDef) and node.name == 'bounded_root_hold')
    old_independent = ast.get_source_segment(before, independent)
    replacement = '''def independent_restore(label='final'):
        os.environ.update(MCDEV_SESSION_FILE=launch['session_file'],MCDEV_OWNER=binding['owner'],MCDEV_ALLOW_USER_FOREGROUND='0')
        sys.path.insert(0,str(Path(binding['project'])/'tools'))
        import probe_liquid_pose_channel as base
        import verify_debug_blueprints as blueprints
        from scene_restore import restore_scene
        check={'schema':1,'owner':binding['owner'],'restored':False,'restore_unknown':True,'checked_at':time.time()}
        try:
            with base.Client(timeout=20) as client:
                check['scene']=restore_scene(client,base.run,blueprints)
            check['source_unchanged']=all(sha(Path(binding['project'])/name)==expected for name,expected in
                                        dict(binding['source_sha256'],**binding['auxiliary_sha256']).items())
            check['restored']=check['scene']['restored'] and check['source_unchanged']
            check['restore_unknown']=False
        except Exception as error:
            check['error']={'type':type(error).__name__,'message':str(error)}
            raise
        finally:
            with (WORK/('independent-restore-v1.json' if label=='final' else 'independent-restore-'+label+'.json')).open('x',encoding='utf-8') as stream:json.dump(check,stream,indent=2)
        assert check['restored'],check'''
    group = replace_once(before, old_independent, replacement)
    group = replace_once(group, ast.get_source_segment(before, hold), '')
    group = replace_once(group,
        "    from hold_policy import validate_hold\n    validate_hold(grant,binding['owner'],sha(WORK/'plan-v1.json'),time.time())\n",
        "    assert grant['schema']==1\n")
    group = replace_once(group, "command('geometry','run_geometry_observation.py',", "command('scene','run_scene_observation.py',")
    group = replace_once(group, '        bounded_root_hold()\n', '')
    (WORK / 'run_scene_group.py').write_bytes(group.encode('utf-8'))
    patches.extend(difflib.unified_diff(before.splitlines(True), group.splitlines(True),
                   fromfile='observer-v2/run_geometry_group.py', tofile='gui-offset-v1/run_scene_group.py'))
    (WORK / 'observer-to-scene-lifecycle.patch').write_bytes(''.join(patches).encode('utf-8'))
    files = dict(manifest['source_sha256'], **manifest['auxiliary_sha256'])
    archive = WORK / 'private-launch-source-v1.zip'
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for relative, value in sorted(files.items()):
            assert sha(project / relative) == value, relative
            output.write(project / relative, relative)
    with zipfile.ZipFile(archive) as source:
        assert sorted(source.namelist()) == sorted(files)
        for relative, value in files.items():
            assert hashlib.sha256(source.read(relative)).hexdigest() == value, relative
    binding = dict(old_binding, owner=OWNER, project=str(project),
        bootstrap_receipt_marker='_water_r27_gui_offset_bootstrap_v1',
        source_sha256=manifest['source_sha256'], auxiliary_sha256=manifest['auxiliary_sha256'],
        source_contract_sha256=manifest['source_contract_sha256'], new_source_bytes_created=True,
        diagnostic_additions_only=False, private_gui_candidate_only=True,
        diagnostic_manifest_sha256=sha(WORK / 'private-source-v1.json'),
        archive={'path': str(archive), 'sha256': sha(archive), 'size_bytes': archive.stat().st_size,
                 'scope': 'New three-file GUI candidate over frozen diagnostic source; not full transitive closure'})
    assert sha(WORK / 'candidate_bootstrap.py') == binding['bootstrap_sha256']
    write('final-source-binding-v1.json', binding)
    inputs = json.loads((OLD / 'product-v2-launch-inputs.json').read_bytes())
    inputs.update(owner=OWNER, project=str(project), source_sha256=manifest['source_sha256'],
                  source_contract_sha256=manifest['source_contract_sha256'], archive=binding['archive'],
                  explicit_gui_candidate=True, production_admission_performed=False)
    write('product-v2-launch-inputs.json', inputs)
    plan = {'schema': 1, 'owner': OWNER, 'project': str(project),
            'declared_at_utc': datetime.now(timezone.utc).isoformat(),
            'private_source_manifest_sha256': sha(WORK / 'private-source-v1.json'),
            'source_contract_sha256': manifest['source_contract_sha256'],
            'scope': 'Explicit candidate normal workspace Scene; SDK/native geometry/static images; no default qualification',
            'phases': [{'label': 'gui4', 'physical_client': [1994, 1105], 'expected_integer_gui': 4},
                       {'label': 'gui3', 'physical_client': [1600, 900], 'expected_integer_gui': 3},
                       {'label': 'gui2', 'physical_client': [1280, 720], 'expected_integer_gui': 2}],
            'cases': [{'label': 'source_tilted', 'identity': 'source', 'pose': [35., 25., 3.]},
                      {'label': 'flow_east_tilted', 'identity': 'flow_east', 'pose': [35., 25., 3.]},
                      {'label': 'wet_fence_front', 'identity': 'wet_oak_fence', 'pose': [0., 0., 3.]},
                      {'label': 'wet_fence_tilted', 'identity': 'wet_oak_fence', 'pose': [35., 25., 3.]}],
            'controls': ['wet', 'dry'], 'captures_declared': 24,
            'same_font_control': 'Actual resize + SDK + explicit Theme.configure(3,True), Workspace closed; separate from actual Scene event refresh',
            'normal_scene_refresh': 'GUI3/GUI2 resize with ordinary Workspace mounted; no manual configure while mounted',
            'geometry_gate': 'Active skeleton only: GetPosition/GetSize within .02 logical units of stored geometry; bank model ID consistency and surface visibility; hidden dimensions retained',
            'original_failures_retained': ['formal_A_incomplete', 'original_global_neutral_masks', 'GUI2_front_WVP_factor_bound'],
            'resource_gates': {'min_available_commit_bytes': 6 * 1024 ** 3, 'max_handles': 250000, 'max_adjacent_growth': 10000},
            'capture_exe': {'path': str(ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'),
                            'sha256': 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'},
            'MC_started': False, 'formal_A_accepted': False, 'production_admission_performed': False,
            'default_path_evidence': False, 'manual_closures_added': 0,
            'host_code_sha256': {name: sha(WORK / name) for name in
                ('run_scene_observation.py', 'scene_game.py', 'scene_policy.py', 'scene_restore.py')}}
    write('plan-v1.json', plan)
    write('stage-r25.json', {'schema': 1, 'owner': OWNER, 'label': 'private-three-GUI-water-Scene',
          'plan_sha256': sha(WORK / 'plan-v1.json'), 'formal_A_accepted': False, 'manual_closures_added': 0,
          'source_scope_is_not_transitive_closure': True})
    sys.path.insert(0, str(WORK))
    from bootstrap_payload import dispatch_code
    code = dispatch_code((WORK / 'candidate_bootstrap.py').read_text('utf-8'), binding)
    (WORK / 'dispatched-bootstrap-payload.py').write_bytes(code.encode('utf-8'))
    for name, text in [('bootstrap', code)] + [(name, value) for name, value in
        __import__('scene_game').__dict__.items() if name.isupper() and isinstance(value, str)]:
        result = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
            'import sys;compile(sys.stdin.read(),sys.argv[1],"exec")', name],
            input=text.encode('utf-8'), capture_output=True)
        assert result.returncode == 0, (name, result.stderr)
    actual_hosts = copied + ('run_scene_group.py', 'run_scene_observation.py', 'scene_game.py', 'scene_policy.py',
                            'scene_restore.py', 'dispatched-bootstrap-payload.py')
    for name in actual_hosts:
        ast.parse((WORK / name).read_bytes(), filename=name)
    old_hosts = json.loads((OLD / 'prelaunch-host-binding-v1.json').read_bytes())
    external = {name: sha(ROOT / name) for name in old_hosts['external_host_sha256']}
    write('prelaunch-host-binding-v1.json', {'schema': 1,
        'source_binding_sha256': sha(WORK / 'final-source-binding-v1.json'),
        'host_sha256': {name: sha(WORK / name) for name in actual_hosts +
                        ('product-v2-launch-inputs.json', 'stage-r25.json', 'plan-v1.json', 'private-source-v1.json')},
        'external_host_sha256': external, 'MC_started': False,
        'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    write('lifecycle-preparation-v1.json', {'schema': 1, 'prepared': True, 'MC_started': False,
          'source_files': len(manifest['source_sha256']), 'auxiliary_files': len(manifest['auxiliary_sha256']),
          'archive_entries_checked': len(files), 'archive': binding['archive'],
          'core_exact_original': True, 'bootstrap_and_game_payloads_python2_compile': True,
          'plan_sha256': sha(WORK / 'plan-v1.json'), 'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json'),
          'formal_A_accepted': False, 'default_path_evidence': False})
    print(json.dumps({'prepared': True, 'MC_started': False, 'archive_bytes': archive.stat().st_size,
                      'plan_sha256': sha(WORK / 'plan-v1.json'),
                      'host_binding_sha256': sha(WORK / 'prelaunch-host-binding-v1.json')}))


if __name__ == '__main__':
    main()
