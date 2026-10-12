"""Owner-bound one-shot PaperDoll diagnostic; default is read-only validation."""
import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

from run_frame_translation import ROOT, ENTITIES, SESSION, ARTIFACTS, OWNER, WGC_EXE, \
    EXE_SHA256, WRAPPER_SHA256, source_config_hashes, save
from session_pack_stage import SessionPackStage, digest, require
from mcdk import Client
from verify_sign_visuals import SignCheck


PROBE_SHA256 = '7d4496ef5d616998d281a802c1dff3ef343808c1e6c1e9f4a26f49a7daf00e1a'
PLAN_SHA256 = '67d61cfc9ddd437c40bd1d970242750b20a4af82a5328c3a2f8429df6d83322b'
GUARD_SHA256 = '8142194003d96260d7c8fffaa203de66fbb19d272340ae304a2bc3e4a308aadf'
BUNDLE = ENTITIES / '.runtime/native-item-paper-doll-r12-final-v4'
EVIDENCE_PREFIX = 'native-item-paper-doll-r12-v4'
HELPER_SHA256 = {
    'flat_frame_item_visual_checks': '4c479f79ce14d6bd98b899b60d2ebe00351d4ef1d4d64d81c59db9c1c52b0315',
    'verify_snow_plant_visibility': '89840f5f94959b10c608fe3a5a4a8fcecf254a155625a26775f88320191710d4',
}


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def load_probe():
    source = ENTITIES / 'tools/probe_native_item_paper_doll.py'
    require(digest(source) == PROBE_SHA256, 'Reviewed native item probe changed')
    require(digest(BUNDLE / 'plan.json') == PLAN_SHA256, 'Reviewed native item plan changed')
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
        require(actual in copies and digest(actual) == expected,
                'Actual imported native pixel helper differs: ' + str(actual))
    specification = importlib.util.spec_from_file_location('reviewed_native_item_paper_doll', source)
    probe = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(probe)
    return probe, source


def execute_once(probe, source, output, runtime_output, guard, clock=time.monotonic):
    report = {'schema': 1, 'scope': 'One finite native attached-item UI diagnostic',
              'owner': OWNER, 'session_id': SESSION.name, 'started_at': timestamp(),
              'source_sha256': digest(Path(__file__)), 'probe_sha256': digest(source),
              'plan_sha256': PLAN_SHA256, 'requests': [], 'errors': [], 'cleanup_errors': [],
              'sdk_dispatch_attempted': False, 'shader_or_pack_mutation_attempted': False,
              'world_or_inventory_mutation_attempted': False, 'completed': False, 'restored': False,
              'production_rendering_accepted': False, 'enchantment_glint_accepted': False,
              'source_and_config_before': source_config_hashes()}
    save(output, report)
    deadline = None

    class RecordedClient(Client):
        def _post(self, method, params=None, notification=False):
            request = {'jsonrpc': '2.0', 'method': method, 'params': params or {}}
            if not notification:
                request['id'] = self.counter + 1
            row = {'request': request, 'started_at': timestamp()}
            report['requests'].append(row)
            save(output, report)
            previous_timeout = self.timeout
            try:
                current_deadline = getattr(self, 'frame_dispatch_deadline', deadline - 30.)
                require(clock() < current_deadline, 'Finite native item dispatch deadline exhausted')
                if method == 'tools/call':
                    row['background_before_request'] = guard.guard()
                    row['physical_window'] = guard.window
                self.timeout = min(previous_timeout, 10., current_deadline - clock())
                require(self.timeout > 0, 'Owner guard consumed native item dispatch budget')
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
        guard.guard()
        guard.verify_pack(guard.source)
        probe.preflight(BUNDLE, runtime_output)
        deadline = clock() + 150.
        report['native_started_monotonic'] = deadline - 150.
        report['native_cleanup_deadline_monotonic'] = deadline
        report['sdk_dispatch_attempted'] = True
        save(output, report)
        client = RecordedClient(timeout=10)
        client.__enter__()
        report['runtime_binding_verified'] = True
        check = SignCheck(client, runtime_output, 10, native_resolution=True, background_only=True,
                          native_capture_helper=str(ROOT / 'tools/capture_native_window.py'))
        runtime = probe.execute_probe(BUNDLE, runtime_output, check, guard, deadline)
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
            report['source_and_config_after'] = source_config_hashes()
            require(report['source_and_config_after'] == report['source_and_config_before'],
                    'Protected source config or session bytes changed')
            require(digest(source) == report['probe_sha256'], 'Native item probe changed during dispatch')
            guard.verify_pack(guard.source)
            report['protected_sources_and_configs_unchanged'] = True
        except Exception as error:
            report['cleanup_errors'].append('protected source/config check: ' + repr(error))
        report['restored'] = report['restored'] and not report['cleanup_errors']
        report['finished_at'] = timestamp()
        report['native_elapsed_seconds'] = None if deadline is None else clock() - (deadline - 150.)
        save(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-reviewed', action='store_true')
    args = parser.parse_args()
    output = ARTIFACTS / (EVIDENCE_PREFIX + '.orchestration.json')
    runtime_output = ARTIFACTS / (EVIDENCE_PREFIX + '.runtime.json')
    require(not output.exists() and not output.with_name(output.name + '.tmp').exists(),
            'Preserve existing one-shot native item evidence')
    os.environ['MCDEV_SESSION_FILE'] = str(SESSION / 'session.json')
    os.environ['MCDEV_OWNER'] = OWNER
    os.environ['MCDEV_NATIVE_CAPTURE_EXE'] = str(WGC_EXE)
    probe, source = load_probe()
    probe.preflight(BUNDLE, runtime_output)
    guard = SessionPackStage(ARTIFACTS, ARTIFACTS / (EVIDENCE_PREFIX + '.unused-stage-journal.json'))
    guard.guard()
    guard.verify_pack(guard.source)
    if not args.execute_reviewed:
        print(json.dumps({'validated': True, 'execute_requested': False, 'frames': 15,
                          'shader_or_pack_mutation_attempted': False}))
        return 0
    report = execute_once(probe, source, output, runtime_output, guard)
    print(json.dumps({key: report[key] for key in ('completed', 'restored',
                                                 'shader_or_pack_mutation_attempted',
                                                 'production_rendering_accepted', 'enchantment_glint_accepted')}))
    return 0 if report['completed'] and report['restored'] and not report['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
