"""Owner-bound, supervised one-shot client anchor probe; default never dispatches."""
import argparse
from datetime import datetime, timezone
import importlib.util
import http.client
import json
import os
from pathlib import Path
import subprocess
import socket
import sys
import threading
import time
import urllib.request

from run_frame_translation import ROOT, ENTITIES, SESSION, ARTIFACTS, OWNER, WGC_EXE, \
    EXE_SHA256, WRAPPER_SHA256, source_config_hashes, save
from run_native_item_paper_doll import HELPER_SHA256, GUARD_SHA256
from session_pack_stage import SessionPackStage, digest, require, file_identity
from mcdk import Client
from verify_sign_visuals import SignCheck


PROBE_SHA256 = '2d93d4314e49dadc4bbe6e93b40c9b6c1e7e0ec5ab7b0c3304072f6ba8366a85'
PLAN_SHA256 = '5a7e328635d1f3f5c83f8f2ed08d2ed5ba56e3aed8526943d3b0f27845126b05'
BUNDLE = ENTITIES / '.runtime/client-anchor-paper-doll-r13-final-v2'
EVIDENCE_PREFIX = 'client-anchor-paper-doll-r13-v2'
NORMAL_SECONDS = 90.
CLEANUP_SECONDS = 120.
OUTER_SECONDS = 150.
START_ENV = 'MCDEV_ANCHOR_OWNER_STARTED_MONOTONIC'


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def absolute_http_open(underlying, request, timeout, deadline, clock, finished):
    """Abort this HTTP connection at its absolute deadline, including streamed reads."""
    deadline = min(deadline, clock() + timeout)
    state = {'sockets': [], 'expired': False, 'finished': False}

    def abort():
        state['expired'] = True
        for connection in list(state['sockets']):
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    timer = threading.Timer(max(0., deadline - clock()), abort)
    timer.daemon = True

    def finalize(error=None):
        if state['finished']:
            return
        state['finished'] = True
        timer.cancel()
        for connection in state['sockets']:
            connection.close()
        finished(error)

    class Connection(http.client.HTTPConnection):
        def connect(self):
            super().connect()
            # urllib transfers the original socket to a file; keep a scoped
            # duplicate so deadline shutdown also interrupts header/body reads.
            state['sockets'].append(self.sock.dup())
            if state['expired'] or clock() >= deadline:
                abort()
                self.close()
                raise TimeoutError('HTTP connection exceeded its absolute deadline')

    class Handler(urllib.request.HTTPHandler):
        def http_open(self, target):
            return self.do_open(Connection, target)

    class Response:
        def __init__(self, response):
            self.response = response

        def __getattr__(self, name):
            return getattr(self.response, name)

        def __enter__(self):
            return self

        def read(self, *args, **kwargs):
            try:
                require(not state['expired'] and clock() < deadline, 'HTTP response read deadline exhausted')
                payload = self.response.read(*args, **kwargs)
                require(not state['expired'] and clock() < deadline, 'Late HTTP response rejected')
                return payload
            except Exception as error:
                finalize(error)
                raise

        def __exit__(self, error_type, error, traceback):
            try:
                self.response.close()
            finally:
                finalize(error)

    require(request.full_url.startswith('http://127.0.0.1:'), 'Only the owner local HTTP endpoint is permitted')
    timer.start()
    try:
        response = urllib.request.build_opener(urllib.request.ProxyHandler({}), Handler()).open(request, timeout=timeout)
        require(not state['expired'] and clock() < deadline, 'Late HTTP response headers rejected')
        return Response(response)
    except Exception as error:
        finalize(error)
        raise


def load_probe():
    source = ENTITIES / 'tools/probe_client_anchor_paper_doll.py'
    require(digest(source) == PROBE_SHA256, 'Reviewed client anchor probe changed')
    require(digest(BUNDLE / 'plan.json') == PLAN_SHA256, 'Reviewed client anchor plan changed')
    require(digest(ROOT / '.runtime/frame-baseline-plan-r11/session_pack_stage.py') == GUARD_SHA256,
            'Reviewed owner guard changed')
    require(digest(ROOT / 'tools/capture_native_window.py') == WRAPPER_SHA256, 'Native capture wrapper changed')
    require(digest(WGC_EXE) == EXE_SHA256, 'Native capture executable changed')
    sys.path.append(str(ENTITIES / 'tools'))
    for name, expected in HELPER_SHA256.items():
        copies = [(root / 'tools' / (name + '.py')).resolve() for root in (ROOT, ENTITIES)]
        for path in copies:
            require(digest(path) == expected, 'Reviewed native pixel helper changed: ' + str(path))
        module = importlib.import_module(name)
        actual = Path(module.__file__).resolve()
        require(actual in copies and digest(actual) == expected, 'Actual pixel helper differs: ' + str(actual))
    specification = importlib.util.spec_from_file_location('reviewed_client_anchor_probe', source)
    probe = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(probe)
    verify_loaded_resources(probe, BUNDLE)
    return probe, source


