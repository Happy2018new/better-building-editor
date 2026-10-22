"""One granted b70 public-T02 support-material diagnostic; never launch MC here."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback
import uuid
from types import SimpleNamespace
from status_access import read_status

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OLD = ROOT / '.runtime/round-20261022/transforms-runtime-v1'
V5 = HERE.with_name('transforms-cache-lineage-v5')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_bytes())
    work = args.config.resolve().parent
    manifest_path = Path(config['source_manifest'])
    assert sha(manifest_path) == config['source_manifest_sha256']
    manifest = json.loads(manifest_path.read_bytes())
    assert manifest['source_commit'] == 'b70ce7bf13ad6a4472f2b089ac812c162b174861'
    assert config['owner'] == manifest['owner']
    assert all(sha(path) == digest for path, digest in config['host_assets'].items())
    project = Path(manifest['project']).resolve()
    plan = json.loads((HERE / 'plan.json').read_bytes())
    assert sha(HERE / 'plan.json') == config['plan_sha256']
    sys.path[:0] = [str(work), str(project / '.agents/skills/pyreact-debugging/scripts'),
        str(project / 'tools'), str(project / 'behavior_pack/modern_projection'), str(V5), str(OLD)]
    from frozen_guard import verify
    assert verify() == manifest
    import verify_debug_blueprints as blue
    import verify_transform_runtime_r23 as base
    import verify_debug_visuals as visuals
    import transform_missing_r23 as missing
    from runtime_adapter import make_check
    from _session import load_session
    from mcdk import Client
    for host in (blue, base, visuals, missing):
        assert Path(host.__file__).resolve().parent == project / 'tools'
    original = module_at('_r28_support_restore_payloads', OLD / 'payloads.py')
    entry = module_at('_r28_support_entry', OLD / 'public_entry_host.py')
    entry.INPUTS = project
    entry.SCRIPTS = project / '.agents/skills/pyreact-debugging/scripts'
    blue.SCRIPTS = entry.SCRIPTS
    pose_steps = module_at('_r28_support_poses', HERE / 'representative_steps.py')
    pose_steps.time = time
    binding = load_session(Path(config['session_file']), config['owner'], live=True)
    assert Path(binding['project']).resolve() == project
    os.environ.update(MCDEV_SESSION_FILE=binding['session_file'], MCDEV_OWNER=config['owner'],
        MCDEV_MCP_URL=binding['mcp_url'], MCDEV_GAME_PID=str(binding['game_pid']), MCDEV_ALLOW_USER_FOREGROUND='0')
    grant = json.loads((work / 'root-review-and-slot-v1.json').read_bytes())
    assert grant['passed'] and grant['source_manifest_sha256'] == config['source_manifest_sha256']
    assert sha(work / 'prelaunch-config.json') == grant['prelaunch_config_sha256']
    assert config['host_assets'] == json.loads((work / 'prelaunch-config.json').read_bytes())['host_assets']
    assert grant['cutoff_utc'] == config['experiment_cutoff']
    out = Path(config['output'])
    out.mkdir(exist_ok=False)

    class Check(make_check(entry, blue, original.CLIENT)):
        def guard(self):
            super().guard()
            if self.cleaning:
                return
            assert datetime.now(timezone.utc) < datetime.fromisoformat(config['experiment_cutoff'])
            status = read_status(Path(config['assertion_status']))
            assert status['owners'] == [config['owner']] and not status['errors'] and not status['other_assertions']
            assert status['host_sha256'] == config['assertion_host_sha256']
            assert (datetime.now(timezone.utc) - datetime.fromisoformat(status['checked_at'])).total_seconds() < 5

    observer = {key: config[key] for key in ('owner', 'source_manifest_sha256', 'host_assets')}
    observer.update(session_id=binding['id'], game_identity=binding['game_identity'],
        mcdk_identity=binding['mcdk_identity'], observer_sha256=sha(V5 / 'observer_client.py'),
        host_sha256=sha(Path(__file__)), host_run_token=uuid.uuid4().hex)
    report = {'side': manifest['side'], 'owner': config['owner'], 'source_commit': manifest['source_commit'],
        'source_manifest_sha256': config['source_manifest_sha256'], 'plan_sha256': config['plan_sha256'],
        'observer_config': observer, 'started_at': datetime.now(timezone.utc).isoformat(),
        'completed': False, 'fixtures': [], 'manual_issues_closed': 0, 'pixels_qualified': False,
        'native_world_occupancy': False, 'world_write_performed': False, 'candidate_profile_assignment': False,
        'public_card_callbacks_tested': False, 'native_mesh_qualified': False, 'wet_snow_qualified': False}

    def save():
        (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')

    save()
    snapshot = installed = visual_saved = tool_saved = False
    with Client(timeout=35) as client:
        check = Check(client, out, binding, report)
        try:
            report['baseline'] = check.run(original.SNAPSHOT)
            snapshot = True
            report['initial_player'] = check.run('_result=json.dumps(b.player_position.GetFootPos())')
            check.run(blue.INSTALL_PROBE)
            installed = True
            check.install_lineage(observer, source_manifest_path=manifest_path)
            check.run(visuals.SAVE_VISUAL)
            visual_saved = True
            check.run(base.SAVE_TOOL)
            tool_saved = True
            pair = module_at('_r28_support_pair', HERE / 'run_pair.py')
            assert pair.OWNER == config['owner'] and pair.PAIR_PLAN == plan
            pair.driver = SimpleNamespace(base=base, steps=pose_steps)
            pair.pair_diagnostic(check, report, save)
            report['completed'] = True
        except Exception as error:
            report.update(error=type(error).__name__ + ': ' + str(error), traceback=traceback.format_exc())
        finally:
            check.cleaning = True
            try:
                if tool_saved:
                    check.run(base.CANCEL_JOB)
                    check.run(base.RESTORE_TOOL)
                if snapshot:
                    check.run(original.RESTORE_PRE)
                if hasattr(check, 'lineage_active'):
                    check.restore_lineage()
                if installed:
                    check.run(blue.RESTORE)
                if tool_saved:
                    check.run('del sys._transform_r23_saved\n_result=True')
                if visual_saved:
                    check.run('del sys._blueprint_visual_saved\n_result=True')
                if snapshot:
                    check.run(original.RESTORE_POST)
                    report['restore_audits'] = [check.wait('original session restored ' + str(index),
                        lambda value: value['preview_ready'], lambda: check.run(original.AUDIT)) for index in range(2)]
                    check.run(original.REMOVE_AUDIT)
                    report['restored'] = True
            except Exception as error:
                report.update(restored=False, restore_error=repr(error), restore_traceback=traceback.format_exc())
            report['source_unchanged'] = verify() == manifest and all(sha(path) == digest for path, digest in config['host_assets'].items())
            report['finished_at'] = datetime.now(timezone.utc).isoformat()
            save()
    print(json.dumps({key: report.get(key) for key in ('side', 'completed', 'restored', 'source_unchanged', 'error')}))
    return 0 if report['completed'] and report.get('restored') and report['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
