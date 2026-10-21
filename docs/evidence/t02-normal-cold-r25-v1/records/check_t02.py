"""Actual public T02 card and bounded transform/edit/full evidence on a normal cold source."""
import os
os.environ['OPENBLAS_NUM_THREADS'] = '1'
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OWNER = 'r25-t02-normal-v1'
PROJECT = ROOT / '.runtime/projects' / OWNER
sys.path[:0] = [str(PROJECT / 'tools'), str(PROJECT / '.agents/skills/pyreact-debugging/scripts')]
from _session import load_session
from mcdk import Client
import verify_debug_blueprints as blue
import verify_transform_runtime_r23 as base
from run_transform_final import bounded_editor, bounded_world
import public_entry_host as entry
from frozen_guard import verify
import payloads as p

IDENTITY = 'test.transforms.acceptance.t02'
OUT = HERE / 'check'


class T02Check(entry.EntryCheck):
    def run(self, code):
        return super().run(p.CLIENT + code)


def main():
    manifest = verify()
    assert manifest['source_commit'] == '900100aa402f7442b1f1cf6cf1554f1f3d76fd14'
    binding = load_session(Path(json.loads((HERE / 'launch/report.json').read_bytes())['session_file']), OWNER, live=True)
    assert Path(binding['project']).resolve() == PROJECT.resolve()
    os.environ.update(MCDEV_SESSION_FILE=binding['session_file'], MCDEV_OWNER=OWNER,
                      MCDEV_MCP_URL=binding['mcp_url'], MCDEV_GAME_PID=str(binding['game_pid']),
                      MCDEV_ALLOW_USER_FOREGROUND='0')
    OUT.mkdir(exist_ok=False)
    report = {'owner': OWNER, 'source_commit': manifest['source_commit'], 'completed': False,
              'manual_issues_closed': 0, 'manual_acceptance': False, 'candidate_profile_assignment': False,
              'native_mouse_clicked': False, 'actual_public_card_callbacks': True,
              'world_write_performed': False, 'missing_checked': False,
              'source_manifest_sha256': hashlib.sha256((HERE / 'source-manifest.json').read_bytes()).hexdigest(),
              'driver_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'started_at': datetime.now(timezone.utc).isoformat(), 'operations': []}
    def save():
        (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    save()
    installed = snapshot = tool_saved = visual_saved = False
    with Client(timeout=35) as client:
        check = T02Check(client, OUT, binding, report)
        def editor_frame(label):
            # Consume the normal focus request; never assign a raw pivot to a mounted camera.
            return bounded_editor(check, label, (11, 3, 15), 1.8)
        def full_frame(label):
            check.run("sys._t02_normal_r25['camera_mutated']=True\n_result=True")
            result = bounded_world(check, label, (11, 3, 15), (-14., 14., -22.), 1.)
            check.run('b.stop_projection()\nowner.open_workspace()\n_result=True')
            check.wait('workspace restored after full capture', lambda row: row['open'] and not row['transition'], check.navigation)
            return result
        try:
            report['baseline'] = check.run(p.SNAPSHOT); snapshot = True
            check.run(blue.INSTALL_PROBE); installed = True
            check.run(base.SAVE_VISUAL); visual_saved = True
            check.run(base.SAVE_TOOL); tool_saved = True
            report['card'] = check.load_card(IDENTITY)
            oracle = base.Editor(base.build(IDENTITY))
            base.prepare(oracle, IDENTITY)
            assert len(oracle.document.blocks) == 60
            from projection.cell import foreground
            samples = sum(foreground(cell)[0] != 'minecraft:stone' for cell in oracle.document.blocks.values())
            assert samples == 28, samples
            report['fixture_cells'] = 60
            report['direction_samples'] = 28
            report['initial_data'] = base.verify(check, oracle, 'actual public T02 initial', report)
            report['initial_editor'] = editor_frame('t02_initial')
            save()
            for operation in ('mirror_y', 'undo', 'redo', 'undo', 'rotate_y90', 'undo', 'redo', 'undo'):
                row = {'operation': operation, 'data': base.transform(check, oracle, operation, evidence=report)}
                report['operations'].append(row)
                if operation in ('mirror_y', 'rotate_y90'):
                    row['editor'] = editor_frame('t02_' + operation)
                    row['full'] = full_frame('t02_' + operation)
                save()
            report['final_fixture_data'] = base.verify(check, oracle, 'T02 restored through final undo', report)
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            report['traceback'] = traceback.format_exc()
        finally:
            check.cleaning = True
            try:
                if tool_saved:
                    check.run(base.CANCEL_JOB)
                    check.run(base.RESTORE_TOOL)
                if snapshot:
                    check.run(p.RESTORE_PRE)
                if installed:
                    check.run(blue.RESTORE)
                if tool_saved:
                    check.run('del sys._transform_r23_saved\n_result=True')
                if visual_saved:
                    check.run('del sys._blueprint_visual_saved\n_result=True')
                if snapshot:
                    check.run(p.RESTORE_POST)
                    audits = []
                    for unused in range(2):
                        audits.append(check.wait('original session independently restored', lambda row: row['preview_ready'], lambda: check.run(p.AUDIT)))
                        time.sleep(.3)
                    report['independent_restore_audits'] = audits
                    check.run(p.REMOVE_AUDIT)
                    report['restored'] = True
            except Exception as error:
                report['restored'] = False
                report['restore_error'] = repr(error)
                report['restore_traceback'] = traceback.format_exc()
            report['source_unchanged'] = verify() == manifest
            save()
    print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error')}))
    return 0 if report['completed'] and report.get('restored') and report['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