def verify_loaded_resources(probe, bundle):
    session = json.loads((SESSION / 'session.json').read_bytes())
    require(session['id'] == SESSION.name and session['owner'] == OWNER,
            'Anchor resource lookup session changed')
    # Keep the loaded logical lookup spelling; the packaged-app physical path
    # exceeds legacy path limits. File handles below retain physical identity.
    world = Path(session['world_path']).absolute()
    appdata = SESSION / 'appdata/MinecraftPE_Netease/games/com.netease'
    plan = json.loads((bundle / 'plan.json').read_bytes())
    frozen = {row['path']: row for row in plan['files']}
    packs, resources = {}, {}
    for pack in ('behavior_pack', 'resource_pack'):
        source = (ROOT / pack).resolve(strict=True)
        manifest = source / 'manifest.json'
        header = json.loads(manifest.read_bytes())['header']
        pack_id, version = header['uuid'], header['version']
        world_manifest = world / ('world_' + pack + 's.json')
        selected = [row for row in json.loads(world_manifest.read_bytes()) if row['pack_id'] == pack_id]
        require(len(selected) == 1 and selected[0]['version'] == version,
                'Anchor pack is absent, duplicated, or version changed: ' + pack)
        lookup_roots = {}
        for location, base in (('world', world), ('appdata', appdata)):
            candidates = []
            for candidate in (base / (pack + 's')).iterdir():
                candidate_manifest = candidate / 'manifest.json'
                if candidate_manifest.is_file() and json.loads(candidate_manifest.read_bytes())['header']['uuid'] == pack_id:
                    candidates.append(candidate)
            require(len(candidates) == 1, 'Anchor loaded pack lookup is absent or ambiguous: ' + location + '/' + pack)
            lookup = candidates[0]
            require(lookup.resolve(strict=True) == source and digest(lookup / 'manifest.json') == digest(manifest),
                    'Anchor loaded pack lookup resolves to different source: ' + str(lookup))
            lookup_roots[location] = lookup
        packs[pack] = {'source': str(source), 'manifest_sha256': digest(manifest),
                       'world_manifest': str(world_manifest), 'world_manifest_sha256': digest(world_manifest),
                       'lookup_roots': {key: str(value) for key, value in lookup_roots.items()}}
        for name, relative in probe.RESOURCE_FILES.items():
            relative = Path(relative)
            if relative.parts[0] != pack:
                continue
            actual = ROOT / relative
            row = frozen[name]
            require(actual.stat().st_size == row['bytes'] and digest(actual) == row['sha256'] and
                    digest(bundle / name) == row['sha256'], 'Reviewed anchor resource changed: ' + name)
            lookups = {}
            for location, lookup in lookup_roots.items():
                path = lookup / Path(*relative.parts[1:])
                require(path.resolve(strict=True) == actual.resolve(strict=True) and digest(path) == row['sha256'],
                        'Loaded anchor resource differs: ' + str(path))
                lookups[location] = {'path': str(path), 'identity': file_identity(path), 'sha256': digest(path)}
            resources[name] = {'source': str(actual), 'bytes': row['bytes'], 'sha256': row['sha256'], 'lookups': lookups}
    require(set(resources) == set(probe.RESOURCE_FILES), 'Anchor resource verification was incomplete')
    return {'world_identity': file_identity(world, directory=True), 'packs': packs, 'resources': resources}


