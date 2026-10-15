"""Bounded plane-only cold candidate; never dismiss native assertions."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / '.runtime/item-edge-r19-candidate-control-v3'
CONTROL.mkdir(exist_ok=False)
for name in ('candidate.json', 'launch-sources.json'):
    shutil.copy2(ROOT / '.runtime/item-edge-r19-candidate-control' / name, CONTROL / name)
sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts')]
from item_sprite_capture_contract import snapshot_sources, snapshot_digest
from check_native_dialogs import assertion_dialogs
from audit_chest_occupied_runtime import process_snapshot
from _session import process_identity
from mcdk import Client, return_value


def save(name, value):
    (CONTROL / name).write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


freeze = json.loads((CONTROL / 'launch-sources.json').read_bytes())
assert snapshot_digest(snapshot_sources(Path(freeze['project']))) == freeze['sha256']
prior = json.loads(Path('C:/Users/Happy2018new/.pyreact-debug/instances/856331b7cc0e4e6aa6a07108b5214842/session.json').read_bytes())
assert prior['state'] == 'stopped'
assert process_identity(prior['game_pid']) != prior['game_identity']
assert process_identity(prior['mcdk_pid']) != prior['mcdk_identity']
guard = prior['noactivation']
instances = ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'
command = [sys.executable, '-X', 'utf8', str(instances), 'start', '--project', freeze['project'],
    '--owner', 'item-plane-r19', '--name', 'item-plane-r19-v3', '--port', '19370', '--wait', '180', '--preset', 'ui',
    '--mcdk', guard['mcdk']['path'], '--noactivate-mcdk-sha256', guard['mcdk']['sha256'],
    '--noactivate-dll', guard['dll']['path'], '--noactivate-sha256', guard['dll']['sha256']]
environment = dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1')
start = subprocess.run(command, cwd=str(ROOT), env=environment, capture_output=True, text=True, encoding='utf-8', timeout=300)
(CONTROL / 'start.stdout.txt').write_text(start.stdout, encoding='utf-8')
(CONTROL / 'start.stderr.txt').write_text(start.stderr, encoding='utf-8')
assert start.returncode == 0, 'Startup failed; inspect ignored logs'
session = json.loads(start.stdout)
save('ready-summary.json', {key: session.get(key) for key in
    ('id', 'owner', 'state', 'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')})
environment.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=session['owner'], MCDEV_MCP_URL=session['mcp_url'])
os.environ.update(environment)
samples = []


def audit(label):
    assert process_identity(session['game_pid']) == session['game_identity'], 'Owned game identity changed'
    assert process_identity(session['mcdk_pid']) == session['mcdk_identity'], 'Owned MCDK identity changed'
    sample = dict(process_snapshot(session['game_pid']), stage=label)
    samples.append(sample)
    save('process-samples.json', samples)
    assert sample['handles'] < 250000, 'Owned game reached handle cap'
    dialogs = [item for item in assertion_dialogs() if item['pid'] == session['game_pid']]
    if dialogs:
        save('native-assertions.json', {'stage': label, 'dialogs': dialogs})
        raise RuntimeError('Owned native assertion; retained read-only child-window text')


try:
    audit('ready')
    deadline = time.monotonic() + 90
    with Client(timeout=15) as client:
        ready = False
        while time.monotonic() < deadline and not ready:
            audit('business-ready')
            value = client.call('execute_code', {'is_client': True, 'direct_return': True, 'code':
                "import mod.client.extraClientApi as api\nowner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')\n"
                "_result=bool(owner is not None and owner.session is not None and owner.bridge is not None)"})
            ready = return_value(value) is True
            if not ready:
                time.sleep(.5)
        assert ready, 'Workspace not initialized'
    for index in range(10):
        audit('post-ready-' + str(index))
        time.sleep(1)
    wgc = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
    for label, angle in [('front', 0), ('side', 45)]:
        audit(label + '-before')
        output = ROOT / '.runtime' / ('item-plane-r19-' + label + '-v3')
        command = [sys.executable, '-X', 'utf8', str(ROOT / 'tools/run_visible_items_r16.py'),
            '--session', session['session_file'], '--owner', session['owner'], '--output', str(output), '--wgc', str(wgc),
            '--skip-closeup', '--orientation-matrix', '--orientation-cases', 'frame_f2_r1', '--icons-only',
            '--editor-zoom', '5', '--near-distance', '3', '--maximum-handles', '250000', '--native-target-plain',
            '--view-angle', str(angle), '--candidate-geometry', str(CONTROL / 'candidate.json')]
        save(label + '-command.json', command)
        with (CONTROL / (label + '.stdout.txt')).open('w', encoding='utf-8') as stdout, \
                (CONTROL / (label + '.stderr.txt')).open('w', encoding='utf-8') as stderr:
            child = subprocess.Popen(command, cwd=str(ROOT), env=environment, stdout=stdout, stderr=stderr)
            deadline = time.monotonic() + 1800
            try:
                while child.poll() is None:
                    audit(label + '-running')
                    assert time.monotonic() < deadline, 'Bounded capture timed out'
                    time.sleep(1)
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=10)
        assert child.returncode == 0, label + ' failed; inspect ignored logs'
        report = json.loads((output / 'report.json').read_bytes())
        print(json.dumps({'stage': label, 'completed': report.get('completed'),
            'source_unchanged': report.get('source_unchanged'), 'cleanup_errors': report.get('cleanup_errors'),
            'error_present': bool(report.get('error'))}), flush=True)
        assert report['completed'] and report['source_unchanged'] and not report['cleanup_errors'], label + ' incomplete'
finally:
    for force in (False, True):
        stop_command = [sys.executable, '-X', 'utf8', str(instances), 'stop', '--session', session['session_file'], '--owner', session['owner']]
        if force:
            stop_command.append('--force')
        stopped = subprocess.run(stop_command, cwd=str(ROOT), capture_output=True, text=True, encoding='utf-8', timeout=50)
        suffix = 'force' if force else 'normal'
        (CONTROL / ('stop-' + suffix + '.stdout.txt')).write_text(stopped.stdout, encoding='utf-8')
        (CONTROL / ('stop-' + suffix + '.stderr.txt')).write_text(stopped.stderr, encoding='utf-8')
        if stopped.returncode == 0:
            break
    state = json.loads(Path(session['session_file']).read_bytes())
    print(json.dumps({'stop_returncode': stopped.returncode, 'state': state['state'], 'owner': state['owner'],
        'game_alive': process_identity(state['game_pid']) == state['game_identity'],
        'mcdk_alive': process_identity(state['mcdk_pid']) == state['mcdk_identity']}), flush=True)
