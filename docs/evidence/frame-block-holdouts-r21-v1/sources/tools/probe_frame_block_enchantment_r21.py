"""Small owner-bound artificial block NBT probe; no screenshots or pixel acceptance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity
from audit_chest_occupied_runtime import process_snapshot
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from check_native_dialogs import assertion_dialogs
from item_sprite_native_reference import PREPARE, FILL, RESTORE
from mcdk import Client, return_value


def run(args):
    assert not args.output.exists(), 'Preserve prior probe evidence'
    session = json.loads(args.session.read_bytes())
    assert session['owner'] == args.owner and session['state'] == 'ready'
    for name in ('game', 'mcdk'):
        assert process_identity(session[name + '_pid']) == session[name + '_identity']
    assert not [row for row in assertion_dialogs() if row['pid'] == session['game_pid']]
    handles, commit = process_snapshot(session['game_pid']), commit_at_boundary()
    assert handles['handles'] < args.maximum_handles, handles
    assert commit['commit_available_bytes'] >= args.minimum_commit_gib * 1024 ** 3, commit
    os.environ.update(MCDEV_SESSION_FILE=session['session_file'], MCDEV_OWNER=session['owner'],
                      MCDEV_MCP_URL=session['mcp_url'], MCDEV_ALLOW_USER_FOREGROUND='1')
    report = {'schema': 1, 'completed': False, 'passed': False, 'restored': False,
              'production_qualified': False, 'pixel_acceptance': False, 'cleanup_errors': [],
              'owner': args.owner, 'session_id': session['id'], 'game_pid': session['game_pid'],
              'game_identity': session['game_identity'], 'process_before': handles, 'commit_before': commit,
              'host_tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'native_fixture_sha256': hashlib.sha256((ROOT / 'tools/item_sprite_native_reference.py').read_bytes()).hexdigest(),
              'scope': 'Native inventory plain quartz insertion, declared synthetic tag write onto preserved actual Item.Block, actual server/client NBT readback; no WGC',
              'public_api_rejection_evidence': 'docs/evidence/frame-block-candidate-r21-v1/quartz-enchantment-rejection.json'}
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def persist():
        args.output.write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')

    persist()
    with Client(timeout=20) as client:
        def execute(code, is_client=False):
            prefix = ("import mod.client.extraClientApi as api\n" if is_client else
                "import mod.server.extraServerApi as api\nplayers=api.GetPlayerList()\nassert len(players)==1\n"
                "from modern_projection.server_system import WorldAdapter\nadapter=WorldAdapter(players[0])\n")
            result = return_value(client.call('execute_code',
                {'is_client': is_client, 'direct_return': True, 'code': prefix + code}))
            return json.loads(result) if isinstance(result, str) else result

        pending = False
        try:
            row = {'mode': 'enchanted', 'item_name': 'minecraft:quartz_block', 'item_aux': 0,
                   'artificial_enchantment': True, 'position': [8, -39, 8], 'support': [8, -39, 9],
                   'face': 2, 'rotation': 0., 'frame_name': 'minecraft:frame'}
            pending = True
            report['prepare'] = execute(PREPARE % ([row], (8, -40, 5)))
            persist()
            report['fill'] = execute(FILL)
            persist()
            read = ("from modern_projection.projection.nbt_spatial import field_key,root_payload,scalar\n"
                "info=api.GetEngineCompFactory().CreateBlockInfo(api.GetLevelId())\n"
                "root=root_payload(info.GetBlockEntityData((8,-39,8)))\n"
                "item=root_payload(root.get(field_key(root,'Item'))) if root else None\n"
                "block=root_payload(item.get(field_key(item,'Block'))) if item else None\n"
                "tags=root_payload(item.get(field_key(item,'tag'))) if item else None\n"
                "ench=tags.get(field_key(tags,'ench')) if tags else None\n"
                "actual=[(scalar(value,'id'),scalar(value,'lvl')) for value in (ench or ())]\n"
                "passed=bool(item and block and scalar(item,'Name')=='minecraft:quartz_block' and "
                "scalar(item,'Damage')==0 and scalar(item,'Count')==1 and actual==[(9,3)])\n"
                "_result={'passed':passed,'root':root,'enchantments':actual,'block':block}")
            deadline = time.monotonic() + 15.
            while True:
                report['client'] = execute(read, True)
                if report['client']['passed']:
                    break
                if time.monotonic() >= deadline:
                    raise TimeoutError('Actual artificially enchanted block NBT did not replicate')
                time.sleep(.3)
            report['completed'] = True
            report['passed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            report['traceback'] = traceback.format_exc()
        finally:
            if pending:
                try:
                    report['restoration'] = execute(RESTORE)
                    report['restored'] = report['restoration']['passed']
                except Exception as error:
                    report['cleanup_errors'].append(type(error).__name__ + ': ' + str(error))
            try:
                assert process_identity(session['game_pid']) == session['game_identity'], 'Owned game process exited or changed'
                report['process_after'] = process_snapshot(session['game_pid'])
            except Exception as error:
                report['cleanup_errors'].append('process after: ' + type(error).__name__ + ': ' + str(error))
            report['passed'] = report['passed'] and report['restored'] and not report['cleanup_errors']
            persist()
    print(json.dumps({key: report.get(key) for key in ('completed', 'passed', 'restored', 'error', 'cleanup_errors')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--maximum-handles', type=int, default=190000)
    parser.add_argument('--minimum-commit-gib', type=float, default=6.)
    raise SystemExit(run(parser.parse_args()))
