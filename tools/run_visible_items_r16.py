"""Owner-bound native captures of public item and content-slot fixtures."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from capture_native_window import capture
from verify_debug_blueprints import BlueprintCheck, INSTALL_PROBE, RESTORE
from context_test_environment import run as environment, SETUP as ENV_SETUP, RESTORE as ENV_RESTORE
from item_sprite_capture_contract import snapshot_sources, snapshot_digest, camera_matches, scene_layout, paired_layout_matches
from item_sprite_calibration import calibrate
from item_sprite_closeup import run as closeup
from audit_chest_occupied_runtime import process_snapshot
from _session import process_identity
from run_item_sprite_product import STATE, CAMERA
from item_sprite_native_reference import (PREPARE as NATIVE_PREPARE, FILL as NATIVE_FILL,
                                         HIDE_CLEAR as NATIVE_CLEAR, HIDE_PLACE as NATIVE_PLACE,
                                         RESTORE as NATIVE_RESTORE)

WORLD_STATE = '''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,)) if companion else ()
items=[item for item in owners if item.__class__.__name__=='ItemProjection']
_result=json.dumps({'active':s.projection_active,'preparing':bool(b.preparing_entity),
 'slots':sum(int(row['group'].uniforms[3][1]) for item in items for row in item.renderer.active.values()),
 'pending':bool(b.projection_occupancy and b.projection_occupancy.pending_pair),
 'error':str((companion.error or companion.renderer.error) or '') if companion else '',
 'groups_data':[{'origin':row['group'].origin,'model':row['group'].model_name,
 'visible':row['visible'],'uniforms':row['group'].uniforms}
 for item in items for row in item.renderer.active.values()]})
'''
EDITOR_HIDE = '''assert not hasattr(sys,'_visible_items_muted')
sys._visible_items_muted=(s.item_controls,s.item_controls.closed,
 [(entry['renderer'],tuple(entry['renderer'].visible)) for entry in s.item_controls.registry.values()])
s.item_controls.closed=True
for renderer,visible in sys._visible_items_muted[2]:
 for slot in (0,1):renderer._show(slot,False)
_result=True
'''
EDITOR_SHOW = '''controls,closed,rows=sys._visible_items_muted
for renderer,visible in rows:
 for slot in (0,1):renderer._show(slot,visible[slot])
controls.closed=closed
del sys._visible_items_muted
_result=True
'''
WORLD_HIDE = '''companion=b.projection_liquid
owners=getattr(companion,'companions',(companion,))
items=[item for item in owners if item.__class__.__name__=='ItemProjection']
assert len(items)==1 and not hasattr(sys,'_visible_items_world_muted')
sys._visible_items_world_muted=items[0]
assert items[0].renderer.set_visible(False)
_result=True
'''
WORLD_SHOW = '''assert sys._visible_items_world_muted.renderer.set_visible(True)
del sys._visible_items_world_muted
_result=True
'''


def run(args):
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    session = json.loads(args.session.read_bytes())
    assert session['owner'] == args.owner and session['state'] == 'ready'
    project = Path(session['project'])
    report = {'schema': 1, 'completed': False, 'production_qualified': False,
              'engine': '3.10.0.420447', 'session': session, 'captures': [], 'cases': [],
              'cleanup_errors': [], 'launch_sources': snapshot_sources(project)}
    report['launch_sources_sha256'] = snapshot_digest(report['launch_sources'])
    report['host_tool_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['process_samples']=[]
    report['profile_mode']='production' if args.production_profile else 'candidate'
    def save(name, value):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    def persist():
        save('report.json', report)
    installed = environment_saved = profile_saved = False
    with Client(timeout=20) as client:
        check = BlueprintCheck(client, output / 'blueprints.json', 45)
        def server(code):
            response = client.call('execute_code', {'is_client': False, 'direct_return': True, 'code':
                "import mod.server.extraServerApi as api\nplayers=api.GetPlayerList()\nassert len(players)==1\n"
                "from modern_projection.server_system import WorldAdapter\nadapter=WorldAdapter(players[0])\n"+code})
            if response.get('isError'):
                raise RuntimeError(response)
            value = return_value(response)
            return json.loads(value) if isinstance(value,str) else value
        def state():
            return check.wait('item controls ready', lambda row: row['plan_ready'] and
                              not row['pending'] and not row['error'], lambda: check.run(STATE))
        def world_state():
            return check.wait('world items ready', lambda row: row['active'] and
                              not row['preparing'] and not row['pending'] and not row['error'],
                              lambda: check.run(WORLD_STATE))
        def sample(label, route):
            before = ((check.run(STATE) if label == 'testing_page' else state()) if route == 'editor'
                      else check.run(WORLD_STATE) if route == 'native' else world_state())
            camera = check.run(CAMERA) if route != 'editor' else None
            started = time.monotonic()
            image = capture(session['session_file'], args.owner, output / (label + '.png'), args.wgc)
            after = ((check.run(STATE) if label == 'testing_page' else state()) if route == 'editor'
                     else check.run(WORLD_STATE) if route == 'native' else world_state())
            camera_after = check.run(CAMERA) if camera else None
            if route == 'editor':
                assert scene_layout(before) == scene_layout(after), 'Editor layout drift'
            else:
                assert camera_matches(camera, camera_after), ('World camera drift',label,camera,camera_after)
            row = {'label': label, 'route': route, 'capture': image, 'state': before,
                   'state_after': after, 'camera': camera, 'camera_after': camera_after,
                   'started': started, 'finished': time.monotonic()}
            report['captures'].append(row)
            persist()
            return image
        def triplet(label, route):
            hide, show = (EDITOR_HIDE, EDITOR_SHOW) if route == 'editor' else (WORLD_HIDE, WORLD_SHOW)
            check.run(hide)
            try:
                time.sleep(.2)
                sample(label + '_hidden_before', route)
            finally:
                check.run(show)
            time.sleep(.2)
            sample(label + '_shown', route)
            check.run(hide)
            try:
                time.sleep(.2)
                sample(label + '_hidden_after', route)
            finally:
                check.run(show)
        try:
            check.run(INSTALL_PROBE)
            installed = True
            report['environment'] = environment(client, ENV_SETUP)
            environment_saved = True
            report['resource_contract']=check.run(
                'from modern_projection.projection import item_icon_data\n'
                '_result={"resource_sha256":item_icon_data.RESOURCE_SHA256,"layout_version":item_icon_data.LAYOUT_VERSION}')
            if args.production_profile:
                check.run('assert s.item_profile is not None and s.item_profile.engine_version=="3.10.0.420447"\n_result=True')
            else:
                check.run("from modern_projection.projection.item_sprite_profile import candidate_profile\n"
                          "assert not hasattr(sys,'_visible_items_profile')\n"
                          "sys._visible_items_profile=s.item_profile\n"
                          "s.item_profile=candidate_profile('3.10.0.420447')\n_result=True")
                profile_saved = True
            report['camera_calibration'] = calibrate(check, session, args.owner, output, args.wgc, save)
            if report['camera_calibration']['cleanup_errors']:
                raise RuntimeError('Camera calibration cleanup failed')
            check.capture = lambda label, tree=None: sample(label, 'editor')
            check.page()
            check.fixture('test.entities.item_contents')
            compiler_lines = Path(session['log']).read_text(encoding='utf8', errors='replace').splitlines()
            report['native_item_shader_errors'] = [line for line in compiler_lines
                if 'Compiler error shaders/glsl/modern_projection_item_icon' in line]
            assert not report['native_item_shader_errors'], report['native_item_shader_errors']
            if not args.skip_closeup:
                closeup(check, client, session, report, STATE, CAMERA, output, args.wgc,
                        save, native_reference=True, native_player_near=True, compact=args.compact_closeup)
            cases = check.run('from modern_projection.projection.debug_item_blueprints import CATALOGUE_CASES\n'
                             '_result=[dict(row,fixture=identity) for identity,rows in CATALOGUE_CASES.items() for row in rows]')
            wanted = set(args.names.split(','))
            cases = [row for row in cases if row['item'][1] == 0 and row['item'][0].split(':')[-1] in wanted]
            assert len(cases) == len(wanted), (len(cases), wanted)
            matrix = [('icon.' + row['item'][0].split(':')[-1], row) for row in cases]
            if not args.icons_only:
                matrix += [(value, None) for value in ('shelf.center', 'shelf.three', 'campfire.one', 'campfire.four')]
            if args.orientation_matrix:
                poses=check.run('from modern_projection.projection.debug_item_blueprints import ORIENTATION_CASES,ORIENTATION_IDENTITY\n'
                               '_result=[dict(row,fixture=ORIENTATION_IDENTITY,item=("minecraft:diamond_sword",0)) for row in ORIENTATION_CASES]')
                selected=set(args.orientation_cases.split(',')) if args.orientation_cases else None
                matrix=[('orientation.'+row['id'],row) for row in poses if selected is None or row['id'] in selected]
                if selected is not None:
                    assert len(matrix)==len(selected), 'Unknown orientation cases'
            report['requested_cases']=[case_id for case_id,source in matrix]
            if args.closeup_only:
                assert not args.skip_closeup
                matrix=[]
                report['requested_cases']=[]
            for case_id, source in matrix:
                if process_identity(session['game_pid'])!=session['game_identity']:
                    raise RuntimeError('Owned process identity changed')
                process=process_snapshot(session['game_pid'])
                report['process_samples'].append(dict(process,case=case_id,phase='before'))
                if process['handles']>=args.maximum_handles:
                    report['stopped_at_handle_budget']=True
                    break
                is_slot = source is None
                is_orientation = not is_slot and 'facing' in source
                doc_code = ("from modern_projection.projection.debug_item_blueprints import slot_document\n"
                            "doc=slot_document(%r)\n" % case_id if is_slot else
                            "from modern_projection.projection.debug_item_blueprints import orientation_document\n"
                            "doc=orientation_document(%r)\n" % source['id'] if is_orientation else
                            "from modern_projection.projection.debug_item_blueprints import catalogue_document\n"
                            "doc=catalogue_document(%r,%r)\n" % (source['fixture'], source['id']))
                pose = (35.,25.,3.5) if is_slot else (180.,0.,3.5)
                face=source['facing'] if is_orientation else 2
                normal=((0,-1,0),(0,1,0),(0,0,-1),(0,0,1),(-1,0,0),(1,0,0))[face]
                local_plain,local_enchanted=((3,3,2),(3,3,5)) if face in (4,5) else ((2,3,3),(5,3,3))
                if not is_orientation:
                    local_plain,local_enchanted=(2,3,2),(5,3,2)
                if is_orientation:
                    pose=((180.,-85.,3.5),(180.,85.,3.5),(180.,0.,3.5),(0.,0.,3.5),
                          (270.,0.,3.5),(90.,0.,3.5))[face]
                    source['targets']={'plain':local_plain,'enchanted':local_enchanted}
                if args.view_angle:
                    assert not is_slot and face==2, 'Oblique captures require north-facing frame contents'
                    pose=(pose[0]+args.view_angle,pose[1],pose[2])
                    source['view_angle_degrees']=args.view_angle
                fixture = check.run(doc_code + 's._loaded(doc)\ns.editor.layer=0\ns.display_mode("full")\n'
                                    's.grid=False\ns.camera_view(*%r)\nowner.open_workspace()\n'
                                    '_result={"size":doc.size,"name":doc.name,"blocks":len(doc.blocks)}' % (pose,))
                check.wait('workspace open', lambda row: row['open'] and not row['transition'], check.navigation)
                stable_sample = [state(),0]
                def settled_layout(row):
                    stable_sample[1] = stable_sample[1]+1 if paired_layout_matches(row,stable_sample[0]) else 0
                    stable_sample[0] = row
                    return stable_sample[1]>=3
                check.wait('stable item control layout',settled_layout,state)
                report['cases'].append({'id': case_id, 'source': source, 'document': fixture})
                triplet(case_id + '_editor', 'editor')
                center = (3.5,3.5,3.5) if is_slot else (4.8,3.5,2.9375)
                offset = ((0.,1.,5.) if case_id.startswith('shelf') else (-3.,3.,-4.)) if is_slot else (0.,1.,-8.)
                if not is_slot:
                    distance=args.near_distance
                    if is_orientation:
                        lateral=2 if face in (4,5) else 0
                        center=tuple((local_plain[axis]+local_enchanted[axis])/2.+.5-normal[axis]*.4375+
                                     (.8 if axis==lateral else 0.) for axis in range(3))
                        offset=tuple(normal[axis]*distance+(-1. if face in (0,1) and axis==2 else
                                     .5 if face not in (0,1) and axis==1 else 0.) for axis in range(3))
                    else:
                        offset=(0.,1.,-distance)
                    if args.view_angle:
                        angle=math.radians(args.view_angle)
                        offset=(math.sin(angle)*distance,offset[1],-math.cos(angle)*distance)
                camera = check.run('foot=b.player_origin()\ns.origin=(foot[0]+5,foot[1]+18,foot[2]+5)\n'
                                  's.opacity=1.\ns.projection_missing=False\ns.projection_outline=False\nb.project()\n_result=s.origin')
                world_state()
                check.run('navigator.pop()\n_result=True')
                check.wait('workspace closed', lambda row: not row['open'] and not row['transition'], check.navigation)
                check.run('cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n'
                          'target=tuple(s.origin[axis]+%r[axis] for axis in range(3))\n'
                          'point=tuple(target[axis]+%r[axis] for axis in range(3))\n'
                          'rot=api.GetRotFromDir(tuple(target[axis]-point[axis] for axis in range(3)))\n'
                          'cam.SetCameraPos(point)\ncam.SetCameraRotation((rot[0],rot[1]+180.,0.))\n_result=True' % (center,offset))
                time.sleep(.6)
                triplet(case_id + '_full', 'full')
                check.run('b.toggle_missing()\n_result=True')
                world_state()
                triplet(case_id + '_missing', 'missing')
                if not is_slot:
                    origin = tuple(camera)
                    position = tuple(origin[axis]+local_plain[axis] for axis in range(3))
                    rows = [{'mode':'plain', 'position':position,
                             'support':tuple(position[axis]-normal[axis] for axis in range(3)),
                             'rotation':source['rotation_degrees'] if is_orientation else 0.,
                             'frame_name':'minecraft:'+source['source_case'].removesuffix('_filled') if is_orientation else 'minecraft:frame',
                             'face':face}]
                    native_camera = check.run(CAMERA)
                    platform = (math.floor(native_camera['position'][0]), position[1]-1,
                                math.floor(native_camera['position'][2]))
                    check.run('b.stop_projection()\n_result=True')
                    pending = True
                    native = {'source_case':source, 'restored':False}
                    report['cases'][-1]['native_reference'] = native
                    try:
                        native['prepare'] = server(NATIVE_PREPARE % (rows,platform))
                        check.run('cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n'
                                  'assert cam.SetCameraPos(%r)\nassert cam.SetCameraRotation(%r)\n_result=True' %
                                  (tuple(native_camera['position']),tuple(native_camera['rotation'])))
                        position_code = repr(position)
                        read = ('from modern_projection.projection.nbt_spatial import root_payload,scalar,field_key\n'
                                'root=root_payload(b.factory.CreateBlockInfo(b.level).GetBlockEntityData(%s))\n'
                                'item=root_payload(root.get(field_key(root,"Item"))) if root else None\n'
                                '_result={"root":root,"name":scalar(item,"Name") if item else None}' % position_code)
                        check.wait('native empty frame replicated',lambda row: bool(row['root']),lambda:check.run(read))
                        time.sleep(.3)
                        sample(case_id+'_native_hidden_before','native')
                        native['fill'] = server(NATIVE_FILL.replace('minecraft:diamond_sword',source['item'][0]))
                        native['client'] = check.wait('native item replicated',
                            lambda row: row['name']==source['item'][0],lambda:check.run(read))
                        time.sleep(.3)
                        sample(case_id+'_native_shown','native')
                        server(NATIVE_CLEAR)
                        server(NATIVE_PLACE)
                        check.wait('native cleared frame replicated',lambda row: bool(row['root']) and not row['name'],
                                   lambda:check.run(read))
                        time.sleep(.3)
                        sample(case_id+'_native_hidden_after','native')
                    finally:
                        if pending:
                            native['restore'] = server(NATIVE_RESTORE)
                            native['restored'] = native['restore']['passed']
                            persist()
                check.run('b.stop_projection()\ncam=b.factory.CreateCamera(b.level)\n'
                          'cam.ResetCameraPos()\ncam.UnDepartCamera()\nowner.open_workspace()\n_result=True')
                report['process_samples'].append(dict(process_snapshot(session['game_pid']),case=case_id,phase='after'))
                report['cases'][-1]['measurement_completed']=True
                persist()
            completed_cases={case['id'] for case in report['cases'] if case.get('measurement_completed')}
            report['remaining_cases']=[case_id for case_id,source in matrix if case_id not in completed_cases]
            report['matrix_completed']=not report['remaining_cases']
            report['logs'] = client.call('get_latest_error_logs', {'max_count': 60})
            compiler_lines = Path(session['log']).read_text(encoding='utf8', errors='replace').splitlines()
            report['native_item_shader_errors'] = [line for line in compiler_lines
                if 'Compiler error shaders/glsl/modern_projection_item_icon' in line]
            assert not report['native_item_shader_errors'], report['native_item_shader_errors']
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
            report['traceback'] = traceback.format_exc()
        finally:
            for label, code in (
                    ('stop projection', 'b.stop_projection()\ncam=b.factory.CreateCamera(b.level)\n'
                     'cam.ResetCameraPos()\ncam.UnDepartCamera()\n_result=True'),
                    ('blueprint restore', RESTORE if installed else ''),
                    ('profile restore', 's.item_profile=sys._visible_items_profile\n'
                     'del sys._visible_items_profile\n_result=True' if profile_saved else '')):
                if code:
                    try:
                        check.run(code)
                    except Exception as error:
                        report['cleanup_errors'].append(label + ': ' + str(error))
            if environment_saved:
                try:
                    report['environment_restored'] = environment(client, ENV_RESTORE)
                except Exception as error:
                    report['cleanup_errors'].append('environment restore: ' + str(error))
            report['sources_after'] = snapshot_sources(project)
            report['source_unchanged'] = report['sources_after'] == report['launch_sources']
            persist()
    print(json.dumps({key: report.get(key) for key in ('completed','error','cleanup_errors')}, ensure_ascii=True))
    return 0 if report['completed'] and not report['cleanup_errors'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--wgc', type=Path, required=True)
    parser.add_argument('--skip-closeup', action='store_true')
    parser.add_argument('--production-profile', action='store_true')
    parser.add_argument('--compact-closeup', action='store_true')
    parser.add_argument('--closeup-only', action='store_true')
    parser.add_argument('--orientation-matrix', action='store_true')
    parser.add_argument('--icons-only', action='store_true')
    parser.add_argument('--orientation-cases')
    parser.add_argument('--near-distance', type=float, default=8.)
    parser.add_argument('--view-angle', type=float, default=0.)
    parser.add_argument('--maximum-handles', type=int, default=220000)
    parser.add_argument('--names', default='diamond_sword,apple,beef,diamond_pickaxe,iron_ingot,bed,bow,bucket,bone,bread,emerald,fishing_rod')
    sys.exit(run(parser.parse_args()))
