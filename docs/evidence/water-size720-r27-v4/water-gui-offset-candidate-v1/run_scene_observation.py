"""Observe three real GUI scales through the ordinary workspace and water Scene."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session, _kernel, _identity
from _window import _list_windows
sys.path.insert(0, str(ROOT / '.runtime/round-20261022/water-size720-v3'))
from resize_adapter import resize_exact, user32
from run_size_group import available_commit
import scene_game as game
from scene_policy import describe_scene
from scene_restore import restore_scene


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--root-grant', required=True, type=Path)
    args = parser.parse_args()
    plan_path = WORK / 'plan-v1.json'
    plan = json.loads(plan_path.read_bytes())
    manifest_path = WORK / 'private-source-v1.json'
    manifest = json.loads(manifest_path.read_bytes())
    output = WORK / 'scene-observation-v1.json'
    assert not output.exists(), 'Preserve the first result'
    assert sha(manifest_path) == plan['private_source_manifest_sha256']
    assert all(sha(WORK / name) == value for name, value in plan['host_code_sha256'].items())
    grant = json.loads(args.root_grant.read_bytes())
    assert grant['owner'] == plan['owner'] and grant['plan_sha256'] == sha(plan_path)
    assert grant['begin'] <= time.time() < grant['until'] - 120
    project = Path(plan['project']).resolve(strict=True)
    sources = dict(manifest['source_sha256'], **manifest['auxiliary_sha256'])
    assert all(sha(project / name) == value for name, value in sources.items())
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=plan['owner'], MCDEV_ALLOW_USER_FOREGROUND='0')
    session = load_session(args.session, plan['owner'], live=True)
    assert Path(session['project']).resolve() == project
    sys.path.insert(0, str(project / 'tools'))
    import probe_liquid_pose_channel as base
    import probe_product_water as product
    import verify_debug_blueprints as blueprints
    import capture_native_window
    from water_capture_contract import stable_scene_predicate, scene_capture_state
    capture_native_window.ROOT = ROOT
    assert base.ROOT.resolve() == project
    capture_exe = Path(plan['capture_exe']['path'])
    assert sha(capture_exe) == plan['capture_exe']['sha256']
    assert user32.SetProcessDPIAware()
    report = {'schema': 1, 'owner': plan['owner'], 'source_contract_sha256': manifest['source_contract_sha256'],
              'plan_sha256': sha(plan_path), 'host_sha256': sha(Path(__file__)),
              'started_at_utc': datetime.now(timezone.utc).isoformat(), 'completed': False,
              'restored': False, 'restore_unknown': True, 'source_unchanged': False,
              'phases': [], 'same_font_real_SDK': [], 'resources': [], 'cleanup_errors': [],
              'formal_A_accepted': False, 'production_admission_performed': False,
              'default_path_evidence': False, 'manual_closures_added': 0,
              'scope': 'Explicit candidate normal workspace Scene; real cache refresh/native geometry/static images only'}

    def save():
        output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')

    def resource(stage):
        assert time.time() < grant['until'] - 60
        kernel = _kernel()
        kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
        sample = {'stage': stage, 'at': time.time(), 'available_commit_bytes': available_commit(), 'processes': {}}
        for kind in ('game', 'mcdk'):
            pid, identity = session[kind + '_pid'], session[kind + '_identity']
            handle = kernel.OpenProcess(0x1000, False, pid)
            assert handle, kind
            try:
                assert _identity(kernel, handle) == identity
                count = wintypes.DWORD()
                assert kernel.GetProcessHandleCount(handle, ctypes.byref(count))
                assert _identity(kernel, handle) == identity
                previous = next((item['processes'][kind]['handles'] for item in reversed(report['resources'])
                                 if kind in item['processes']), None)
                sample['processes'][kind] = {'pid': pid, 'identity': identity, 'handles': count.value,
                    'previous_handles': previous, 'growth': None if previous is None else count.value - previous}
            finally:
                kernel.CloseHandle(handle)
        report['resources'].append(sample)
        save()
        assert sample['available_commit_bytes'] >= plan['resource_gates']['min_available_commit_bytes']
        assert all(item['handles'] < plan['resource_gates']['max_handles']
                   and (item['growth'] is None or item['growth'] < plan['resource_gates']['max_adjacent_growth'])
                   for item in sample['processes'].values())

    def resize(stage, row):
        resource(stage['label'] + '_before_resize')
        with desktop_lock():
            windows = [value for value in _list_windows() if value['pid'] == session['game_pid']]
            assert len(windows) == 1
            resize_exact(windows[0]['hwnd'], session['game_pid'], session['game_identity'],
                         *stage['physical_client'], row)
        resource(stage['label'] + '_after_resize')

    save()
    with base.Client(timeout=30) as client:
        check = blueprints.BlueprintCheck(client, output, 45.)
        def call(code):
            return base.run(client, game.PREFIX + code)
        try:
            report['saved'] = call(game.SAVE)
            # This subcontrol uses real SDK data after real resize, but calls
            # Theme.configure explicitly while Workspace is closed. It is kept
            # separate from the event-driven normal Scene resize observations.
            for stage in plan['phases']:
                row = {'label': stage['label'], 'explicit_configure_while_workspace_closed': True}
                report['same_font_real_SDK'].append(row)
                resize(stage, row)
                row['native'] = call(game.SAME_FONT)
                save()
                assert row['native']['cached_gui'] == row['native']['sdk_integer_gui'] == stage['expected_integer_gui']
                assert row['native']['font'] == 5.
            report['theme_restored_before_workspace'] = call(game.RESTORE_THEME)
            report['probe_installed'] = check.run(blueprints.INSTALL_PROBE)
            state_code = product.SCENE_STATE + game.EXTRA_STATE
            for index, stage in enumerate(plan['phases']):
                phase = {'label': stage['label'], 'requested': stage, 'rows': [],
                         'workspace_mounted_during_resize': index > 0}
                report['phases'].append(phase)
                resize(stage, phase)
                if index == 0:
                    check.run('owner.open_workspace()\n_result=True')
                    check.wait('normal workspace opened', lambda value: value['open'] and not value['transition'], check.navigation)
                for case in plan['cases']:
                    for control in ('wet', 'dry'):
                        label = stage['label'] + '_' + case['label'] + '_' + control
                        row = {'label': label, 'case': case, 'control': control, 'samples': []}
                        phase['rows'].append(row)
                        resource(label + '_before_load')
                        pose = tuple(case['pose'])
                        row['loaded'] = check.run(product.LOAD % ((case['identity'], control, pose),))
                        save()
                        pan = (.15, -.08) if pose[:2] == (0., 0.) else (0., 0.)
                        stable = stable_scene_predicate(pose, pan, product.workspace.scene_ready)
                        def ready(state):
                            geometry = describe_scene(state, stage['expected_integer_gui'], control == 'wet')
                            return stable(state) and geometry['complete']
                        row['ready'] = check.wait(label + ' actual Scene/native geometry', ready, lambda: check.run(state_code))
                        for unused in range(3):
                            state = check.run(state_code)
                            row['samples'].append({'state': state,
                                'native_geometry': describe_scene(state, stage['expected_integer_gui'], control == 'wet')})
                            save()
                            assert row['samples'][-1]['native_geometry']['complete']
                            time.sleep(.2)
                        before = row['samples'][-1]['state']
                        resource(label + '_before_capture')
                        row['capture'] = base.capture(args.session, plan['owner'], WORK / 'captures' / (label + '.png'), capture_exe)
                        resource(label + '_after_capture')
                        row['after'] = check.run(state_code)
                        row['capture_layout_unchanged'] = scene_capture_state(before) == scene_capture_state(row['after'])
                        save()
                        assert row['capture_layout_unchanged']
                        assert describe_scene(row['after'], stage['expected_integer_gui'], control == 'wet')['complete']
                phase['completed'] = True
                save()
            report['completed'] = True
        except BaseException as error:
            report['error'] = {'type': type(error).__name__, 'message': str(error)}
            raise
        finally:
            try:
                report['explicit_restore'] = restore_scene(client, base.run, blueprints)
                report['restored'] = report['explicit_restore']['restored']
                report['restore_unknown'] = False
            except Exception as error:
                report['cleanup_errors'].append({'step': 'scene_restore', 'type': type(error).__name__, 'message': str(error)})
            try:
                report['source_unchanged'] = all(sha(project / name) == value for name, value in sources.items())
            except Exception as error:
                report['cleanup_errors'].append({'step': 'source_audit', 'type': type(error).__name__, 'message': str(error)})
            report['ended_at'] = time.time()
            save()
    assert report['completed'] and report['restored'] and report['source_unchanged'] and not report['cleanup_errors']
    print(json.dumps({'completed': True, 'phases': len(report['phases']), 'restored': True,
                      'images': sum(len(phase['rows']) for phase in report['phases']),
                      'formal_A_accepted': False, 'default_path_evidence': False}))


if __name__ == '__main__':
    main()
