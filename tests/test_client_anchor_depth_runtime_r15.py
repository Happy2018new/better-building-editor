"""R15 failure cleanup, frozen submissions, native blank and offline controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
from types import ModuleType
import unittest
from unittest.mock import patch
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import execute_client_anchor_depth_candidate_r15 as runtime
import client_anchor_depth_owner_r15 as owner

ARCHIVE = ROOT / 'docs/evidence/client-anchor-world-ui-r14-v1/full-evidence'
ORIGINAL = json.loads((ARCHIVE / 'client-anchor-world-ui-r14-v1.runtime.json').read_bytes())
ANCHOR = runtime.dependencies()['probe_client_anchor_paper_doll']


def adapt_original():
    initial = deepcopy(ORIGINAL['initial'])
    initial['ui_params']['render_depth'] = -15
    frame = deepcopy(ORIGINAL['states']['ui_empty']['frames'][0])
    pending = [frame['tree']]
    while pending:
        node = pending.pop()
        pending.extend(node.get('children', []))
        if node.get('key') == 'native_item_probe_doll':
            node['props']['renderDepth'] = -15
    frame['status']['ui_params'] = initial['ui_params']
    frame['layout'] = runtime.layout_readback(ANCHOR, frame['tree'], frame['status'], initial)
    frame['paper_doll_roi'] = ANCHOR.base.frame_crop(frame['layout'], frame['capture']['size'], frame['marker_mapping'])
    return initial, frame


def attachment(state='bound'):
    value = {'id': 7, 'state': state, 'offset': [0., 0., 0.], 'rotation': [0., 0., 0.],
             'scale': 1., 'item_nonmutation': True}
    if state == 'removed':
        value.update(remove_attempted=True, remove_result=True)
    return value


def state_values(label, initial):
    submitted = dict(initial['ui_params'], render_depth=-50 if label == 'ui_plain_depth50' else -15)
    if label.startswith('ui_cow_'):
        del submitted['entity_id']
        submitted.update(entity_identifier='minecraft:cow', init_rot_y=60.)
    before = label in ('ui_cow_positive', 'ui_empty')
    plain = label in ('ui_plain_depth15', 'ui_plain_depth50', 'ui_plain_depth15_repeat')
    attachments = [] if before else [attachment('bound' if plain else 'removed')]
    native = {'attachments': attachments, 'native_item': None, 'actor': initial['actor'], 'control': label,
              'journal': [{'operation': 'RenderEntity:'+label, 'state': 'returned', 'value': True}]}
    if plain:
        native['native_item'] = {'id': 7, 'offset': [0., 0., 0.], 'rotation': [0., 0., 0.], 'scale': 1.}
    return submitted, attachments, native


class ScorerControls(unittest.TestCase):
    def test_layout_adapter_preserves_real_depth_and_rejects_old_prop(self):
        initial, frame = adapt_original()
        self.assertEqual(frame['layout']['props']['renderDepth'], -15)
        self.assertEqual(frame['status']['ui_params']['render_depth'], -15)
        original = deepcopy(ORIGINAL['states']['ui_empty']['frames'][0])
        with self.assertRaisesRegex(ValueError, 'props changed'):
            runtime.layout_readback(ANCHOR, original['tree'], original['status'], initial)

    def test_original_six_blank_ui_crops_cannot_pass_cow_gate(self):
        for label in ('ui_empty', 'ui_plain', 'ui_empty_restored'):
            for source in ORIGINAL['states'][label]['frames']:
                frame = deepcopy(source)
                record = frame['capture']
                record['path'] = str(ARCHIVE / Path(record['path']).name)
                record['capture']['path'] = record['path']
                frame['paper_doll_roi'] = ANCHOR.base.frame_crop(frame['layout'], record['size'], frame['marker_mapping'])
                self.assertEqual(runtime.cow_pixels(frame), 0)

    def test_submission_and_same_binding_tamper_are_rejected(self):
        initial, frame = adapt_original()
        label = 'ui_plain_depth50'
        submitted, attachments, native = state_values(label, initial)
        status = dict(frame['status'], control=label, last_submission=submitted, attachments=attachments, journal=native['journal'])
        self.assertEqual(runtime.validate_state(label, status, initial, native, 7), 7)
        status['last_submission']['render_depth'] = -15
        with self.assertRaises(ValueError):
            runtime.validate_state(label, status, initial, native, 7)
        status['last_submission']['render_depth'] = -50
        with self.assertRaises(ValueError):
            runtime.validate_state(label, status, initial, native, 8)

    def report(self, directory, restored_change=False):
        initial, prototype = adapt_original()
        report = {'completed': True, 'restored': True, 'initial': initial,
                  'plan_sha256': owner.PLAN_HASH,
                  'actor_ready': {'clock': 0.}, 'frozen_marker_calibration': prototype['marker_mapping']['calibration'],
                  'states': {}}
        original_path = ARCHIVE / Path(prototype['capture']['path']).name
        with Image.open(original_path) as source:
            empty = source.convert('RGB')
        roi = runtime.positive_roi(prototype)
        clock = 1.
        for label in runtime.candidate.STATES:
            submitted, attachments, native = state_values(label, initial)
            row = report['states'][label] = {'native': native, 'frames': []}
            for index in range(2):
                frame = deepcopy(prototype)
                frame['status'].update(control=label, last_submission=submitted, attachments=attachments, clock=clock,
                                       journal=native['journal'])
                clock += 1.
                image = empty.copy()
                draw = ImageDraw.Draw(image)
                if label.startswith('ui_cow_'):
                    draw.rectangle((roi[0]+20, roi[1]+20, roi[0]+39, roi[1]+39), fill=(10, 10, 10))
                if label in ('ui_plain_depth15', 'ui_plain_depth15_repeat'):
                    draw.rectangle((roi[0]+50, roi[1]+50, roi[0]+59, roi[1]+69), fill=(0, 100, 120))
                if restored_change and label == 'ui_empty_restored':
                    draw.rectangle((roi[0]+70, roi[1]+50, roi[0]+79, roi[1]+69), fill=(255, 0, 0))
                path = Path(directory) / (label + str(index) + '.png')
                image.save(path)
                raw = path.read_bytes()
                record = frame['capture']
                record.update(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
                record['capture'].update(path=str(path), sha256=record['sha256'], bytes=len(raw))
                row['frames'].append(frame)
        return report

    def test_synthetic_paired_depth_and_negative_restoration_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            report = self.report(directory)
            score = runtime.score_probe(report)
            self.assertEqual(score['classification'], 'depth15_positive_depth50_zero_repeat_positive_requires_visual_review')
            self.assertEqual(score['stable_plain_pixels']['ui_plain_depth50'], 0)
            self.assertEqual(score['restored_difference_pixels'], 0)
            self.assertTrue(all(value >= 80 for value in score['stable_cow_pixels'].values()))
            self.assertFalse(score['enchantment_glint_accepted'])
            self.assertFalse(score['production_rendering_accepted'])
            bad = self.report(directory, restored_change=True)
            self.assertEqual(runtime.score_probe(bad)['classification'], 'invalid_controls')


class CleanupAndOwner(unittest.TestCase):
    def fake_runtime(self, directory, cow_positive=False, capture_failure=False, persist_failure=False):
        bundle = Path(directory) / 'bundle'
        bundle.mkdir()
        for name in runtime.candidate.FILES + tuple(label + '_client.py' for label in runtime.candidate.STATES):
            (bundle / name).write_text(name, encoding='ascii')
        (bundle / 'plan.json').write_text('{}', encoding='ascii')
        initial, frame = adapt_original()
        calls = []
        state = {'label': None, 'clock': 1., 'native': None}

        def run(code):
            calls.append(code)
            if code == 'install_client.py':
                return initial
            if code == 'actor_ready_client.py':
                return {'ready': True, 'clock': 1.}
            if code == 'status_client.py':
                status = deepcopy(frame['status'])
                label = state['label'] or 'ui_cow_positive'
                submitted, attachments, native = state_values(label, initial)
                state['clock'] += 1.
                status.update(ready=True, control=label, clock=state['clock'], last_submission=submitted, attachments=attachments,
                              journal=native['journal'])
                return status
            if code.endswith('_client.py') and code[:-10] in runtime.candidate.STATES:
                state['label'] = code[:-10]
                return state_values(state['label'], initial)[2]
            if code == 'remove_client.py':
                return {'errors': []}
            if code == 'navigation_client.py':
                return {'owned': False, 'transition': False, 'contains_owned': False}
            if code == 'absent_client.py':
                return {'absent': True}
            if code == 'verify_client.py':
                return {'restored': True}
            return {}

        check = SimpleNamespace(run=run, wait=lambda *args: None, command=lambda _: {'tree': frame['tree']})

        class FakeBounded:
            def __init__(self, check, guard, deadline):
                self.original = check.run
                self.cleanup = False
            def capture_adapter(self):
                return None
            def remaining(self):
                return 100.
            def run(self, code):
                return self.original(code)
            def wait(self, label, predicate, read):
                result = read()
                if not predicate(result):
                    raise TimeoutError(label)
                return result
            def capture(self, path):
                if capture_failure:
                    raise RuntimeError('injected native capture failure')
                return frame['capture']

        writes = []
        def save(path, report):
            writes.append(report.get('attempted_operation'))
            if persist_failure and 'install_client.py' in calls:
                raise OSError('injected disk failure')
        modules = runtime.dependencies()
        modules = dict(modules, execute_frame_item_translation=SimpleNamespace(BoundedRuntime=FakeBounded, save_report=save))
        with patch.object(runtime, 'dependencies', return_value=modules), patch.object(runtime, 'preflight', return_value={}), \
                patch.object(runtime, 'layout_readback', return_value=frame['layout']), \
                patch.object(runtime, 'score_probe', return_value={'positive_cow_gate_passed': cow_positive}), \
                patch.object(runtime.time, 'sleep'):
            report = runtime.execute_probe(bundle, Path(directory)/'runtime.json', check, None, 120.)
        return report, calls

    def test_cow_failure_stops_before_binding_and_cleans(self):
        with tempfile.TemporaryDirectory() as directory:
            report, calls = self.fake_runtime(directory)
        self.assertFalse(report['completed'])
        self.assertTrue(report['restored'])
        self.assertNotIn('ui_plain_depth15_client.py', calls)
        self.assertEqual(calls.count('remove_client.py'), 1)
        self.assertEqual(calls.count('destroy_client.py'), 1)
        self.assertIn('Ordinary cow', report['errors'][0])

    def test_native_capture_failure_still_cleans_exact_owned_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            report, calls = self.fake_runtime(directory, capture_failure=True)
        self.assertFalse(report['completed'])
        self.assertTrue(report['restored'])
        self.assertEqual(calls.count('remove_client.py'), 1)
        self.assertEqual(calls.count('pop_client.py'), 1)
        self.assertEqual(calls.count('destroy_client.py'), 1)

    def test_disk_failure_cannot_block_cleanup_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            report, calls = self.fake_runtime(directory, persist_failure=True)
        self.assertFalse(report['restored'])
        self.assertTrue(report['cleanup_errors'])
        self.assertEqual(calls.count('remove_client.py'), 1)
        self.assertEqual(calls.count('destroy_client.py'), 1)

    def test_wrong_workspace_identity_never_reaches_fixture_mutation(self):
        client = SimpleNamespace(binding={'game_pid': 10, 'token': 'owned-token'})
        with patch.object(owner, 'execute', return_value={'pid': 10, 'token': 'foreign-token'}):
            with self.assertRaisesRegex(ValueError, 'PID/token'):
                owner.ready_workspace(client, 10**20, {}, lambda: None)

    def test_supervisor_timeout_preserves_no_retry_and_unresolved_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / 'session.json'
            (session.parent / 'artifacts').mkdir()
            session.write_text('{}')
            error = subprocess.TimeoutExpired(['owner'], 150)
            with patch.object(owner, 'verify', return_value={}), patch.object(owner, 'save'), \
                    patch.object(owner.time, 'monotonic', return_value=100.):
                result = owner.supervise(directory, session, run=lambda *args, **kwargs: (_ for _ in ()).throw(error))
            self.assertTrue(result['timed_out'])
            self.assertTrue(result['no_retry'])
            self.assertFalse(result['cleanup_verified'])
            self.assertEqual(result['attempts'], 1)

    def test_session_ready_false_is_not_a_real_workspace(self):
        api = ModuleType('mod.client.extraClientApi')
        session = SimpleNamespace(ready=False)
        api.GetSystem = lambda *args: SimpleNamespace(session=session, bridge=SimpleNamespace(session=session))
        api.GetLocalPlayerId = lambda: 'player'
        pyreact = ModuleType('modern_projection.pyreact')
        pyreact.navigator = SimpleNamespace(is_ready=True, is_transitioning=False, get_entries=lambda: [])
        mod, client_mod = ModuleType('mod'), ModuleType('mod.client')
        mod.client, client_mod.extraClientApi = client_mod, api
        with patch.dict(sys.modules, {'mod': mod, 'mod.client': client_mod, 'mod.client.extraClientApi': api,
                                     'modern_projection.pyreact': pyreact}):
            env = {}
            exec(owner.READINESS, env)
        self.assertFalse(json.loads(env['_result'])['ready'])

    def test_startup_budget_and_single_attempt_survive_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []
            def run(command, **kwargs):
                calls.append((command, kwargs))
                raise subprocess.TimeoutExpired(command, kwargs['timeout'])
            with patch.object(owner, 'verify', return_value={}), patch.object(owner, 'registry_dir', return_value=Path(directory)), \
                    patch.object(owner.time, 'monotonic', return_value=100.):
                result = owner.launch(directory, run=run)
                self.assertTrue(result['timed_out'])
                self.assertEqual(result['attempts'], 1)
                self.assertEqual(calls[0][1]['timeout'], 240.)
                self.assertEqual(calls[0][0][-2:], ['--wait', '180'])
                self.assertEqual(calls[0][1]['creationflags'], subprocess.CREATE_NO_WINDOW)
                with self.assertRaisesRegex(ValueError, 'Only one startup'):
                    owner.launch(directory, run=run)
            self.assertEqual(len(calls), 1)

    def test_actual_http_deadline_stops_streamed_headers_and_body(self):
        for headers in (False, True):
            class SlowResponse(BaseHTTPRequestHandler):
                def do_GET(self):
                    try:
                        if headers:
                            self.wfile.write(b'HTTP/1.1 200 OK\r\nX-Drip: ')
                        else:
                            self.send_response(200)
                            self.send_header('Content-Length', '1000')
                            self.end_headers()
                        for _ in range(50):
                            self.wfile.write(b'x')
                            self.wfile.flush()
                            time.sleep(.03)
                    except (ConnectionError, OSError):
                        return
                def log_message(self, *args):
                    return
            server = ThreadingHTTPServer(('127.0.0.1', 0), SlowResponse)
            server.daemon_threads = True
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            errors = []
            started = time.monotonic()
            try:
                request = urllib.request.Request('http://127.0.0.1:%d/' % server.server_port)
                with self.assertRaises(Exception):
                    with owner.absolute_http_open(None, request, .15, started+1., time.monotonic, errors.append) as response:
                        response.read()
                self.assertLess(time.monotonic()-started, .8)
                self.assertEqual(len(errors), 1)
                self.assertIsNotNone(errors[0])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=1.)


if __name__ == '__main__':
    unittest.main()
