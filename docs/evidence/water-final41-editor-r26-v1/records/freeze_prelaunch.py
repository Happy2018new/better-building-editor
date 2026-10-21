"""Freeze only new private host inputs and verify immutable original source bytes."""
import ast
from datetime import datetime, timezone
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(name, value):
    with (WORK / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    binding_path = WORK / 'final-source-binding-v1.json'
    binding = json.loads(binding_path.read_bytes())
    project = Path(binding['project'])
    previous = WORK.with_name('water-final41-r25-v5')
    assert binding['owner'] == 'water-r25-final41-editor-v6'
    assert binding['guard_deadline_utc'] == '2026-10-21T06:57:00+00:00'
    assert not (WORK / 'launch').exists() and not (WORK / 'group-execution-v1.json').exists()
    source = {name: sha(project / name) for name in binding['source_sha256']}
    auxiliary = {name: sha(project / name) for name in binding['auxiliary_sha256']}
    assert source == binding['source_sha256'] and len(source) == 4479
    assert auxiliary == binding['auxiliary_sha256'] and len(auxiliary) == 1391
    discovered = [path for folder in ('behavior_pack', 'resource_pack')
                  for path in (project / folder).rglob('*')
                  if path.is_file() and '__pycache__' not in path.parts and path.suffix not in ('.pyc', '.pyo')]
    discovered += list((project / 'tools').glob('*.py'))
    discovered += list((project / '.agents/skills/pyreact-debugging/scripts').glob('*.py'))
    assert {path.relative_to(project).as_posix() for path in discovered} == set(source)
    digest = hashlib.sha256(json.dumps(source, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
    assert digest == binding['source_contract_sha256']
    assert sha(Path(binding['archive']['path'])) == binding['archive']['sha256']
    assert sha(project / binding['qualification_path']) == binding['qualification_sha256']
    assert sha(WORK / 'candidate_bootstrap.py') == binding['bootstrap_sha256']
    assert (WORK / 'candidate_bootstrap.py').read_bytes() == Path(binding['bootstrap_core_byte_copy_from']).read_bytes()
    for name in ('source_sha256', 'auxiliary_sha256', 'archive', 'bootstrap_sha256',
                 'owner_contract_sha256', 'old_qualification_implementation_sha256', 'qualification_sha256'):
        assert binding[name] == json.loads((previous / 'final-source-binding-v1.json').read_bytes())[name]
    config = json.loads((project / '.mcdev.json').read_bytes())
    assert all(config.get(key) is False for key in
               ('auto_hot_reload_mods', 'auto_hot_reload_ui', 'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    gate, owners = {}, {}
    exec(compile((project / binding['qualification_path']).read_text('ascii'), '<original-qualification>', 'exec'), gate)
    owner_path = project / 'behavior_pack/modern_projection/projection/liquid_product_owner_data.py'
    exec(compile(owner_path.read_text('ascii'), '<frozen-41-owner>', 'exec'), owners)
    assert gate['PRODUCT_QUALIFIED'] is True and gate['QUALIFICATION_STAGE'] == 'product'
    assert gate['QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256'] == binding['old_qualification_implementation_sha256']
    assert owners['IMPLEMENTATION_CONTRACT_SHA256'] == binding['owner_contract_sha256']
    assert owners['IMPLEMENTATION_CONTRACT_SHA256'] != gate['QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256']
    host_files = sorted(WORK.glob('*.py')) + [WORK / 'product-v2-launch-inputs.json', WORK / 'stage-r25.json']
    for path in WORK.glob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    sys.path.insert(0, str(WORK))
    import bootstrap_payload
    payload = bootstrap_payload.dispatch_code((WORK / 'candidate_bootstrap.py').read_text('utf-8'), binding)
    payloads = {'dispatch': payload, 'readback': bootstrap_payload.readback_code(binding['bootstrap_receipt_marker']),
                'retire': bootstrap_payload.readback_code(binding['bootstrap_receipt_marker'], retire=True)}
    py2 = Path('D:/Program/Python27/python.exe')
    py2_check = subprocess.run([str(py2), '-B', '-c',
        "import json,sys;data=json.load(sys.stdin);[compile(text.encode('utf-8'),name,'exec') for name,text in data.items()];print(json.dumps({'version':sys.version,'compiled':sorted(data)}))"],
        input=json.dumps(payloads), capture_output=True, text=True, timeout=10)
    py2_check.check_returncode()
    external = set()
    todo = [ROOT / name for name in (
        'tools/watch_owned_disabled_skin_assert_r20.py', 'tools/dismiss_owned_disabled_skin_assert.py',
        'tools/check_native_dialogs.py', '.runtime/round-20261019/watch_exact_start.py',
        '.agents/skills/pyreact-debugging/scripts/instances.py', '.agents/skills/pyreact-debugging/scripts/mcdk.py',
        '.agents/skills/pyreact-debugging/scripts/_window.py', '.agents/skills/pyreact-debugging/scripts/_session.py')]
    roots = [ROOT / 'tools', ROOT / '.agents/skills/pyreact-debugging/scripts']
    while todo:
        path = todo.pop()
        if path in external:
            continue
        external.add(path)
        for node in ast.walk(ast.parse(path.read_bytes())):
            names = ([alias.name for alias in node.names] if isinstance(node, ast.Import) else
                     [node.module] if isinstance(node, ast.ImportFrom) and node.module else [])
            for name in names:
                for base in [path.parent] + roots:
                    local = base / (name.replace('.', '/') + '.py')
                    if local.is_file() and local not in external:
                        todo.append(local)
    expected_external = {
        'tools/watch_owned_disabled_skin_assert_r20.py': 'f93e4c5ba1b728fe0b6627ed58c8d4938b18913a6dafa96305237b84198b07df',
        'tools/dismiss_owned_disabled_skin_assert.py': 'f64b8167c621f71981158bb49ff8abc5cc52f594ada2ef60ae1e9736328151af',
        '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe': 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
        'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll': '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe': 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8',
    }
    for name, expected in expected_external.items():
        assert sha(ROOT / name) == expected, name
        external.add(ROOT / name)
    external.update(path for path in (ROOT / 'tools/native_wgc').iterdir() if path.is_file())
    hosts = {'schema': 1, 'revision': 6, 'source_binding_sha256': sha(binding_path),
             'host_sha256': {path.name: sha(path) for path in host_files},
             'external_host_sha256': {path.relative_to(ROOT).as_posix(): sha(path) for path in sorted(external)},
             'previous_failed_host_binding_sha256': sha(previous / 'prelaunch-host-binding-v5.json'),
             'launch_approved': False, 'MC_started': False, 'manual_closures_added': 0,
             'foreground_policy': 'MCDEV_ALLOW_USER_FOREGROUND=0 on all execution hosts',
             'resource_coverage': '6GiB pre-command commit; continuous exact identity/handles/deadline/unknown modal from first game and MCDK discovery',
             'no_force': True, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()}
    write_new('prelaunch-host-binding-v6.json', hosts)
    changes = []
    for path in sorted(WORK.glob('*.py')):
        old = previous / path.name
        changes += list(difflib.unified_diff(old.read_text('utf-8').splitlines(True) if old.exists() else [],
                        path.read_text('utf-8').splitlines(True), fromfile='v5/' + path.name, tofile='v6/' + path.name))
    with (WORK / 'host-v5-to-v6.patch').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(''.join(changes))
    controls = {}
    for name in ('bootstrap-offline-controls-v1.json', 'guard-offline-controls-v1.json',
                 'payload-offline-controls-v1.json', 'payload-wrapper-controls-v1.json', 'modal-guard-offline-controls-v1.json'):
        data = json.loads((WORK / name).read_bytes())
        assert data.get('passed', data.get('all_passed', False)), name
        controls[name] = {'sha256': sha(WORK / name), 'checks': len(data.get('checks', []))}
    result = {'schema': 1, 'passed': True, 'offline_only': True, 'MC_started': False,
              'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'owner': binding['owner'],
              'source_files_verified': len(source), 'auxiliary_files_verified': len(auxiliary),
              'source_contract_sha256': digest, 'source_archive_sha256': binding['archive']['sha256'],
              'original_core_sha256': binding['bootstrap_sha256'], 'source_unchanged_from_v5': True,
              'old_qualification_preserved': True, 'normal_production_expected_refusal': True,
              'owner_scope_is_not_transitive_closure': True,
              'game_payload_python2_compile': {'interpreter': str(py2), 'interpreter_sha256': sha(py2),
                                               'stdout': py2_check.stdout, 'stderr': py2_check.stderr, 'exit_code': py2_check.returncode},
              'prelaunch_binding_sha256': sha(WORK / 'prelaunch-host-binding-v6.json'),
              'diff_sha256': sha(WORK / 'host-v5-to-v6.patch'), 'controls': controls,
              'scope': {'stages': ['one-shot-bootstrap', 'G-editor', 'narrow-F-editor'],
                        'F_cases': ['source', 'flow_east', 'wet_oak_fence', 'neighbor_stone', 'transparent_overlap'],
                        'A_or_D_or_default_qualification': False, 'manual_closures_added': 0},
              'invoke': ['D:/Program/Python/python.exe', '-B', '-X', 'utf8', str(WORK / 'run_editor_group.py')],
              'new_long_step_cutoff_utc': '2026-10-21T06:55:00+00:00',
              'cleanup_deadline_utc': binding['guard_deadline_utc'],
              'launch_requires_parent_independent_review': True}
    write_new('prelaunch-review-v6.json', result)
    print(json.dumps({'passed': True, 'review': str(WORK / 'prelaunch-review-v6.json'),
                      'review_sha256': sha(WORK / 'prelaunch-review-v6.json'),
                      'binding_sha256': result['prelaunch_binding_sha256'],
                      'diff_sha256': result['diff_sha256'], 'external_inputs': len(external)}))


if __name__ == '__main__':
    main()
