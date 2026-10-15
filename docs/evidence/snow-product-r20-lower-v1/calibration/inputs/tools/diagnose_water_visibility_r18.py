"""Separate free-model bounds, entity distance and player context in an owned world."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback


STATE = '''renderer=liquid.renderer
render=b.factory.CreateActorRender(api.GetLocalPlayerId())
cam=b.factory.CreateCamera(b.level)
_result=json.dumps({'projection_type':type(liquid).__name__,'renderer_type':type(renderer).__name__,
 'default_bounding_box':renderer.BOUNDING_BOX,
 'active_count':len(renderer.active),'staging_count':len(renderer.staging),'retired_count':len(renderer.retired),
 'player_foot':b.factory.CreatePos(api.GetLocalPlayerId()).GetFootPos(),
 'camera':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'entity_render_distance':render.GetEntityRenderDistance(),
 'block_render_distance':b.factory.CreateBlockInfo(b.level).GetBlockRenderDistance(),
 'models':[{'id':record['model_id'],'center':renderer.center(record['anchor'],record['group'].origin),
 'visible':record['visible'],'uniforms':[renderer.model.GetExtraUniformValue(record['model_id'],index)
 for index in (1,2,3,4)]} for record in renderer.active.values()]})
'''
PLAYER = '''import json
import mod.server.extraServerApi as api
player=api.GetPlayerList()[0]
comp=api.GetEngineCompFactory().CreatePos(player)
assert comp.SetFootPos(%r)
_result=json.dumps({'foot':comp.GetFootPos()})
'''


def server(client, code, value):
    result = client.call('execute_code', {'code': code, 'is_client': False, 'direct_return': True})
    if result.get('isError'):
        raise RuntimeError(result)
    observed = value(result)
    return json.loads(observed) if isinstance(observed, str) else observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--capture-exe', required=True, type=Path)
    parser.add_argument('--launch-inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--origin', nargs=3, type=int, default=(63, -61, 3))
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh diagnostic evidence')
    project = args.project.resolve(strict=True)
    sys.path.insert(0, str(project / 'tools'))
    import probe_product_water as probe
    from _session import load_session
    from mcdk import return_value
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)),
                      MCDEV_OWNER=args.owner, MCDEV_ALLOW_USER_FOREGROUND='1')
    bound = load_session(args.session, args.owner, live=True)
    if Path(bound['project']).resolve() != project:
        parser.error('Project differs from the bound session')
    before = probe.snapshot_sources(project)
    launch = json.loads(args.launch_inputs.read_bytes())
    if before != launch.get('source_sha256'):
        parser.error('Project changed after its frozen launch inputs')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = {'schema': 1, 'diagnostic_only': True, 'product_admission_performed': False,
              'completed': False, 'restored': False, 'cleanup_errors': [], 'captures': {},
              'session_id': bound['id'], 'project': str(project), 'origin': args.origin,
              'launch_contract_sha256': launch['source_contract_sha256'],
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'phases': {}}
    with probe.base.Client(timeout=45) as client:
        check = probe.blueprints.BlueprintCheck(client, args.output, 45.)
        installed = visual_saved = profile_saved = False
        saved_foot = distance = None
        try:
            check.run(probe.blueprints.INSTALL_PROBE)
            installed = True
            check.run(probe.PROFILE % (True, True))
            profile_saved = True
            check.run(probe.visuals.SAVE_VISUAL)
            visual_saved = True
            check.run(probe.LOAD % (('pool', 'wet', (35., 25., 4.6)),))
            origin = tuple(args.origin)
            check.run('s.origin=%r\ns.opacity=1.\ns.projection_missing=False\nb.project()\n_result=True' % (origin,))
            report['ready'] = check.wait('world water ready', probe.workspace.world_ready,
                                         lambda: check.run(probe.WORLD_STATE))
            target = tuple(axis + 3.5 for axis in origin)
            report['camera_requested'] = check.run(probe.CAMERA % ((target, (3., 2.5, 4.)),))
            initial = check.run(probe.workspace.WATER_OWNER + STATE)
            assert initial['projection_type'] == 'ProductLiquidProjection', initial
            assert initial['renderer_type'] == 'ProductWorldLiquidRenderer', initial
            assert initial['default_bounding_box'] == [[-4.] * 3, [4.] * 3], initial
            check.run(probe.workspace.WATER_OWNER + 'sys._r18_visibility_owner=liquid\n_result=True')
            saved_foot, distance = tuple(initial['player_foot']), initial['entity_render_distance']

            def capture_phase(name):
                report['phases'][name] = check.run(probe.workspace.WATER_OWNER + STATE)
                for shown in (False, True):
                    check.run(probe.workspace.WATER_OWNER +
                              'assert liquid.renderer.set_visible(%r)\n_result=True' % shown)
                    time.sleep(.4)
                    label = name + ('_wet' if shown else '_hidden')
                    path = args.output.with_name(args.output.stem + '_' + label + '.png')
                    report['captures'][label] = probe.base.capture(args.session, args.owner,
                                                                   path, args.capture_exe)
                report['phases'][name]['after'] = check.run(probe.workspace.WATER_OWNER + STATE)
                probe.base.write(args.output, report)

            def restore_fixture_camera():
                check.run(probe.CAMERA % ((target, (3., 2.5, 4.)),))
                return check.wait('fixed fixture camera after player move',
                    lambda row: (max(abs(row['camera'][i] - initial['camera'][i]) for i in range(3)) < .05
                                 and max(abs((row['rotation'][i] - initial['rotation'][i] + 180.) % 360. - 180.)
                                         for i in range(3)) < .1),
                    lambda: check.run(probe.workspace.WATER_OWNER + STATE))

            capture_phase('baseline')
            for bound in (2., 4., 8., 16., 32., 64.):
                check.run(probe.workspace.WATER_OWNER + '''for record in liquid.renderer.active.values():
 assert liquid.renderer.model.SetFreeModelBoundingBox(record['model_id'],(-%r,)*3,(%r,)*3)
_result=True''' % (bound, bound))
                capture_phase('bounds_%g' % bound)
            check.run(probe.workspace.WATER_OWNER + '''for record in liquid.renderer.active.values():
 assert liquid.renderer.model.SetFreeModelBoundingBox(record['model_id'],(-64.,)*3,(64.,)*3)
_result=True''')
            capture_phase('large_bounds')
            check.run('assert b.factory.CreateActorRender(api.GetLocalPlayerId()).SetEntityRenderDistance(1024.)\n_result=True')
            capture_phase('entity_distance_1024')
            check.run(probe.workspace.WATER_OWNER + '''for record in liquid.renderer.active.values():
 assert liquid.renderer.model.SetFreeModelBoundingBox(record['model_id'],*liquid.renderer.BOUNDING_BOX)
_result=True''')
            check.run('assert b.factory.CreateActorRender(api.GetLocalPlayerId()).SetEntityRenderDistance(%r)\n_result=True' % distance)
            near = (float(origin[0]) + 2.5, saved_foot[1], float(origin[2]) + 2.5)
            report['player_moved_near'] = server(client, PLAYER % (near,), return_value)
            check.wait('near player replicated', lambda row: max(abs(row['player_foot'][i] - near[i])
                for i in range(3)) < .1, lambda: check.run(probe.workspace.WATER_OWNER + STATE))
            report['near_camera_restored'] = restore_fixture_camera()
            capture_phase('player_near')
            report['player_moved_back'] = server(client, PLAYER % (saved_foot,), return_value)
            check.wait('original player replicated', lambda row: max(abs(row['player_foot'][i] - saved_foot[i])
                for i in range(3)) < .1, lambda: check.run(probe.workspace.WATER_OWNER + STATE))
            report['far_camera_restored'] = restore_fixture_camera()
            capture_phase('player_far_return')
            report['completed'] = True
        except Exception:
            report['error'] = traceback.format_exc()
            raise
        finally:
            cleanup = []
            if saved_foot is not None:
                cleanup.append(('player', lambda: server(client, PLAYER % (saved_foot,), probe.base.return_value)))
            if distance is not None:
                cleanup.append(('distance', lambda: check.run('assert b.factory.CreateActorRender(api.GetLocalPlayerId()).SetEntityRenderDistance(%r)\n_result=True' % distance)))
            if installed:
                cleanup.append(('stop_projection', lambda: check.run('b.stop_projection()\n_result=True')))
                cleanup.append(('owner_cleanup', lambda: check.run('''row=None
if hasattr(sys,'_r18_visibility_owner'):
 liquid=sys._r18_visibility_owner
 renderer=liquid.renderer
 row={'closed':liquid.closed,'renderer_closed':renderer.closed,'active':len(renderer.active),
  'staging':len(renderer.staging),'retired':len(renderer.retired),'cleanup_errors':renderer.cleanup_errors}
 del sys._r18_visibility_owner
_result=json.dumps(row)''')))
            if visual_saved:
                cleanup.append(('camera', lambda: check.run(probe.visuals.camera_restore_code(False))))
                cleanup.append(('view', lambda: check.run("saved=sys._blueprint_visual_saved\ns.origin=saved['origin'];s.opacity=saved['opacity'];s.projection_missing=saved['missing'];s.projection_outline=saved['outline']\ndel sys._blueprint_visual_saved\n_result=True")))
            if profile_saved:
                cleanup.append(('profile_workspace', lambda: check.run(probe.RESTORE_PROFILE)))
            elif installed:
                cleanup.append(('workspace', lambda: check.run(probe.blueprints.RESTORE)))
            for label, restore in cleanup:
                try:
                    report[label + '_restore'] = restore()
                except (ValueError, RuntimeError, OSError, TimeoutError) as error:
                    report['cleanup_errors'].append({'phase': label, 'error': str(error)})
            retired_owner = report.get('owner_cleanup_restore')
            if retired_owner is not None and (not retired_owner['closed'] or not retired_owner['renderer_closed']
                    or any(retired_owner[key] for key in ('active', 'staging', 'retired', 'cleanup_errors'))):
                report['cleanup_errors'].append({'phase': 'owner_cleanup', 'state': retired_owner})
            report['restored'] = not report['cleanup_errors']
            report['source_unchanged'] = before == probe.snapshot_sources(project)
            probe.base.write(args.output, report)
    print(json.dumps({key: report[key] for key in ('completed', 'restored', 'source_unchanged')}))


if __name__ == '__main__':
    main()
