"""Bounded owner CPU/wall profiler observations over identical editor cases."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r20-state-v7/profiler-cpu-wall-v1'
OWNER = 'water-r20-v7'
assert not OUTPUT.exists()
OUTPUT.mkdir()
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe
from _session import load_session

binding_path = json.loads((OUTPUT.parent / 'start.json').read_bytes())['session_file']
os.environ.update(MCDEV_SESSION_FILE=binding_path, MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
binding = load_session(binding_path, OWNER, live=True)
assert Path(binding['project']).resolve() == PROJECT.resolve()
before = probe.snapshot_sources(PROJECT)
target = OUTPUT / 'report.json'
report = {'schema': 1, 'diagnostic_only': True, 'production_qualified': False,
    'completed': False, 'restored': False, 'cleanup_errors': [], 'screenshots': [],
    'window_actions': [], 'source_contract_sha256': probe.snapshot_digest(before),
    'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'profiles': {},
    'session_binding': {key: binding[key] for key in ('id', 'owner', 'game_pid', 'game_identity', 'session_file')}}


def save():
    probe.base.write(target, report)


with probe.base.Client(timeout=45) as client:
    check = probe.blueprints.BlueprintCheck(client, target, 45.)
    installed = False
    active_job = None
    try:
        check.run(probe.blueprints.INSTALL_PROBE)
        installed = True
        check.run(probe.PROFILE % (True, True))
        check.run('owner.open_workspace()\n_result=True')
        check.wait('open editor', lambda row: row['open'] and not row['transition'], check.navigation)
        report['query_help'] = client.call('mc_profiler', {'op': '/help', 'args': {'topic': '/query'}})
        for clock in ('cpu', 'wall'):
            phase = report['profiles'][clock] = {'rows': [], 'started': time.time()}
            check.run(probe.LOAD % (('pool','wet',(35.,25.,4.6)),))
            check.wait('baseline pool', probe.stable_scene_predicate((35.,25.,4.6),(0.,0.),probe.workspace.scene_ready),
                lambda: check.run(probe.SCENE_STATE))
            phase['metrics_before'] = probe.workspace.transport.metrics(binding_path, OWNER)
            phase['start'] = client.call('mc_profiler', {'op': '/start', 'args': {
                'kind': 'python.cpu', 'target': 'client', 'clock': clock,
                'duration_seconds': 30, 'storage': 'disk'}})
            structured = phase['start']['structuredContent']
            active_job = structured['job']['id']
            phase['job_id'] = active_job
            save()
            for case in ('pool','flow_west','wet_oak_slab'):
                for control in ('wet','dry'):
                    check.run(probe.LOAD % ((case,control,(35.,25.,4.6)),))
                    ready = check.wait(clock + ' ' + case + ' ' + control,
                        probe.stable_scene_predicate((35.,25.,4.6),(0.,0.),probe.workspace.scene_ready),
                        lambda: check.run(probe.SCENE_STATE))
                    phase['rows'].append({'case': case, 'control': control,
                        'groups': len(ready.get('liquid_groups', ())), 'time': time.time()})
                    save()
            deadline = time.monotonic() + 60
            while True:
                phase['status'] = client.call('mc_profiler', {'op': '/status', 'args': {'job_id': active_job}})
                state = phase['status']['structuredContent']['job']['state']
                save()
                if state not in ('pending','starting','running','stopping','finalizing','cleanup_pending'):
                    break
                assert time.monotonic() < deadline, phase['status']
                time.sleep(.5)
            phase['hotspots'] = client.call('mc_profiler', {'op': '/query', 'args': {
                'job_id': active_job, 'view': 'hotspots', 'limit': 50}})
            phase['export'] = client.call('mc_profiler', {'op': '/export', 'args': {
                'job_id': active_job, 'format': 'markdown'}})
            phase['metrics_after'] = probe.workspace.transport.metrics(binding_path, OWNER)
            phase['ended'] = time.time()
            active_job = None
            save()
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if active_job:
            try:
                report['profiler_stop'] = client.call('mc_profiler', {'op': '/stop', 'args': {'job_id': active_job}})
            except Exception:
                report['cleanup_errors'].append({'phase': 'profiler', 'error': traceback.format_exc()})
        if installed:
            for label, code in (('close', 'if navigator.top is not None:navigator.pop()\n_result=True'),
                                ('workspace', probe.RESTORE_PROFILE)):
                try:
                    report[label + '_restore'] = check.run(code)
                except Exception:
                    report['cleanup_errors'].append({'phase': label, 'error': traceback.format_exc()})
        report['source_unchanged'] = before == probe.snapshot_sources(PROJECT)
        report['restored'] = not report['cleanup_errors'] and report['source_unchanged']
        save()
print(json.dumps({key: report.get(key) for key in ('completed','restored','source_unchanged','error')}))
raise SystemExit(0 if report['completed'] and report['restored'] else 1)
