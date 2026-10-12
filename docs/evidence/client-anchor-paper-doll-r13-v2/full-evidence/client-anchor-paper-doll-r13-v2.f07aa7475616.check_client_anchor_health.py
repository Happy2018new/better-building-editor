"""One bounded owner health check after anchor cleanup; no fixtures or input."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from run_client_anchor_paper_doll import ROOT, SESSION, ARTIFACTS, OWNER, EVIDENCE_PREFIX, \
    BUNDLE, absolute_http_open, save
from session_pack_stage import SessionPackStage, digest, require
from mcdk import Client, return_value


START_ENV = 'MCDEV_ANCHOR_HEALTH_STARTED_MONOTONIC'
NORMAL_SECONDS, CLEANUP_SECONDS, OUTER_SECONDS = 20., 30., 40.
IDENTITY = '''import json,os,sys,time
import mod.%s.extra%sApi as api
_result=json.dumps({'runtime':api.GetMinecraftVersion(),'pid':os.getpid(),
 'token':getattr(sys,'_pyreact_mcdk_session',None),'now':time.time()})
'''
START = '''import json,sys,time
import mod.server.extraServerApi as api
marker=%r
assert not hasattr(sys,marker)
state={'nonce':%r,'started':time.time(),'callbacks':[],'attempted':[]}
setattr(sys,marker,state)
game=api.GetEngineCompFactory().CreateGame(api.GetLevelId())
for delay in (.2,.4):
 state['attempted'].append(delay)
 game.AddTimer(delay,lambda current=state:current['callbacks'].append(time.time()))
_result=json.dumps(state)
'''
STOP = '''import json,sys,time
marker=%r
state=getattr(sys,marker,None)
_result=json.dumps({'owned':False,'restored':True})
if state is not None:
 assert state['nonce']==%r
 observed=dict(state)
 observed.update(owned=True,now=time.time())
 delattr(sys,marker)
 observed['restored']=not hasattr(sys,marker)
 _result=json.dumps(observed)
'''


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def child(started):
    output = ARTIFACTS / (EVIDENCE_PREFIX + '.post-restoration-health.json')
    require(not output.exists(), 'Preserve existing anchor health evidence')
    nonce = json.loads((BUNDLE / 'plan.json').read_bytes())['nonce']
    marker = '_client_anchor_health_' + nonce
    report = {'schema': 1, 'owner': OWNER, 'session_id': SESSION.name,
              'scope': 'Fresh owner client/server clocks and two owned server timer callbacks',
              'started_at': timestamp(), 'source_sha256': digest(Path(__file__)),
              'normal_deadline_monotonic': started + NORMAL_SECONDS,
              'cleanup_deadline_monotonic': started + CLEANUP_SECONDS,
              'outer_deadline_monotonic': started + OUTER_SECONDS,
              'requests': [], 'network_requests': [], 'errors': [], 'cleanup_errors': [],
              'timer_start_attempted': False, 'timer_cleanup_verified': False,
              'completed': False, 'passed': False, 'fixture_mutation_attempted': False,
              'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
              'enchantment_glint_accepted': False}
    cleanup = False

    def preserve():
        try:
            save(output, report)
        except Exception as error:
            report['cleanup_errors'].append('report persistence: ' + repr(error))
            if not cleanup:
                raise

    preserve()
    guard = SessionPackStage(ARTIFACTS, ARTIFACTS / (EVIDENCE_PREFIX + '.unused-health-stage-journal.json'))

    class DeadlineOpener:
        def __init__(self, underlying, client):
            self.underlying, self.client = underlying, client

        def open(self, request, timeout=None):
            deadline = started + OUTER_SECONDS if request.get_method() == 'DELETE' else self.client.deadline
            row = {'http_method': request.get_method(), 'started_at': timestamp()}
            report['network_requests'].append(row)
            preserve()

            def finished(error=None):
                if error is not None:
                    row['error'] = repr(error)
                row['finished_at'] = timestamp()
                preserve()

            try:
                remaining = deadline - time.monotonic()
                require(remaining > 0, 'Actual health network deadline exhausted')
                row['timeout_seconds'] = min(5., remaining, timeout if timeout is not None else 5.)
                row['deadline_monotonic'] = min(deadline, time.monotonic() + row['timeout_seconds'])
                response = absolute_http_open(self.underlying, request, row['timeout_seconds'],
                                              row['deadline_monotonic'], time.monotonic, finished)
                row['status'] = getattr(response, 'status', None)
                return response
            except Exception as error:
                finished(error)
                raise

    class RecordedClient(Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.deadline = started + NORMAL_SECONDS
            self.opener = DeadlineOpener(self.opener, self)

        def _post(self, method, params=None, notification=False):
            request = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
            if not notification:
                request['id'] = self.counter + 1
            row = {'request': request, 'started_at': timestamp()}
            report['requests'].append(row)
            preserve()
            previous_timeout = self.timeout
            try:
                require(time.monotonic() < self.deadline, 'Health RPC deadline exhausted')
                if method == 'tools/call':
                    row['background_before_request'] = guard.guard()
                    row['physical_window'] = guard.window
                self.timeout = min(previous_timeout, 5., self.deadline - time.monotonic())
                require(self.timeout > 0, 'Health guard exhausted dispatch deadline')
                row['response'] = super()._post(method, params, notification)
                return row['response']
            except Exception as error:
                row['error'] = repr(error)
                raise
            finally:
                self.timeout = previous_timeout
                row['finished_at'] = timestamp()
                preserve()

    client = None

    def execute(code, is_client):
        value = return_value(client.call('execute_code', {'code': code, 'is_client': is_client, 'direct_return': True}))
        return json.loads(value) if isinstance(value, str) else value

    try:
        require(time.monotonic() < started + NORMAL_SECONDS, 'Health initialization deadline exhausted')
        report['background_before'] = guard.guard()
        guard.verify_pack(guard.source)
        client = RecordedClient(timeout=min(5., started + NORMAL_SECONDS - time.monotonic()))
        client.__enter__()
        report['binding_verified'] = True
        for is_client, module, api_name in ((True, 'client', 'Client'), (False, 'server', 'Server')):
            value = execute(IDENTITY % (module, api_name), is_client)
            require(value['pid'] == client.binding['game_pid'] and value['token'] == client.binding['token'],
                    'Fresh health runtime identity changed')
            report[module + '_before'] = value
            preserve()
        report['timer_start_attempted'] = True
        preserve()
        report['timer_start'] = execute(START % (marker, nonce), False)
        require(time.monotonic() + .8 < client.deadline, 'No health callback observation budget')
        time.sleep(.8)
        for is_client, module, api_name in ((True, 'client', 'Client'), (False, 'server', 'Server')):
            value = execute(IDENTITY % (module, api_name), is_client)
            require(value['now'] > report[module + '_before']['now'] and
                    value['pid'] == client.binding['game_pid'] and value['token'] == client.binding['token'],
                    'Fresh health clock did not advance with the same runtime identity')
            report[module + '_after'] = value
            preserve()
        report['completed'] = True
    except Exception as error:
        report['errors'].append(repr(error))
    finally:
        cleanup = True
        if client is not None:
            client.deadline = started + CLEANUP_SECONDS
            if report['timer_start_attempted']:
                report['timer_stop_attempted'] = True
                preserve()
                try:
                    stop = report['timer_stop'] = execute(STOP % (marker, nonce), False)
                    report['timer_cleanup_verified'] = stop['restored']
                    require(stop['owned'] and len(stop['callbacks']) == 2 and
                            stop['started'] < stop['callbacks'][0] < stop['callbacks'][1] <= stop['now'],
                            'Fresh health timer callbacks were incomplete')
                except Exception as error:
                    report['cleanup_errors'].append(repr(error))
            try:
                client.close()
            except Exception as error:
                report['cleanup_errors'].append('connection close: ' + repr(error))
        report['passed'] = report['completed'] and report['timer_cleanup_verified'] and not report['errors'] and not report['cleanup_errors']
        report['elapsed_seconds'] = time.monotonic() - started
        report['finished_at'] = timestamp()
        preserve()
        if report['cleanup_errors']:
            report['passed'] = False
    print(json.dumps({'passed': report['passed'], 'timer_cleanup_verified': report['timer_cleanup_verified'],
                      'elapsed_seconds': report['elapsed_seconds']}))
    return 0 if report['passed'] else 1


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    os.environ['MCDEV_SESSION_FILE'] = str(SESSION / 'session.json')
    os.environ['MCDEV_OWNER'] = OWNER
    if args.execute_child:
        require(START_ENV in os.environ, 'Health supervisor is required')
        started = float(os.environ[START_ENV])
        require(0 <= time.monotonic() - started < OUTER_SECONDS, 'Stale health supervisor')
        return child(started)
    output = ARTIFACTS / (EVIDENCE_PREFIX + '.health-supervision.json')
    require(not output.exists(), 'Preserve existing anchor health supervision')
    report = {'schema': 1, 'attempts': 1, 'outer_limit_seconds': OUTER_SECONDS,
              'started_at': timestamp(), 'completed': False, 'timed_out': False, 'no_retry': True}
    save(output, report)
    environment = dict(os.environ)
    environment[START_ENV] = repr(started)
    try:
        result = subprocess.run([sys.executable, '-X', 'utf8', str(Path(__file__)), '--execute-child'],
                                cwd=str(ROOT), env=environment, capture_output=True, text=True,
                                encoding='utf-8', timeout=started + OUTER_SECONDS - time.monotonic(),
                                creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, completed=True)
    except subprocess.TimeoutExpired as error:
        report.update(timed_out=True, error=repr(error), timer_cleanup_verified=False)
    finally:
        report['elapsed_seconds'] = time.monotonic() - started
        report['finished_at'] = timestamp()
        save(output, report)
    print(json.dumps(report))
    return 0 if report.get('returncode') == 0 and not report['timed_out'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