def execute_once(probe, source, output, runtime_output, guard, started, clock=time.monotonic):
    normal_deadline = started + NORMAL_SECONDS
    cleanup_deadline = started + CLEANUP_SECONDS
    outer_deadline = started + OUTER_SECONDS
    report = {'schema': 1, 'scope': 'One finite client anchor root item and same-actor block body diagnostic',
              'owner': OWNER, 'session_id': SESSION.name, 'started_at': timestamp(),
              'source_sha256': digest(Path(__file__)), 'probe_sha256': digest(source),
              'plan_sha256': PLAN_SHA256, 'requests': [], 'network_requests': [],
              'errors': [], 'cleanup_errors': [], 'sdk_dispatch_attempted': False,
              'shader_or_pack_mutation_attempted': False, 'world_or_inventory_mutation_attempted': False,
              'player_position_mutation_attempted': False, 'completed': False, 'restored': False,
              'production_rendering_accepted': False, 'editor_frame_content_accepted': False,
              'enchantment_glint_accepted': False, 'source_and_config_before': source_config_hashes(),
              'owner_started_monotonic': started, 'normal_deadline_monotonic': normal_deadline,
              'cleanup_deadline_monotonic': cleanup_deadline, 'outer_deadline_monotonic': outer_deadline}
    save(output, report)

    class DeadlineOpener:
        def __init__(self, underlying, client):
            self.underlying, self.client = underlying, client

        def open(self, request, timeout=None):
            method = request.get_method()
            row = {'http_method': method, 'started_at': timestamp()}
            report['network_requests'].append(row)
            save(output, report)
            deadline = outer_deadline if method == 'DELETE' else self.client.frame_dispatch_deadline
            remaining = deadline - clock()

            def finished(error=None):
                if error is not None:
                    row['error'] = '%s: %s' % (type(error).__name__, error)
                row['finished_at'] = timestamp()
                save(output, report)

            try:
                require(remaining > 0, 'Actual network request deadline exhausted')
                row['timeout_seconds'] = min(10., remaining, timeout if timeout is not None else 10.)
                row['deadline_monotonic'] = min(deadline, clock() + row['timeout_seconds'])
                response = absolute_http_open(self.underlying, request, row['timeout_seconds'],
                                              row['deadline_monotonic'], clock, finished)
                row['status'] = getattr(response, 'status', None)
                return response
            except Exception as error:
                finished(error)
                raise

    class RecordedClient(Client):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.frame_dispatch_deadline = normal_deadline
            self.opener = DeadlineOpener(self.opener, self)

        def _post(self, method, params=None, notification=False):
            request = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
            if not notification:
                request['id'] = self.counter + 1
            row = {'request': request, 'started_at': timestamp()}
            report['requests'].append(row)
            save(output, report)
            previous_timeout = self.timeout
            try:
                require(clock() < self.frame_dispatch_deadline, 'Finite client anchor dispatch deadline exhausted')
                if method == 'tools/call':
                    row['background_before_request'] = guard.guard()
                    row['physical_window'] = guard.window
                self.timeout = min(previous_timeout, 10., self.frame_dispatch_deadline - clock())
                require(self.timeout > 0, 'Owner guard consumed client anchor dispatch budget')
                row['response'] = super()._post(method, params, notification)
                return row['response']
            except Exception as error:
                row['error'] = '%s: %s' % (type(error).__name__, error)
                raise
            finally:
                self.timeout = previous_timeout
                row['finished_at'] = timestamp()
                save(output, report)

    client = None
    try:
        require(clock() < normal_deadline, 'Client anchor initialization deadline exhausted')
        guard.guard()
        guard.verify_pack(guard.source)
        probe.preflight(BUNDLE, runtime_output)
        report['loaded_resources_before'] = verify_loaded_resources(probe, BUNDLE)
        require(clock() < normal_deadline, 'Client anchor preflight consumed normal budget')
        report['sdk_dispatch_attempted'] = True
        save(output, report)
        client = RecordedClient(timeout=min(10., normal_deadline - clock()))
        client.__enter__()
        report['runtime_binding_verified'] = True
        require(clock() < normal_deadline, 'Client anchor binding consumed normal budget')
        check = SignCheck(client, runtime_output, 10, native_resolution=True, background_only=True,
                          native_capture_helper=str(ROOT / 'tools/capture_native_window.py'))
        runtime = probe.execute_probe(BUNDLE, runtime_output, check, guard, cleanup_deadline)
        report['runtime_report'] = {'path': str(runtime_output), 'sha256': digest(runtime_output)}
        report['completed'], report['restored'] = runtime['completed'], runtime['restored']
        report['errors'].extend(runtime['errors'])
        report['cleanup_errors'].extend(runtime['cleanup_errors'])
    except Exception as error:
        report['errors'].append('%s: %s' % (type(error).__name__, error))
    finally:
        if client is not None:
            client.close()
        try:
            require(clock() < outer_deadline, 'Client anchor outer verification deadline exhausted')
            report['source_and_config_after'] = source_config_hashes()
            require(report['source_and_config_after'] == report['source_and_config_before'],
                    'Protected source config or session bytes changed')
            require(digest(source) == report['probe_sha256'], 'Client anchor probe changed during dispatch')
            guard.verify_pack(guard.source)
            report['loaded_resources_after'] = verify_loaded_resources(probe, BUNDLE)
            require(report['loaded_resources_after'] == report['loaded_resources_before'],
                    'Loaded anchor resource identity or bytes changed')
            require(clock() < outer_deadline, 'Protected source verification consumed outer budget')
            report['protected_sources_and_configs_unchanged'] = True
        except Exception as error:
            report['cleanup_errors'].append('protected source/config check: ' + repr(error))
        report['restored'] = report['restored'] and not report['cleanup_errors']
        report['finished_at'] = timestamp()
        report['native_elapsed_seconds'] = clock() - started
        save(output, report)
    return report


