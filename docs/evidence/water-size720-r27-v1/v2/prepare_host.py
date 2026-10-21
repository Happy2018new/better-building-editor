"""Prepare one private R27 size diagnostic; never edit frozen product source."""
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
OLD = ROOT / '.runtime/round-20261021/water-final41-r25-v6'
OWNER = 'water-r27-final41-size720-v2'
DEADLINE = '2026-10-21T23:45:00+00:00'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, data):
    with (WORK / name).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(data, stream, indent=2)
        stream.write('\n')


def main():
    assert not (WORK / 'launch').exists()
    names = ('candidate_bootstrap.py', 'bootstrap_payload.py', 'guard_policy.py',
             'modal_guard.py', 'launch_r25.py', 'start_assert_watch.py',
             'watch_handles.py', 'run_candidate_bootstrap.py',
             'retire_bootstrap_marker.py')
    changes = []
    for name in names:
        raw = (OLD / name).read_bytes()
        if name != 'candidate_bootstrap.py':
            raw = raw.replace(b'water-r25-final41-editor-v6', OWNER.encode('ascii'))
            raw = raw.replace(b'prelaunch-host-binding-v6.json', b'prelaunch-host-binding-r27.json')
        (WORK / name).write_bytes(raw)
        if raw != (OLD / name).read_bytes():
            changes.extend(difflib.unified_diff((OLD / name).read_text('utf-8').splitlines(True),
                           raw.decode('utf-8').splitlines(True), fromfile='v6/' + name, tofile='r27/' + name))
    trace_old = ROOT / '.runtime/round-20261021/trace-lifetime-v2/experiment-isolated-v1'
    for name, original in (('run_camera.py', trace_old / 'run_camera.py'),
                           ('run_diagnostic.py', trace_old / 'run_product_v2_stages_v3.py'),
                           ('run_size_group.py', OLD / 'run_editor_group.py')):
        raw = original.read_bytes()
        raw = raw.replace(b'parents[4]', b'parents[3]')
        raw = raw.replace(b'water-r25-final-v1', b'water-r25-final41-v2')
        raw = raw.replace(b'water-r25-lifetime-isolated-v2', OWNER.encode('ascii'))
        raw = raw.replace(b'water-r25-final41-editor-v6', OWNER.encode('ascii'))
        raw = raw.replace(b"MCDEV_ALLOW_USER_FOREGROUND='1'", b"MCDEV_ALLOW_USER_FOREGROUND='0'")
        raw = raw.replace(b'2026-10-21T06:55:00+00:00', b'2026-10-21T23:30:00+00:00')
        raw = raw.replace(b'diagnostic-east-editor-v2', b'diagnostic-east-editor-size720-v1')
        if name == 'run_size_group.py':
            before = b"        command('G', 'run_product_v2_stages.py', ('G',))\r\n        assert datetime.now(timezone.utc) < datetime.fromisoformat('2026-10-21T23:30:00+00:00'), 'Do not start a long batch after cutoff'\r\n        command('F-editor', 'run_product_v2_f_editor.py')"
            assert before in raw
            raw = raw.replace(before, b"        command('resize', 'resize_background.py')\r\n        command('camera', 'run_camera.py', ('camera',))\r\n        command('A', 'run_diagnostic.py', ('A',))")
            raw = raw.replace(b"'final41-editor'", b"'final41-size720-diagnostic'")
        (WORK / name).write_bytes(raw)
    binding = json.loads((OLD / 'final-source-binding-v1.json').read_bytes())
    binding.update(owner=OWNER, guard_deadline_utc=DEADLINE,
                   bootstrap_receipt_marker='_water_r27_size720_bootstrap_v2',
                   new_source_bytes_created=False, previous_host_binding_sha256=sha(OLD / 'prelaunch-host-binding-v6.json'))
    write('final-source-binding-v1.json', binding)
    (WORK / 'product-v2-launch-inputs.json').write_bytes((OLD / 'product-v2-launch-inputs.json').read_bytes())
    write('stage-r25.json', {'schema': 1, 'round': 'R27', 'owner': OWNER,
          'diagnostic_only': True, 'formal_A_accepted': False,
          'single_variable': 'actual client area 1994x1105 -> 1280x720',
          'source_contract_sha256': binding['source_contract_sha256'],
          'preparation_ms': 1500, 'measurement_ms': 3200, 'gap_limit_ms': 150,
          'cases': ['flow_east'], 'routes': ['editor'], 'manual_closures_added': 0,
          'no_long_step_after_utc': '2026-10-21T23:30:00+00:00',
          'cleanup_deadline_utc': DEADLINE, 'source_scope_is_not_transitive_closure': True})
    project = Path(binding['project'])
    for key in ('source_sha256', 'auxiliary_sha256'):
        for name, expected in binding[key].items():
            assert sha(project / name) == expected, name
    assert sha(Path(binding['archive']['path'])) == binding['archive']['sha256']
    assert sha(WORK / 'candidate_bootstrap.py') == binding['bootstrap_sha256']
    assert sha(project / binding['qualification_path']) == binding['qualification_sha256']
    previous = json.loads((OLD / 'prelaunch-host-binding-v6.json').read_bytes())
    external = {name: sha(ROOT / name) for name in previous['external_host_sha256']}
    for name in ('.agents/skills/pyreact-debugging/scripts/resize_window.py',
                 'tools/capture_native_burst.py', 'tools/capture_native_burst_deferred.py',
                 'tools/capture_native_burst_startup.py'):
        external[name] = sha(ROOT / name)
    diagnostic = ROOT / '.runtime/round-20261021/trace-lifetime-v2/host-contract-v1.json'
    contract = json.loads(diagnostic.read_bytes())
    assert all(sha(Path(name)) == expected for name, expected in contract['sources'].items())
    assert sha(Path(contract['binary']['path'])) == contract['binary']['sha256']
    for path in WORK.glob('*.py'):
        ast.parse(path.read_bytes(), filename=str(path))
    # The same original core plus the rebound marker must still be Python 2 syntax.
    sys.path.insert(0, str(WORK))
    from bootstrap_payload import dispatch_code, readback_code
    payload = dispatch_code((WORK / 'candidate_bootstrap.py').read_text('utf-8'), binding)
    (WORK / 'dispatched-payload.py').write_text(payload, encoding='utf-8')
    py2 = subprocess.run(['D:/Program/Python27/python.exe', '-B', '-c',
        'import sys;compile(open(sys.argv[1],"rb").read(),sys.argv[1],"exec")',
        str(WORK / 'dispatched-payload.py')], capture_output=True, text=True)
    py2.check_returncode()
    write('prelaunch-host-binding-r27.json', {'schema': 1,
          'source_binding_sha256': sha(WORK / 'final-source-binding-v1.json'),
          'host_sha256': {p.name: sha(p) for p in sorted(WORK.glob('*.py'))} |
                         {name: sha(WORK / name) for name in ('product-v2-launch-inputs.json', 'stage-r25.json')},
          'external_host_sha256': external,
          'diagnostic_contract_sha256': sha(diagnostic),
          'MC_started': False, 'frozen_at_utc': datetime.now(timezone.utc).isoformat()})
    (WORK / 'v6-to-r27-host.patch').write_text(''.join(changes), encoding='utf-8')
    write('prelaunch-review-r27.json', {'schema': 1, 'passed': True, 'owner': OWNER,
          'source_files': len(binding['source_sha256']), 'auxiliary_files': len(binding['auxiliary_sha256']),
          'original_core_sha256': sha(WORK / 'candidate_bootstrap.py'),
          'source_contract_sha256': binding['source_contract_sha256'],
          'binding_sha256': sha(WORK / 'prelaunch-host-binding-r27.json'),
          'python2_compile_exit': py2.returncode, 'manual_closures_added': 0,
          'source_unchanged': True, 'default_admission_performed': False,
          'diagnostic_only': True, 'MC_started': False})
    print(json.dumps({'passed': True, 'owner': OWNER,
                      'review_sha256': sha(WORK / 'prelaunch-review-r27.json')}))


if __name__ == '__main__':
    main()
