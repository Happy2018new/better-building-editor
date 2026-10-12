"""Reviewable one-shot owner orchestrator; validation is the default action."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client
from verify_sign_visuals import SignCheck
from session_pack_stage import SessionPackStage, digest, require

SESSION = Path('C:/Users/Happy2018new/.pyreact-debug/instances/773c643b5cf344918e04d8b4eef2657a')
ARTIFACTS = SESSION / 'artifacts'
OWNER = 'frame-r11-background'
ENTITIES = ROOT.parent / 'r11-entities'
BUNDLE = ENTITIES / '.runtime/frame-item-translation-r11-final-v1'
STAGING_SHA256 = '8142194003d96260d7c8fffaa203de66fbb19d272340ae304a2bc3e4a308aadf'
WRAPPER_SHA256 = 'b008a23aaf53411e2fdda2752d43f2b4c219cfbb9b22ceff3cefa973b9c92754'
EXE_SHA256 = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
WGC_EXE = ROOT.parents[1] / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/' \
          '.runtime/native_wgc/build/Release/native_wgc_capture.exe'


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def save(path, report):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('x', encoding='ascii') as target:
        json.dump(report, target, ensure_ascii=True, indent=2)
        target.write('\n')
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)


def load_executor(expected):
    source = ENTITIES / 'tools/execute_frame_item_translation.py'
    require(len(expected) == 64 and digest(source) == expected.lower(), 'Reviewed executor hash mismatch')
    sys.path.append(str(ENTITIES / 'tools'))
    specification = importlib.util.spec_from_file_location('frame_translation_reviewed_executor', source)
    executor = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(executor)
    return executor, source


def source_config_hashes():
    paths = [ROOT / '.mcdev.json', SESSION / '.mcdev.json', SESSION / 'session.json']
    return {str(path): digest(path) for path in paths}


def execute_once(executor, executor_source, output, runtime_output, journal, clock=time.monotonic):
    report = {'schema': 1, 'scope': 'One finite staged frame diagnostic', 'started_at': timestamp(),
              'owner': OWNER, 'session_id': SESSION.name, 'source_sha256': digest(Path(__file__)),
              'executor_source': str(executor_source), 'executor_sha256': digest(executor_source),
              'source_and_config_before': source_config_hashes(), 'requests': [], 'errors': [],
              'cleanup_errors': [], 'staging_mutation_attempted': False, 'fixture_mutation_attempted': False,
              'shader_reload_attempted': False, 'filesystem_restored': False, 'runtime_restored': False,
              'post_link_original_reload_verified': False, 'completed': False,
              'runtime_restoration_applicable': False, 'post_link_original_reload_applicable': False,
              'production_rendering_accepted': False, 'animation_acceptance': False}
    save(output, report)
    stage = SessionPackStage(ARTIFACTS, journal)
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
                per_request_deadline = getattr(self, 'frame_dispatch_deadline', deadline)
                if per_request_deadline is not None:
                    remaining = per_request_deadline - clock()
                    require(remaining > 0, 'Finite native dispatch deadline exhausted')
                    self.timeout = min(self.timeout, 10., remaining)
                if method == 'tools/call':
                    row['background_before_request'] = stage.guard()
                    row['physical_window'] = stage.window
                    if per_request_deadline is not None:
                        remaining = per_request_deadline - clock()
                        require(remaining > 0, 'Native guard consumed remaining dispatch budget')
                        self.timeout = min(self.timeout, remaining)
                row['response'] = super()._post(method, params, notification)
                return row['response']
            except Exception as error:
                row['error'] = '%s: %s' % (type(error).__name__, error)
                raise
            finally:
                self.timeout = previous_timeout
                row['finished_at'] = timestamp()
                save(output, report)

    client = check = None
    try:
        require(digest(ROOT / '.runtime/frame-baseline-plan-r11/session_pack_stage.py') == STAGING_SHA256,
                'Reviewed staging helper changed')
        require(digest(ROOT / 'tools/capture_native_window.py') == WRAPPER_SHA256, 'Reviewed WGC wrapper changed')
        require(digest(WGC_EXE) == EXE_SHA256, 'Reviewed WGC executable changed')
        stage.guard()
        executor.preflight(BUNDLE, runtime_output)
        executor.verify_native_sources(stage, json.loads((BUNDLE / 'plan.json').read_bytes()))
        client = RecordedClient(timeout=10)
        client.__enter__()
        report['runtime_binding_verified'] = True
        check = SignCheck(client, runtime_output, 10, native_resolution=True, background_only=True,
                          native_capture_helper=str(ROOT / 'tools/capture_native_window.py'))
        deadline = clock() + 150.
        client.frame_dispatch_deadline = deadline
        report['native_started_monotonic'] = deadline - 150.
        report['native_cleanup_deadline_monotonic'] = deadline
        report['staging_mutation_attempted'] = True
        save(output, report)
        stage.prepare()
        require(clock() < deadline - 30., 'Staging consumed the normal execution budget')
        stage.swap()
        require(clock() < deadline - 30., 'Junction swap consumed the normal execution budget')
        report['fixture_mutation_attempted'] = True
        report['runtime_restoration_applicable'] = True
        report['shader_reload_attempted'] = True
        save(output, report)
        runtime = executor.execute_runtime(BUNDLE, runtime_output, check, stage, deadline)
        report['runtime_report'] = {'path': str(runtime_output), 'sha256': digest(runtime_output)}
        report['completed'] = runtime['completed']
        report['runtime_restored'] = runtime['runtime_restored']
        report['errors'].extend(runtime['errors'])
        report['cleanup_errors'].extend(runtime['cleanup_errors'])
    except Exception as error:
        report['errors'].append('%s: %s' % (type(error).__name__, error))
    finally:
        if report['staging_mutation_attempted']:
            report['post_link_original_reload_applicable'] = (
                report['fixture_mutation_attempted'] or stage.report.get('lookup_mutation_occurred', False) or
                stage.report.get('loaded_shader_mutation_attempted', False))
            try:
                errors = stage.restore_filesystem()
                report['cleanup_errors'].extend(errors)
                report['filesystem_restored'] = stage.report['filesystem_restored']
            except Exception as error:
                report['cleanup_errors'].append('filesystem restoration: ' + repr(error))
            if report['post_link_original_reload_applicable'] and client is not None and check is not None:
                try:
                    require(deadline is not None and clock() < deadline, 'Post-link reload budget exhausted')
                    client.frame_dispatch_deadline = deadline
                    client.timeout = min(10., (deadline - clock()) / 2.)
                    report['post_link_original_reload'] = check.run(
                        (BUNDLE / 'reload_shader_client.py').read_text(encoding='utf8'))
                    require(report['post_link_original_reload'] is True, 'Post-link original reload returned false')
                    report['post_link_original_reload_verified'] = True
                except Exception as error:
                    report['cleanup_errors'].append('post-link original reload: ' + repr(error))
        else:
            report['filesystem_restoration_applicable'] = False
        if client is not None:
            client.close()
        try:
            report['source_and_config_after'] = source_config_hashes()
            require(report['source_and_config_before'] == report['source_and_config_after'],
                    'Source config or managed session bytes changed')
            stage.verify_pack(stage.source)
            require(digest(executor_source) == report['executor_sha256'], 'Reviewed executor changed during run')
            report['protected_sources_and_configs_unchanged'] = True
        except Exception as error:
            report['cleanup_errors'].append('protected source/config check: ' + repr(error))
        report['restored'] = ((report['runtime_restored'] or not report['runtime_restoration_applicable']) and
                             report['filesystem_restored'] and
                             (report['post_link_original_reload_verified'] or
                              not report['post_link_original_reload_applicable']) and not report['cleanup_errors'])
        report['finished_at'] = timestamp()
        report['native_elapsed_seconds'] = None if deadline is None else clock() - (deadline - 150.)
        save(output, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executor-sha256', required=True)
    parser.add_argument('--execute-reviewed', action='store_true')
    args = parser.parse_args()
    output = ARTIFACTS / 'frame-item-translation-v2.orchestration.json'
    runtime_output = ARTIFACTS / 'frame-item-translation-v2.runtime.json'
    journal = ARTIFACTS / 'frame-shader-stage-v2.journal.json'
    for path in (output, output.with_name(output.name + '.tmp'), journal,
                 journal.with_name(journal.name + '.tmp')):
        require(not os.path.lexists(path), 'Preserve existing one-shot evidence: ' + str(path))
    os.environ['MCDEV_SESSION_FILE'] = str(SESSION / 'session.json')
    os.environ['MCDEV_OWNER'] = OWNER
    os.environ['MCDEV_NATIVE_CAPTURE_EXE'] = str(WGC_EXE)
    executor, source = load_executor(args.executor_sha256)
    executor.preflight(BUNDLE, runtime_output)
    stage = SessionPackStage(ARTIFACTS, journal)
    stage.guard()
    stage.verify_pack(stage.source)
    if not args.execute_reviewed:
        print(json.dumps({'validated': True, 'execute_requested': False, 'stage_exists': stage.stage.exists(),
                          'journal_exists': journal.exists(), 'native_controls': 12}))
        return 0
    report = execute_once(executor, source, output, runtime_output, journal)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'filesystem_restored',
                                                 'runtime_restored', 'post_link_original_reload_verified',
                                                 'production_rendering_accepted')}))
    return 0 if report['completed'] and report['restored'] and not report['errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
