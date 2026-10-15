"""Bounded depth-only diagnostic against a source-bound native pose reference."""
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
from mcdk import Client, return_value
from _session import process_identity
from audit_chest_occupied_runtime import process_snapshot
from capture_native_window import capture
from context_test_environment import run as environment, SETUP as ENV_SETUP, RESTORE as ENV_RESTORE
from item_sprite_capture_contract import snapshot_sources, snapshot_digest, camera_matches
from item_sprite_native_reference import PREPARE, FILL, HIDE_CLEAR, HIDE_PLACE, RESTORE as NATIVE_RESTORE
from run_visible_items_r16 import WORLD_STATE, WORLD_HIDE, WORLD_SHOW
from run_item_sprite_product import CAMERA
from verify_debug_blueprints import BlueprintCheck, INSTALL_PROBE, RESTORE


def run(args):
    session = json.loads(args.session.read_bytes())
    reference = json.loads(args.reference.read_bytes())
    assert session['owner'] == args.owner and session['state'] == 'ready'
    assert all(session[key] == reference['session'][key]
               for key in ('owner', 'game_pid', 'game_identity', 'session_file'))
    assert reference['completed'] and reference['source_unchanged'] and not reference['cleanup_errors']
    assert reference['camera_calibration']['passed']
    case = reference['cases'][0]
    assert case['id'] == 'orientation.frame_f2_r1' and case['native_reference']['restored']
    rows = case['native_reference']['prepare']['rows']
    source_rows = {row['label']: row for row in reference['captures']}
    camera = source_rows[case['id'] + '_full_shown']['camera']
    plain = case['source']['targets']['plain']
    origin = tuple(rows[0]['position'][axis] - plain[axis] for axis in range(3))
    os.environ.update(MCDEV_ALLOW_USER_FOREGROUND='1', MCDEV_SESSION_FILE=session['session_file'],
                      MCDEV_OWNER=args.owner, MCDEV_MCP_URL=session['mcp_url'])
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'schema': 1, 'completed': False, 'production_qualified': False, 'session': session,
              'source_reference': {'path': str(args.reference.resolve()),
                                   'sha256': hashlib.sha256(args.reference.read_bytes()).hexdigest()},
              'camera_calibration': reference['camera_calibration'], 'camera': camera,
              'case': case['source'], 'origin': origin, 'captures': [], 'cleanup_errors': [],
              'offsets_pixels':args.offsets,
              'launch_sources': snapshot_sources(Path(session['project'])),
              'host_tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report['host_sources'] = {str(path.relative_to(ROOT)).replace('\\', '/'):
        hashlib.sha256(path.read_bytes()).hexdigest() for path in (Path(__file__),
        ROOT/'tools/item_sprite_native_reference.py', ROOT/'tools/run_visible_items_r16.py',
        ROOT/'tools/run_item_sprite_product.py', ROOT/'tools/item_sprite_capture_contract.py',
        ROOT/'tools/capture_native_window.py', ROOT/'tools/verify_debug_blueprints.py',
        ROOT/'tools/context_test_environment.py', ROOT/'tools/audit_chest_occupied_runtime.py',
        ROOT/'.agents/skills/pyreact-debugging/scripts/mcdk.py',
        ROOT/'.agents/skills/pyreact-debugging/scripts/_session.py')}
    report['launch_sources_sha256'] = snapshot_digest(report['launch_sources'])
    assert report['launch_sources'] == reference['launch_sources']
    installed = environment_saved = profile_saved = native_pending = False
    def persist():
        (output / 'report.json').write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    with Client(timeout=20) as client:
        check = BlueprintCheck(client, output / 'blueprints.json', 45)
        def server(code):
            result = client.call('execute_code', {'is_client': False, 'direct_return': True, 'code':
                "import mod.server.extraServerApi as api\nplayers=api.GetPlayerList()\nassert len(players)==1\n"
                "from modern_projection.server_system import WorldAdapter\nadapter=WorldAdapter(players[0])\n" + code})
            if result.get('isError'):
                raise RuntimeError(result)
            value = return_value(result)
            return json.loads(value) if isinstance(value, str) else value
        def world():
            return check.wait('edge world ready', lambda row: row['active'] and not row['preparing']
                              and not row['pending'] and not row['error'], lambda: check.run(WORLD_STATE))
        def sample(label, native=False):
            assert process_identity(session['game_pid']) == session['game_identity']
            process = process_snapshot(session['game_pid'])
            assert process['handles'] < 250000, 'Handle budget reached'
            state = check.run(WORLD_STATE) if native else world()
            before = check.run(CAMERA)
            image = capture(session['session_file'], args.owner, output / (label + '.png'), args.wgc)
            after = check.run(CAMERA)
            assert camera_matches(before, camera) and camera_matches(after, camera), 'Camera drift'
            report['captures'].append({'label': label, 'capture': image, 'state': state,
                                       'camera': before, 'camera_after': after, 'process': process})
            persist()
        def item_offset(pixels):
            receipt = check.run("owners=getattr(b.projection_liquid,'companions',(b.projection_liquid,))\n"
                "item=[owner for owner in owners if owner.__class__.__name__=='ItemProjection'][0]\n"
                "observed=[]\nfor record in item.renderer.active.values():\n"
                " base=item.renderer.center(record['anchor'],record['group'].origin)\n"
                " position=(base[0],base[1],base[2]-%r/16.)\n" % pixels +
                " changed=item.renderer.model.SetFreeModelPos(record['model_id'],*position)\n"
                " observed.append({'model_id':record['model_id'],'base':base,'requested':position,'returned':changed})\n"
                "assert observed and all(row['returned'] for row in observed)\n_result=observed")
            report.setdefault('offset_receipts', []).append({'pixels_toward_viewer': pixels, 'models': receipt})
            persist()
            time.sleep(.3)
        try:
            installed = True
            check.run(INSTALL_PROBE)
            report['environment'] = environment(client, ENV_SETUP)
            environment_saved = True
            profile_saved = True
            check.run("from modern_projection.projection.item_sprite_profile import candidate_profile\n"
                "assert not hasattr(sys,'_item_edge_profile')\nsys._item_edge_profile=s.item_profile\n"
                "s.item_profile=candidate_profile('3.10.0.420447')\n"
                "from modern_projection.projection.debug_item_blueprints import orientation_document\n"
                "s._loaded(orientation_document('frame_f2_r1'))\ns.editor.layer=0\ns.display_mode('full')\n"
                "s.grid=False\ns.origin=%r\ns.opacity=1.\ns.projection_missing=False\ns.projection_outline=False\n"
                "b.project()\n_result=True" % (origin,))
            world()
            check.run("if navigator.top is not None:navigator.pop()\n_result=True")
            check.wait('workspace closed', lambda row: not row['open'] and not row['transition'], check.navigation)
            check.run("cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n"
                "cam.LockModCameraPitch(True)\ncam.LockModCameraYaw(True)\n"
                "assert cam.SetCameraPos(%r)\nassert cam.SetCameraRotation(%r)\n_result=True" %
                (tuple(camera['position']), tuple(camera['rotation'])))
            item_offset(0.)
            sample('baseline_shown')
            check.run(WORLD_HIDE)
            try:
                time.sleep(.2)
                sample('baseline_hidden')
            finally:
                check.run(WORLD_SHOW)
            for offset in args.offsets:
                item_offset(offset)
                sample('offset_' + str(offset))
            item_offset(0.)
            report['body_move'] = check.run("assert not hasattr(sys,'_item_edge_bodies')\n"
                "entities=set(b.projection_entities.values())\n"
                "if b.entity:entities.add(b.entity)\n"
                "sys._item_edge_bodies=[]\n"
                "for entity in entities:\n"
                " pos=b.factory.CreatePos(entity)\n old=pos.GetPos()\n"
                " assert old is not None\n sys._item_edge_bodies.append((entity,old))\n"
                " assert pos.SetPosForClientEntity((old[0]+1024.,old[1],old[2]))\n"
                "assert sys._item_edge_bodies\n_result=sys._item_edge_bodies")
            time.sleep(.3)
            sample('body_hidden_item_shown')
            check.run(WORLD_HIDE)
            try:
                time.sleep(.2)
                sample('body_hidden_item_hidden')
            finally:
                check.run(WORLD_SHOW)
            report['body_restore'] = check.run("observed=[]\nfor entity,old in sys._item_edge_bodies:\n"
                " pos=b.factory.CreatePos(entity)\n returned=pos.SetPosForClientEntity(old)\n"
                " observed.append({'entity':entity,'requested':old,'actual':pos.GetPos(),'returned':returned})\n"
                "assert all(row['returned'] and max(abs(row['requested'][axis]-row['actual'][axis]) "
                "for axis in range(3))<.002 for row in observed)\n"
                "del sys._item_edge_bodies\n_result=observed")
            time.sleep(.3)
            sample('baseline_restored')
            check.run('b.stop_projection()\n_result=True')
            native_pending = True
            platform = case['native_reference']['prepare']['player_placement']['platform']
            report['native_prepare'] = server(PREPARE % (rows, platform))
            check.run("cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n"
                "cam.LockModCameraPitch(True)\ncam.LockModCameraYaw(True)\n"
                "assert cam.SetCameraPos(%r)\nassert cam.SetCameraRotation(%r)\n_result=True" %
                (tuple(camera['position']), tuple(camera['rotation'])))
            position = tuple(rows[0]['position'])
            read = ("from modern_projection.projection.nbt_spatial import root_payload,scalar,field_key\n"
                "root=root_payload(b.factory.CreateBlockInfo(b.level).GetBlockEntityData(%r))\n"
                "item=root_payload(root.get(field_key(root,'Item'))) if root else None\n"
                "_result={'root':root,'name':scalar(item,'Name') if item else None}" % (position,))
            check.wait('native empty', lambda row: bool(row['root']) and not row['name'], lambda: check.run(read))
            time.sleep(.3)
            sample('native_hidden_before', True)
            report['native_fill'] = server(FILL)
            report['native_client'] = check.wait('native item', lambda row: row['name'] == 'minecraft:diamond_sword',
                                                 lambda: check.run(read))
            time.sleep(.3)
            sample('native_shown', True)
            server(HIDE_CLEAR)
            server(HIDE_PLACE)
            check.wait('native cleared', lambda row: bool(row['root']) and not row['name'], lambda: check.run(read))
            time.sleep(.3)
            sample('native_hidden_after', True)
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            report['traceback'] = traceback.format_exc()
        finally:
            if native_pending:
                try:
                    report['native_restore'] = server(NATIVE_RESTORE)
                except Exception as error:
                    report['cleanup_errors'].append('native restore: ' + str(error))
            actions = [('owned body restore', "if hasattr(sys,'_item_edge_bodies'):\n"
                " for entity,old in sys._item_edge_bodies:assert b.factory.CreatePos(entity).SetPosForClientEntity(old)\n"
                " del sys._item_edge_bodies\n_result=True"),
                ('stop projection', 'b.stop_projection()\ncam=b.factory.CreateCamera(b.level)\n'
                 'cam.ResetCameraPos()\ncam.LockModCameraPitch(False)\ncam.LockModCameraYaw(False)\ncam.UnDepartCamera()\n_result=True')]
            if profile_saved:
                actions.append(('profile restore', 's.item_profile=sys._item_edge_profile\ndel sys._item_edge_profile\n_result=True'))
            if installed:
                actions.append(('blueprint restore', RESTORE))
            for label, code in actions:
                try:
                    check.run(code)
                except Exception as error:
                    report['cleanup_errors'].append(label + ': ' + str(error))
            if environment_saved:
                try:
                    report['environment_restore'] = environment(client, ENV_RESTORE)
                except Exception as error:
                    report['cleanup_errors'].append('environment restore: ' + str(error))
            report['sources_after'] = snapshot_sources(Path(session['project']))
            report['source_unchanged'] = report['launch_sources'] == report['sources_after']
            persist()
    print(json.dumps({key: report.get(key) for key in ('completed', 'source_unchanged', 'cleanup_errors')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wgc', type=Path, required=True)
    parser.add_argument('--offsets',type=float,nargs='+',default=[.5,1.,1.5])
    args=parser.parse_args()
    if len(args.offsets)>8 or len(set(args.offsets))!=len(args.offsets) or not all(0.<value<=1.5 for value in args.offsets):
        parser.error('Use at most eight unique finite offsets in (0,1.5] model pixels')
    run(args)