def supervise(output, started, clock=time.monotonic, run=subprocess.run):
    report = {'schema': 1, 'scope': 'One bounded owner helper subprocess', 'started_at': timestamp(),
              'owner_started_monotonic': started, 'outer_limit_seconds': OUTER_SECONDS,
              'attempts': 1, 'completed': False, 'timed_out': False,
              'no_automatic_retry': True, 'production_rendering_accepted': False}
    require(not output.exists(), 'Preserve existing client anchor supervisor evidence')
    save(output, report)
    environment = dict(os.environ)
    environment[START_ENV] = repr(started)
    try:
        remaining = started + OUTER_SECONDS - clock()
        require(remaining > 0, 'Client anchor supervisor preflight exhausted outer budget')
        result = run([sys.executable, '-X', 'utf8', str(Path(__file__)), '--execute-child'],
                     cwd=str(ROOT), env=environment, capture_output=True, text=True,
                     encoding='utf-8', timeout=remaining, creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr, completed=True)
    except subprocess.TimeoutExpired as error:
        report.update(timed_out=True, error=repr(error),
                      cleanup_verified=False, unresolved_runtime_requires_owner_review=True)
    except Exception as error:
        report['error'] = repr(error)
    finally:
        report['elapsed_seconds'] = clock() - started
        report['finished_at'] = timestamp()
        save(output, report)
    return report


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--execute-reviewed', action='store_true')
    mode.add_argument('--execute-child', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    output = ARTIFACTS / (EVIDENCE_PREFIX + '.orchestration.json')
    runtime_output = ARTIFACTS / (EVIDENCE_PREFIX + '.runtime.json')
    require(not output.exists() and not output.with_name(output.name + '.tmp').exists(),
            'Preserve existing one-shot client anchor evidence')
    os.environ['MCDEV_SESSION_FILE'] = str(SESSION / 'session.json')
    os.environ['MCDEV_OWNER'] = OWNER
    os.environ['MCDEV_NATIVE_CAPTURE_EXE'] = str(WGC_EXE)
    if args.execute_child:
        require(START_ENV in os.environ, 'Owner supervisor is required for child dispatch')
        started = float(os.environ[START_ENV])
        require(0 <= time.monotonic() - started < OUTER_SECONDS, 'Stale client anchor supervisor budget')
    if args.execute_reviewed:
        supervision = supervise(ARTIFACTS / (EVIDENCE_PREFIX + '.supervision.json'), started)
        print(json.dumps(supervision))
        return 0 if supervision.get('returncode') == 0 and not supervision['timed_out'] else 1
    probe, source = load_probe()
    probe.preflight(BUNDLE, runtime_output)
    guard = SessionPackStage(ARTIFACTS, ARTIFACTS / (EVIDENCE_PREFIX + '.unused-stage-journal.json'))
    if not args.execute_child:
        guard.guard()
        guard.verify_pack(guard.source)
        print(json.dumps({'validated': True, 'execute_requested': False,
                          'normal_seconds': NORMAL_SECONDS, 'cleanup_deadline_seconds': CLEANUP_SECONDS,
                          'outer_seconds': OUTER_SECONDS, 'shader_or_pack_mutation_attempted': False}))
        return 0
    report = execute_once(probe, source, output, runtime_output, guard, started)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'native_elapsed_seconds',
                                                 'production_rendering_accepted', 'enchantment_glint_accepted')}))
    return 0 if report['completed'] and report['restored'] and not report['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
