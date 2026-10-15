"""Same-session water-only S/SE falsification, after frozen cache A/B completion."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

os.environ['OPENBLAS_NUM_THREADS'] = '1'
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / 'result'
CACHE_HOST = ROOT / '.runtime/water-r21-depth-cache-v1/host.py'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
CAPTURE_SHA = 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
CANDIDATE_SHA = '00fa11e977324c8fa64aac94501362df2c44c9826b37d676319131e1560d62a9'
PHASES = (('skeleton_baseline', 'S'), ('candidate', 'SE'),
          ('skeleton_restore', 'S'), ('candidate_repeat', 'SE'), ('final_skeleton', 'S'))
POSE = (35., 25., 4.6)
INSTALL = '''assert not hasattr(sys,'_water_ui_se')
assert not hasattr(sys,'_water_depth_ab')
namespace={}
eval(compile(%r,'water-ui-candidate','exec'),namespace)
eval(compile(%r,'water-ui-settled-pool','exec'),namespace)
sys._water_ui_se=namespace['SettledPool'](s,namespace['entity_draw_pose'])
sys._water_ui_se.suspend()
_result=sys._water_ui_se.initial
'''
RESTORE_DEPTH = '''engine=sys._water_ui_se
engine.restore_methods()
engine.controls.closed=engine.closed
s.camera_depth=engine.depth
s.emit('camera_depth')
_result=True
'''


def cache_module():
    spec = importlib.util.spec_from_file_location('water_cache_frozen_host', CACHE_HOST)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def save(report):
    (OUTPUT / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n', encoding='ascii')


def recovery(check, report, probe):
    present = check.run("_result=hasattr(sys,'_water_ui_se')")
    if present:
        check.run(RESTORE_DEPTH)
        check.wait('recover ordinary depth', lambda row: row['ready'],
            lambda: check.run("_result={'ready':abs(s.camera_depth_pose-s.camera_depth)<.0001 and not s.liquid_controls.pending}"))
        submitted = check.run('sys._water_ui_se.suspend()\n_result=sys._water_ui_se.restore_submissions()')
        report['native_restore_submissions'] = submitted
        assert submitted['restored'], 'One or more native S restorations failed; state retained for recovery'
        check.wait('restore native skeleton IDs', lambda row: row['ready'],
            lambda: check.run('_result=sys._water_ui_se.poll_ids()'))
        report['native_restore_payload'] = check.run('_result=sys._water_ui_se.payload()')
        report['native_restore'] = check.run('_result=sys._water_ui_se.finish()')
        check.run('del sys._water_ui_se\n_result=True')
    # These existing controls are individually guarded inside the saved probe.
    if check.run("_result=hasattr(sys,'_blueprint_qa_saved')"):
        if check.navigation()['open']:
            check.run('navigator.pop()\n_result=True')
            check.wait('close restored pool', lambda row: not row['open'] and not row['transition'], check.navigation)
        report['workspace_restore'] = check.run(probe.RESTORE_PROFILE)


def run(args):
    assert args.scheduled_by_root and args.session, 'Root runtime/WGC scheduling and exact session required'
    cache = cache_module()
    plan, probe = cache.validate_plan()
    assert cache.sha(HERE / 'candidate.py') == CANDIDATE_SHA
    assert cache.sha(CAPTURE) == CAPTURE_SHA
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve()), MCDEV_OWNER=cache.OWNER,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    from _session import load_session
    session = load_session(args.session, cache.OWNER, live=True)
    assert Path(session['project']).resolve() == cache.PROJECT.resolve()
    ready = cache.read(cache.OUTPUT / 'launch-ready.json')
    for key in ('id', 'owner', 'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'):
        assert ready[key] == session[key], 'Unified session changed: ' + key
    assert session['ready'] and session['noactivation']['window_noactivate']
    cache.retained_observer(session)
    if args.action == 'run':
        ab = cache.read(cache.OUTPUT / 'ab-report.json')
        assert all(ab[key] for key in ('completed', 'restored', 'source_unchanged'))
        assert not ab['cleanup_errors']
        assert ab['session_binding']['id'] == session['id']
        assert not OUTPUT.exists(), 'One-use candidate output already exists; use recover after interruption'
        OUTPUT.mkdir()
        report = {'schema': 1, 'completed': False, 'restored': False, 'cleanup_errors': [],
            'diagnostic_only': True, 'production_qualified': False, 'repair_accepted': False,
            'native_visual_review': 'pending: cow, geometry, depth and water outline must be inspected',
            'baseline_visible_policy': 'inconclusive_for_invisible_state_repair',
            'candidate_sha256': CANDIDATE_SHA, 'capture_helper_sha256': CAPTURE_SHA,
            'source_contract_sha256': plan['source_contract_sha256'],
            'host_sha256': cache.sha(__file__), 'engine_sha256': cache.sha(HERE / 'runtime_engine.py'),
            'cache_ab_report_sha256': cache.sha(cache.OUTPUT / 'ab-report.json'),
            'session_binding': {key: session[key] for key in ('id', 'owner', 'session_file', 'game_pid', 'game_identity')},
            'phases': {}, 'captures': {}, 'capacity': [], 'window_actions': [],
            'cold_start_performed': False, 'settled_pool_only': True,
            'initial_construction_qualified': False, 'shared_depth_qualified': False}
    else:
        assert OUTPUT.is_dir(), 'No existing candidate result to recover'
        report = cache.read(OUTPUT / 'report.json')
        assert report['session_binding']['id'] == session['id']
        report.setdefault('recovery_attempts', []).append({'started': time.time()})
        report.setdefault('previous_cleanup_errors', []).extend(report['cleanup_errors'])
        report['cleanup_errors'] = []
    save(report)
    before = probe.snapshot_sources(cache.PROJECT)

    def boundary(label):
        observer = cache.retained_observer(session)
        coverage = cache.watcher_coverage()
        state = cache.capacity(probe, session)
        report['capacity'].append({'label': label, 'state': state, 'watcher': coverage,
                                  'retained': observer['processes']})
        save(report)
        assert state['passed'] and coverage['passed'], 'Identity, 6 GiB, handles or watcher gate failed'
        assert not probe.assertion_dialogs(session['game_pid']), 'Native assertion present'

    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, OUTPUT / 'report.json', 45.)

        def ids(label):
            time.sleep(.6)
            value = check.wait(label + ' asynchronous IDs', lambda row: row['ready'],
                               lambda: check.run('_result=sys._water_ui_se.poll_ids()'))
            assert value['ids'] == initial_ids, 'Owned front IDs changed during API sequence'
            return value

        def capture(label):
            boundary('before_capture_' + label)
            before_state = check.run('_result=sys._water_ui_se.snapshot()')
            frame = probe.base.capture(session['session_file'], cache.OWNER, OUTPUT / (label + '.png'), CAPTURE)
            report['captures'][label] = frame
            assert frame['reliable'] and frame['ok'] and frame['guarded_no_activation']
            assert not frame['activation_fallback'] and not frame['agent_activation_allowed']
            assert frame['helper']['sha256'] == CAPTURE_SHA
            assert frame['session_file'] == session['session_file'] and frame['owner'] == cache.OWNER
            assert frame['game_pid'] == session['game_pid'] and frame['game_identity'] == session['game_identity']
            capture_size = [frame['width'], frame['height']]
            assert capture_size == report.setdefault('capture_size', capture_size), 'Native viewport changed'
            after_state = check.run('_result=sys._water_ui_se.snapshot()')
            assert before_state == after_state, 'Pool native state changed during capture'
            frame['pool_before'], frame['pool_after'] = before_state, after_state
            boundary('after_capture_' + label)
            save(report)

        try:
            if args.action == 'run':
                boundary('before_workspace')
                assert not check.navigation()['open'], 'Cache A/B must restore its workspace before S/SE'
                check.run(probe.blueprints.INSTALL_PROBE)
                report['profile'] = check.run(probe.PROFILE % (True, True))
                check.run('owner.open_workspace()\n_result=True')
                check.wait('open pool workspace', lambda row: row['open'] and not row['transition'], check.navigation)
                report['load'] = check.run(probe.LOAD % (('pool', 'wet', POSE),))
                report['ready'] = check.wait('ordinary single frozen pool',
                    probe.stable_scene_predicate(POSE, (0., 0.), probe.workspace.scene_ready),
                    lambda: check.run(probe.SCENE_STATE))
                initial = report['initial'] = check.run(INSTALL % (
                    (HERE / 'candidate.py').read_text(encoding='ascii'),
                    (HERE / 'runtime_engine.py').read_text(encoding='ascii')))
                initial_ids = [row['actual_ids'][row['front']] for row in initial['entries']]
                assert len(initial_ids) == 8 and -1 not in initial_ids
                for label, mode in PHASES:
                    boundary('before_' + label)
                    phase = report['phases'][label] = {}
                    phase['submitted'] = check.run('_result=sys._water_ui_se.submit(%r)' % mode)
                    phase['ids'] = ids(label)
                    assert phase['ids']['state'] == initial, 'Payload, geometry, depth or ownership changed'
                    phase['wet_payload'] = check.run('_result=sys._water_ui_se.payload()')
                    capture(label + '_wet')
                    phase['hidden_payload'] = check.run('_result=sys._water_ui_se.payload(True)')
                    capture(label + '_hidden')
                    check.run('_result=sys._water_ui_se.payload()')
                    if label == 'candidate_repeat':
                        report['depth_release'] = check.run('_result=sys._water_ui_se.release_for_depth()')
                        check.run('s.move_depth(1)\n_result=True')
                        check.wait('ordinary depth step', lambda row: row['ready'],
                            lambda: check.run("_result={'ready':abs(s.camera_depth_pose-s.camera_depth)<.0001 and not s.liquid_controls.pending}"))
                        check.run('sys._water_ui_se.suspend()\n_result=True')
                        report['depth_step'] = check.run('_result=sys._water_ui_se.snapshot()')
                        assert report['depth_step']['depth'] != initial['depth']
                        capture('candidate_depth_step')
                        check.run(RESTORE_DEPTH)
                        check.wait('ordinary depth return', lambda row: row['ready'],
                            lambda: check.run("_result={'ready':abs(s.camera_depth_pose-s.camera_depth)<.0001 and not s.liquid_controls.pending}"))
                        check.run('sys._water_ui_se.suspend()\n_result=True')
                        report['depth_return'] = check.run('_result=sys._water_ui_se.snapshot()')
                        assert report['depth_return'] == initial, 'Ordinary depth return changed the original pool'
                    boundary('after_' + label)
                report['completed'] = True
        except Exception:
            report['error'] = traceback.format_exc()
        finally:
            try:
                recovery(check, report, probe)
                final_capacity = cache.capacity(probe, session)
                report['after_restore_capacity'] = final_capacity
                if not final_capacity['passed']:
                    report['completed'] = False
                    report['execution_gate_failure_after_cleanup'] = True
            except Exception:
                report['cleanup_errors'].append({'phase': 'recover', 'error': traceback.format_exc()})
            report['source_unchanged'] = before == probe.snapshot_sources(cache.PROJECT)
            report['restored'] = not report['cleanup_errors'] and report['source_unchanged']
            report['assessment'] = 'await_native_pixel_review' if report['completed'] and report['restored'] else 'rejected_or_incomplete'
            save(report)
    print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'assessment', 'error')}))
    return 0 if report['completed'] and report['restored'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('run', 'recover'))
    parser.add_argument('--session', required=True)
    parser.add_argument('--scheduled-by-root', action='store_true')
    raise SystemExit(run(parser.parse_args()))
